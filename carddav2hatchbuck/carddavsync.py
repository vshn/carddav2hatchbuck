#!/usr/bin/env python3
"""
Hatchbuck parser. Run from command line or import as module.
"""
import logging
import os
import pprint
import re
import sys
import binascii

import phonenumbers
import vobject

from hatchbuck import Hatchbuck
from pycountry import countries

from .cli import parse_arguments
from .logger import configure as configure_logging
from .notifications import NotificationService


class HatchbuckParser:
    """
    An object that does all the parsing for/with Hatchbuck.
    """

    def __init__(self, args):
        self.args = args
        self.stats = {}
        self.hatchbuck = None
        self.log = configure_logging(self.args.verbose)

    def main(self):
        """Parsing gets kicked off here"""
        self.log.debug("starting with arguments: %s", self.args)
        self.init_hatchbuck()
        self.parse_files()

    def show_summary(self):
        """Show some statistics"""
        print(self.stats)

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
                self.log.debug("parsing file %s", file)
                self.parse_file(file)
        elif self.args.dir:
            for direc in self.args.dir:
                self.log.debug("using directory %s", direc)
                for file in os.listdir(direc):
                    if file.endswith(".vcf"):
                        file_path = os.path.join(direc, file)
                        self.log.debug("parsing file %s", file_path)
                        try:
                            self.parse_file(file_path)
                        except binascii.Error as error:
                            self.log.error("error parsing: %s", error)
        else:
            print('Nothing to do.')

    @staticmethod
    def short_contact(profile):
        """
        Return a short version of an contact
        """
        text = ''

        if profile.get('firstName', False) and profile.get('lastName', False):
            text += '%s %s, ' % (profile['firstName'], profile['lastName'])
        for email in profile.get('emails', []):
            text += '%s, ' % email['address']

        return 'Contact(%s)' % text[:-2]

    # pylint: disable=too-many-branches
    # pylint: disable=too-many-locals
    # pylint: disable=too-many-statements
    def parse_file(self, file):
        """
        Parse a single address book file
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
            if 'email' not in content or \
                    not re.match(r"^[^@]+@[^@]+\.[^@]+$", content['email'][0].value):
                self.stats['noemail'] = self.stats.get('noemail', 0) + 1
                return
            self.stats['valid'] = self.stats.get('valid', 0) + 1

            # aggregate stats what kind of fields we have available
            for i in content:
                # if i in c:
                self.stats[i] = self.stats.get(i, 0) + 1

            emails = []
            for email in content.get('email', []):
                if re.match(r"^[^@äöü]+@[^@]+\.[^@]+$", email.value):
                    emails.append(email.value)

            profile_list = []
            for email in emails:
                profile = self.hatchbuck.search_email(email)
                if profile:
                    profile_list.append(profile)
                else:
                    continue

            # No contacts found
            if not profile_list:
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
                self.log.info("added contact: %s", profile)

            for profile in profile_list:
                if profile['firstName'] == '':
                    profile = self.hatchbuck.profile_add(profile, 'firstName',
                                                         None,
                                                         content['n'][0].
                                                         value.given)

                if profile['lastName'] == '':
                    profile = self.hatchbuck.profile_add(profile, 'lastName',
                                                         None,
                                                         content['n'][0].
                                                         value.family)

                if 'title' in content and profile.get('title', '') == '':
                    profile = self.hatchbuck.profile_add(profile, 'title',
                                                         None,
                                                         content['title'][0].
                                                         value)
                if 'company' in profile:
                    if 'org' in content and profile.get('company', '') == '':
                        profile = self.hatchbuck.profile_add(profile, 'company',
                                                             None,
                                                             content['org'][0].
                                                             value)
                    if profile['company'] == '':
                        # empty company name ->
                        # maybe we can guess the company name from the email
                        # address?
                        # self.log.warning("empty company with emails: %s",
                        #                  profile['emails'])
                        pass

                    # clean up company name
                    if re.match(r";$", profile['company']):
                        self.log.warning("found unclean company name: %s",
                                         profile['company'])

                    if re.match(r"\|", profile['company']):
                        self.log.warning("found unclean company name: %s",
                                         profile['company'])

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
                    self.log.debug("adding address %s %s", address, profile)
                    profile = self.hatchbuck.profile_add_address(
                        profile, address, kind)

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
                        self.log.warning("could not parse number %s in %s",
                                         telefon.value,
                                         self.short_contact(profile))
                        pformatted = telefon.value

                        # try to guess the country from the addresses
                        countries_found = []
                        for addr in profile.get('addresses', []):
                            if addr.get('country', False) and \
                                    addr['country'] not in countries_found:
                                countries_found.append(addr['country'])
                        self.log.debug("countries found %s", countries_found)

                        if len(countries_found) == 1:
                            # lets try to parse the number with the country
                            countrycode = countries.lookup(
                                countries_found[0]).alpha_2
                            self.log.debug("countrycode %s", countrycode)
                            try:
                                phonenumber = phonenumbers.parse(
                                    telefon.value,
                                    countrycode)
                                pformatted = phonenumbers.format_number(
                                    phonenumber,
                                    phonenumbers.PhoneNumberFormat.INTERNATIONAL
                                )
                                self.log.debug("guess %s", pformatted)
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
                                self.log.warning(
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
                                self.log.warning("not adding number %s in %s",
                                                 num,
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
                            self.log.warning("number from %s to %s",
                                             telefon,
                                             pformatted)
                            profile = self.hatchbuck.profile_add(
                                profile,
                                'phones',
                                'number',
                                pformatted,
                                {'id': telefon['id'], 'type': telefon['type']}
                            )

                    except phonenumbers.phonenumberutil.NumberParseException:
                        self.log.warning("could not parse number %s in %s",
                                         telefon['number'],
                                         self.short_contact(profile))
                        num = telefon['number'].replace(' ', '')[1:]
                        redundant = False
                        for tel2 in profile['phones']:
                            if tel2['id'] != telefon['id'] and \
                                    tel2['number'].replace(' ', '').endswith(num):
                                self.log.warning("redundant number %s in %s",
                                                 num,
                                                 self.short_contact(profile))
                                redundant = True
                                break
                        if redundant:
                            # delete this number
                            newprofile = self.hatchbuck.update(
                                profile['contactId'],
                                {'phones': [
                                    {'number': '',
                                     'id': telefon['id'],
                                     'type': telefon['type'], }, ]})
                            if newprofile is not None:
                                # if the removal was successful continue working
                                # with the new profile
                                profile = newprofile
                        else:
                            # so this is an unique number but without country code
                            # try to guess the country from the postal addresses
                            countries_found = []
                            for addr in profile.get('addresses', []):
                                if addr.get('country', False) and \
                                        addr['country'] not in countries_found:
                                    countries_found.append(addr['country'])
                            self.log.debug("countries found %s", countries_found)
                            if len(countries_found) == 1:
                                # lets try to parse the number with the country
                                countrycode = countries.lookup(
                                    countries_found[0]).alpha_2
                                self.log.debug("countrycode %s", countrycode)
                                try:
                                    phonenumber = phonenumbers.parse(
                                        telefon.value,
                                        countrycode)
                                    pformatted = phonenumbers.format_number(
                                        phonenumber,
                                        phonenumbers.PhoneNumberFormat
                                        .INTERNATIONAL)
                                    self.log.debug("guess %s", pformatted)
                                    profile = self.hatchbuck.update(
                                        profile['contactId'],
                                        {
                                            'phones': [
                                                {
                                                    'number': pformatted,
                                                    'id': telefon['id'],
                                                    'type': telefon['type'],
                                                },
                                            ],
                                        })
                                    # if we got here we now have a full number
                                    continue
                                except phonenumbers.phonenumberutil.NumberParseException:
                                    self.log.warning("could not parse number %s in %s",
                                                     telefon.value,
                                                     self.short_contact(profile))

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

            # get the list of unique contacts IDs to detect if there are
            # multiple contacts in hatchbuck for this one contact in CardDAV
            profile_contactids = []
            message = ""
            for profile in profile_list:
                if profile['contactId'] not in profile_contactids:
                    profile_contactids.append(profile['contactId'])

                    email_profile = " "
                    for email_add in profile.get('emails', []):
                        email_profile = email_add['address'] + " "

                    number_profile = " "
                    for phone_number in profile.get('phones', []):
                        number_profile = phone_number['number'] + " "

                    message += "{0} {1} ({2}, {3}, {4})".format(
                        profile['firstName'], profile['lastName'],
                        email_profile, number_profile,
                        profile['contactUrl']) + ', '

            if len(profile_contactids) > 1:
                # there are duplicates
                NotificationService().send_message(
                    'Duplicates: %s from file: %s' % (message[:-2], file)
                )


def main():
    """Script execution starts here."""
    args = parse_arguments()

    parser = HatchbuckParser(args)
    parser.main()
    parser.show_summary()


if __name__ == "__main__":
    main()
