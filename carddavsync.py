#!/usr/bin/env python3
"""
Hatchbuck parser. Run from command line or import as module.
"""
import argparse
import os
import pprint
import logging
import sys
import vobject  # pylint: disable=import-error
from hatchbuck import Hatchbuck  # pylint: disable=import-error


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
                'requests.packages.urllib3.connectionpool'). \
                setLevel(logging.WARNING)
        logging.debug("starting with arguments: %s", (self.args))

    def init_hatchbuck(self):
        """Initialize hatchbuck API incl. authentication"""
        if not self.args.hatchbuck:
            logging.error('No hatchbuck_key found.')
            sys.exit(1)

        self.hatchbuck = Hatchbuck(self.args.hatchbuck, noop=self.args.noop)

    def parse_files(self):
        """Start parsing files"""
        if self.args.file:
            for file in self.args.file:
                logging.debug("parsing file %s", (file))
                self.parse_file(file)
        elif self.args.dir:
            for direc in self.args.dir:
                logging.debug("using directory %s", (direc))
                for file in os.listdir(direc):
                    if file.endswith(".vcf"):
                        logging.debug("parsing file %s", (direc + file))
                        self.parse_file(direc + file)
        else:
            print('Nothing to do.')

    def parse_file(self, file):
        # pylint: disable=too-many-statements
        # pylint: disable=too-many-locals
        # pylint: disable=too-many-branches
        """Parse a single address book file"""
        prin = pprint.PrettyPrinter()
        self.stats = {}

        for vob in vobject.readComponents(open(file)):
            content = vob.contents
            if 'n' not in content:
                self.stats['noname'] = self.stats.get('noname', 0) + 1
                return
            if 'email' not in content:
                self.stats['noemail'] = self.stats.get('noemail', 0) + 1
                return
            self.stats['valid'] = self.stats.get('valid', 0) + 1

            # aggregate stats what kind of fields we have available
            for i in content:
                # if i in c:
                self.stats[i] = self.stats.get(i, 0) + 1

            if self.args.verbose:
                prin.pprint(content)

            emails = []
            for email in content['email']:
                emails.append(email.value)

            # search if there is already a contact with that email address
            profile = self.hatchbuck.search_email_multi(emails)
            if not profile:
                # none of the email addresses found in CRM yet
                if self.args.update:
                    # skip this contact if its not in hatchbuck yet
                    continue

                # create new contact
                profile = dict()
                profile['firstName'] = content['n'][0].value.given
                profile['lastName'] = content['n'][0].value.family
                if 'title' in content:
                    profile['title'] = content['title'][0].value
                if 'org' in content:
                    profile['company'] = content['org'][0].value

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
                for email in content.get('email', []):
                    if 'WORK' in email.type_paramlist:
                        kind = "Work"
                    elif 'HOME' in email.type_paramlist:
                        kind = "Home"
                    else:
                        kind = "Other"
                    profile['emails'].append(
                        {'address': email.value, 'type': kind})

                profile = self.hatchbuck.create(profile)
                logging.info("added contact: %s", (profile))
            else:
                self.stats['found'] = self.stats.get('found', 0) + 1

            if profile.get('firstName', '') == '':
                profile = self.hatchbuck.profile_add(profile, 'firstName',
                                                     None,
                                                     content['n'][0].
                                                     value.given)

            if profile.get('lastName', '') == '':
                profile = self.hatchbuck.profile_add(profile, 'lastName', None,
                                                     content['n'][0].
                                                     value.family)

            if 'title' in content and profile.get('title', '') == '':
                profile = self.hatchbuck.profile_add(profile, 'title', None,
                                                     content['title'][0].value)

            if 'company' in content and profile.get('company', '') == '':
                profile = self.hatchbuck.profile_add(profile, 'company', None,
                                                     content['org'][0].value)

            for email in content.get('email', []):
                if 'WORK' in email.type_paramlist:
                    kind = "Work"
                elif 'HOME' in email.type_paramlist:
                    kind = "Home"
                else:
                    kind = "Other"
                profile = self.hatchbuck.profile_add(profile, 'emails',
                                                     'address',
                                                     email.value,
                                                     {'type': kind})

            for addr in content.get('adr', []):
                address = {
                    'street': addr.value.street,
                    'zip_code': addr.value.code,
                    'city': addr.value.city,
                    'country': addr.value.country,
                }
                try:
                    if 'WORK' in addr.type_paramlist:
                        kind = "Work"
                    elif 'HOME' in addr.type_paramlist:
                        kind = "Home"
                    else:
                        kind = "Other"
                except AttributeError:
                    # if there is no type at all
                    kind = "Other"
                logging.debug("adding address %s %s", address, profile)
                profile = self.hatchbuck.profile_add_address(profile, address,
                                                             kind)
            for telefon in content.get('tel', []):
                number = telefon.value
                for rep in "()-":
                    # clean up number
                    number = number.replace(rep, '')
                try:
                    if 'WORK' in telefon.type_paramlist:
                        kind = "Work"
                    elif 'HOME' in telefon.type_paramlist:
                        kind = "Home"
                    else:
                        kind = "Other"
                except AttributeError:
                    # if there is no type at all
                    kind = "Other"
                profile = self.hatchbuck.profile_add(profile, 'phones',
                                                     'number',
                                                     number, {'type': kind})

            for email in content.get('x-skype', []):
                profile = self.hatchbuck.profile_add(profile,
                                                     'instantMessaging',
                                                     'address', email.value,
                                                     {'type': 'Skype'})

            for email in content.get('x-msn', []):
                profile = self.hatchbuck.profile_add(profile,
                                                     'instantMessaging',
                                                     'address', email.value,
                                                     {'type': 'Messenger'})

            for email in content.get('x-msnim', []):
                profile = self.hatchbuck.profile_add(profile,
                                                     'instantMessaging',
                                                     'address', email.value,
                                                     {'type': 'Messenger'})

            for email in content.get('x-twitter', []):
                if "twitter.com" in email.value:
                    value = email.value
                else:
                    value = "http://twitter.com/" + email.value. \
                        replace('@', '')
                profile = self.hatchbuck.profile_add(profile, 'socialNetworks',
                                                     'address', value,
                                                     {'type': 'Twitter'})

            for email in content.get('url', []) + content. \
                    get('x-socialprofile', []):
                value = email.value
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

            for email in content.get('bday', []):
                date = {
                    'year': email.value[0:4],
                    'month': email.value[4:6],
                    'day': email.value[6:8],
                }
                profile = self.hatchbuck.profile_add_birthday(profile, date)

            if self.args.tag:
                if not self.hatchbuck.profile_contains(profile, 'tags', 'name',
                                                       self.args.tag):
                    self.hatchbuck.add_tag(profile['contactId'], self.args.tag)


class HatchbuckArgs(object):
    # pylint: disable=too-few-public-methods
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
