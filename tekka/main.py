#!/usr/bin/env python
# coding: UTF-8
"""
Copyright (c) 2008 Marian Tietz
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

"""
Coding style

Classes: MyClass
Methods: my_method
Variables: my_var OR myVar (that does not matter to me)

Line length: 80 characters
Indentation: Lines split up but with same context should
			 stick together:

			 if (myLongCondition != otherLongThing
			 and thatIsAll):
				 pass

			 or

			 my_string_function(
				 firstParam,
				 "This should be filled with %(vars)s." % {
					 "vars": testVar},
				 anotherParam)
"""
# TODO:  Introduce two ignore methods, one complete ignore method
# TODO:: where everything from that sender is ignored and one,
# TODO:: where it's indicated that there WAS an action but only
# TODO:: shown what and from who


# TODO:  would be nice to be notified (in a visual way?) if there's
# TODO:: a new markup in the server tree for a hidden tab (not in the
# TODO:: current view scope due to scrolling). It would be cool if the
# TODO:: top or bottom (in order which direction the tab with the new
# TODO:: markup is) of the server tree smoothly flashes or something
# TODO:: like that.

import pygtk
pygtk.require("2.0")

import sys
import traceback

import gtk # TODO: catch gtk.Warning after init with warnings module

import os
import gobject
import pango
import dbus
import webbrowser
import locale
import types as ptypes
import logging

import gettext
from gettext import gettext as _

import tekka.gui as gui
import tekka.gui.tabs

# local modules
import tekka.config as config
import tekka.com as com
import tekka.signals as signals
import tekka.commands as commands

from tekka.typecheck import types

import tekka.lib.dialog_control as dialog_control
import tekka.lib.plugin_control as plugin_control


from tekka.lib.inline_dialog import InlineMessageDialog
from tekka.lib.welcome_window import WelcomeWindow

from tekka.helper.shortcuts import addShortcut, removeShortcut
from tekka.helper import tabcompletion

from tekka.menus import *

import gui.builder

"""
Tekka intern signals
"""

def sushi_error_cb(sushi, title, message):
	def response_cb(d, i):
		gui.status.unset(title)
		d.destroy()

	d = InlineMessageDialog(title, message)
	d.connect("response", response_cb)
	gui.mgmt.show_inline_dialog(d)

	gui.status.set_visible(title, title)

def maki_connect_callback(sushi):
	""" connection to maki etablished """
	gui.mgmt.set_useable(True)

def maki_disconnect_callback(sushi):
	""" connection to maki lost """
	# FIXME:  after disconnecting and reconnecting,
	# FIXME:: the current tab's textview
	# FIXME:: is still insensitive - is this good or bad?
	gui.mgmt.set_useable(False)

def tekka_server_away_cb(tab, msg):
	pass

def tekka_server_new_nick_cb(tab, nick):
	activeTabs = gui.tabs.get_current_tabs()

	if (tab in activeTabs
	or (not tab.is_server() and tab.server in activeTabs)):
		gui.mgmt.set_nick(nick)

def tekka_tab_new_markup_cb(tab):
	# FIXME: is there a better solution than _this_?
	if tab.path:
		store = gui.widgets.get_widget("serverTree").get_model()
		store.set_value(store.get_iter(tab.path), 0, tab)

def tekka_tab_new_message_cb(tab, mtype):
	""" a new message of the given type was received """
	if gui.tabs.is_active(tab):
		tab.setNewMessage(None)

		if tab.window.auto_scroll and mtype:
			# FIXME:  on high load, the whole application
			# FIXME:: hangs. High load means, you insert a
			# FIXME:: text with around 2000 characters.
			if tab.window.textview.is_smooth_scrolling():
				tab.window.textview.stop_scrolling()
				tab.window.textview.scroll_to_bottom(no_smooth = True)
			else:
				tab.window.textview.scroll_to_bottom()

	else:
		pass

def tekka_tab_reset_message_cb(tab):
	""" message stack was reset """
	pass

def tekka_tab_new_name_cb(tab, name):
	tekka_tab_new_markup_cb(tab)

def tekka_tab_server_connected_cb(tab, connected):
	""" the server of the tab connected/disconnected """
	if not connected:
		gui.tabs.set_useable(tab, False)

def tekka_channel_joined_cb(tab, switch):
	""" channel received a change on joined attribute """
	gui.tabs.set_useable(tab, switch)

def tekka_channel_topic_cb(tab, topic):
	""" topic set """
	pass

def tekka_tab_new_path_cb(tab, new_path):
	""" a new path is set to the path """
	pass

def tekka_tab_switched_cb(tabclass, old, new):
	""" switched from tab old to tab new """
	inputBar = gui.widgets.get_widget("inputBar")

	if old:
		itext = inputBar.get_text()
		old.set_input_text(itext)
		old.window.textview.set_read_line()

	inputBar.set_text("")
	inputBar.set_position(1)

	if new:
		inputBar.set_text(new.get_input_text())
		inputBar.set_position(len(inputBar.get_text()))

		if new.window.auto_scroll:
			# XXX: Needs testing!
			def check_for_scrolling():
				sw = new.window
				adj = sw.get_vadjustment()

				if adj.get_value() != (adj.upper - adj.page_size):
					sw.textview.scroll_to_bottom( no_smooth = True )
				else:
					print "No need for scrolling!"
				return False

			gobject.idle_add(check_for_scrolling)

def tekka_tab_add_cb(tab):
	""" a tab is added """
	if type(gui.widgets.get_widget("outputWindow")) == WelcomeWindow:
		# TODO: this is called often if the tab is not changed
		hide_welcome_screen()

def tekka_tab_remove_cb(tab):
	""" a tab is about to be removed """

	if gui.tabs.get_current_tab() == tab:
		# switch to another tab

		if tab.is_server():
			# server and children are removed, choose
			# another server
			server = gui.tabs.get_next_server(tab)

			if server:
				tabs = gui.tabs.get_all_tabs(servers = [server.name])
				nextTab = tabs[0]
			else:
				nextTab = None
		else:
			nextTab = gui.tabs.get_next_tab(tab)

		if None == nextTab:
			# lock interface
			# XXX:  maybe the inputBar should
			# XXX:: useable, though.
			gui.mgmt.set_useable(False)
		else:
			gui.tabs.switch_to_tab(nextTab)

	elif (tab.is_server()
	and len(gui.get_widget("serverTree").get_model()) == 1):
		gui.mgmt.set_useable(False)

"""
Glade signals
"""

def mainWindow_scroll_event_cb(mainWindow, event):
	if (event.state & gtk.gdk.MOD1_MASK
	and event.direction == gtk.gdk.SCROLL_DOWN):
		gui.tabs.switch_to_next()

	elif (event.state & gtk.gdk.MOD1_MASK
	and event.direction == gtk.gdk.SCROLL_UP):
		gui.tabs.switch_to_previous()

def mainWindow_delete_event_cb(mainWindow, event):
	"""
		The user want's to close the main window.
		If the status icon is enabled and the
		"hideOnClose" option is set the window
		will be hidden, otherwise the main looped
		will be stopped.
		On hide there is an read-line inserted
		in every tab so the user does not have to
		search were he was reading last time.
	"""
	statusIcon = gui.widgets.get_widget("statusIcon")

	if (config.get_bool("tekka", "hide_on_close")
	and statusIcon and statusIcon.get_visible()):

		for tab in gui.tabs.get_all_tabs():
			tab.window.textview.set_read_line()

		mainWindow.hide()

		return True

	else:
		gtk.main_quit()

def mainWindow_focus_in_event_cb(mainWindow, event):
	"""
		User re-focused the main window.
		If we were in urgent status, the user
		recognized it now so disable the urgent thing.
	"""
	gui.mgmt.set_urgent(False)
	return False

def mainWindow_size_allocate_cb(mainWindow, alloc):
	"""
		Main window was resized.
		Store the new size in the config.
	"""
	if not mainWindow.window.get_state() & gtk.gdk.WINDOW_STATE_MAXIMIZED:
		config.set("sizes","window_width",alloc.width)
		config.set("sizes","window_height",alloc.height)

def mainWindow_window_state_event_cb(mainWindow, event):
	"""
		Window state was changed.
		Track maximifoo and save it.
	"""

	if event.new_window_state & gtk.gdk.WINDOW_STATE_MAXIMIZED:
		config.set("tekka","window_maximized","True")
	else:
		config.set("tekka","window_maximized","False")

def inputBar_activate_cb(inputBar):
	"""
		Receives if a message in the input bar
		was entered and sent.
		The entered message will be passed
		to the commands module (parseInput(text))
		and the input bar will be cleared.
	"""
	text = inputBar.get_text()

	tab = gui.tabs.get_current_tab()

	commands.parseInput(text)

	if tab:
		tab.input_history.add_entry(text)
		tab.input_history.reset()

	inputBar.set_text("")

def inputBar_key_press_event_cb(inputBar, event):
	"""
		Key pressed in inputBar.
		Implements tab and command completion.
	"""
	key =  gtk.gdk.keyval_name(event.keyval)
	tab =  gui.tabs.get_current_tab()

	text = unicode(inputBar.get_text(), "UTF-8")

	if key == "Up":
		# get next input history item
		if not tab:
			return

		hist = tab.input_history.get_previous()

		if hist != None:
			inputBar.set_text(hist)
			inputBar.set_position(len(hist))

	elif key == "Down":
		# get previous input history item
		if not tab:
			return

		hist = tab.input_history.get_next()

		if hist == None:
			return

		inputBar.set_text(hist)
		inputBar.set_position(len(hist))

	elif key == "Tab":
		# tab completion comes here.

		tabcompletion.complete(tab, inputBar, text)
		return True

	if key != "Tab":
		tabcompletion.stopIteration()

def outputShell_widget_changed_cb(shell, old_widget, new_widget):
	""" old_widget: OutputWindow
		new_widget: OutputWindow
	"""
	print "widgets changed: %s to %s" % (old_widget, new_widget)

	if (type(old_widget) == WelcomeWindow
	and type(new_widget) != WelcomeWindow):
		hide_welcome_screen()

	new_widget.set_property("name", "outputWindow")
	new_widget.textview.set_property("name", "output")

	gui.widgets.remove_widget(old_widget)
	gui.widgets.add_widget(new_widget)

	gui.widgets.remove_widget(old_widget.textview)
	gui.widgets.add_widget(new_widget.textview)

def serverTree_misc_menu_reset_activate_cb(menuItem):
	"""
	reset the markup of all tabs
	"""
	for tab in gui.tabs.get_all_tabs():
		tab.setNewMessage(None)

def serverTree_button_press_event_cb(serverTree, event):
	"""
		A row in the server tree was activated.
		The main function of this method is to
		cache the current activated row as path.
	"""

	try:
		path = serverTree.get_path_at_pos(int(event.x),int(event.y))[0]
		tab = serverTree.get_model()[path][0]
	except Exception as e:
		tab = None

	if event.button == 1:
		# activate the tab

		if tab:
			gui.tabs.switch_to_path(path)

	elif event.button == 2:
		# if there's a tab, ask to close
		if tab:
			askToRemoveTab(tab)

	elif event.button == 3:
		# popup tab menu

		if tab:
			menu = servertree_menu.ServerTreeMenu().get_menu(tab)

			if not menu:
				logging.error("error in creating server tree tab menu.")
				return False

			else:
				menu.popup(None, None, None, event.button, event.time)
				return True

		else:
			# display misc. menu
			menu = gtk.Menu()
			reset = gtk.MenuItem(label=_(u"Reset markup"))
			reset.connect("activate",
				serverTree_misc_menu_reset_activate_cb)
			menu.append(reset)
			reset.show()
			menu.popup(None,None,None,event.button,event.time)

	return False

def serverTree_row_activated_cb(serverTree, path, column):
	""" open the history dialog for the pointed tab """
	model = serverTree.get_model()
	tab = model[path][0]

	dialog_control.show_dialog("history", tab)

def nickList_row_activated_cb(nickList, path, column):
	"""
		The user activated a nick in the list.

		If there's a nick in the row a query
		for the nick on the current server will be opened.
	"""
	serverTab,channelTab = gui.tabs.get_current_tabs()

	try:
		name = nickList.get_model()[path][lib.nick_list_store.COLUMN_NICK]
	except TypeError:
		# nickList has no model
		return
	except IndexError:
		# path is invalid
		return

	if gui.tabs.search_tab(serverTab.name, name):
		# already a query open
		return

	query = gui.tabs.create_query(serverTab, name)
	query.connected = True

	gui.tabs.add_tab(serverTab, query)

	gui.print_last_log("", "", tab = query)
	gui.tabs.switch_to_tab(query)

def nickList_button_press_event_cb(nickList, event):
	"""
		A button pressed inner nickList.

		If it's the right mouse button and there
		is a nick at the coordinates, pop up a menu
		for setting nick options.
	"""
	if event.button == 3:
		# right mouse button pressed.

		path = nickList.get_path_at_pos(int(event.x), int(event.y))

		nick = None

		# get marked nick
		try:
			nick = nickList.get_model()[path[0]]
		except TypeError:
			# no model
			pass
		except IndexError:
			# path is "invalid"
			pass

		if nick:
			# display nick specific menu

			nick = nick[lib.nick_list_store.COLUMN_NICK]

			menu = nicklist_menu.NickListMenu().get_menu(nick)

			if not menu:
				return False

			# finaly popup the menu
			menu.popup(None, None, None, event.button, event.time)

	return False

def outputVBox_size_allocate_cb(outputVBox, alloc):
	widget = gui.widgets.get_widget("topicBar")
	widget.set_size_request(alloc.width, -1)

"""
	Shortcut callbacks
