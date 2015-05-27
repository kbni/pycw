# Author: Alex Wilson <alex@kbni.net>
# License: None, but be cool.

import datetime, time, dateutil.parser
import copy
import email.parser # This is a bit WTF, isn't it? (It's for parsing email attachments in tickets.)

class CWObjectIsStale(Exception):
	pass

class CWObjectNotFound(Exception):
	pass

class ConnectWiseORM:
	def __init__( self, caddy ):
		self.pycw_types = {}
		self.caddy = caddy
		self.cache = {}

		# This is kind of nasty - but we need dict of all CWObject items
		for k,v in globals().iteritems():
			if [ True for x in ( '_id_fields', '_name', '_load') if hasattr(v, x) ]:
				self.pycw_types[k] = v

	def __repr__( self ):
		return "<ConnectwiseORM(id=%s)>" % id(self)

	def __str__( self ):
		return str(self.__repr__())

	def search(self, obj_name, conditions, limit=None, skip=None, orderby=None):
		obj = self.pycw_types.get(obj_name, None)

		if not obj and hasattr(obj_name, '_name'):
			obj = obj_name
			obj_name = obj._name

		if obj._search_cond:
			if conditions and conditions != '':
				conditions = '%s And ( %s )' % ( obj._search_cond, conditions )
			else:
				conditions = obj._saerch_cond

		if '.' in obj._search:
			search_api, search_func = obj._search.split('.')
			kwargs = dict()

			if limit is not None: kwargs['limit'] = limit
			if limit is not None: kwargs['skip'] = skip
			if limit is not None: kwargs['orderBy'] = orderby

			soap_res = self.caddy.soap_call(search_api, search_func, conditions, **kwargs)
			results = []

			if soap_res:
				for x in soap_res[0]:
					for id_field in obj._id_fields:
						if hasattr(x, id_field):
							found_obj = self._load_object(obj_name, getattr(x, id_field))
							if found_obj not in results:
								results.append( found_obj )
						elif hasattr(x, 'Id'):
							found_obj = self._load_object(obj_name, x.Id)
							if found_obj not in results:
								results.append( found_obj )

			return results

	def _load_object(self, load_obj, *crit1, **crit2):
		if load_obj in self.pycw_types.keys():
			load_obj = self.pycw_types[load_obj]

		if len(crit1) == 0:
			o = load_obj(orm=self, record_id=None, **crit2)
			return o

		if crit1 and len(crit1) == 1 and isinstance(crit1[0], int):
			key = (load_obj, crit1[0])

			o = self.cache.get(key, None)
			if o is not None:
				return o

			o = load_obj(orm=self, record_id=crit1[0], **crit2)
			self.cache[key] = o
			return o

		if crit2 and crit2.has_key('parent') and crit2.has_key('from_basic'):
			found_id = crit2['from_basic'].Id
			key = (load_obj, found_id)

			o = self.cache.get(key, None)
			if o is not None:
				o.load(use_data=crit2['from_basic'])
				return o

			o = load_obj(orm=self, record_id=found_id, **crit2)
			self.cache[key] = o
			return o

		raise CWObjectNotFound("%s %s" % ( str(crit1), str(crit2) ))

	def _walk_attributes( self, parent, use_type, *args ):
		def deepgetattr(obj, attr):
			"""Recurses through an attribute chain to get the ultimate value."""
			try:
				return reduce(getattr, args, obj)
			except AttributeError:
				return []

		deepval = deepgetattr(parent.load_data, args)

		def fake_append(self, obj):
			print 'fake_append', self, obj

		def fake_remove(self, obj):
			print 'fake_remove', self, obj

		if use_type in self.pycw_types.keys():
			for new_child in [ self._load_object(use_type, parent=parent, from_basic=d) for d in deepval ]:
				parent.new_child(new_child)
			our_list = [ obj for obj in parent.children if isinstance(obj, self.pycw_types[use_type]) ]
			return our_list
		else:
			return use_type(deepval)

	def __getattr__(self, key):
		if self.pycw_types.has_key(key):

			def load_it( *crit1, **crit2 ):
				return self._load_object(key, *crit1, **crit2)
			return load_it
		raise AttributeError("%s has no attribute %s" % (self, key))

