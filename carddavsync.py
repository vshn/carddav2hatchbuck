#!/usr/bin/env python3
"""
Hatchbuck parser. Run from command line or import as module.
"""
import argparse
import os
import pprint
import logging
import sys
import vobject
from hatchbuck import Hatchbuck


class HatchbuckParser(object):
    """
    An object that does all the parsing for/with Hatchbuck.
    """

    def __init__(self, args):
        self.args = args
        self.stats = {}
        self.hatchbuck = None

    def main(self):
        """Parsing gets kicked off here"""
        self.init_logging()
        self.init_hatchbuck()
        self.parse_files()

    def show_summary(self):
        """Show some statistics"""
        print(self.stats)

    def init_logging(self):
        """Initialize logging"""
        logformat = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

        if self.args.verbose:
            logging.basicConfig(level=logging.DEBUG, format=logformat)
        else:
            logging.basicConfig(level=logging.INFO, format=logformat)
            logging.getLogger(
                'requests.packages.urllib3.connectionpool').setLevel(
                logging.WARNING)

        logging.debug("starting with arguments: {0}".format(self.args))

    def init_hatchbuck(self):
        """Initialize hatchbuck API incl. authentication"""
        if not self.args.hatchbuck:
            logging.error('No hatchbuck_key/hatchbuck_username found.'
                          ' Please get the api key at'
                          ' https://app.hatchbuck.com/Account/UpdateAPIKey')
            sys.exit(1)

        self.hatchbuck = Hatchbuck(self.args.hatchbuck, noop=self.args.noop)

    def parse_files(self):
        """Start parsing files"""
        if self.args.file:
            for f in self.args.file:
                logging.debug("parsing file {0}".format(f))
                self.parse_file(f)
        elif self.args.dir:
            for d in self.args.dir:
                logging.debug("using directory {0}".format(d))
                for f in os.listdir(d):
                    if f.endswith(".vcf"):
                        logging.debug("parsing file {0}".format(d + f))
                        self.parse_file(d + f)
        else:
            print('Nothing to do.')

    def parse_file(self, f):
        """Parse a single address book file"""
        pp = pprint.PrettyPrinter()
        self.stats = {}

        for v in vobject.readComponents(open(f)):
            c = v.contents
            if 'n' not in c:
                self.stats['noname'] = self.stats.get('noname', 0) + 1
                return
            if 'email' not in c:
                self.stats['noemail'] = self.stats.get('noemail', 0) + 1
                return
            self.stats['valid'] = self.stats.get('valid', 0) + 1

            # aggregate stats what kind of fields we have available
            for i in c:
                # if i in c:
                self.stats[i] = self.stats.get(i, 0) + 1

            if self.args.verbose:
                pp.pprint(c)

            emails = []
            for e in c['email']:
                emails.append(e.value)

            profile = self.hatchbuck.search_email_multi(emails)
            if not profile:
                if self.args.update:
                    # skip this contact if its not in hatchbuck yet
                    continue

                # create new contact
                profile = dict()
                profile['firstName'] = c['n'][0].value.given
                profile['lastName'] = c['n'][0].value.family
                if 'title' in c:
                    profile['title'] = c['title'][0].value
                if 'org' in c:
                    profile['company'] = c['org'][0].value

                profile['subscribed'] = True
                profile['status'] = {'name': 'Lead'}

                if self.args.source:
                    profile['source'] = {'id': self.args.source}

                # override hatchbuck sales rep username if set
                # (default: api key owner)
                if self.args.user:
                    profile['salesRep'] = {
                        'username': self.args.user}

                profile['emails'] = []
                for e in c.get('email', []):
                    if 'WORK' in e.type_paramlist:
                        kind = "Work"
                    elif 'HOME' in e.type_paramlist:
                        kind = "Home"
                    else:
                        kind = "Other"
                    profile['emails'].append(
                        {'address': e.value, 'type': kind})

                profile = self.hatchbuck.create(profile)
                logging.info("added contact: {0}".format(profile))
            else:
                self.stats['found'] = self.stats.get('found', 0) + 1

            if profile.get('firstName', '') == '':
                profile = self.hatchbuck.profile_add(profile, 'firstName',
                                                     None,
                                                     c['n'][0].value.given)

            if profile.get('lastName', '') == '':
                profile = self.hatchbuck.profile_add(profile, 'lastName', None,
                                                     c['n'][0].value.family)

            if 'title' in c and profile.get('title', '') == '':
                profile = self.hatchbuck.profile_add(profile, 'title', None,
                                                     c['title'][0].value)

            if 'company' in c and profile.get('company', '') == '':
                profile = self.hatchbuck.profile_add(profile, 'company', None,
                                                     c['org'][0].value)

            for e in c.get('email', []):
                if 'WORK' in e.type_paramlist:
                    kind = "Work"
                elif 'HOME' in e.type_paramlist:
                    kind = "Home"
                else:
                    kind = "Other"
                profile = self.hatchbuck.profile_add(profile, 'emails',
                                                     'address',
                                                     e.value, {'type': kind})

            for a in c.get('adr', []):
                address = {
                    'street': a.value.street,
                    'zip_code': a.value.code,
                    'city': a.value.city,
                    'country': a.value.country,
                }
                try:
                    if 'WORK' in a.type_paramlist:
                        kind = "Work"
                    elif 'HOME' in a.type_paramlist:
                        kind = "Home"
                    else:
                        kind = "Other"
                except KeyError:
                    # if there is no type at all
                    kind = "Other"
                logging.debug(
                    "adding address {0} to {1}".format(address, profile))
                profile = self.hatchbuck.profile_add_address(profile, address,
                                                             kind)

            for t in c.get('tel', []):
                number = t.value
                for r in "()-":
                    # clean up number
                    number = number.replace(r, '')
                try:
                    if 'WORK' in t.type_paramlist:
                        kind = "Work"
                    elif 'HOME' in t.type_paramlist:
                        kind = "Home"
                    else:
                        kind = "Other"
                except KeyError:
                    # if there is no type at all
                    kind = "Other"
                profile = self.hatchbuck.profile_add(profile, 'phones',
                                                     'number',
                                                     number, {'type': kind})

            for e in c.get('x-skype', []):
                profile = self.hatchbuck.profile_add(profile,
                                                     'instantMessaging',
                                                     'address', e.value,
                                                     {'type': 'Skype'})

            for e in c.get('x-msn', []):
                profile = self.hatchbuck.profile_add(profile,
                                                     'instantMessaging',
                                                     'address', e.value,
                                                     {'type': 'Messenger'})

            for e in c.get('x-msnim', []):
                profile = self.hatchbuck.profile_add(profile,
                                                     'instantMessaging',
                                                     'address', e.value,
                                                     {'type': 'Messenger'})

            for e in c.get('x-twitter', []):
                if "twitter.com" in e.value:
                    value = e.value
                else:
                    value = "http://twitter.com/" + e.value.replace('@', '')
                profile = self.hatchbuck.profile_add(profile, 'socialNetworks',
                                                     'address', value,
                                                     {'type': 'Twitter'})

            for e in c.get('url', []) + c.get('x-socialprofile', []):
                value = e.value
                if not value.startswith("http"):
                    value = "http://" + value
                if "facebook.com" in value:
                    profile = self.hatchbuck.profile_add(profile,
                                                         'socialNetworks',
                                                         'address', value,
                                                         {'type': 'Facebook'})
                elif "twitter.com" in value:
                    profile = self.hatchbuck.profile_add(profile,
                                                         'socialNetworks',
                                                         'address', value,
                                                         {'type': 'Twitter'})
                else:
                    profile = self.hatchbuck.profile_add(profile, 'website',
                                                         'websiteUrl', value)

            for e in c.get('bday', []):
                date = {
                    'year': e.value[0:4],
                    'month': e.value[4:6],
                    'day': e.value[6:8],
                }
                profile = self.hatchbuck.profile_add_birthday(profile, date)

            if self.args.tag:
                if not self.hatchbuck.profile_contains(profile, 'tags', 'name',
                                                       self.args.tag):
                    self.hatchbuck.add_tag(profile['contactId'], self.args.tag)

            self.hatchbuck.update(profile['contactId'], profile)


