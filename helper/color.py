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

"""
IRC color specifications
"""

import re
import gtk

from typecheck import types

import helper.escape
import lib.contrast
import lib.gui_control

COLOR_PATTERN = "([0-9]{1,2})(,[0-9]{1,2}){0,1}.*"
COLOR_TABLE =  {
			 0: lib.contrast.CONTRAST_COLOR_WHITE,
			 1: lib.contrast.CONTRAST_COLOR_BLACK,
			 2: lib.contrast.CONTRAST_COLOR_BLUE,
			 3: lib.contrast.CONTRAST_COLOR_DARK_GREEN,
			 4: lib.contrast.CONTRAST_COLOR_DARK_RED,
			 5: lib.contrast.CONTRAST_COLOR_LIGHT_BROWN,
			 6: lib.contrast.CONTRAST_COLOR_PURPLE,
			 7: lib.contrast.CONTRAST_COLOR_ORANGE,
			 8: lib.contrast.CONTRAST_COLOR_YELLOW,
			 9: lib.contrast.CONTRAST_COLOR_LIGHT_GREEN,
			10: lib.contrast.CONTRAST_COLOR_CYAN,
			11: lib.contrast.CONTRAST_COLOR_AQUA,
			12: lib.contrast.CONTRAST_COLOR_LIGHT_BLUE,
			13: lib.contrast.CONTRAST_COLOR_MAGENTA,
			14: lib.contrast.CONTRAST_COLOR_GREY,
			15: lib.contrast.CONTRAST_COLOR_LIGHT_GREY
		}

@types (msg = basestring)
def parse_color_codes_to_tags(msg):
	""" Parse the mIRC color format ^Cn[,m] and convert it
		to the intern handled <font></font> tag.
		Convert the numbers n and m into contrast color codes
		and use them as foreground/background.
	"""
	def get_gdk_color(ccolor):
		bg_color = lib.gui_control.widgets.get_widget("output").\
			get_style().base[gtk.STATE_NORMAL]
		return lib.contrast.contrast_render_foreground_color(
			bg_color, ccolor)

	last_i = -1
	count = 0 # openend <font>
	self = parse_color_codes_to_tags

	try:
		self.pattern
		self.color_table
	except AttributeError:
		self.pattern = re.compile(chr(3)+COLOR_PATTERN)
		self.color_table = COLOR_TABLE

	while True:
		try:
			i = msg.index(chr(3), last_i+1)
		except ValueError:
			break

		match = self.pattern.match(msg[i:i+6])

		if match:
			groups = match.groups()
			tag = "<span"

			if count != 0:
				# close the previous color
				tag = "</span>" + tag
				count -= 1

			try:
				fg = self.color_table[int(groups[0])]
				fg = get_gdk_color(fg)
			except (KeyError, TypeError):
				fg = None
			else:
				tag += " foreground='%s'" % fg

			try:
				bg = self.color_table[int(groups[1][1:])]
				bg = get_gdk_color(bg)
			except (KeyError, TypeError):
				bg = None
			else:
				tag += " background='%s'" % bg

			tag += ">"
			skip_len = 1 + (groups[0] and len(groups[0]) or 0) \
				+ (groups[1] and len(groups[1]) or 0)
			msg = msg[:i] + tag + msg[i+skip_len:]

			count += 1

		else:
			if count > 0:
				# single ^C, if there's an open tag, close it
				msg = msg[:i] + "</span>" + msg[i+1:]
				count -= 1

		last_i = i

	if count != 0:
		# make sure the <font> is closed.
		msg = msg + "</span>"

	return msg

@types (s = basestring)
def parse_color_codes_to_markups(s):
	""" convert color codes to color markups (%C) and escape
		every % in s with %%.
	"""
	s = s.replace("%", "%%")
	return s.replace(chr(3), "%C")

@types (s = basestring)
def parse_color_markups_to_codes(s):
	""" split s for %C markups and parse the numbers following.
		After parsing, return the new string.
	"""
	self = parse_color_markups_to_codes

	try:
		self.color_pattern
	except AttributeError:
		self.color_pattern = re.compile(helper.color.COLOR_PATTERN)

	s_split = helper.escape.unescape_split("%C", s, escape_char="%")
	return chr(3).join(s_split)


