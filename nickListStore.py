import gtk,gobject


class nickListStore(gtk.ListStore):
	"""
Store class for the nickList widget.
Stores the prefix and the nick name
in a list:
<prefix_0>,<nick_0>
<prefix_1>,<nick_1>
...

prefix is a item of nickListStore.modes,
nick is a string.
	"""

	COLUMN_PREFIX=0
	COLUMN_NICK=1

	def __init__(self, nicks=None):
		gtk.ListStore.__init__(self, gobject.TYPE_STRING, gobject.TYPE_STRING)

		if nicks:
			self.addNicks(nicks)
		self.modes = ["*","!","@","%","+"," "]

	def findRow(self, store, column, needle):
		"""
		Iterating through ListStore `store` and
		comparing the content of the column (identified
		by `column`) with needle.
		If a match is found the row is returned.
		"""
		for row in store:
			if row[column] == needle:
				return row
		return None

	def findLowerRow(self, store, column, needle):
		"""
		Strings only.
		Does the same as findRow but compares the 
		lower cased content of the column with the
		lower cased needle so character case does not
		matter.
		"""
		for row in store:
			if row[column].lower() == needle.lower():
				return row
		return None

	def addNicks(self, nicks):
		"""
		Adds a list of nicks to the nickListStore.
		After adding all nicks sortNicks is called.
		"""
		if not nicks or len(nicks) == 0:
			return
		for nick in nicks:
			self.appendNick(nick,sort=False)
		self.sortNicks()

	def getNicks(self):
		"""
		returns all nick names(!) stored
		"""
		return [l[self.COLUMN_NICK] for l in self if l is not None ]

	def appendNick(self, nick, sort=True):
		""" 
		appends a nick to the store, if sort is false, 
		data in the nickListStore would'nt be sorted in-place
		"""
		store = self
		iter = store.append(None)
		store.set(iter, self.COLUMN_NICK, nick)

		if sort:
			self.sortNicks()

	def modifyNick(self, nick, newnick):
		"""
		renames the nick `nick` to `newnick`
		"""
		store = self
		row = self.findRow(store, self.COLUMN_NICK, nick)
		if not row:
			return
		store.set(row.iter, self.COLUMN_NICK, newnick)

		self.sortNicks()

	def removeNick(self, nick):
		"""
		removes the whole column where nick name = `nick`
		"""
		store = self
		row = self.findRow(store, self.COLUMN_NICK, nick)
		if not row:
			return
		store.remove(row.iter)

	def setPrefix(self, nick, prefix, sort=True):
		"""
		sets the prefix `prefix` to the nick `nick`.
		After setting the prefix and sort is true
		the data in the nickListStore will be sorted
		in place.
		"""
		store = self
		row = self.findRow(store, self.COLUMN_NICK, nick)
		if not row:
			return
		row[self.COLUMN_PREFIX] = prefix

		if sort:
			self.sortNicks()

	def getPrefix(self, nick):
		"""
		returns the prefix for the nick identified
		by `nick`
		"""
		store = self
		row = self.findRow(store, self.COLUMN_NICK, nick)
		if not row:
			return " "
		return row[self.COLUMN_PREFIX]

	def searchNick(self, needle):
		"""
		returns a list of nicks wich are beginning with 
		the string `needle`
		"""
		return [l[self.COLUMN_NICK] for l in self if l and l[self.COLUMN_NICK][0:len(needle)].lower()==needle]

	def sortNicks(self):
		"""
	sort the nickListStore in-place by prefix and
	then by nick name
		"""
		store = self
		modes = self.modes
		nl = []

		for row in store:
			prefix = row[0] or " "
			nick = row[1]
			try:
				i = modes.index(prefix)
			except ValueError:
				print "sortNicks: i < 0"
				continue
			nl.append([i,nick])
		nl.sort(cmp=lambda a,b: cmp(a[0],b[0]) or cmp(a[1].lower(),b[1].lower()))
		store.clear()
		for (prefix,nick) in nl:
			iter = store.append(None)
			prefix = modes[prefix]
			store.set(iter, 0, prefix, 1, nick)

