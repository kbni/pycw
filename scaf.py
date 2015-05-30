# Author: Alex Wilson <alex@kbni.net>
# License: None, but be cool.

import sys
import os
import socket
import code
import datetime

import argparse
try:
	import configparser
except:
	import ConfigParser as configparser

import pycw

def hostname():
	import socket
	return socket.gethostname().split('.')[0]

def split_str(str_to_split):
	if ',' in str_to_split:
		return str_to_split.split(',')
	if '|' in str_to_split:
		return str_to_split.split('|')
	return [str_to_split,]

def first_or_false(chk_list):
	if len(chk_list) > 0:
		return chk_list[0]
	else:
		return False

def textual_bool(str_text):
	if not str_text:
		return False
	if str_text.lower() in ('y', 'yes', '1'):
		return True
	elif str_text.lower() in ('n', 'no', '0'):
		return False
	else:
		return None

class Scaffold:
	argparser = None
	args = None
	required_keys = None

	def __init__(self):
		"""

		"""
		defaults = dict(
			base_dir = '.',
			instance_id = self.__class__.__name__.split('.')[-1],
		)

		self.argparser = argparse.ArgumentParser()
		self.argparser.add_argument('--shell', dest='drop_to_shell', action='store_true', help='Just drop to shell after reading config')
		self.argparser.add_argument('--setup', dest='setup_config', action='store_true', help='create configuration files')
		self.argparser.add_argument('--base-dir', dest='base_dir', action='store', help='Find stale schedules', default=defaults['base_dir'])
		self.argparser.add_argument('--instance-id', dest='instance_id', action='store', help='Unique instance ID', default=defaults['instance_id'])
		self.required_config_keys = [ 'connectwise.hostname', 'connectwise.password', 'connectwise.username', 'connectwise.database' ]

	def add_argument(self, *args, **kwargs):
		"""
		Proxy to ArgumentParser.add_argument()
		"""
		return self.argparser.add_argument(*args, **kwargs)

	def setup(self):
		"""
		Quick and nasty setup..
		"""

		print "Are you okay with the following configuration locations?"
		print "  Base Directory (--base-dir) = %s" % self.args.base_dir
		print "  Instance Id (--instance-id) = %s" % self.args.instance_id
		print "Using these two values, we will write to the following file"
		print "  %s" % self.get_config_file()
		print "If this is cool, type yes"

		if raw_input(">") != "yes":
			self.fatal('aborted setup..')

		if not os.path.exists(self.args.base_dir):
			os.mkdir(self.args.base_dir)

		if not os.path.exists(os.path.join(self.args.base_dir, 'etc')):
			os.mkdir(os.path.join(self.args.base_dir, 'etc'))

		print "Let's run through some configuration items. If you are unsure, read the manual."

		new_config = configparser.ConfigParser()

		for req_key in self.required_config_keys:
			new_data = raw_input("[%s]\n>" % req_key)
			if not new_data:
				self.fatal('bad data entered..')
			else:
				sec, key = req_key.split('.')
				if not new_config.has_section(sec):
					new_config.add_section(sec)
				new_config.set(sec, key, new_data)

		with open(self.get_config_file(), 'wb') as config_fh:
			new_config.write(config_fh)

	def get_config_file(self):
		return os.path.join(self.args.base_dir, 'etc', self.args.instance_id+'.ini')

	def run(self):
		"""
		Check with have core configuration values and get started!
		"""

		self.args = self.argparser.parse_args()

		if self.args.setup_config:
			self.setup()

		if not os.path.exists(self.get_config_file()):
			self.fatal("config_file does not exist: %s" % config_file)
		else:
			self._config = configparser.ConfigParser()
			self._config.read(self.get_config_file())
			for req_key in self.required_config_keys:
				self.ini(*req_key.split('.'))

		self.cw = pycw.cw_orm(
			self.ini('connectwise', 'hostname'),
			self.ini('connectwise', 'database'),
			self.ini('connectwise', 'username'),
			self.ini('connectwise', 'password'),
		)

		if self.error_count > 0:
			self.fatal('too many errors, unable to start()')

		elif self.args.drop_to_shell:
			self.shell()

		else:
			try:
				for func in ( self.start, self.loop, self.finish ):
					func()
				sys.exit(0)
			except KeyboardInterrupt:
				self.stop()

	#
	# Now, here's the methods you should be overriding
	#

	def start(self):
		"""
		This is run at the start of your script, for things like
		* Establishing connections to other databases
		* Caching values for repetitive use in loop()
		* Requesting user-input
		"""
		pass

	def loop(self):
		"""
		This is the meat of your script, this will not loop by itself
		so you should add something to it. :)
		"""
		pass

	def finish(self):
		"""
		This is finished when a script succesfully finishes
		* Disconnect from external-databases (like who bothers with this anymore?)
		* Clean up any unused files or temporary databases
		* Success email notification??
		"""
		pass

	def stop(self):
		"""
		Catches Ctrl+C / SIGTERM
		* Same as finish(), except this will only run when 
		"""
		sys.exit(1)

	#
	#  Logging functions, we should probably replace this with logging module at some point
	# 

	def log(self, message, level='info', stdout_one_line=False):
		now = datetime.datetime.now()
		msg_start = '[%s][%-6s] ' % ( now.strftime('%Y%m%d %H%M'), level )
		len_start = len(msg_start)

		message = message.encode('utf-8', 'ignore')

		level_out = sys.stdout
		if level in ('fatal', 'error'):
			level_out = sys.stderr

		for line in str(message).split("\n"):
			level_out.write(msg_start+line+"\n")
			level_out.flush()
			if stdout_one_line:
				break
			msg_start = ' '*len_start

		if level == 'fatal':
			self.stop()

	info_count = 0
	def info(self, message, **kwargs):
		self.info_count += 1
		self.log(message, 'info', **kwargs)

	warning_count = 0
	def warning(self, message, **kwargs):
		self.warning_count += 1
		self.log(message, 'warn', **kwargs)

	debug_count = 0
	def debug(self, message, **kwargs):
		self.debug_count += 1
		self.log(message, 'debug', **kwargs)

	error_count = 0
	def error(self, message, **kwargs):
		self.error_count += 1
		self.log(message, 'error', **kwargs)

	fatal_count = 0
	def fatal(self, message, **kwargs):
		self.fatal_count += 1
		self.log(message, 'fatal', **kwargs)

	#  Configuration stuff

	def ini(self, section, key_name, default=-1):
		if self._config._sections.has_key(section):
			if self._config._sections[section].has_key(key_name):
				val = self._config._sections[section][key_name]

				if default != -1 and isinstance(default, bool):
					return str(val).lower() in ('1', 'yes', 'true', 'y')
				return val

		if default == -1:
			self.error('no value for %s.%s in config file' % (section, key_name))
			return None

		return default

	#   Useful for testing, start with --shell to just get dumped to shell ;)

	def shell(self, use_locals=None):
		if use_locals is None:
			use_locals = {}
		code.interact(local=use_locals)
