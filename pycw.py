# Author: Alex Wilson <alex@kbni.net>
# License: None, but be cool.

# It's just going to complain anyways.
import logging; logging.getLogger('suds.plugin').setLevel(logging.CRITICAL)

from soap import SoapCaddy
from orm import ConnectWiseORM
from tests import TestFeatures

def cw_caddy(cw_host, cw_db, cw_user, cw_pass):
	"""
	Return a SoapCaddy object, this is a place you can store your SOAPs
	@cw_host - ConnectWise hostname 'support.yourcompany.com' 
	@cw_db   - Your database name 'yourcompany' (same as login screen)
	@cw_user - Integrator Login (Setup Tables > Integrator Logins)
	@cw_pass - Integrator Password (Setup Tables > Integrator)

	You should probably just use ORM, from which you can access the caddy anyhow..
	"""
	new_caddy = SoapCaddy(cw_host, cw_db, cw_user, cw_pass)
	return new_caddy

def cw_orm(cw_host, cw_db, cw_user, cw_pass):
	"""
	Return a ORM object, this is a place you can store your SOAPs
	@cw_host - ConnectWise hostname 'support.yourcompany.com' 
	@cw_db   - Your database name 'yourcompany' (same as login screen)
	@cw_user - Integrator Login (Setup Tables > Integrator Logins)
	@cw_pass - Integrator Password (Setup Tables > Integrator)

	Creates a SoapCaddy object, then a ConnectWiseORM object using that caddy.
	Access the SoapCaddy directly by accessing YourObject.caddy
	"""
	new_caddy = cw_caddy(cw_host, cw_db, cw_user, cw_pass)
	return ConnectWiseORM(new_caddy)

def run_tests(**kwargs):
	"""
	Run the feature tests with default options, you might want to actually inspect the tests file before doing so.
	You can provide cw_host etc arguments as with cw_orm() and cw_caddy(), but otherwise these will be picked up from
	the following environment variables:

		CW_USERNAME  CW_PASSWORD  CW_HOSTNAME  CW_DATABASE
	"""
	tests = TestFeatures(**kwargs)
	return tests.start()
