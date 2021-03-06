"""
Copyright (c) 2010 Marian Tietz
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions
are met:

1. Redistributions of source code must retain the above copyright
   notice, this list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright
   notice, this list of conditions and the following disclaimer in the
   documentation and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE AUTHORS AND CONTRIBUTORS ``AS IS'' AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED. IN NO EVENT SHALL THE AUTHORS OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
SUCH DAMAGE.
"""

""" Purpose:
	Raw config dialog for a plugin which can save the settings
	for a given plugin and displays the options the plugin offers.

	This is used by the plugin management dialog.
"""


import gtk
import gobject
from gettext import gettext as _
import logging
import json

from .. import config
from .. import plugins
from . import psushi
from .error import TekkaError

PLUGIN_OPTIONS_LENGTH = 4

class PluginConfigDialog(gtk.Dialog):

	def __init__(self, plugin_name):
		super(PluginConfigDialog, self).__init__(
			title=_("Configure %(name)s" % {"name": plugin_name}),
			buttons=(gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE)
		)

		self.plugin_name = plugin_name
		self.plugin_options, err = plugins.get_options(plugin_name)

		if err != None:
			logging.error(err)
			gui.mgmt.show_inline_message(
				"Config dialog %s" % (plugin_name),
				"Can't load the config dialog for plugin '%s': %s" % (
					plugin_name, err),
				dtype="error")
			return


		self._data_map = {}

		self._build_interface()

		self._fill()


	def _build_interface(self):

		self.table = table = gtk.Table(
				rows=len(self.plugin_options),
				columns=2)
		table.set_property("column-spacing", 12)
		table.set_property("row-spacing", 6)

		# put another vbox arround it because
		# d.vbox.set_property("border-width",..) does not work...
		self.content_vbox = vbox = gtk.VBox()
		vbox.set_property("border-width", 12)
		vbox.pack_start(table)
		self.vbox.pack_start(vbox)

	def composit_list_widget(self, opt, label, value, dataMap):
		""" Return a widget which holds and manages a list widget """
			
		def row_content_to_entry(tv, path, column, entry):
			model = tv.get_model()
			entry.set_text(model[path][0])
			entry.grab_focus()
			model.remove(model.get_iter(path))
	
		def add_data_to_list(btn, listview, entry):
			model = listview.get_model()
			model.append(row=(entry.get_text(),))
			entry.set_text("")
	
		def delete_data_from_list(btn, listview):
			(model, iter) = listview.get_selection().get_selected()
			if iter == None:
				return
			model.remove(iter)
	
		def update_data_map(model, path, *_):
			dataMap[opt] = json.dumps([n[0] for n in model])
	
		addButton = gtk.Button(stock=gtk.STOCK_ADD)
		deleteButton = gtk.Button(stock=gtk.STOCK_REMOVE)
	
		listStore = gtk.ListStore(str)
		listRenderer = gtk.CellRendererText()
		listView = gtk.TreeView(listStore)
		listWindow = gtk.ScrolledWindow()
	
		textEntry = gtk.Entry()
	
		# list setup
		listView.insert_column_with_attributes(0, "", listRenderer, text=0)
		listView.set_property("headers-visible", False)
		
		default_list = []
		if value:
			try:
				default_list = json.loads(value)
			except Exception as e:
				default_list = []
		
		if default_list and not isinstance(default_list, list):
			logging.error("Invalid default value (not a list)")
		else:
			for item in default_list:
				listStore.append(row=(item,))
	
		# window setup
		listWindow.set_properties(hscrollbar_policy=gtk.POLICY_AUTOMATIC,
			vscrollbar_policy=gtk.POLICY_AUTOMATIC, border_width=3)
		listWindow.set_shadow_type(gtk.SHADOW_ETCHED_IN)
		listWindow.add(listView)
	
		container = gtk.VBox()
		buttonBox = gtk.HBox()
	
		buttonBox.pack_start(addButton)
		buttonBox.pack_start(deleteButton)
	
		container.pack_start(listWindow, expand=True)
		container.pack_start(textEntry, expand=False)
		container.pack_start(buttonBox, expand=False)
	
		frame = gtk.Frame(label=label)
		frame.set_shadow_type(gtk.SHADOW_ETCHED_IN)
		frame.set_property("border-width", 6)
		frame.add(container)
	
		# signals
		listView.connect("row-activated", row_content_to_entry, textEntry)
	
		listStore.connect("row-changed", update_data_map)
		listStore.connect("row-deleted", update_data_map)
	
		addButton.connect("clicked", add_data_to_list, listView, textEntry)
		deleteButton.connect("clicked", delete_data_from_list, listView)
	
		return frame,None

	def composit_map_widget(*x):
		return None

	def _fill(self):
		""" fill the dialog's content box/table with widgets
			according to the plugin options.
		"""

		cSection = plugins.get_plugin_config_section(
				self.plugin_name)

		dataMap = {} # config_key : value
		rowCount = 0

		for option in self.plugin_options:
			
			if len(option) != PLUGIN_OPTIONS_LENGTH:
				logging.error("Faulty plugin %s: Invalid plugin options count: %d" % (
					self.plugin_name, len(option)))
				return
			
			(opt, label, vtype, value) = option

			def text_changed_cb(widget, option):
				value = widget.get_text()
				dataMap[option] = value


			wLabel = gtk.Label(label+": ")
			wLabel.set_property("xalign", 0)

			widget = None

			cValue = config.get(cSection, opt) or value
			dataMap[opt] = cValue


			if vtype == psushi.TYPE_STRING:
				# Simple text entry
				widget = gtk.Entry()
				widget.set_text(cValue)

				widget.connect("changed", text_changed_cb, opt)

			elif vtype == psushi.TYPE_PASSWORD:
				# Hidden char. entry
				widget = gtk.Entry()
				widget.set_text(cValue)
				widget.set_property("visibility", False)

				widget.connect("changed", text_changed_cb, opt)

			elif vtype == psushi.TYPE_NUMBER:
				# Number entry field

				def changed_cb(widget, option):
					dataMap[option] = widget.get_value_as_int()

				widget = gtk.SpinButton()
				widget.set_range(-99999,99999)
				widget.set_increments(1, 5)
				widget.set_value(int(cValue))

				widget.connect("value-changed", changed_cb, opt)

			elif vtype == psushi.TYPE_BOOL:
				# Check button for boolean values

				def changed_cb(widget, option):
					dataMap[option] = widget.get_active()

				widget = gtk.CheckButton()
				if type(cValue) == bool:
					widget.set_active(cValue)
				else:
					widget.set_active(cValue.lower() != "false")

				widget.connect("toggled", changed_cb, opt)

			elif vtype == psushi.TYPE_CHOICE:
				# Multiple values. Stored as [0] = key and [1] = value

				def changed_cb(widget, option):
					if widget.get_active() >= 0:
						value = widget.get_model()[widget.get_active()][1]
						dataMap[option] = value
					else:
						dataMap[option] = ""

				wModel = gtk.ListStore(
						gobject.TYPE_STRING,
						gobject.TYPE_STRING)
				widget = gtk.ComboBox(wModel)

				widget.connect("changed", changed_cb, opt)

				wRenderer = gtk.CellRendererText()
				widget.pack_start(wRenderer, True)
				widget.add_attribute(wRenderer, "text", 0)

				for (key, val) in value:
					wModel.append(row = (key, val))

				# this is tricky, if there's a saved value,
				# find the matching value (second field!)
				# and set the index to that position.
				if cValue and cValue != value:
					i = 0
					for row in wModel:
						if row[1] == cValue:
							break
						i+=1
					widget.set_active(i)
				else:
					widget.set_active(0)

			elif vtype == psushi.TYPE_LIST:
				
				widget,error = self.composit_list_widget(opt, label, cValue, dataMap)
				
				if error != None:
					logging.error(error)
					continue
					
				wLabel = gtk.Label("") # no need for extra label

			elif vtype == psushi.TYPE_MAP:
				widget = self.composit_map_widget(opt, label, value, dataMap)

			else:
				logging.error(
					"PluginConfigDialog: Wrong type given: %d" % (vtype))


			self.table.attach(wLabel, 0, 1, rowCount, rowCount+1)
			self.table.attach(widget, 1, 2, rowCount, rowCount+1)

			rowCount += 1

		self._data_map = dataMap


	def save(self):
		""" save the changes made in the plugin's config section """

		cSection = plugins.get_plugin_config_section(
				self.plugin_name)
		config.create_section(cSection)

		for (key, value) in self._data_map.items():

			logging.debug("PluginConfigDialog: Result: %s -> %s" % (
					key, str(value)))
			config.set(cSection, key, str(value))

