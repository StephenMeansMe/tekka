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
import gobject

from typecheck import types

class NickListStore(gtk.ListStore):
	"""
	Store class for the nickList widget.
	Stores the prefix and the nick name
	in a list:
	<prefix_0>,<nick_0>
	<prefix_1>,<nick_1>
	...

	prefix is a item of NickListStore.modes,
	nick is a string.
	"""

	COLUMN_PREFIX=0
	COLUMN_NICK=1

	def __init__(self, nicks=None, prefixes=None):
		gtk.ListStore.__init__(self, gobject.TYPE_STRING, gobject.TYPE_STRING)

		self.__modes = []
		# user count, operator count, dowehaveoperators?
		self.__count = 0
		self.__opcount = 0

		if nicks and prefixes and len(nicks) == len(prefixes):
			self.add_nicks(nicks, prefixes)

	def __len__(self):
		return self.__count

	def get_operator_count(self):
		return self.__opcount

	def set_modes(self, modes):
		self.__modes = list(modes)
		self.__modes.append(" ") # append the empty mode
		print "self.__modes = %s"  % self.__modes

	@types(needle = basestring)
	def find_nick_row(self, needle):
		for row in self:
			if row[self.COLUMN_NICK].lower() == needle.lower():
				return row
		return None

	def add_nicks(self, nicks, prefixes):
		"""
		Adds a list of nicks to the NickListStore.
		After adding all nicks sortNicks is called.
		"""
		if not nicks or not prefixes:
			return

		for i in range(len(nicks)):
			self.append_nick(nicks[i], sort=False)
			self.set_prefix(nicks[i], prefixes[i], sort=False)

		self.sort_nicks()

	def get_nicks(self):
		"""
		returns all nick names stored
		"""
		return [l[self.COLUMN_NICK] for l in self if l is not None ]

	def get_nicks_mode(self):
		""" return a tuple per nick with (prefix,nick) """
		return [
			(l[self.COLUMN_PREFIX],l[self.COLUMN_NICK]) for l in self
			if l]

	def append_nick(self, nick, sort=True):
		"""
		appends a nick to the store, if sort is false,
		data in the NickListStore would'nt be sorted in-place
		"""
		iter = self.append(None)
		self.set(iter, self.COLUMN_NICK, nick)

		self.__count += 1

		if sort:
			self.sort_nicks()

	def modify_nick(self, nick, newnick):
		"""
		renames the nick `nick` to `newnick`
		"""
		row = self.find_nick_row(nick)

		if row:
			self.set(row.iter, self.COLUMN_NICK, newnick)
			self.sort_nicks()

	def remove_nick(self, nick):
		"""
		removes the whole column where nick name = `nick`
		"""
		store = self
		row = self.find_nick_row(nick)

		if not row:
			return

		if row[self.COLUMN_PREFIX] in self.__modes[:-2]:
			self.__opcount -= 1

		self.__count -= 1

		store.remove(row.iter)

	def clear(self, count_reset = True):
		"""
		remove all entries from the store
		and set counts to 0.
		"""
		gtk.ListStore.clear(self)

		if count_reset:
			self.__count = 0
			self.__opcount = 0

	def set_prefix(self, nick, prefix, sort=True):
		"""
		sets the prefix `prefix` to the nick `nick`.
		After setting the prefix and sort is true
		the data in the NickListStore will be sorted
		in place.
		"""
		row = self.find_nick_row(nick)

		if not row:
			return

		# list without voice and no-mode
		op_pre = self.__modes[:-2]

		if row[self.COLUMN_PREFIX] in op_pre and prefix not in op_pre:
			# op goes to non-op
			self.__opcount -= 1

		elif row[self.COLUMN_PREFIX] not in op_pre and prefix in op_pre:
			# wasn't an op and becomes one
			self.__opcount += 1

		row[self.COLUMN_PREFIX] = prefix

		if sort:
			self.sort_nicks()

	def get_prefix(self, nick):
		""" returns the prefix for the nick identified
			by `nick`. If the nick is not found
			None is returned.
		"""
		row = self.find_nick_row(nick)

		if not row:
			return None

		return row[self.COLUMN_PREFIX]

	def search_nick(self, needle):
		""" returns a list of nicks wich are beginning with
			the string `needle`
		"""
		return [l[self.COLUMN_NICK] for l in self
			if l and l[self.COLUMN_NICK][0:len(needle)].lower()==needle]

	def search_nick_by_prefix(self, prefixes):
		""" Searches for nicks which prefix is in the tuple prefixes
			and returns the found nicks as a list.
		"""
		return [l[self.COLUMN_NICK] for l in self
			if l and l[self.COLUMN_PREFIX] in prefixes]

	def sort_nicks(self):
		""" sort the NickListStore in-place by prefix and
			then by nick name
		"""
		modes = self.__modes
		nl = []

		for row in self:
			prefix = row[self.COLUMN_PREFIX] or " "
			nick = row[self.COLUMN_NICK]

			try:
				i = modes.index(prefix)
			except ValueError:
				print "sort_nicks: prefix for %s (%s) not in modes (%s)" %(
					nick, prefix, self.__modes)

			nl.append([i,nick])

		nl.sort( cmp = lambda a,b: (cmp(a[0], b[0])
			or cmp(a[1].lower(), b[1].lower())) )

		self.clear(count_reset = False)

		for (prefix, nick) in nl:
			try:
				prefixSign = modes[prefix]
			except IndexError:
				prefixSign = "?"

			self.append(row = (prefixSign, nick))
