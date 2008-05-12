#!/usr/bin/env python
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

import sys

import gtk
import gobject

from tekkaConfig import tekkaConfig
from tekkaCom import tekkaCom
import tekkaGUI
from tekkaCommands import tekkaCommands
from tekkaSignals import tekkaSignals

import tekkaDialog
import tekkaPlugins

class tekkaMain(object):
	def __init__(self):
		self.config = tekkaConfig()
		self.config.readConfig()

		self.com = tekkaCom(self.config)
		self.gui = tekkaGUI.tekkaGUI(self.config)
		self.plugins = tekkaPlugins.tekkaPlugins(self.config)

		if not self.com.connectMaki():
			print "Connection to maki failed."
			sys.exit(1)

		self.commands = tekkaCommands(self.com,self.gui)
		self.signals = tekkaSignals(self.com,self.gui)

		self._setupSignals(self.gui.getWidgets())

		self.gui.getServertree().expand_all()

		self.initShortcuts()

	def getConfig(self):
		return self.config

	def getCom(self):
		return self.com

	def getGui(self):
		return self.gui

	def getCommands(self):
		return self.commands

	def getSignals(self):
		return self.signals

	def getPlugins(self):
		return self.plugins

	def _setupSignals(self, widgets):
		sigdic = {
				   "tekkaMainwindow_Quit_activate_cb" : gtk.main_quit,
				   "tekkaInput_activate_cb" : self.userInput,
				   "tekkaTopic_activate_cb" : self.topicbarActivate,
				   "tekkaServertree_realize_cb" : lambda w: w.expand_all(),
				   "tekkaNicklist_row_activated_cb" : self.nicklistActivateRow,
				   "tekkaNicklist_button_press_event_cb" : self.nicklistButtonPress,
		           "tekkaMainwindow_Connect_activate_cb" : self.showServerDialog,
				   "tekkaMainwindow_Shutdown_activate_cb" : self.makiShutdown
		         }

		widgets.signal_autoconnect(sigdic)
		widget = widgets.get_widget("tekkaMainwindow")
		if widget:
			widget.connect("destroy", gtk.main_quit)
		widget = widgets.get_widget("tekkaMainwindow_MenuTekka_Quit")
		if widget:
			widget.connect("activate", gtk.main_quit)

		self.gui.getServertree().connect("button-press-event", self.servertreeButtonPress)
		self.gui.getInput().connect("key-press-event", self.userInputEvent)

	def _showServerDialog(self, widget):
		serverlist = tekkaDialog.serverDialog(self)
		result,server = serverlist.run()
		if result == serverlist.RESPONSE_CONNECT:
			print "we want to connect to server %s" % server
			if server:
				self.com.connect(server)

	""" Change the current tab to the tab identified by "path" """
	def switchTreeTab(self, path):
		servertree = self.gui.getServertree()
		srow,crow = servertree.getRowFromPath(path)

		if srow and not crow:
			server = srow[servertree.COLUMN_NAME]
			obj = srow[servertree.COLUMN_OBJECT]

			output = obj.getBuffer()

			if not output:
				print "No output!"
				return

			self.gui.getOutput().set_buffer(output) # set output buffer
			self.gui.scrollOutput(output) # scroll to the bottom

			# reset hightlight
			obj.setNewMessage(False)
			servertree.serverDescription(server, obj.markup())

			self.gui.getNicklist().set_model(None)
			self.gui.getTopicbar().set_property("visible",False)

		elif srow and crow:
			server = srow[servertree.COLUMN_NAME]
			channel = crow[servertree.COLUMN_NAME]
			desc = crow[servertree.COLUMN_DESCRIPTION]
			obj = crow[servertree.COLUMN_OBJECT]

			output = obj.getBuffer()
			if not output:
				print "No output!"
				return

			self.gui.getOutput().set_buffer(output)
			self.gui.scrollOutput(output)

			obj.setNewMessage(False)
			servertree.channelDescription(server, channel, obj.markup())

			self.gui.getNicklist().set_model(obj.getNicklist())

			topicbar = self.gui.getTopicbar()
			topicbar.set_text("")
			self.gui.setTopicInBar(server=server,channel=channel)
			topicbar.set_property("visible",True)
		else:
			print "Activation failed due to wrong path."

	""" Wrapper for shortcut functionality """
	def switchTabByKey(self, path):
		servertree = self.gui.getServertree()
		servertree.set_cursor(path)
		servertree.updateCurrentRowFromPath(path)
		self.switchTreeTab(path)

	def initShortcuts(self):
		servertree = self.gui.getServertree()
		accelGroup = self.gui.getAccelGroup()
		for i in range(1,10):
			gobject.signal_new("shortcut_%d" % i, tekkaGUI.tekkaServertree, gobject.SIGNAL_ACTION, None, ())
			servertree.add_accelerator("shortcut_%d" % i, accelGroup, ord("%d" % i), gtk.gdk.MOD1_MASK, gtk.ACCEL_VISIBLE)
			servertree.connect("shortcut_%d" % i, eval("self.shortcut_%d" % i))


	"""
	Widget-Signals
	"""

	""" Keyboard shortcut signals (alt+[1-9]) """
	def shortcut_1(self,w):
		self.switchTabByKey(self.gui.getServertree().getShortcut("1"))
	def shortcut_2(self,w):
		self.switchTabByKey(self.gui.getServertree().getShortcut("2"))
	def shortcut_3(self,w):
		self.switchTabByKey(self.gui.getServertree().getShortcut("3"))
	def shortcut_4(self,w):
		self.switchTabByKey(self.gui.getServertree().getShortcut("4"))
	def shortcut_5(self,w):
		self.switchTabByKey(self.gui.getServertree().getShortcut("5"))
	def shortcut_6(self,w):
		self.switchTabByKey(self.gui.getServertree().getShortcut("6"))
	def shortcut_7(self,w):
		self.switchTabByKey(self.gui.getServertree().getShortcut("7"))
	def shortcut_8(self,w):
		self.switchTabByKey(self.gui.getServertree().getShortcut("8"))
	def shortcut_9(self,w):
		self.switchTabByKey(self.gui.getServertree().getShortcut("9"))

	"""
	A button in the servertree was pressed.
	"""
	def servertreeButtonPress(self, widget, event):
		path = widget.get_path_at_pos(int(event.x), int(event.y))

		if not path or not len(path):
			return

		servertree = self.gui.getServertree()
		srow,crow = servertree.getRowFromPath(path[0])

		# left click -> activate tab
		if event.button == 1:
			self.switchTreeTab(path[0])

		# right click -> menu for tab
		elif event.button == 3:
			server = None
			channel = None

			if srow:
				server = srow[servertree.COLUMN_NAME]
			if crow:
				channel = crow[servertree.COLUMN_NAME]

			if not crow and not srow:
				return

			menu = gtk.Menu()

			if crow:
				obj = servertree.getObject(server,channel)

				if not obj.getJoined():
					label = gtk.MenuItem(label="Join")
					label.connect("activate", lambda w: self.com.join(server,channel))
					menu.append( label )
				else:
					label = gtk.MenuItem(label="Part")
					label.connect("activate", lambda w: self.com.part(server, channel))
					menu.append( label )

				label = gtk.CheckMenuItem(label="Autojoin")
				if self.com.getChannelAutojoin(server,channel) == "true":
					label.set_active(True)
				label.connect("toggled", lambda w: self.channelMenuAutojoin(server,channel,w))
				menu.append( label )
			elif srow:
				if not srow[servertree.COLUMN_OBJECT].getConnected():
					label = gtk.MenuItem(label="Connect")
					label.connect("activate",lambda w: self.com.connectServer(server))
					menu.append( label )
				else:
					label = gtk.MenuItem(label="Disconnect")
					label.connect("activate",lambda w: self.com.quitServer(server))
					menu.append( label )

			label = gtk.MenuItem(label="Close Tab")
			label.connect("activate", self._menuRemoveTab, *(server,channel))

			menu.append( label )

			menu.show_all()

			menu.popup(None, None, None, button=event.button, activate_time=event.time)

	"""
	The user pressed enter in the inputbox
	"""
	def userInput(self, widget):
		text =  widget.get_text()
		server,channel = self.gui.getServertree().getCurrentChannel()
		self.gui.getHistory().append(server, channel,text)
		self.commands.sendMessage(server, channel, text)
		widget.set_text("")

	"""
	Autojoin button in context menu of the servertree was pressed
	"""
	def channelMenuAutojoin(self, server, channel, w):
		self.com.setChannelAutojoin(server,channel, w.get_active())

	"""
	A nick in the nicklist was double clicked
	"""
	def nicklistActivateRow(self, treeview, path, parm1):
		servertree = self.gui.getServertree()
		server = servertree.getCurrentServer()
		if not server: return
		nick = self.gui.getNicklist().get_model()[path[0]][tekkaGUI.tekkaNicklistStore.COLUMN_NICK]
		servertree.addChannel(server, nick)

	"""
	A button inner the nicklist-area was pressed
	"""
	def nicklistButtonPress(self, widget, event):
		path = widget.get_path_at_pos(int(event.x), int(event.y))
		if not path or not len(path):
			return
		srow,crow = self.gui.getServertree().getCurrentRow()

		if not crow:
			return

		nicklist = crow[self.gui.getServertree().COLUMN_OBJECT].getNicklist()
		nickrow = nicklist[path[0]]

		# left click -> activate tab
		if event.button == 1:
			print "Would do any left-click action"
			pass

		elif event.button == 3:
			nick = nickrow[tekkaGUI.tekkaNicklistStore.COLUMN_NICK]
			server = srow[tekkaGUI.tekkaServertree.COLUMN_NAME]
			channel = crow[tekkaGUI.tekkaServertree.COLUMN_NAME]

			menu = gtk.Menu()

			kickItem = gtk.MenuItem(label="Kick")
			kickItem.connect("activate", lambda w: self.com.kick(server, channel, nick))
			menu.append(kickItem)

			banItem = gtk.MenuItem(label="Ban")
			banItem.connect("activate", lambda w: self.com.mode(server, channel, "+b %s!*@*" % nick))
			menu.append(banItem)

			unbanItem = gtk.MenuItem(label="Unban")
			unbanItem.connect("activate", lambda w: self.com.mode(server, channel, "-b %s" % nick))
			menu.append(unbanItem)

			ignoreItem = gtk.CheckMenuItem(label="Ignore")
			pattern = "%s!*" % nick
			ignores = self.com.fetchIgnores(server)
			if pattern in ignores:
				ignoreItem.set_active(True)
				ignoreItem.connect("toggled", lambda w: self.com.unignore(server, pattern))
			else:
				ignoreItem.connect("toggled", lambda w: self.com.ignore(server, pattern))
			menu.append(ignoreItem)

			mode_menu = gtk.Menu()
			modeItem = gtk.MenuItem(label="Mode")
			modeItem.set_submenu(mode_menu)

			menu.append(modeItem)

			opItem       = gtk.MenuItem(label="Op")
			opItem.connect("activate", lambda w: self.modeChange(w, server, channel, nick, "+o"))
			mode_menu.append(opItem)

			deopItem     = gtk.MenuItem(label="Deop")
			deopItem.connect("activate", lambda w: self.modeChange(w, server, channel, nick, "-o"))
			mode_menu.append(deopItem)

			halfopItem   = gtk.MenuItem(label="Halfop")
			halfopItem.connect("activate", lambda w: self.modeChange(w, server, channel, nick, "+h"))
			mode_menu.append(halfopItem)

			dehalfopItem = gtk.MenuItem(label="DeHalfop")
			dehalfopItem.connect("activate", lambda w: self.modeChange(w, server, channel, nick, "-h"))
			mode_menu.append(dehalfopItem)

			voiceItem    = gtk.MenuItem(label="Voice")
			voiceItem.connect("activate", lambda w: self.modeChange(w, server, channel, nick, "+v"))
			mode_menu.append(voiceItem)

			devoiceItem  = gtk.MenuItem(label="Devoice")
			devoiceItem.connect("activate", lambda w: self.modeChange(w, server, channel, nick, "-v"))
			mode_menu.append(devoiceItem)

			mode_menu.show_all()
			menu.show_all()
			menu.popup(None, None, None, button=event.button, activate_time=event.time)


	"""
	User clicked on a mode-menu item in nicklist menu
	"""
	def modeChange(self, widget, server, channel, nick, mode):
		self.com.mode(server, channel, "%s %s" % (mode, nick))

	"""
	User pressed enter in the topicbar
	"""
	def topicbarActivate(self, widget):
		self.commands.makiTopic(widget.get_text().split(" "))

	"""
	User added text or pressed a button in the input line
	"""
	def userInputEvent(self, widget, event):
		name = gtk.gdk.keyval_name( event.keyval )

		if name == "Up":
			server,channel = self.gui.getServertree().getCurrentChannel()
			text = self.gui.get_history().getUp(server,channel)

			widget.set_text(text)
			widget.set_position(len(text))
			return True
		elif name == "Down":
			server,channel = self.gui.getServertree().getCurrentChannel()
			text = self.gui.get_history().getDown(server,channel)

			widget.set_text(text)
			widget.set_position(len(text))
			return True
		if name == "Tab":
			s,c = self.gui.getServertree().getCurrentRow()
			if not c:
				print "Server keyword tabcompletion."
			else:
				obj = c[self.gui.getServertree().COLUMN_OBJECT]
				if not obj:
					return True

				text = widget.get_text()
				text = text.split(" ")

				needle = text[-1]

				if not needle:
					return True

				result = None

				if needle[0] == "#": # channel completion
					channels = self.gui.getServertree().searchTab(s.iterchildren(),needle.lower())
					if channels:
						result = channels[0]
				elif needle[0] == "/": # command completion
					needle = needle[1:]
					commands = [l for l in self.commands.get_commands().iterkeys() if l and l[0:len(needle)].lower() == needle.lower()]
					if commands:
						result = "/%s" % commands[0]
				else: # nick completion
					nicks = obj.getNicklist().searchNick(needle.lower())
					if nicks:
						result = nicks[0]

				if result:
					text[-1] = result+" "
					text = " ".join(text)
					widget.set_text(text)
					widget.set_position(len(text))

				return True
		return False

	"""
	"Close tab" in servertree contextmenu was clicked
	"""
	def _menuRemoveTab(self, w, server, channel):
		servertree = self.gui.getServertree()
		cs,cc = servertree.getCurrentChannel()

		if not server and not channel:
			return
		elif server and not channel:
			self.com.quitServer(server)
			servertree.removeServer(server)
			if server == cs:
				self.gui.get_output().get_buffer().set_text("")
		elif server and channel:
			self.com.part(server, channel)
			servertree.removeChannel(server,channel)

			if cc == channel:
				self.gui.get_output().get_buffer().set_text("")
				self.gui.get_topicbar().set_text("")
				self.gui.get_nicklist().set_model(None)


	"""
	"Connect" in the main-menu was clicked
	"""
	def showServerDialog(self, widget):
		serverlist = tekkaDialog.serverDialog(self)
		result,server = serverlist.run()
		if result == serverlist.RESPONSE_CONNECT:
			print "we want to connect to server %s" % server
			if server:
				self.com.connectServer(server)

	"""
	Shutdown button in main-menu was clicked
	"""
	def makiShutdown(self, widget):
		self.com.shutdown()
		for server in self.getServertree().getServers().get_model() or []:
			obj = server[tekkaGUI.tekkaServertree.COLUMN_OBJECT]
			obj.setConnected(False)
			for channel in server.iterchildren():
				obj = channel[tekkaGUI.tekkaServertree.COLUMN_OBJECT]
				obj.setJoined(False)
		# TODO: disable widgets (entry, tekka->connect, tekka->close maki,
		# nicklist->menu, servertree->menu)

if __name__ == "__main__":

	tekka = tekkaMain()
	gtk.main()
