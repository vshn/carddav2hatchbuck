#!/usr/bin/env python3
"""
This script downloads address book(s) from CardDAV sources to
synchronize the contacts with hatchbuck CRM

It reads the CardDAV login credentials from environment variables
VDIRSYNC_USER and VDIRSYNC_PASS
"""
import pathlib
import time
import os
import sys
import subprocess
import argparse
from dotenv import load_dotenv
from carddavsync import HatchbuckArgs, HatchbuckParser

PARSER = argparse.ArgumentParser(
    description='sync carddav address books and synchonize'
                ' each of them with hatchbuck')
PARSER.add_argument('-n', '--noop',
                    help='dont actually post anything to hatchbuck,'
                         ' just log what would have been posted',
                    action='store_true', default=False)
ARG = PARSER.parse_args()

load_dotenv()

NOW = time.strftime('%Y-%m-%d %H:%M:%S')
print('Starting carddav sync at %s ...' % NOW)

CARDDAV_DIR = pathlib.Path('carddav')
CARDDAV_DIR.mkdir(parents=True, exist_ok=True)

try:
    URL = os.environ['VDIRSYNC_URL']
    USERNAME = os.environ['VDIRSYNC_USER']
    PASSWORD = os.environ['VDIRSYNC_PASS']

    ARGS = HatchbuckArgs()
    ARGS.hatchbuck = os.environ['HATCHBUCK_KEY']
    ARGS.source = os.environ['HATCHBUCK_SOURCE']
    ARGS.verbose = False
    ARGS.update = True
    ARGS.noop = ARG.noop

except KeyError:
    print('Environment variables must be set:'
          ' VDIRSYNC_URL, VDIRSYNC_USER, VDIRSYNC_PASS')
    print('Aborting.')
    sys.exit(1)

with open('vdirsyncer.config.template', 'r') as template:
    CONTENT = template.read()
    CONTENT = CONTENT.replace('VDIRSYNC_URL', URL)
    CONTENT = CONTENT.replace('VDIRSYNC_USER', USERNAME)
    CONTENT = CONTENT.replace('VDIRSYNC_PASS', PASSWORD)

with open('vdirsyncer.config', 'w') as config:
    config.write(CONTENT)

subprocess.run("yes | vdirsyncer -c vdirsyncer.config discover",
               shell=True,
               check=True,
               stdout=subprocess.PIPE)

subprocess.run("vdirsyncer -c vdirsyncer.config sync",
               shell=True,
               check=True,
               stdout=subprocess.PIPE)

os.remove('vdirsyncer.config')

print('Carddav sync done, starting carddavsync')

FILES_LIST = os.listdir("./carddav")
for file_name in FILES_LIST:
    file_detail = file_name.split('_')
    if len(file_detail) == 4:
        ARGS.tag = 'Adressbuch-' + file_detail[0]
        ARGS.user = file_detail[0] + '.' + file_detail[2]
        ARGS.dir = ['carddav/{}/'.format(file_name)]
        PARSER = HatchbuckParser(ARGS)
        PARSER.main()
    else:
        print('File not compatible. Skipping: %s' % file_detail)
        continue
