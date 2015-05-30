# Author: Alex Wilson <alex@kbni.net>
# License: None, but be cool.

import pycw
import os, sys, code
import datetime
import traceback

class TestFeatures:
	"""
		This class will run basic tests using your ConnectWise details, you may
		want to override these default properties (kwargs passed to __init__)

		@cw_host = ConnectWise hostname (support.yourcompany.com)
		@cw_db = ConnectWise database (yourcompany)
		@cw_user = ConnectWise username (SomeIntegratorUsername)
		@cw_pass = ConnectWise password (Some1nt3grat0rP@ssw0rd)

		@with_company = 'XYZ Test Company' <- full company name
		@with_board = '1DC | Client Conundrums' <- full service board name
		@with_activity_type = 'Call' <- activity type 
		@with_member = 'alex' <- member's email address
		@with_contact = 'george@example.com' <- contact's email address
		@status_new = 'SilentNew' <- status for create_ticket
		@status_close = 'SilentClosed' <- status for close_ticket

		@search_member = True <- test searching for a member
		@search_company = True <- test searching for a company
		@search_contact = True <- test searching for a contact
		@create_ticket = True <- test creating a ticket
		@create_schedule = True <- test creating a schedule entry
		@create_time_entry = True <- test creating a time entry
		@create_internal = True <- test creating an internal note
		@close_ticket = True <- test closing a ticket
		@assoc_config = True <- test associating a configuration
		@create_activity = True <- test creating an activity
		@delete_ticket = True <- test deleting a ticket

		It's important to note these tests aren't entirely conclusive, and created
		test objects should be inspected for errors before proceeding any further.
	"""

	cw_host = None
	cw_db = None
	cw_user = None
	cw_pass = None

	with_company = 'XYZ Test Company'
	with_board = '1DC | Client Conundrums'
	with_activity_type = 'Call'
	with_member = 'alex'
	with_contact = 'george@example.com'
	status_new = 'SilentNew'
	status_close = 'SilentClosed'

	search_member = True
	search_company = True
	search_contact = True   
	create_ticket = True
	create_schedule = True
	create_time_entry = True
	create_internal = True
	close_ticket = True
	assoc_config = True
	create_activity = True
	delete_ticket = True

	_last_ticket = None

	def __init__(self, **kwargs):
		for k,v in kwargs.iteritems():
			if hasattr(self, k):
				setattr(self, k, v)

	def start(self):
		tests = []

		if self.search_company:
			tests.append([ self.test_search_company, self.with_company ])
		if self.search_contact:
			tests.append([ self.test_search_contact, self.with_contact ])
		if self.create_activity:
			tests.append([ self.test_create_activity, self.with_activity_type, self.with_member ])
		if self.create_ticket:
			tests.append([ self.test_create_ticket, self.with_board, self.with_company, self.with_contact ])
		if self.create_schedule:
			tests.append([ self.test_create_schedule, self.with_member ])
		if self.create_internal:	
			tests.append([ self.test_create_internal, self.with_member ])
		if self.assoc_config:
			tests.append([ self.test_assoc_config ])
		if self.create_time_entry:
			tests.append([ self.test_create_time_entry, self.with_member ])
		if self.close_ticket:
			tests.append([ self.test_close_ticket ])

		print '%d tests ready to go!' % len(tests)

		success = True

		for index,test in enumerate(tests):
			func, args = test[0], test[1:]
			func_desc = func.func_name
			func_desc += '(' + ', '.join([ '"%s"' % a for a in args ]) + ')'
			print '(%2d of %2d) %s running..' % (index+1, len(tests), func_desc)
			status = 'FAIL'
			try:
				func(*args)
				status = 'OKAY'
			except:
				traceback.print_exc()
				success = False
				print

			print '(%2d of %2d) %s %s' % (index+1, len(tests), func_desc, status)

		if success:
			print 'All tests completed okay.'
		else:
			sys.stderr.write('Looks like some tests failed. Oops\n')
			sys.exit(1)

	def get_cw(self):
		cw = pycw.cw_orm(self.cw_host, self.cw_db, self.cw_user, self.cw_pass)
		return cw

	def test_search_company(self, with_company):
		cw = pycw.cw_orm(self.cw_host, self.cw_db, self.cw_user, self.cw_pass)
		companies = cw.search('Company', 'CompanyName = "%s"' % with_company, 1)
		company = cw.Company(companies[0].record_id) # We already have the object, but let's reload it using the record_id

		print '* Located Company: %s (%s)' % ( company, company.CompanyName )

	def test_search_contact(self, with_contact):
		cw = pycw.cw_orm(self.cw_host, self.cw_db, self.cw_user, self.cw_pass)
		contacts = cw.search('Contact', 'Email = "%s"' % with_contact, 1)	
		contact = contacts[0]

		print '* Located Contact: %s (%s %s)' % (contact, contact.FirstName, contact.LastName)

	def test_create_activity(self, with_activity_type, with_member):
		cw = pycw.cw_orm(self.cw_host, self.cw_db, self.cw_user, self.cw_pass)

		activity = cw.Activity()
		activity.Subject = 'Just a test %s activity' % with_activity_type
		activity.CompanyIdentifier = 'Catchall' # hope you have a catchall :/
		activity.AssignTo = with_member
		activity.Type = with_activity_type
		activity.Status = 'Open'
		activity.Notes = 'Just ignore this - testing pycw'
		activity.TimeRange.StartTime = datetime.datetime.now() + datetime.timedelta(minutes=4)
		activity.TimeRange.EndTime = datetime.datetime.now() + datetime.timedelta(minutes=7)
		activity.DueDate = datetime.datetime.now() + datetime.timedelta(minutes=60)
		activity.save()

		print '* Created %s - %s' % (activity, activity.Subject)

	def test_create_ticket(self, with_board, with_company, with_contact):
		cw = pycw.cw_orm(self.cw_host, self.cw_db, self.cw_user, self.cw_pass)

		contacts = cw.search('Contact', 'Email = "%s"' % with_contact, 1)
		contact = contacts[0]
		company = contact.get_company()

		create_ticket = cw.ServiceTicket()
		create_ticket.Summary = 'Test ticket for %s %s' % ( contact.FirstName, contact.LastName )
		create_ticket.Board = with_board
		create_ticket.ContactEmailAddress = contact.Email
		create_ticket.ContactId = contact.record_id
		create_ticket.CompanyIdentifier = company.CompanyIdentifier
		create_ticket.StatusName = self.status_new
		create_ticket.save()

		print '* Created %s - %s' % (create_ticket, create_ticket.Summary)

		self._last_ticket = create_ticket

	def test_create_time_entry(self, with_member, ticket = None):
		if not ticket:
			ticket = self._last_ticket

		time_entry = ticket.orm.TimeEntry()
		time_entry.TicketId = ticket.record_id
		time_entry.MemberIdentifier = with_member
		time_entry.DateStart = datetime.datetime.now()
		time_entry.TimeStart = datetime.datetime.now() + datetime.timedelta(minutes=25)
		time_entry.TimeEnd = datetime.datetime.now() + datetime.timedelta(minutes=26)
		time_entry.Notes = 'Test time entry..'
		time_entry.AddNotesToDetailDescription = True
		time_entry.save()

		print '* Added %s to %s' % ( time_entry, ticket )

	def test_create_internal(self, with_member, ticket = None):
		if not ticket:
			ticket = self._last_ticket
		
		member_recid = ticket.orm.caddy.get_member_recid('alex')

		ticket_note = ticket.orm.TicketNote(parent=ticket)
		ticket_note.MemberId = member_recid
		ticket_note.NoteText = 'Test internal note'
		ticket_note.IsInternalNote = False
		ticket_note.IsExternalNote = False
		ticket_note.ProcessNotifications = False
		ticket_note.IsPartOfDetailDescription = False
		ticket_note.IsPartOfInternalAnalysis = True
		ticket_note.IsPartOfResolution = False
		ticket_note.save()

		print '* Added %s to %s' % ( ticket_note, ticket )

	def test_create_schedule(self, with_member, ticket = None):
		if not ticket:
			ticket = self._last_ticket

		schedule = ticket.orm.TicketScheduleEntry()
		schedule.TicketId = int(ticket.record_id)
		schedule.MemberIdentifier = with_member
		schedule.DateStart = datetime.datetime.now() + datetime.timedelta(minutes=30)
		schedule.DateEnd = datetime.datetime.now() + datetime.timedelta(minutes=60)
		schedule.save()

		print '* Added %s to %s' % ( schedule, ticket )

	def test_close_ticket(self, ticket = None):
		if not ticket:
			ticket = self._last_ticket

		ticket.load()
		ticket.StatusName = self.status_close
		ticket.save()

		print '* Changed Status of %s to %s' % ( ticket, ticket.StatusName )

	def test_assoc_config(self, ticket = None):
		if not ticket:
			ticket = self._last_ticket

		cw = ticket.orm

		ticket.load()
		configs = ticket.orm.search('Configuration', 'CompanyId = %s' % ticket.CompanyId, 1)

		ticket.assoc_configuration(configs[0])
		ticket.save()
		ticket.load()

		print '* Added %s to %s' % ( configs[0], ticket )

if __name__ == "__main__":
	cw_host = os.environ.get('CW_HOSTNAME', None)
	cw_user = os.environ.get('CW_USERNAME', None)
	cw_pass = os.environ.get('CW_PASSWORD', None)
	cw_db = os.environ.get('CW_DATABASE', None)
	if '--shell-only' in sys.argv or '--shell' in sys.argv:
		cw = pycw.cw_orm(cw_host, cw_db, cw_user, cw_pass)
		tf = TestFeatures(cw_host=cw_host, cw_user=cw_user, cw_pass=cw_pass, cw_db=cw_db)
		code.interact(local=locals())
	if '--just-run':
		TestFeatures(cw_host=cw_host, cw_user=cw_user, cw_pass=cw_pass, cw_db=cw_db).start()
