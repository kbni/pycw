# pycw - Python bindings for ConnectWise

Basic feature list:

* ORM like access to ConnectWise SOAP endpoints
* Some helper functions for handling odd-ball CW API situations
* Caddy object to store all your CW SOAP clients, should you not like the ORM
* Some nasty suds.plugin hacks to get around CW endpoint sending unclean XML

Third party libraries required (Debian Package name provided):

* python-dateutil - powerful extensions to the standard datetime module
* python-suds - Lightweight SOAP client for Python

Here's some example uses:

### Getting Started

```python
import pycw
cw = pycw.cw_orm('support.mycompany.com', 'mycompany', 'MyIntegratorUser', '1nt3gr4t0rP@ssW3rd')
```

### Examples

#### Example: Search for a Company
```python
companies = cw.search('Company', 'CompanyName LIKE "C%s"', 10)
for company in companies:
    print 'Found %s' % company.CompanyName
```

#### Example: Search for a Contact
```python
contacts = cw.search('Contact', 'Email = "george@example.com"', 1)
for contact in contacts:
	print 'Found %s %s' % (contact.FirstName, contact.LastName)
```

#### Example: Create a ServiceTicket
```python
create_ticket = cw.ServiceTicket()
create_ticket.Summary = "George's server closet is full of eels."
create_ticket.Board = "Helpdesk"
create_ticket.ContactEmailAddress = contact.Email # see pevious example
create_ticket.ContactId = contact.record_id
create_ticket.CompanyIdentifier = contact.get_company().CompanyIdentifier
create_ticket.StatusName = self.status_new
create_ticket.save()
```

#### Example: Attach a Configuration to a ServiceTicket
```python
configs = ticket.orm.search('Configuration', 'CompanyId = %s And ConfigurationName LIKE "%-sv-%"' % create_ticket.CompanyId, 20)
for config in configs:
    create_ticket.assoc_configuration(config)
create_ticket.save()
```

### tests.py
Only very basic tests have been implemented. You can try these out in an interactive console. The standard routine will:

* Search for a company (by `tf.with_company` - a full company name)
* Search for a contact (by `tf.with_contact` - an email address)
* Create an acitivty (for `tf.with_member`, of type `tf.with_activity_type`
* Create a service ticket (on `tf.with_board`, with Status `tf.status_new`)
* Create a schedulee ntry (for `tf.with_member`)
* Create an internal note (by `tf.with_member`)
* Associate the 1st Configuration under Company to ServiceTicket
* Create a time entry (by `tf.with_member`)
* Close service ticket (with `tf.status_close`)

It will dump ids you can use on your own to lookup and inspect, and I would recommend checking data is consistent with your ConnectWise too.

```plain
export CW_HOSTNAME=support.mycompany.com
export CW_DATABASE=mycompany
export CW_USERNAME=MyIntegratorUser
export CW_PASSWORD='1nt3gr4t0rP@ssW3rd'
$ python -B tests.py --shell
Python 2.7.3 (default, Mar 13 2014, 11:03:55)
[GCC 4.7.2] on linux2
Type "help", "copyright", "credits" or "license" for more information.
(InteractiveConsole)
>>> cw.ServiceTicket(250263)
<ServiceTicket(id=250263)>
>>> tf
<__main__.TestFeatures instance at 0x2a39128>
>>> tf.with_company = 'XYZ Test Company'
>>> tf.with_board = '1DC | Client Conundrums'
>>> tf.with_activity_type = 'Call'
>>> tf.with_member = 'alex'
>>> tf.with_contact = 'george@example.com'
>>> tf.status_new = 'SilentNew'
>>> tf.status_close = 'SilentClosed'
>>> tf.start()
9 tests ready to go!
( 1 of  9) test_search_company("XYZ Test Company") running..
* Located Company: <Company(id=133)> (XYZ Test Company)
( 1 of  9) test_search_company("XYZ Test Company") OKAY
( 2 of  9) test_search_contact("george@example.com") running..
* Located Contact: <Contact(id=1327)> (Curious George)
( 2 of  9) test_search_contact("george@example.com") OKAY
( 3 of  9) test_create_activity("Call", "alex") running..
* Created <Activity(id=23165)> - Just a test Call activity
( 3 of  9) test_create_activity("Call", "alex") OKAY
( 4 of  9) test_create_ticket("1DC | Client Conundrums", "XYZ Test Company", "george@example.com") running..
* Created <ServiceTicket(id=250367)> - Test ticket for Curious George
( 4 of  9) test_create_ticket("1DC | Client Conundrums", "XYZ Test Company", "george@example.com") OKAY
( 5 of  9) test_create_schedule("alex") running..
* Added <TicketScheduleEntry(id=35722)> to <ServiceTicket(id=250367)>
( 5 of  9) test_create_schedule("alex") OKAY
( 6 of  9) test_create_internal("alex") running..
* Added <('TicketNote',)(id=328345)> to <ServiceTicket(id=250367)>
( 6 of  9) test_create_internal("alex") OKAY
( 7 of  9) test_assoc_config() running..
* Added <Configuration(id=659)> to <ServiceTicket(id=250367)>
( 7 of  9) test_assoc_config() OKAY
( 8 of  9) test_create_time_entry("alex") running..
* Added <TimeEntry(id=10071)> to <ServiceTicket(id=250367)>
( 8 of  9) test_create_time_entry("alex") OKAY
( 9 of  9) test_close_ticket() running..
* Changed Status of <ServiceTicket(id=250367)> to SilentClosed
( 9 of  9) test_close_ticket() OKAY
All tests completed okay.
>>> ...do more, if you like...
```

### Important Information

Code is offered without any form of warranty. You alone are liable for the data on your system.

No license is offered. Just be cool.

If you have any feedback, feel free to email them to me (alex -at- kbni -dot- net).