class HatchbuckArgs(object):
    """
    Replacement for argparse command line arguments when used as module.
    """
    verbose = True
    update = True
    noop = True

    hatchbuck = None
    source = None
    dir = None
    file = None

    def __str__(self):
        """Show the content of this class nicely when printed"""
        return str(self.__dict__)


def parse_arguments():
    """Parse arguments from command line"""
    parser = argparse.ArgumentParser(
        description='parse vcard (.vcf) contact files')
    parser.add_argument('--hatchbuck', help='Hatchbuck API key')
    parser.add_argument('-s', '--source', help='Hatchbuck contact source')
    parser.add_argument('-t', '--tag', help='Hatchbuck contact tag')
    parser.add_argument('--user', help='Hatchbuck sales rep username')
    parser.add_argument('-v', '--verbose', help='output verbose debug logging',
                        action='store_true', default=False)
    parser.add_argument('-u', '--update',
                        help='only update existing contacts in hatchbuck,'
                             ' dont add new ones',
                        action='store_true', default=False)
    parser.add_argument('-n', '--noop',
                        help='dont actually post anything to hatchbuck,'
                             ' just log what would have been posted',
                        action='store_true', default=False)
    parser.add_argument('-f', '--file', '--files',
                        help='read a list of vcf files, ignore directories',
                        nargs='*')
    parser.add_argument('dir',
                        help='read all vcf files from directories',
                        nargs='*')
    args = parser.parse_args()
    return args


def main():
    """Script execution starts here."""
    args = parse_arguments()

    parser = HatchbuckParser(args)
    parser.main()
    parser.show_summary()


if __name__ == "__main__":
    main()
