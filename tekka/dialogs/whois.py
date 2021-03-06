# coding: UTF-8
"""
Copyright (c) 2009 Marian Tietz
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

import gtk
import gobject
from gobject import TYPE_STRING
from gettext import gettext as _

from .. import signals
from .. import com

class WhoisDialog(gtk.Dialog):

	def __init__(self, server, nick):
		gtk.Dialog.__init__(self,
			flags=gtk.DIALOG_DESTROY_WITH_PARENT,
			buttons=(gtk.STOCK_CLOSE, gtk.RESPONSE_CLOSE))

		self.set_default_size(350, 200)

		self.end = False

		self.treeview = self._setup_treeview()

		self.scrolled_window = gtk.ScrolledWindow()
		self.scrolled_window.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
		self.scrolled_window.add(self.treeview)

		self.get_content_area().add(self.scrolled_window)

		self.set_data(server, nick)


	def _setup_treeview(self):
		treeview = gtk.TreeView()
		treeview.set_model(gtk.ListStore(TYPE_STRING))

		renderer = gtk.CellRendererText()
		column = gtk.TreeViewColumn(
			"Data", renderer, text=0)

		treeview.append_column(column)

		return treeview

	def set_data(self, server, nick):
		self.nick = nick
		self.server = server
		self.set_title(_("Whois on %(server)s" % {
			"server":server}))

		label = gtk.Label()
		label.set_use_underline(False)
		label.set_text(_("Whois data of %(nick)s" % {
				"nick":nick}))
		label.show()

		self.treeview.get_column(0).set_widget(label)

	def whois_input(self, time, server, nick, message):
		# message == "" -> EOL
		if self.end:
			self.treeview.get_model().clear()
			self.end = False

		if message:
			self.treeview.get_model().append(row=(message,))

		else:
			self.end = True

diag = None

def dialog_response_cb(dialog, id):
	if id in (gtk.RESPONSE_NONE, gtk.RESPONSE_CLOSE):
		global diag
		signals.disconnect_signal("whois", dialog.whois_input)

		diag = None
		dialog.destroy()

def loading_timeout_cb(dialog):
	if (dialog.treeview.get_model()
	and len(dialog.treeview.get_model()) <= 1):
		dialog.end = True
		dialog.whois_input(0, "", "", _("No data received so far. Are you still connected?"))
	return False

def run(server, nick):
	global diag

	if not diag:
		diag = WhoisDialog(server, nick)
		diag.connect("response", dialog_response_cb)

		signals.connect_signal("whois", diag.whois_input)

	else:
		diag.set_data(server, nick)

	com.sushi.whois(server, nick)
	diag.whois_input(0, "", "",_("Loading..."))
	diag.end = True

	gobject.timeout_add(20000, loading_timeout_cb, diag)

	diag.show_all()

def setup():
	pass
