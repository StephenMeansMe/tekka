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

import os
import sys
import ConfigParser

class tekkaConfig(object):
	def __init__(self):
		self.useExternalDBus = False
		self.busAdress = "tcp:host=192.168.1.101,port=3333"

		if os.path.islink(sys.argv[0]):
			self.prefix = os.path.dirname(os.path.abspath(os.readlink(sys.argv[0])))
		else:
			self.prefix = os.path.dirname(os.path.abspath(sys.argv[0]))

		self.gladefiles = {}
		self.gladefiles["mainwindow"] = os.path.join(self.prefix, "mainwindow.glade")
		self.gladefiles["dialogs"] = os.path.join(self.prefix, "dialogs.glade")

		self.windowSize = [400,500]

		self.sidePosition = 0

		self.servertabShortcuts = True

		self.colors = {}
		self.colors["ownNick"] = "#444444"
		self.colors["ownText"] = "#444444"
		self.colors["nick"] = "#2222AA"
		self.colors["joinNick"] = "#004444"
		self.colors["partNick"] = "#004444"
		self.colors["modeActNick"] = "#AA2222"
		self.colors["modeParam"] = "#2222AA"

		# seperator to add after tab completion of nick
		self.nickCompletionSeperator=": "

		# additional words to highlight on
		self.highlightWords = []

		self.generalOutput = True
		self.generalOutputHeight = 100
		self.generalOutputFont = "Monospace"

		self.lastLogLines = 10

		self.trayicon = True

		self.showStatusBar = True

		self.hideOnDestroy = True

		# random nick colors
		self.nickColors=["#AA0000","#2222AA","#44AA44","#123456","#987654"]

		self.outputFont = "Monospace"

		self.browser = "xdg-open"
		self.browserArguments = "%s"

		configParser = ConfigParser.ConfigParser()
		success = configParser.read(['%s/sushi/tekka' % self.getXDGConfigHome()])

		if not success:
			print "Failed to parse config file."
			return

		# Generic colors
		try:
			items = configParser.items("colors")
		except ConfigParser.NoSectionError:
			pass
		else:
			for (cName,cColor) in items:
				if cColor[0] != "#":
					print "Only hexadecimal colors supported."
					continue
				self.colors[cName] = cColor

		# Nick colors
		try:
			tmp = configParser.get("colors","nick_colors")
			self.nickColors = tmp.split(",")
			del self.colors["nick_colors"]
		except ConfigParser.NoSectionError:
			pass

		# General traffic window
		trans = {
			"show":"b#self.generalOutput",
			"height":"i#self.generalOutputHeight",
			"font":"s#self.generalOutputFont"
		}

		self.transConfig(configParser, "general_output", trans)

		# Tekka options

		trans = {
			"nick_seperator":"s#self.nickCompletionSeperator",
			"highlightwords":"a#self.highlightWords",
			"outputfont":"s#self.outputFont",
			"lastloglines":"i#self.lastLogLines",
			"showstatusbar":"b#self.showStatusBar",
			"hideondestroy":"b#self.hideOnDestroy"
		}

		self.transConfig(configParser, "tekka", trans)

		trans = {
			"exec":"s#self.browser",
			"args":"s#self.browserArguments"
		}

		self.transConfig(configParser, "browser", trans)

		trans = {
			"show":"b#self.trayicon"
		}

		self.transConfig(configParser, "trayicon", trans)

		del trans

	def getColor(self, name):
		if not self.colors.has_key(name):
			return "#FFFFFF"
		return self.colors[name]

	def getNickColors(self):
		return self.nickColors

	def getShortcuts(self, startkey):
		if self.shortcuts.has_key(startkey):
			return self.shortcuts[startkey]
		return None

	def getPrefix(self):
		return self.prefix

	def getXDGConfigHome(self):
		try:
			return os.environ["XDG_CONFIG_HOME"]
		except KeyError:
			return os.path.expanduser("~/.config")

	def transConfig(self, configParser, cat, trans):
		try:
			items = configParser.items(cat)
		except Exception,e:
			print e
			return

		for (key,val) in items:
			if not trans.has_key(key):
				print "Unknown variable: %s" % key
				continue

			rule = trans[key][0]
			var = trans[key][2:]

			if rule=="a":
				exec('%s = val.split(",")' % var)
			elif rule=="s":
				val = val.replace('"','')
				exec('%s = val' % var)
			elif rule=="b":
				if val == "1" or val.lower() == "true":
					exec('%s = True' % var)
				else:
					exec('%s = False' % var)
			elif rule=="i":
				try:
					exec('%s = int(val)' % var)
				except ValueError:
					print "Wrong arg for key '%s'. int required." % key

class tekkaConfigDialog(object):
	def __init__(self):
		pass
