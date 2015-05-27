# Author: Alex Wilson <alex@kbni.net>
# License: None, but be cool.

import suds.client
import hashlib
import re
import logging

api_locations = dict(
	Activity = '/v4_6_release/apis/2.0/ActivityApi.asmx?wsdl',
	Company = '/v4_6_release/apis/2.0/CompanyApi.asmx?wsdl',
	Configuration = '/v4_6_release/apis/2.0/ConfigurationApi.asmx?wsdl',
	Contact = '/v4_6_release/apis/2.0/ContactApi.asmx?wsdl',
	Invoice = '/v4_6_release/apis/2.0/InvoiceApi.asmx?wsdl',
	ManagedDevice = '/v4_6_release/apis/2.0/ManagedDeviceApi.asmx?wsdl',
	Marketing = '/v4_6_release/apis/2.0/MarketingApi.asmx?wsdl',
	Member = '/v4_6_release/apis/2.0/MemberApi.asmx?wsdl',
	Opportunity = '/v4_6_release/apis/2.0/OpportunityApi.asmx?wsdl',
	OpportunityConversion = '/v4_6_release/apis/2.0/OpportunityConversionApi.asmx?wsdl',
	Product = '/v4_6_release/apis/2.0/ProductApi.asmx?wsdl',
	Project = '/v4_6_release/apis/2.0/ProjectApi.asmx?wsdl',
	Purchasing = '/v4_6_release/apis/2.0/PurchasingApi.asmx?wsdl',
	Reporting = '/v4_6_release/apis/2.0/ReportingApi.asmx?wsdl',
	Scheduling = '/v4_6_release/apis/2.0/SchedulingApi.asmx?wsdl',
	ServiceTicket = '/v4_6_release/apis/2.0/ServiceTicketApi.asmx?wsdl',
	System = '/v4_6_release/apis/2.0/SystemApi.asmx?wsdl',
	TimeEntry = '/v4_6_release/apis/2.0/TimeEntryApi.asmx?wsdl',
)

from suds.plugin import MessagePlugin

def strip_control_characters(str_to_clean):  
		# unicode invalid characters  
		RE_XML_ILLEGAL = u'([\u0000-\u0008\u000b-\u000c\u000e-\u001f\ufffe-\uffff])|'
		RE_XML_ILLEGAL += u'([%s-%s][^%s-%s])|([^%s-%s][%s-%s])|([%s-%s]$)|(^[%s-%s])' % (
			unichr(0xd800),unichr(0xdbff),unichr(0xdc00),unichr(0xdfff),
			unichr(0xd800),unichr(0xdbff),unichr(0xdc00),unichr(0xdfff),
			unichr(0xd800),unichr(0xdbff),unichr(0xdc00),unichr(0xdfff),
		)

		str_to_clean = re.sub(RE_XML_ILLEGAL, '?', str_to_clean)  
		str_to_clean = re.sub(r"[\x01-\x1F\x7F]", "", input)  

		return str_to_clean
		# ascii control characters  
		#input = re.sub(r"[\x01-\x1F\x7F]", "", input)  
  

_illegal_xml_chars_RE = re.compile(u'[\x00-\x08\x0b\x0c\x0e-\x1F\uD800-\uDFFF\uFFFE\uFFFF]')
_illegal_xml_encoded_RE = re.compile('&#x.+;')
class RemoveNonValidChars(MessagePlugin):
	def received(self, context):
		context.reply = context.reply.replace('&#xD;', '')
		context.reply = _illegal_xml_chars_RE.sub('?', context.reply)
		context.reply = _illegal_xml_encoded_RE.sub('?', context.reply)
		context.reply = strip_control_characters(context.reply)
		fh = open('/tmp/last_received', 'w')
		fh.write(str(context.reply))
		fh.close()

