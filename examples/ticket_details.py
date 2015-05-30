import pycw

class TicketDetails(pycw.Scaffold):
	def __init__(self):
		pycw.Scaffold.__init__(self)
		self.add_argument('list_tickets', nargs='*')
	def loop(self):
		for ticket_no in self.args.list_tickets:
			try:
				t = self.cw.ServiceTicket(int(ticket_no))
				print 'Ticket #%s - %s' % ( t.record_id, t.Summary )
			except pycw.CWObjectNotFound:
				print 'No such ticket: #%s!' % ticket_no

if __name__ == '__main__':
	TicketDetails().run()
