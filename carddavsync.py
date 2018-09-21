#!/usr/bin/env python3
"""
Hatchbuck parser. Run from command line or import as module.
"""
import argparse
import os
import pprint
import logging
import sys
import re
import vobject
from hatchbuck import Hatchbuck
from pycountry import countries
import phonenumbers

# pylint: disable=logging-format-interpolation
# pylint: disable=too-many-locals
# pylint: disable=too-many-branches
# pylint: disable=too-many-statements
# pylint: disable=too-few-public-methods
# pylint: disable=logging-not-lazy


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

    @staticmethod
    def short_contact(profile):
        """
        :param profile:
        :return:
        """
        text = "Contact("
        if profile.get('firstName', False) and profile.get('lastName', False):
            text = text + profile['firstName'] + " " + \
                   profile['lastName'] + ", "
        for email in profile.get('emails', []):
            text = text + email['address'] + ", "
        text = text[:-2] + ")"
        return text

    def parse_file(self, file):
        """
        Parse a single address book file
        :param file:
        :return:
        """
        prin = pprint.PrettyPrinter()
        self.stats = {}

        for vob in vobject.readComponents(open(file)):
            content = vob.contents
            if self.args.verbose:
                prin.pprint(content)

            if 'n' not in content:
                self.stats['noname'] = self.stats.get('noname', 0) + 1
                return
            if 'email' not in content or not re.match(r"^[^@]+@[^@]+\.[^@]+$",
                                                      content['email'][
                                                          0].value):  # noqa pylint: disable=line-too-long
                self.stats['noemail'] = self.stats.get('noemail', 0) + 1
                return
            self.stats['valid'] = self.stats.get('valid', 0) + 1

            # aggregate stats what kind of fields we have available
            for i in content:
                # if i in c:
                self.stats[i] = self.stats.get(i, 0) + 1

            emails = []
            for email in content['email']:
                if re.match(r"^[^@äöü]+@[^@]+\.[^@]+$", email.value):
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
                    if not re.match(r"^[^@äöü]+@[^@]+\.[^@]+$", email.value):
                        continue
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

            if 'org' in content and profile.get('company', '') == '':
                profile = self.hatchbuck.profile_add(profile, 'company', None,
                                                     content['org'][0].value)
            if profile.get('company', '') == '':
                # empty company name ->
                # maybe we can guess the company name from the email address?
                # logging.warning("empty company with emails: {0}".
                #                format(profile['emails']))
                pass

            # clean up company name
            if re.match(r";$", profile.get('company', '')):
                logging.warning("found unclean company name: %s",
                                format(profile['company']))

            if re.match(r"\|", profile.get('company', '')):
                logging.warning("found unclean company name: %s",
                                format(profile['company']))

            for email in content.get('email', []):
                if not re.match(r"^[^@]+@[^@]+\.[^@]+$", email.value):
                    continue
                if 'WORK' in email.type_paramlist:
                    kind = "Work"
                elif 'HOME' in email.type_paramlist:
                    kind = "Home"
                else:
                    kind = "Other"
                lookup = self.hatchbuck.search_email(email.value)
                if lookup is not None and \
                        lookup['contactId'] != profile['contactId']:
                    short_profile = dict()
                    short_profile['firstName'] = lookup['firstName']
                    short_profile['lastName'] = lookup['lastName']
                    short_profile['emails'] = lookup['emails']
                    short_profile['phones'] = lookup['phones']
                    f_write = open('contact.txt', 'a')
                    prof = str(short_profile)
                    f_write.write(prof)
                    f_write.write('\n\n')
                # logging.warning(
                #     "email %s from %s already belongs to %s" % (
                #         email.value,
                #         self.short_contact(profile),
                #         self.short_contact(lookup)))
                elif lookup is None:
                    profile = self.hatchbuck.profile_add(
                        profile,
                        'emails',
                        'address',
                        email.value,
                        {'type': kind}
                    )
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
                for rep in "()-\xa0":
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

                redundant = False

                try:
                    phonenumber = phonenumbers.parse(telefon.value, None)
                    pformatted = phonenumbers.format_number(
                        phonenumber,
                        phonenumbers.PhoneNumberFormat.INTERNATIONAL
                    )
                except phonenumbers.phonenumberutil.NumberParseException:
                    logging.warning("could not parse number %s in %s",
                                    telefon.value,
                                    self.short_contact(profile))
                    pformatted = telefon.value

                    # try to guess the country from the addresses
                    countries_found = []
                    for addr in profile.get('addresses', []):
                        if addr.get('country', False) and \
                                addr['country'] not in countries_found:
                            countries_found.append(addr['country'])
                    logging.debug("countries found %s",
                                  format(countries_found))
                    if len(countries_found) == 1:
                        # lets try to parse the number with the country
                        countrycode = countries.lookup(
                            countries_found[0]).alpha_2
                        logging.debug("countrycode %s", format(countrycode))
                        try:
                            phonenumber = phonenumbers.parse(
                                telefon.value,
                                countrycode)
                            pformatted = phonenumbers.format_number(
                                phonenumber,
                                phonenumbers.PhoneNumberFormat.INTERNATIONAL
                            )
                            logging.debug("guess %s", format(pformatted))
                            profile = self.hatchbuck.profile_add(
                                profile,
                                'phones',
                                'number',
                                pformatted,
                                {'type': kind}
                            )
                            # if we got here we now have a full number
                            continue
                        except phonenumbers.phonenumberutil. \
                                NumberParseException:
                            logging.warning(
                                "could not parse number %s in %s",
                                telefon.value,
                                self.short_contact(profile))
                            pformatted = telefon.value

                    # check that there is not an international/longer
                    # number there already
                    # e.g. +41 76 4000 464 compared to 0764000464

                    # skip the 0 in front
                    num = telefon.value.replace(' ', '')[1:]
                    for tel2 in profile['phones']:
                        # check for suffix match
                        if tel2['number'].replace(' ', '').endswith(num):
                            logging.warning("not adding number %s in %s", num,
                                            self.short_contact(profile))
                            redundant = True
                            break

                    if not redundant:
                        profile = self.hatchbuck.profile_add(
                            profile,
                            'phones',
                            'number',
                            pformatted,
                            {'type': kind}
                        )

            for telefon in profile.get('phones', []):
                # now go through all phone numbers in hatchbuck
                #  to clean them up
                try:
                    phonenumber = phonenumbers.parse(telefon['number'], None)
                    pformatted = phonenumbers.format_number(
                        phonenumber,
                        phonenumbers.PhoneNumberFormat.INTERNATIONAL
                    )
                    if telefon['number'] != pformatted:
                        logging.warning("number from {0} to {1}".
                                        format(telefon, pformatted))
                        profile = self.hatchbuck.profile_add(
                            profile,
                            'phones',
                            'number',
                            pformatted,
                            {'id': telefon['id'], 'type': telefon['type']}
                        )

                except phonenumbers.phonenumberutil.NumberParseException:
                    logging.warning("could not parse number {0} in {1}".
                                    format(telefon['number'],
                                           self.short_contact(profile)))
                    num = telefon['number'].replace(' ', '')[1:]
                    redundant = False
                    for tel2 in profile['phones']:
                        if tel2['id'] != telefon['id'] and \
                                tel2['number'].replace(' ', '').endswith(num):
                            logging.warning("redundant number %s in %s",
                                            num, self.short_contact(profile))
                            redundant = True
                            break
                    if redundant:
                        # delete this number
                        profile = self.hatchbuck.update(
                            profile['contactId'],
                            {'phones': [
                                {'number': '',
                                 'id': telefon['id'],
                                 'type': telefon['type'], }, ]})
                    else:
                        # so this is an unique number but without country code
                        # try to guess the country from the postal addresses
                        countries_found = []
                        for addr in profile.get('addresses', []):
                            if addr.get('country', False) and \
                                    addr['country'] not in countries_found:
                                countries_found.append(addr['country'])
                        logging.debug("countries found %s",
                                      format(countries_found))
                        if len(countries_found) == 1:
                            # lets try to parse the number with the country
                            countrycode = countries.lookup(
                                countries_found[0]).alpha_2
                            logging.debug(
                                "countrycode %s", format(countrycode))
                            try:
                                phonenumber = phonenumbers.parse(
                                    telefon.value,
                                    countrycode)
                                pformatted = phonenumbers.format_number(
                                    phonenumber,
                                    phonenumbers.PhoneNumberFormat
                                    .INTERNATIONAL)
                                logging.debug("guess %s", format(pformatted))
                                profile = self.hatchbuck.update(
                                    profile['contactId'],
                                    {'phones': [
                                        {'number': pformatted,
                                         'id': telefon['id'],
                                         'type': telefon['type'], }, ]})
                                # if we got here we now have a full number
                                continue
                            except phonenumbers.phonenumberutil. \
                                    NumberParseException:
                                logging.warning(
                                    "could not parse number {0} in {1}".format(
                                        telefon.value,
                                        self.short_contact(profile)))

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
                    'month': email.value[5:7],
                    'day': email.value[8:10],
                }
                profile = self.hatchbuck.profile_add_birthday(profile, date)

            if self.args.tag:
                if not self.hatchbuck.profile_contains(profile, 'tags', 'name',
                                                       self.args.tag):
                    self.hatchbuck.add_tag(profile['contactId'], self.args.tag)


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