class ClearEmpty(MessagePlugin):
	def clear_empty_tags(self, tags):
		for tag in tags:
			children = tag.getChildren()[:]
			if children:
				self.clear_empty_tags(children)
			if re.match(r'^<[^>]+?/>$', tag.plain()):
				tag.parent.remove(tag)
			if tag.parent:
				tag.parent.prune()

	def marshalled(self, context):
		self.clear_empty_tags(context.envelope.getChildren()[:])
		context.envelope = context.envelope.prune()

	def sending(self, context):
		context.envelope = re.sub('\s+<[^>]+?/>', '', context.envelope)

USE_CLIENT_PLUGINS = [ClearEmpty, RemoveNonValidChars]

class SoapLoader:
	def __init__( self, orm, server, companyid, username, password ):
		self.orm = orm

	def __getattr__( self, name ):
		if name in api_locations.keys():
			return_client( )

		raise AttributeError
	
class SoapCaddy:
	def __init__( self, server, companyid, username = False, password = False):
		self.clients = {}
		self.credentials = {}
		self.suds = suds
		self.cached_member_recid = {}

		if not server.startswith('http'):
			server = 'https://'+server

		if username and password:
			self.add_credentials(username, password)

		self.server = server
		self.companyid = companyid

	def add_credentials( self, username, password, module = False ):
		if not module: module = '$default'
		self.credentials[module] = (username, password)

	def get_credentials( self, module = False ):

		module_creds = self.credentials.get(module, None)
		if module_creds is None:
			module_creds = self.credentials.get('$default', None)

		return module_creds

	def get_client( self, module ):
		if module not in self.clients.keys():
			wsdl_url = '%s%s' % ( self.server, api_locations[module] )
			self.clients[module] = suds.client.Client(wsdl_url, plugins=[ plugin() for plugin in USE_CLIENT_PLUGINS ])

		client = self.clients[module]
		api_user, api_pass = self.get_credentials(module)

		credentials = client.factory.create('ApiCredentials')
		credentials.CompanyId = self.companyid
		credentials.IntegratorLoginId = api_user
		credentials.IntegratorPassword = api_pass
		client.credentials = credentials

		return client

	def Activity( self, *args ): return self.get_client('Activity', *args)
	def Company( self, *args ): return self.get_client('Company', *args)
	def Configuration( self, *args ): return self.get_client('Configuration', *args)
	def Contact( self, *args ): return self.get_client('Contact', *args)
	def Invoice( self, *args ): return self.get_client('Invoice', *args)
	def ManagedDevice( self, *args ): return self.get_client('ManagedDevice', *args)
	def Marketing( self, *args ): return self.get_client('Marketing', *args)
	def Member( self, *args ): return self.get_client('Member', *args)
	def Opportunity( self, *args ): return self.get_client('Opportunity', *args)
	def OpportunityConversion( self, *args ): return self.get_client('OpportunityConversion', *args)
	def Product( self, *args ): return self.get_client('Product', *args)
	def Project( self, *args ): return self.get_client('Project', *args)
	def Purchasing( self, *args ): return self.get_client('Purchasing', *args)
	def Reporting( self, *args ): return self.get_client('Reporting', *args)
	def Scheduling( self, *args ): return self.get_client('Scheduling', *args)
	def System( self, *args ): return self.get_client('System', *args)
	def ServiceTicket( self, *args ): return self.get_client('ServiceTicket', *args)
	def TimeEntry( self, *args ): return self.get_client('TimeEntry', *args) 

	def soap_call( self, module, action, *args, **kwargs ):
		m = self.get_client(module)
		svc_func = getattr(m.service, action)
		try:
			return svc_func( m.credentials, *args, **kwargs )
		except:
			raise

	# Reporting.RunReportQuery / Member report
	def get_member_recid( self, need_member_id ):
		if need_member_id not in self.cached_member_recid:
			res = self.soap_call('Reporting', 'RunReportQuery', 'Member')
			for member in res[0]:
				member_id = None
				member_recid = None
				for col in member[1]:
					if col._Name == 'Member_ID':
						member_id = col.value
					if col._Name == 'Member_RecID':
						member_recid = col.value
					if member_id and member_recid:
						break
				self.cached_member_recid[member_id] = member_recid

		return self.cached_member_recid[need_member_id]