"""

def inputBar_shortcut_ctrl_u(inputBar, shortcut):
	"""
		Ctrl + U was hit, clear the inputBar
	"""
	gui.widgets.get_widget("inputBar").set_text("")

def output_shortcut_ctrl_l(inputBar, shortcut):
	"""
		Ctrl+L was hit, clear the outputs.
	"""
	gui.clear_all_outputs()

def output_shortcut_ctrl_f(inputBar, shortcut):
	""" show/hide the search toolbar """
	sb = gui.widgets.get_widget("searchBar")

	if sb.get_property("visible"):
		sb.hide()
	else:
		sb.show_all()
		sb.grab_focus()

def output_shortcut_ctrl_g(inputBar, shortcut):
	""" search further """
	gui.widgets.get_widget("searchBar").search_further()

def serverTree_shortcut_ctrl_Page_Up(serverTree, shortcut):
	"""
		Ctrl+Page_Up was hit, go up in server tree
	"""
	gui.tabs.switch_to_previous()

def serverTree_shortcut_ctrl_Page_Down(serverTree, shortcut):
	"""
		Ctrl+Page_Down was hit, go down in server tree
	"""
	gui.tabs.switch_to_next()

def askToRemoveTab(tab):
	def response_handler(dialog, response_id):

		if response_id == gtk.RESPONSE_YES:

			if tab.is_channel():
				com.sushi.part(tab.server.name, tab.name,
					config.get("chatting", "part_message", ""))

			elif tab.is_server():
				com.sushi.quit(tab.name,
					config.get("chatting", "quit_message", ""))

			gui.tabs.remove_tab(tab)

		dialog.destroy()

	if tab.is_channel():
		message = _(u"Do you really want to close channel “%(name)s”?")
	elif tab.is_query():
		message = _(u"Do you really want to close query “%(name)s”?")
	elif tab.is_server():
		message = _(u"Do you really want to close server “%(name)s”?")

	dialog = InlineMessageDialog(
		message % { "name": tab.name },
		icon=gtk.STOCK_DIALOG_QUESTION,
		buttons=gtk.BUTTONS_YES_NO
	)
	dialog.connect("response", response_handler)

	gui.mgmt.show_inline_dialog(dialog)

def serverTree_shortcut_ctrl_w(serverTree, shortcut):
	"""
		Ctrl+W was hit, close the current tab (if any)
	"""

	tab = gui.tabs.get_current_tab()

	if not tab:
		return

	askToRemoveTab(tab)

def output_shortcut_Page_Up(inputBar, shortcut):
	"""
		Page_Up was hit, scroll up in output
	"""
	vadj = gui.widgets.get_widget("outputWindow").get_vadjustment()

	if vadj.get_value() == 0.0:
		return # at top already

	n = vadj.get_value()-vadj.page_size
	if n < 0: n = 0
	gobject.idle_add(vadj.set_value,n)

def output_shortcut_Page_Down(inputBar, shortcut):
	"""
		Page_Down was hit, scroll down in output
	"""
	vadj = gui.widgets.get_widget("outputWindow").get_vadjustment()

	if (vadj.upper - vadj.page_size) == vadj.get_value():
		return # we are already at bottom

	n = vadj.get_value()+vadj.page_size
	if n > (vadj.upper - vadj.page_size): n = vadj.upper - vadj.page_size
	gobject.idle_add(vadj.set_value,n)

def inputBar_shortcut_ctrl_c(inputBar, shortcut):
	"""
		Ctrl + C was hit.
		Check every text input widget for selection
		and copy the selection to clipboard.
		FIXME: this solution sucks ass.
	"""
	buffer = gui.widgets.get_widget("output").get_buffer()
	goBuffer = gui.widgets.get_widget("generalOutput").get_buffer()
	topicBar = gui.widgets.get_widget("topicBar")
	cb = gtk.Clipboard()

	if buffer.get_property("has-selection"):
		buffer.copy_clipboard(cb)
	elif inputBar.get_selection_bounds():
		inputBar.copy_clipboard()
	elif goBuffer.get_property("has-selection"):
		goBuffer.copy_clipboard(cb)
	elif topicBar.get_selection_bounds():
		bounds = topicBar.get_selection_bounds()
		text = unicode(topicBar.get_text(), "UTF-8")
		text = text[bounds[0]:bounds[1]]
		cb.set_text(text)

def serverTree_query_tooltip_cb(widget, x, y, kbdmode, tooltip):
	""" show tooltips for treeview rows """

	def limit(s):
		limit = int(config.get("tekka","popup_line_limit"))
		if len(s) > limit:
			return gui.escape(s[:limit-3]+u"...")
		return gui.escape(s)

	path = widget.get_path_at_pos(x,y)

	if not path:
		return

	path = path[0]

	try:
		tab = widget.get_model()[path][0]
	except IndexError:
		return

	if tab.is_server():
		# TODO: away status
		s = "<b>" + _("Nickname: ") + "</b>" +  gui.escape(tab.nick)

	elif tab.is_channel():
		s = "<b>" +_("User: ") + "</b>" + str(len(tab.nickList)) +\
			"\n<b>" + _("Topic: ") + "</b>" +\
				limit(tab.topic) +\
			"\n<b>" + _("Last sentence: ") + "</b>" +\
				limit(tab.window.textview.get_last_line())

	elif tab.is_query():
		s = "<b>" + _("Last sentence: ") + "</b>" +\
			limit(tab.window.textview.get_last_line())

	tooltip.set_markup(s)

	return True

def serverTree_render_server_cb(column, renderer, model, iter):
	""" Renderer func for column "Server" in servertree """
	tab = model.get(iter, 0)
	if not tab or not tab[0]:
		return
	renderer.set_property("markup",tab[0].markup())

def nickList_render_nicks_cb(column, renderer, model, iter):
	""" Renderer func for column "Nicks" in NickList """

	if not com.sushi.connected:
		# do not render if no connection exists
		return

	# highlight own nick
	serverTab = gui.tabs.get_current_tabs()[0]

	if not serverTab:
		return

	nick = model.get(iter, 1)

	if not nick:
		return

	nick = nick[0]

	# highlight own nick
	if com.get_own_nick(serverTab.name) == nick:
		renderer.set_property("weight", pango.WEIGHT_BOLD)
	else:
		renderer.set_property("weight", pango.WEIGHT_NORMAL)

	# TODO: highlighing of users which are away

"""
Initial setup routines
"""

def setup_mainWindow():
	"""
		- set window title
		- set window icon
		- set window size
		- set window state
	"""
	win = gui.widgets.get_widget("mainWindow")

	if config.get_bool("tekka", "rgba"):
		colormap = win.get_screen().get_rgba_colormap()
		if colormap:
			gtk.widget_set_default_colormap(colormap)

	iconPath = config.get("tekka","status_icon")
	if iconPath:
		try:
			# Explicitly add a 64x64 icon to work around
			# a Compiz bug (LP: #312317)
			gtk.window_set_default_icon_list(
				gtk.gdk.pixbuf_new_from_file(iconPath),
				gtk.gdk.pixbuf_new_from_file_at_size(
					iconPath,
					64,
					64))

		except gobject.GError:
			# file not found
			pass

	width = config.get("sizes","window_width")
	height = config.get("sizes","window_height")

	if width and height:
		win.resize(int(width),int(height))

	if config.get_bool("tekka","window_maximized"):
		win.maximize()

	# enable scrolling through server tree by scroll wheel
	def kill_mod1_scroll(w,e):
		if e.state & gtk.gdk.MOD1_MASK:
			w.emit_stop_by_name("scroll-event")

	for widget in ("scrolledWindow_generalOutput",
				"scrolledWindow_serverTree","scrolledWindow_nickList"):
		gui.widgets.get_widget(widget).connect("scroll-event",
			kill_mod1_scroll)

	win.connect("scroll-event", mainWindow_scroll_event_cb)

	win.show()


def treemodel_rows_reordered_cb(treemodel, path, iter, new_order):
	""" new_order is not accessible, so hack arround it... """
	updated = False
	for row in treemodel:
		if not row[0]:
			continue

		if gui.tabs.currentPath == row[0].path and not updated:
			gui.tabs.currentPath = row.path
			updated = True

		row[0].path = row.path

		for child in row.iterchildren():
			if not child[0]:
				continue

			if gui.tabs.currentPath == child[0].path and not updated:
				gui.tabs.currentPath = child.path
				updated = True

			child[0].path = child.path


def setup_serverTree():
	"""
		Sets up a treemodel with three columns.
		The first column is a pango markup language
		description, the second is the identifying
		channel or server name and the third is a
		tab object.
		XXX: mostly deprecated by GtkBuilder
	"""
	tm = gtk.TreeStore(gobject.TYPE_PYOBJECT)

	# Sorting
	def cmpl(m,i1,i2):
		" compare columns lower case "
		a = m.get_value(i1, 0)
		b = m.get_value(i2, 0)
		c,d=None,None
		if a: c=a.name.lower()
		if b: d=b.name.lower()
		return cmp(c,d)

	tm.set_sort_func(1,
		lambda m,i1,i2,*x: cmpl(m,i1,i2))
	tm.set_sort_column_id(1, gtk.SORT_ASCENDING)
	tm.connect("rows-reordered", treemodel_rows_reordered_cb)

	# further stuff (set model to treeview, add columns)

	widget = gui.widgets.get_widget("serverTree")

	widget.set_model(tm)
	widget.set_property("has-tooltip", True)

	widget.connect("query-tooltip", serverTree_query_tooltip_cb)

	renderer = gtk.CellRendererText()
	column = gtk.TreeViewColumn("Server", renderer)
	column.set_cell_data_func(renderer, serverTree_render_server_cb)

	widget.append_column(column)
	widget.set_headers_visible(False)


def setup_nickList():
	"""
		Sets up a empty nickList widget.
		Two columns (both rendered) were set up.
		The first is the prefix and the second
		the nick name.
		XXX: deprecated by GtkBuilder
	"""
	widget = gui.widgets.get_widget("nickList")
	widget.set_model(None)

	renderer = gtk.CellRendererText()
	column = gtk.TreeViewColumn("Prefix", renderer, text=0)
	widget.append_column(column)

	renderer = gtk.CellRendererText()
	column = gtk.TreeViewColumn("Nicks", renderer, text=1)
	column.set_cell_data_func(renderer, nickList_render_nicks_cb)
	widget.append_column(column)

	widget.set_headers_visible(False)
	widget.set_rules_hint(True)


def setup_shortcuts():
	"""
		Set shortcuts to widgets.

		- ctrl + page_up -> scroll to prev tab in server tree
		- ctrl + page_down -> scroll to next tab in server tree
		- ctrl + w -> close the current tab
		- ctrl + l -> clear the output buffer
		- ctrl + u -> clear the input entry
		- ctrl + s -> hide/show the side pane
	"""
	gui.widgets.get_widget("mainWindow").add_accel_group(gui.accelGroup)

	addShortcut(gui.accelGroup, gui.widgets.get_widget("inputBar"),
		"<ctrl>u", inputBar_shortcut_ctrl_u)
	addShortcut(gui.accelGroup, gui.widgets.get_widget("inputBar"),
		"<ctrl>l", output_shortcut_ctrl_l)
	addShortcut(gui.accelGroup, gui.widgets.get_widget("inputBar"),
		"<ctrl>f", output_shortcut_ctrl_f)
	addShortcut(gui.accelGroup, gui.widgets.get_widget("inputBar"),
		"<ctrl>g", output_shortcut_ctrl_g)

	addShortcut(gui.accelGroup, gui.widgets.get_widget("serverTree"),
		"<ctrl>Page_Up", serverTree_shortcut_ctrl_Page_Up)
	addShortcut(gui.accelGroup, gui.widgets.get_widget("serverTree"),
		"<ctrl>Page_Down", serverTree_shortcut_ctrl_Page_Down)
	addShortcut(gui.accelGroup, gui.widgets.get_widget("serverTree"),
		"<ctrl>w", serverTree_shortcut_ctrl_w)

	addShortcut(gui.accelGroup, gui.widgets.get_widget("inputBar"),
		"Page_Up", output_shortcut_Page_Up)
	addShortcut(gui.accelGroup, gui.widgets.get_widget("inputBar"),
		"Page_Down", output_shortcut_Page_Down)

	addShortcut(gui.accelGroup, gui.widgets.get_widget("inputBar"),
		"<ctrl>c", inputBar_shortcut_ctrl_c)

	addShortcut(gui.accelGroup,
		gui.widgets.get_widget("menu_View_showSidePane"), "<ctrl>s",
		lambda w,s: w.set_active(not w.get_active()))


def connect_maki():
	"""
		Tries to connect to maki over DBus.
		If succesful, the GUI is enabled (gui.setUseable(True))
		and signals, dialogs, menus as well as the commands module
		were set up.

		See also: maki_connect_callback
	"""
	com.connect()

def load_paned_positions():
	""" restore the positions of the
		paned dividers for the list,
		main and output paneds.
	"""
	paneds = [
		gui.widgets.get_widget("listVPaned"),
		gui.widgets.get_widget("mainHPaned"),
		gui.widgets.get_widget("outputVPaned")]

	for paned in paneds:
		paned.set_property("position-set", True)
		position = config.get("sizes", paned.name, None)

		if position == None:
			continue

		try:
			paned.set_position(int(position))
		except ValueError:
			logging.error("Failed to set position for paned %s" % (
				paned.name))
			continue

def setup_paneds():

	def paned_notify_cb(paned, gparam):
		""" save the paned position in the config under the
			paned's name """
		if gparam.name == "position":
			config.set("sizes", paned.name, paned.get_property("position"))

	load_paned_positions()

	sigdic = {
		# watch for position change of paneds
		"listVPaned_notify_cb":
			paned_notify_cb,
		"mainHPaned_notify_cb":
			paned_notify_cb,
		"outputVPaned_notify_cb":
			paned_notify_cb,
		}
	# TODO:  catch inline dialog popups and restore the horizontal
	# TODO:: paned position (when they're closed?)
	gui.widgets.signal_autoconnect(sigdic)

	return False