class CWObject(object):
	orm = None 
	parent = None
	attrs = []
	children = []

	old = None
	base = None
	new = None

	_name = 'None'        #
	_use_basic = False    # 
	_load = False         # 'APIname.APIfunc' or 'FROM_PARENT'
	_save = False         # 'APIname.APIfunc' or 'FROM_PARENT'
	_search = False       # 'APIname.APIfunc'
	_search_cond = False  # If you need to add an additional comdition string to 

	def __init__(self, orm = None, record_id = None, parent = None, data = None, from_basic = None):
		"""
			@param orm =  ORM object
			@param record_id = Record ID to assign this object (is negative if not_real)
			@param data - Pre-loaded data, this would mostly be used for anything with parent_load = True
			@param parent_load - If load/save should be proxied through parent CWObject (such as for TicketNotes)
			@param parent - Parent CWObject, for relationship purposes only
		"""

		self.load_level = 0
		self.load_data = data
		self.record_id = 0 - id(self)

		self.changes_attrs = {}      # Changed attribute dict
		self.changes_funcs = []      # Functions that should be applied before save
		self.deleted = False         # HAs this item been deleted?

		if orm is not None:
			self.orm = orm

		self.old = None
		self.base = self.get_factory()
		self.data = self.get_factory()

		if parent is not None:
			self.parent = parent

			if self not in self.parent.children:
				self.parent.children.append(self)

		if record_id:
			self.record_id = record_id
			self.load()

		if False and from_basic is not None:
			for attr in dir(from_basic):
				if hasattr(self.data, attr):
					setattr(self.data, attr, getattr(from_basic, attr))

	def __repr__(self):
		"""
			Return <ObjectName(id=ObjectRecID)>, or <ObjectName(id=UNSAVED)> if object has not been saved!
		"""
		if not self.is_real_record():
			return '<%s(id=UNSAVED)>' % (self._name,)
		else:
			return '<%s(id=%s)>' % (self._name, self.record_id)

	def __str__(self):
		return str(self.__repr__())

	def parent_save(self):
		return self._save == 'FROM_PARENT'

	def parent_load(self):
		return self._load == 'FROM_PARENT'

	def is_real_record(self):
		return self.record_id and self.record_id > 0

	def allow_basic_load(self):
		return self._use_basic

	def update_cache(self):
		self.orm.update_cache(self)

	def has_full_load(self):
		"""
			Test if we have populated data yet
		"""
		return self.old is not None

	def require_full_load(self):
		if self.is_real_record() and not self.has_full_load():
			self.load()

		return self

	def load(self, use_data = None):
		if use_data is not None and self._use_basic:
			self.load_data = use_data
			self.load_level = 1
			return self # successful load

		if '.' in self._load:
			load_api, load_func = self._load.split('.')
			self.old = self.orm.caddy.soap_call(load_api, load_func, self.record_id)
			self.data = copy.copy(self.old)
			self.load_level = 3
			return self # successful load

		if self._load == 'FROM_PARENT':
			self.load_level = 2
			if self.parent.load():
				if hasattr(self, 'load_from_parent'):
					self.load_from_parent()
				return self # successful load
			else:
				return False

		return False

	def load_once(self):
		if not self.load_level or self.load_level == 0:
			return self.load()
		else:
			return self

	def save(self, *args, **kwargs):
		if self.parent and self._save == 'FROM_PARENT':
			self.parent.save()
			return self

		if not self._save or not '.' in self._save:
			return False

		save_api, save_func = self._save.split('.')
		send_data = copy.deepcopy(self.data)

		for contact_type in 'Phones Emails Faxes Pagers'.split(' '):
			if hasattr(send_data, contact_type):
				remove_list = []
				for contact_item in getattr(send_data, contact_type)[0]:
					if contact_item.Value is None and contact_item.Id in (0, '0', None):
						remove_list.append(contact_item)

				for contact_item in remove_list:
					getattr(send_data, contact_type)[0].remove(contact_item)

				if len(getattr(send_data, contact_type)[0]) == 0:
					delattr(send_data, contact_type)

		if save_func == 'AddOrUpdateTicketNote':
			saved_data = self.orm.caddy.soap_call(save_api, save_func, send_data, self.parent.record_id)
		elif save_func.endswith('ViaCompanyId'):
			saved_data = self.orm.caddy.soap_call(save_api, save_func, send_data.CompanyId, send_data)
		elif save_func.endswith('ViaCompanyIdentifier'):
			saved_data = self.orm.caddy.soap_call(save_api, save_func, send_data.CompanyIdentifier, send_data)
		else:
			saved_data = self.orm.caddy.soap_call(save_api, save_func, send_data, *args)

		self.old = saved_data
		self.data = copy.copy(self.old)

		for id_attr in list(self._id_fields + ['RecordId','Id',]):
			if hasattr(self.data, id_attr):
				self.record_id = int(getattr(self.data, id_attr))
				break

		sleep_time = kwargs.get('sleep', 0)
		if sleep_time > 0:
			time.sleep(sleep_time)

		return self

	def __setattr__(self, key, val):
		if hasattr(self.base, key):
			setattr(self.data, key, val)
		else:
			super(CWObject, self).__setattr__(key, val)

	def __getattr__(self, key):
		if hasattr(self.base, key):
			return getattr(self.data, key)
		else:
			raise AttributeError('No such attribute in data: %s' % key)

	def delete(self):
		pass

	def get_factory(self, diff_factory_name = None):
		if '.' in self._factory:
			api_name, factory_name = self._factory.split('.')
			if diff_factory_name is not None:
				factory_name = diff_factory_name
			soap_client = self.orm.caddy.get_client(api_name)
			return soap_client.factory.create(factory_name)

	def discard(self):
		if self.parent and self.parent_load:
			self.parent.discard()
			return self
		else:
			self.changes_attrs = {}
			self.changes_funcs = []
			return self

	def new_child(self, new_child):
		if new_child not in self.children:
			self.children.append(new_child)
		return new_child

