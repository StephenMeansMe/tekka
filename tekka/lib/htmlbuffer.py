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

import gtk
import pango
import logging
import xml.sax
import xml.sax.handler

from StringIO import StringIO

from .. import gui

from ..helper.url import URLToTag
from .. import helper
from .. import config



class HTMLHandler(xml.sax.handler.ContentHandler):
	"""
	Parses HTML like strings and applies
	the tags as format rules for the given text buffer.
	"""

	def __init__(self, textbuffer, handler):
		xml.sax.handler.ContentHandler.__init__(self)

		self.textbuffer = textbuffer
		self.ignoreableEndTags = ["msg","br","su","sb"]
		self.no_cache = ["a","sb","su"]
		self.URLHandler = handler

		self._reset_values()

	def _reset_values(self):
		self.elms = []
		self.tags = []
		self.sucount = 0
		self.sbcount = 0

	def _get_cache_name(self, name, attrs):
		" return the caching name of a element for tag caching "

		def attrs_to_dict(attrs):
			return "{"+ ",".join(
				[n+":"+attrs.getValue(n) for n in attrs.getNames()]) +"}"

		if name in ("font","span"):
			return name + attrs_to_dict(attrs)

		return name

	def _get_cached(self, cachename):
		" return the cached tag for the given element or None "
		return self.textbuffer.get_tag_table().lookup(cachename)

	def _apply_tag(self, name, tag):
		""" mark the element and the tag to be added later.
			This is usually called in startElement.
		"""
		self.elms.insert(0, name)
		self.tags.insert(0, tag)

	def characters(self, text):
		""" Raw characters? Apply them (with tags, if given)
			to the text buffer
		"""
		if len(self.tags):
			# there are tags, apply them to the text
			self.textbuffer.insert_with_tags(
				self.textbuffer.get_end_iter(),
				text,
				*self.tags)
		else:
			# no tags, just add the text
			self.textbuffer.insert(
				self.textbuffer.get_end_iter(),
				text)

	def startDocument(self):
		pass

	def startElement(self, name, attrs):


		if not name in self.no_cache:

			cname = self._get_cache_name(name,attrs)

			tag = self.textbuffer.get_tag_table().lookup(cname)

			if tag: # found a already known tag, use it
				self._apply_tag(name, tag)
				return

		# handle no tag creating elements

		if name == "br":
			self.textbuffer.insert(self.textbuffer.get_end_iter(),"\n")
			return

		# create a new tag

		if name in self.no_cache:
			tag = self.textbuffer.create_tag(None)
		else:
			tag = self.textbuffer.create_tag(
				self._get_cache_name(name, attrs))

		tag.s_attribute = {} # special attribute for identifying

		tag.s_attribute[name] = True

		if name == "b":
			tag.set_property("weight", pango.WEIGHT_BOLD)

		elif name == "i":
			tag.set_property("style", pango.STYLE_ITALIC)

		elif name == "u":
			tag.set_property("underline", pango.UNDERLINE_SINGLE)

		elif name == "a":
			if self.URLHandler:
				tag.set_property("underline", pango.UNDERLINE_SINGLE)
				tag.connect("event", self.URLHandler, attrs["href"])
				tag.s_attribute["a.href"] = attrs["href"]

		elif name == "su":
			self.sucount += 1

			if self.sucount % 2 != 0:
				tag.set_property("underline", pango.UNDERLINE_SINGLE)
			else:
				tag.set_property("underline", pango.UNDERLINE_NONE)

		elif name == "sb":
			self.sbcount += 1
			if self.sbcount % 2 != 0:
				tag.set_property("weight", pango.WEIGHT_BOLD)
			else:
				tag.set_property("weight", pango.WEIGHT_NORMAL)

		elif name in ("font","span"):
			self._parseFont(tag, attrs)

		elif name == "msg":
			# start tag to avoid errors due to
			# missing overall-tag
			#
			self._parseFont(tag, attrs)


		self._apply_tag(name, tag)

	def endElement(self, name):
		if name in self.ignoreableEndTags:
			return

		try:
			i = self.elms.index(name)
		except ValueError:
			pass
		else:
			del self.elms[i]
			del self.tags[i]

	def endDocument(self):
		""" Close all special bold/underline tags. """

		if self.sbcount % 2 != 0 or self.sucount % 2 != 0:
			tag = self.textbuffer.create_tag(None)

			if self.sbcount % 2 != 0:
				tag.set_property("weight", pango.WEIGHT_NORMAL)

			if self.sucount % 2 != 0:
				tag.set_property("underline", pango.UNDERLINE_NONE)

			self.textbuffer.insert_with_tags(
				self.textbuffer.get_end_iter(),
				"",
				tag)

		self._reset_values()

	""" PARSING HELPER """

	def _parseFont(self, tag, attrs):
		if not attrs or attrs.getLength() == 0:
			return

		for name in attrs.getNames():
			if name == "weight":
				if attrs[name] == "bold":
					tag.set_property("weight", pango.WEIGHT_BOLD)
				elif attrs[name] == "normal":
					tag.set_property("weight", pango.WEIGHT_NORMAL)
			elif name == "style":
				if attrs[name] == "italic":
					tag.set_property("style", pango.STYLE_ITALIC)
				elif attrs[name] == "normal":
					tag.set_property("style", pango.STYLE_NORMAL)
			else:
				try:
					tag.set_property(name, attrs[name])
				except Exception as ex:
					logging.error("_parseFont: %s" % (ex))