def setup_fonts():
	""" add default font callback """
	try:
		import gconf

		def default_font_cb (client, id, entry, data):
			if not config.get_bool("tekka", "use_default_font"):
				return

			gui.apply_new_font()

		c = gconf.client_get_default()

		c.add_dir("/desktop/gnome/interface", gconf.CLIENT_PRELOAD_NONE)
		c.notify_add("/desktop/gnome/interface/monospace_font_name",
			default_font_cb)

	except:
		# ImportError or gconf reported a missing dir.
		pass

def show_welcome_screen():

	self = show_welcome_screen
	self.hides = ("scrolledWindow_generalOutput", "listVPaned")

	for w in self.hides:
		gui.widgets.get_widget(w).hide()

	s = gui.widgets.get_widget("outputShell")

	w = WelcomeWindow()

	s.set(w)
	s.show_all()

	com.sushi.g_connect("maki-disconnected",
		lambda sushi: s.set_sensitive(True))

def hide_welcome_screen():
	hides = show_welcome_screen.hides

	for w in hides:
		gui.widgets.get_widget(w).show()

def setupGTK():
	"""
		Set locale, parse glade files.
		Connects gobject widget signals to code.
		Setup widgets.
	"""
	gladefiles = config.get("gladefiles", default={})

	# setup locale stuff
	try:
		locale.setlocale(locale.LC_ALL, '')
	except:
		pass

	gettext.bindtextdomain("tekka", config.get("tekka","locale_dir"))
	gettext.textdomain("tekka")

	gtk.glade.bindtextdomain("tekka", config.get("tekka","locale_dir"))
	gtk.glade.textdomain("tekka")

	# parse glade file for main window
	gui.builder.load_widgets(gladefiles["mainwindow"], "mainWindow")

	def about_dialog_url_hook (dialog, link, data):
		if gtk.gtk_version >= (2, 16, 0):
			return

		webbrowser.open(link)

	gtk.about_dialog_set_url_hook(about_dialog_url_hook, None)

	setup_mainWindow()

	# to some setup on the search toolbar
	searchBar = gui.widgets.get_widget("searchBar")
	searchBar.hide()
	searchBar.textview_callback = lambda: gui.widgets.get_widget("output")

	# connect tab control signals
	gui.tabs.add_callbacks({
		"new_message": tekka_tab_new_message_cb,
		"reset_message": tekka_tab_reset_message_cb,
		"new_name": tekka_tab_new_name_cb,
		"new_path": tekka_tab_new_path_cb,
		"add": tekka_tab_add_cb,
		"remove": tekka_tab_remove_cb,
		"new_markup": tekka_tab_new_markup_cb,
		"server_connected": tekka_tab_server_connected_cb,
		"joined": tekka_channel_joined_cb,
		"away": tekka_server_away_cb,
		"topic": tekka_channel_topic_cb,
		"new_nick": tekka_server_new_nick_cb,
		"tab_switched": tekka_tab_switched_cb })

	# connect main window signals:
	sigdic = {
		# main window signals
		"mainWindow_delete_event_cb":
			mainWindow_delete_event_cb,
		"mainWindow_focus_in_event_cb":
			mainWindow_focus_in_event_cb,
		"mainWindow_size_allocate_cb":
			mainWindow_size_allocate_cb,
		"mainWindow_window_state_event_cb":
			mainWindow_window_state_event_cb,

		# server tree signals
		"serverTree_realize_cb":
			lambda w: w.expand_all(),
		"serverTree_button_press_event_cb" :
			serverTree_button_press_event_cb,
		"serverTree_row_activated_cb":
			serverTree_row_activated_cb,

		# nick list signals
		"nickList_row_activated_cb":
			nickList_row_activated_cb,
		"nickList_button_press_event_cb":
			nickList_button_press_event_cb,

		# output vbox signals
		"outputVBox_size_allocate_cb":
			outputVBox_size_allocate_cb,
	}

	gui.widgets.signal_autoconnect(sigdic)

	# setup manual signals

	# push status messages directly in the status bar
	gui.status.connect("set-visible-status",
		lambda w,s,m: gui.widgets.get_widget("statusBar")\
		.push(gui.status.id(s), m))

	# pop status message if they're unset
	gui.status.connect("unset-status",
		lambda w,s: gui.widgets.get_widget("statusBar")\
		.pop(gui.status.id(s)))

	bar = gui.widgets.get_widget("inputBar")
	bar.connect("key-press-event", inputBar_key_press_event_cb)
	bar.connect("activate", inputBar_activate_cb)

	# output window switched
	shell = gui.widgets.get_widget("outputShell")
	shell.connect("widget-changed", outputShell_widget_changed_cb)
	shell.reset()

	# setup more complex widgets

	setup_serverTree()

	setup_nickList()

	setup_fonts()

	# set input font
	gui.mgmt.set_font(gui.widgets.get_widget("inputBar"),
		gui.mgmt.get_font())

	# set general output font
	gui.mgmt.set_font(gui.widgets.get_widget("generalOutput"),
		gui.mgmt.get_font())

	setup_shortcuts()

	# disable the GUI and wait for commands :-)
	gui.mgmt.set_useable(False)

	show_welcome_screen()

	gobject.idle_add(setup_paneds)