class Configuration(CWObject):
	_name = 'Configuration'
	_factory = 'Configuration.Configuration'
	_load = 'Configuration.LoadConfiguration'
	_search = 'Configuration.FindConfigurations'
	_save = 'Configuration.AddOrUpdateConfiguration'
	_id_fields = [ 'ConfigID', 'ConfigurationID' ]

class Activity(CWObject):
	_name = 'Activity'
	_factory = 'Activity.Activity'
	_load = 'Activity.LoadActivity'
	_search = 'Activity.FindActivities'
	_save = 'Activity.AddOrUpdateActivity'
	_delete = 'Activity.DeleteActivity'
	_id_fields = [ 'SOActivityRecID', 'ActivityID', 'ActivityRecID' ]

class Company(CWObject):
	_name = 'Company'
	_load = 'Company.LoadCompany'
	_search = 'Company.FindCompanies'
	_save = 'Company.AddOrUpdateCompany'
	_factory = 'Company.Company'
	_id_fields = [ 'CompanyRecordId', 'CompanyRecId', 'CompanyRecID' ]

class TicketScheduleEntry(CWObject):
	_name = 'TicketScheduleEntry'
	_factory = 'Scheduling.TicketScheduleEntry'
	_load = 'Scheduling.GetTicketScheduleEntry'
	_search = 'Scheduling.FindScheduleEntries'
	_search_cond = '( ScheduleType = "Service" OR ScheduleType = "Project" )'
	_save = 'Scheduling.AddOrUpdateTicketScheduleEntry'
	_id_fields = [ ]

class ActivityScheduleEntry(CWObject):
	_name = 'ActivityScheduleEntry'
	_factory = 'Scheduling.ActivityScheduleEntry'
	_load = 'Scheduling.GetActivityScheduleEntry'
	_search = 'Scheduling.FindActivityEntries'
	_search_cond = 'ScheduleType = "Sales"'
	_save = 'Scheduling.AddOrUpdateActivityScheduleEntry'
	_id_fields = [ ]

class MiscScheduleEntry(CWObject):
	_name = 'MiscScheduleEntry'
	_factory = 'Scheduling.MiscScheduleEntry'
	_load = 'Scheduling.GetMiscScheduleEntry'
	_search = 'Scheduling.FindMiscEntries'
	_search_cond = 'ScheduleType = "Sales"'
	_save = 'Scheduling.AddOrUpdateMiscScheduleEntry'
	_id_fields = [ ]