class ScanHandler(xml.sax.ContentHandler):

	def __init__(self):
		xml.sax.ContentHandler.__init__(self)

class HTMLBuffer(gtk.TextBuffer):

	__gtype_name__ = "HTMLBuffer"

	global_tagtable = gtk.TextTagTable()

	def __init__(self, handler=None, tagtable=None):
		self.lines = 0

		self.group_string = None
		self.group_color = False

		if tagtable:
			self.tagtable = tagtable
		else:
			self.tagtable = self.global_tagtable

		self.URLHandler = handler

		gtk.TextBuffer.__init__(self, self.tagtable)

		self.scanner = xml.sax.make_parser()
		self.parser = xml.sax.make_parser()

		self.scanner.setContentHandler(ScanHandler())

		contentHandler = HTMLHandler(self, self.URLHandler)
		self.parser.setContentHandler(contentHandler)

	def setURLHandler(self, handler):
		self.URLHandler = handler
		self.parser.getContentHandler().URLHandler = handler

	def getURLHandler(self):
		return self.URLHandler

	def clear(self):
		""" Clears the output and resets the tag
			table to zero to save memory.
		"""
		self.set_text("")

		# clear the tagtable
		tt = self.get_tag_table()
		if tt:
			tt.foreach(lambda tag,data: data.remove(tag), tt)

	def insert(self, iter, text, *x):
		" make the buffer a ring buffer with a limit of max_output_lines "
		siter = self.get_selection_bounds()

		if siter:
			soff = siter[0].get_offset()
			ioff = siter[1].get_offset()

		gtk.TextBuffer.insert(self, iter, text, *x)

		self.lines += text.count("\n")

		try:
			max_lines = int(config.get("tekka",
				"max_output_lines"))
		except ValueError:
			max_lines = int(config.get_default("tekka",
				"max_output_lines"))

		diff = self.lines - max_lines

		if diff > 0:
			a = self.get_iter_at_line(0)
			b = self.get_iter_at_line(diff)
			self.delete(a,b)
			self.lines -= diff

		if siter:
			self.select_range(
				self.get_iter_at_offset(soff),
				self.get_iter_at_offset(ioff)
			)
		# FIXME new selection range is off by some bytes

	def insert_html(self, iter, text, group_string=None):
		""" parse text for HTML markups before adding
			it to the buffer at the given iter.

			This method is deprecated. Use insert_html.
		"""
		startoffset = iter.get_offset()

		if gtk.TextBuffer.get_char_count(self) > 0:
			text = "<br/>" + text

		text = URLToTag(text)


		if self.group_string != group_string:
			self.group_string = group_string
			self.group_color = not self.group_color

		# color the lines, group coloring by some string
		if (config.get_bool("tekka","text_rules")
		and self.group_color
		and self.group_string):
			color = helper.color.get_color_by_key("rules_color").to_string()

			text = "<msg paragraph-background='%s'>%s</msg>" % (
						color, text)
		else:
			text = "<msg>%s</msg>" % text


		def applyToParser(text):
			try:
				self.parser.parse(StringIO(text))
			except xml.sax.SAXParseException,e:
				raise Exception,\
					"%s.applyToParser: '%s' raised with '%s'." % (e, text)


		while True:
			try:
				self.scanner.parse(StringIO(text))

			except xml.sax.SAXParseException, e:
				# Exception while parsing, get (if caused by char)
				# the character and delete it. Then try again to
				# add the text.
				# If the exception is caused by a syntax error,
				# abort parsing and print the error with line
				# and position.

				pos = e.getColumnNumber()
				line = e.getLineNumber()

				if (pos-2 >= 0 and text[pos-2:pos] == "</"):
					logging.error("Syntax error on line %d, "\
						"column %d: %s\n\t%s" % (
							line,
							pos,
							text[pos:],
							text))
					return

				logging.error("HTMLBuffer: faulty char on line %d "
					"char %d ('%s')" % (line, pos, text[pos]))

				# skip the faulty char
				text = text[:pos] + text[pos+1:]

				continue

			else:

				# everything went fine, no need
				# for looping further.
				applyToParser(text)

				break
