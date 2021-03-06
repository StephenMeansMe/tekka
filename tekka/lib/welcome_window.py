"""
Copyright (c) 2009-2010 Marian Tietz
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
from gettext import gettext as _

from .. import com
from .. import config

from .output_window import OutputWindow

class WelcomeWindow(OutputWindow):

	def __init__(self, *args, **kwargs):
		OutputWindow.__init__(self, *args, **kwargs)

		self.set_properties(
			hscrollbar_policy=gtk.POLICY_AUTOMATIC,
			vscrollbar_policy = gtk.POLICY_NEVER )

		self.remove(self.textview)

		self.table = gtk.Table(rows = 2, columns = 2)
		self.table.set_homogeneous(False)
		self.table.set_property("border-width", 12)

		try:
			self.pixbuf = gtk.icon_theme_get_default().load_icon("tekka",128,0)
		except:
			self.pixbuf = None

		self.image = gtk.image_new_from_pixbuf(self.pixbuf)

		# Create Header label
		self.label = gtk.Label()
		self.label.set_property("yalign", 1)
		self.label.set_property("xalign", 0.05)
		self.label.set_markup(
			_("<big><b>Welcome to tekka!</b></big>"))

		# Add Image to table
		self.ibox = gtk.EventBox()
		self.ibox.add(self.image)

		self.table.attach(self.ibox, 0, 1, 0, 2,
			xoptions=gtk.FILL|gtk.SHRINK,
			yoptions = gtk.FILL|gtk.EXPAND)

		# Add Label to table
		self.lbox = gtk.EventBox()
		self.lbox.add(self.label)

		self.table.attach(self.lbox, 1, 2, 0, 1,
			xoptions=gtk.FILL|gtk.EXPAND,
			yoptions=gtk.FILL|gtk.EXPAND)

		# Create Description label
		self.descr = gtk.Label()
		self.descr.set_properties(
			xalign=0.05,
			yalign=0.2,
			selectable=True,
			use_markup=True,
			width_chars=30,
			wrap=True)

		# Add Description to table
		self.dbox = gtk.EventBox()
		self.dbox.add(self.descr)

		self.table.attach(self.dbox, 1, 2, 1, 2,
			xoptions=gtk.FILL|gtk.EXPAND,
			yoptions=gtk.FILL|gtk.EXPAND)

		def mod_bg(w, c):
			# for debugging purposes
			if False:
				s = w.get_style().copy()
				s.bg[gtk.STATE_NORMAL] = c
				w.set_style(s)

		mod_bg(self.lbox, gtk.gdk.Color("#FF0000"))
		mod_bg(self.dbox, gtk.gdk.Color("#00FF00"))
		mod_bg(self.ibox, gtk.gdk.Color("#0000FF"))

		self.add_with_viewport(self.table)

		if com.sushi.connected:
			self.sushi_connected_cb(com.sushi)
		else:
			self.sushi_disconnected_cb(com.sushi)

		com.sushi.g_connect("maki-connected", self.sushi_connected_cb)
		com.sushi.g_connect("maki-disconnected", self.sushi_disconnected_cb)

	def sushi_connected_cb(self, sushi):
		s = _("You are connected to maki. The next step "
				"is to connect to a server via the server "
				"dialog in the tekka menu.")
		self.descr.set_markup(s)

	def sushi_disconnected_cb(self, sushi):
		s = _("You are not connected to maki. "
				"Without maki you can not connect to "
				"servers or write messages.\n\n"
				"If you are having problems running maki "
				"visit http://sushi.ikkoku.de/ and look whether there is "
				"a solution for your problem. Otherwise, feel free "
				"to ask for support.")
		self.descr.set_markup(s)