def tekka_excepthook(extype, exobj, extb):
	""" we got an exception, print it in a dialog box and,
		if possible, to the standard output.
	"""

	def dialog_response_cb(dialog, rid):
		del tekka_excepthook.dialog
		dialog.destroy()

	class ErrorDialog(gtk.Dialog):
		def __init__(self, message):
			gtk.Dialog.__init__(self,
				parent = gui.widgets.get_widget("mainWindow"),
				title = _("Error occured"),
				buttons = (gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE))

			self.set_default_size(400,300)

			self.error_label = gtk.Label()
			self.error_label.set_properties(
				width_chars = 50, wrap = True, xalign = 0.0)
			self.error_label.set_markup(_(
				"<span size='larger' weight='bold'>Error</span>\n\n"
				"An error occured — we apologize for that. "
				"Feel free to submit a bug report at "
				"https://bugs.launchpad.net/sushi."))

			self.tv = gtk.TextView()
			self.tv.get_buffer().set_text(message)

			self.sw = gtk.ScrolledWindow()
			self.sw.set_properties(
				shadow_type = gtk.SHADOW_ETCHED_IN,
				hscrollbar_policy = gtk.POLICY_AUTOMATIC,
				vscrollbar_policy = gtk.POLICY_AUTOMATIC)
			self.sw.add(self.tv)

			self.vbox_inner = gtk.VBox()
			self.vbox_inner.set_property("border-width", 6)

			self.vbox_inner.pack_start(self.error_label)
			self.vbox_inner.pack_end(self.sw)

			self.vbox.pack_start(self.vbox_inner)
			self.vbox.show_all()

		def set_message(self, msg):
			self.tv.get_buffer().set_text(msg)

	message = "%s\n%s: %s\n" % (
		"".join(traceback.format_tb(extb)),
		extype.__name__,
		str(exobj))

	try:
		print >> sys.stderr, message
	except:
		pass

	self = tekka_excepthook
	try:
		dialog = self.dialog
	except AttributeError:
		dialog = self.dialog = ErrorDialog(message)
		dialog.connect("response", dialog_response_cb)
		dialog.show_all()
	else:
		self.dialog.set_message(message)

	sys.__excepthook__(extype, exobj, extb)

