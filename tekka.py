import sys
import imp
import config
import com
import commands

gui = None
pluginPaths = []
_plugins = {}

# FIXME:  it would be probably a problem that the plugins are
# FIXME:: set up after the sucessful connect to maki. Check this!

class sushiPluginHandler(object):
	"""
	interface connecting dbus and plugins.
	"""

	def __init__(self, plugin, sushi):
		"""
			plugin: the name of the plugin receiving the instance of the class
			sushi: dbus.Interface connected to de.ikkoku.sushi
		"""
		self._plugin = plugin
		self._sushi = sushi

	def _check(self, handler, *args):
		"""
			Forwards args to handler if the plugin
			is permitted to receive signals (loaded and enabled).
		"""
		if (_plugins.has_key(self._plugin) and
			_plugins[self._plugin]["enabled"]):

			handler(*args)

	def connect_to_signal(self, signal, handler):
		"""
			tries to associate signal with handler.
			it adds a check function "over" handler
			which checks every time it was called if
			the plugin is permitted to receive the
			data (=> plugin enabled yes/no).
		"""
		try:
			_plugins[self._plugin]["signals"].index(signal)
		except ValueError:
			self._sushi.connect_to_signal(signal, lambda *x: self._check(handler,*x))
			_plugins[self._plugin]["signals"].append(signal)
		else:
			# already connected
			return False

	def __getattr__(self, member):
		if member.startswith('__') and member.endswith('__'):
			raise AttributeError(member)
		else:
			return eval("self._sushi.%s" % member)


class plugin(object):

	def __init__(self, name):
		global _plugins

		if not _plugins.has_key(name):
			raise Exception("No entry for plugin.")

		_plugins[name]["object"] = self

		self.__name = name
		self.__proxy = None
		self.__commands = []

	def get_commands(self):
		return list(self.__commands)

	def get_name(self):
		return str(self.__name)

	def get_module(self):
		return self.__module
	
	def get_dbus_interface(self):
		if not self.__proxy:
			self.__proxy = sushiPluginHandler(self.__name, com.sushi)
		return self.__proxy

	def register_command(self, command, callback):
		if not _plugins.has_key(command) or not _plugins[self.__name]["enabled"]:
			return

		try:
			self.__commands.index(command)
		except ValueError:
			ret = commands.addCommand(command, callback)
			if ret:
				self.__commands.append(command)
			return ret
		else:
			return False

	def plugin_info(self):
		return ("Basic plugin class", "0.1")

	def set_option(self, option, value):
		config.addSection(self.__name)
		if value:
			return config.set(self.__name, option, value)
		else:
			return config.unset(self.__name, option)

	def get_option(self, option):
		return config.get(self.__name, option)

	def get_gui(self):
		return gui


"""
	Methods for plugin stuff.
"""

def _registerPlugin(name, module):
	"""
		Registers the plugin in a global dict.
		Only loaded plugins would be registered.
	"""
	global _plugins

	if _plugins.has_key(name):
		print "double plugin '%s'!" % (name)
		return False

	_plugins[name]={
		"object":None,
		"module":module,
		"signals":[],
		"enabled":True
		}

	return True

def hasPlugin(name):
	"""
		Returns True if the plugin
		is registered.
	"""
	if _plugins.has_key(name):
		return True
	return False

def isLoaded(name):
	"""
		Returns True if the plugin
		is loaded.
	"""
	if not hasPlugin(name):
		return False
	return _plugins[name]["enabled"]

def loadPlugin(name):
	"""
		searches for a module named like `name` in
		pluginPaths. If a suitable module was found,
		load it, set the plugin-API-methods to the
		module and register it in global dict `plugins`.
		Then call the __init__ function in the module.

		If a plugin was already loaded (plugins[name] exists)
		reload the module and change "enabled" flag to True.

		If the load was successful this method returns True,
		otherwise False.
	"""
	if not pluginPaths:
		print "No search paths."
		return

	global _plugins

	# search for plugin in plugin path

	oldPath = sys.path
	sys.path = pluginPaths

	if _plugins.has_key(name):
		print "Module already existing. Enabling."

		data = _plugins[name]

		# perform a reload of the module
		
		reload(data["module"])
		data["enabled"] = True

		sys.path = oldPath
		
		return True

	modTuple = None
	try:
		modTuple = imp.find_module(name)
	except ImportError, e:
		print "E: ", e
		pass

	# reset old search path
	sys.path = oldPath

	if not modTuple:
		print "no such plugin found '%s'" % (name)
		return False

	plugin = None
	try:
		plugin = imp.load_module(name, *modTuple)
	except ImportError,e:
		print "Failure while loading plugin '%s': " % (name), e
	finally:
		try:
			modTuple[0].close()
		except (IndexError,AttributeError):
			pass

	if not plugin:
		return False

	if not _registerPlugin(name, plugin):
		# registration failed, abort loading..
		print "registration failed."
		return False

	plugin.load()
	return True

def unloadPlugin(name):
	"""
		removes the plugin (refcount = 0).
		Before the deletion is made, __destruct__
		is called in the module.

		On successful unload the method returns True,
		otherwise False.
	"""
	global _plugins

	if not _plugins.has_key(name):
		print "no such plugin registered ('%s')" % (name)
		return False

	try:
		_plugins[name]["module"].unload()
	except AttributeError:
		pass

	for command in _plugins[name]["object"].get_commands():
		commands.removeCommand(command)

	_plugins[name]["enabled"] = False
	return True

def setup(_gui):
	"""
		module setup function.
	"""
	global gui, pluginPaths


	# if the call is a re-setup reload all plugins
	# TODO: check if this is needed.
	# TODO:: (connection to maki lost -> reconnect)
	if _plugins:
		for key in _plugins:
			unloadPlugin(key)
			loadPlugin(key)

	gui = _gui

	# TODO: make multiple plugin paths possible
	path = config.get("tekka", "plugin_dir", default="")

	if not path: return

	pluginPaths.append(path)

	autoLoads = config.get("autoload_plugins").values()

	for plugin in autoLoads:
		print "auto loading '%s'" % (plugin)

		loadPlugin(plugin)