class Contact(CWObject):
	_name = 'Contact'
	_load = 'Contact.LoadContact'
	_search = 'Contact.FindContacts'
	_save = 'Contact.AddOrUpdateContact'
	_delete = 'Contact.DeleteContact'
	_factory = 'Contact.Contact'
	_id_fields = [ 'ContactRecID', 'ContactID', 'ContactId' ]

	def get_birthday(self):
		if self.data.BirthDay and isinstance(self.data.BirthDay, datetime.datetime):
			try:
				return self.data.BirthDay.strftime('%Y%m%d')
			except ValueError:
				return # connectwise fuck us again

	def set_birthday(self, birthday_str):
		if isinstance(birthday_str, str):
			self.data.BirthDay = datetime.datetime.fromtimestamp(time.mktime(time.strptime(birthday_str.replace('-',''), "%Y%m%d")))
		if isinstance(birthday_str, datetime.datetime):
			self.data.BirthDay = birthday_str
		return self.data.BirthDay

	def get_company(self):
		if self.data.CompanyIdentifier is not None:
			res = self.orm.search('Company', 'CompanyIdentifier = "%s"' % self.data.CompanyIdentifier)
			if res:
				return res[0]

	def get_full_name(self):
		return '%s %s' % (self.FirstName, self.LastName)

class TimeEntry(CWObject):
	_name = 'TimeEntry'
	_factory = 'TimeEntry.TimeEntry'
	_load = 'TimeEntry.LoadTimeEntry'
	_search = 'TimeEntry.FindTimeEntries'
	_save = 'TimeEntry.AddOrUpdateTimeEntry'
	_delete = 'TimeEntry.DeleteTimeEntry'
	_id_fields = [ ]

class TicketNote(CWObject):
	_name = 'TicketNote',
	_factory = 'ServiceTicket.TicketNote'
	_load = 'FROM_PARENT'
	_search = 'NOT_AVAILABLE'
	_save = 'ServiceTicket.AddOrUpdateTicketNote'
	_id_fields = [ 'NoteId', ]
	_use_basic = True,

	def load_from_parent(self):
		if self.parent._name == 'ServiceTicket':
			for attr in ('ResolutionDescription','InternalAnalysisNotes','DetailNotes'):
				note_attr = getattr(self.parent.data, attr, None)
				if note_attr and len(note_attr[0]) > 0:
					for tn_data in note_attr[0]:
						if tn_data.Id == self.record_id:
							self.data = tn_data
							return self

class ServiceTicket(CWObject):
	_name = 'ServiceTicket'
	_factory = 'ServiceTicket.ServiceTicket'
	_load = 'ServiceTicket.LoadServiceTicket'
	_search = 'ServiceTicket.FindServiceTickets'
	_save = 'ServiceTicket.AddOrUpdateServiceTicketViaCompanyIdentifier'
	_id_fields = [ 'TicketNumber', ]

	original_email = None

	def assoc_configuration(self, config):
		_TicketConfiguration = self.orm.caddy.get_client('ServiceTicket').factory.create('TicketConfiguration')
		_ArrayOfTicketConfiguration = self.orm.caddy.get_client('ServiceTicket').factory.create('ArrayOfTicketConfiguration')
		_ArrayOfTicketNote = self.orm.caddy.get_client('ServiceTicket').factory.create('ArrayOfTicketNote')

		if not self.data.Configurations or self.data.Configurations == "":
			self.data.Configurations = _ArrayOfTicketConfiguration

		_TicketConfiguration.Id = config.record_id
		self.data.Configurations[0].append(_TicketConfiguration)

	def first_ticket_note(self):
		if not self.DetailNotes:
			return False
		first_note = None
		for note in self.DetailNotes[0]:
			if first_note is None or first_note.Id > note.Id:
				first_note = note
		return self.orm.TicketNote(first_note.Id, parent=self)

	def first_internal_note(self):
		if not self.InternalAnalysisNotes:
			return False
		first_note = None
		for note in self.InternalAnalysisNotes[0]:
			if first_note is None or first_note.Id > note.Id:
				first_note = note
		return self.orm.TicketNote(first_note.Id, parent=self)

	def first_ticket_doc(self):
		if not self.Documents:
			return False
		first_doc = None
		for doc in self.Documents[0]:
			if first_doc is None or first_doc.Id > doc.Id:
				first_doc = doc
		return first_doc

	def get_original_email(self):
		if self.original_email is not None:
			return self.original_email
		if not self.Documents:
			return False

		first_doc = None
		for doc in self.Documents[0]:
			if ( first_doc is None or first_doc.Id > doc.Id ) and doc.FileName.endswith('.eml'):
				first_doc = doc

		if first_doc:
			real_doc = self.orm.caddy.soap_call('ServiceTicket', 'GetDocument', doc.Id)
			email_str = str(real_doc.Content).decode('base64','strict').decode('utf-8-sig').encode('utf-8')
			parsed = email.parser.Parser().parsestr(email_str)
			self.original_email = parsed
			return self.original_email