def setup_logging():
	""" set the path of the logfile to tekka.logfile config
		value and create it (including path) if needed.
		After that, add a logging handler for exceptions
		which reports exceptions catched by the logger
		to the tekka_excepthook. (DBus uses this)
	"""
	try:
		class ExceptionHandler(logging.Handler):
			""" handler for exceptions caught with logging.error.
				dump those exceptions to the exception handler.
			"""
			def emit(self, record):
				if record.exc_info:
					tekka_excepthook(*record.exc_info)

		logfile = config.get("tekka","logfile")
		logdir = os.path.dirname(logfile)

		if not os.path.exists(logdir):
			os.makedirs(logdir)

		logging.basicConfig(filename = logfile, level = logging.DEBUG,
			filemode="w")

		logging.getLogger("").addHandler(ExceptionHandler())

	except BaseException as e:
		print >> sys.stderr, "Logging init error: %s" % (e)


def setup():
	""" Setup the UI """

	# load config file, apply defaults
	config.setup()

	# create logfile, setup logging module
	setup_logging()

	# setup callbacks
	com.sushi.g_connect("sushi-error", sushi_error_cb)
	com.sushi.g_connect("maki-connected", maki_connect_callback)
	com.sushi.g_connect("maki-disconnected", maki_disconnect_callback)
	signals.setup()

	# build graphical interface
	setupGTK()

	# setup exception handler
	sys.excepthook = tekka_excepthook


def main():
	""" Fire up the UI """

	# connect to maki daemon
	connect_maki()

	plugin_control.load_autoloads()

	# start main loop
	gtk.main()

	# after main loop break, write config
	config.write_config_file()

	# At last, close maki if requested
	if config.get_bool("tekka", "close_maki_on_close"):
		com.sushi.shutdown(config.get("chatting", "quit_message", ""))
