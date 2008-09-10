import gtk
import gtk.glade
import config
import com

widgets = None

def readLog(tab):
	logDir = "/home/nemo/.local/share/sushi/logs/"

	if tab.is_server():
		return

	name = logDir+"/"+tab.server+"/"+tab.name+".txt"
	try:
		fd = file(name,"r")
	except IOError:
		print "IOERROR WHILE READING '%s'" % (name)
		return None

	dateOffsets = {}
	lastDate = ""
	offset = 0
	startOffset = None

	for line in fd:
		date = line.split(" ")[0]

		offset += len(line)
		
		if not lastDate:
			lastDate = date
			startOffset = 0L
			continue

		if lastDate != date:
			# close lastDate

			dateOffsets[lastDate] = (startOffset, offset-len(line))

			lastDate = date
			startOffset = offset


	return (fd, dateOffsets)

def fillCalendar(calendar):
	
	mkey = "%02d-%02d-%%02d" % calendar.get_properties("year","month")

	for day in range(1,32):
		key = mkey % day

		if calendar.offsets.has_key(key):
			calendar.mark_day(day)

def calendar_realize_cb(calendar):
	"""
		initial fill.
	"""
	fillCalendar(calendar)
	calendar_day_selected_cb(calendar)

def calendar_month_changed_cb(calendar):
	"""
		get all days which have a history and
		highlight them.
	"""
	fillCalendar(calendar)

def calendar_day_selected_cb(calendar):
	"""
		get the history of calendar.day from maki.
	"""
	key = "%02d-%02d-%02d" % calendar.get_properties("year","month","day")

	buffer = widgets.get_widget("historyView").get_buffer()

	if not calendar.offsets.has_key(key):
		print "no such entry!"
		buffer.set_text("")	
		return

	(start,end) = calendar.offsets[key]
	calendar.fd.seek(start)
	buffer.set_text(calendar.fd.read(end-start))

def run(tab):
	calendar = widgets.get_widget("calendar")
	calendar.tab = tab

	fdata = readLog(tab)

	if not fdata:
		# TODO: error dialog
		return

	calendar.fd = fdata[0]
	calendar.offsets = fdata[1]

	dialog = widgets.get_widget("historyDialog")

	result = dialog.run()
	
	dialog.destroy()

	fdata[0].close()

def setup(dialog):
	"""
	"""
	global widgets
	
	widgets = gtk.glade.XML(config.get("gladefiles","dialogs"), "historyDialog")

	sigdic = {
		"calendar_month_changed_cb" : calendar_month_changed_cb,
		"calendar_day_selected_cb" : calendar_day_selected_cb
	}

	widgets.get_widget("calendar").connect("realize", calendar_realize_cb)

	widgets.signal_autoconnect(sigdic)
