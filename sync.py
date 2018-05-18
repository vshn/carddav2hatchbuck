#!/usr/bin/env python3
"""
This script downloads address book(s) from CardDAV sources to
synchronize the contacts with hatchbuck CRM

It reads the CardDAV login credentials from environment variables
VDIRSYNC_USER and VDIRSYNC_PASS
"""
from carddavsync import HatchbuckArgs, HatchbuckParser
from dotenv import load_dotenv
import pathlib
import time
import os
import sys
import subprocess

load_dotenv()

now = timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
print('Starting carddav sync at %s ...' % now)

carddav_dir = pathlib.Path('carddav')
carddav_dir.mkdir(parents=True, exist_ok=True)

try:
    url = os.environ['VDIRSYNC_URL']
    username = os.environ['VDIRSYNC_USER']
    password = os.environ['VDIRSYNC_PASS']

    args = HatchbuckArgs()
    args.hatchbuck = os.environ['HATCHBUCK_KEY']
    args.source = os.environ['HATCHBUCK_SOURCE']
except KeyError:
    print('Environment variables must be set:'
          ' VDIRSYNC_URL, VDIRSYNC_USER, VDIRSYNC_PASS')
    print('Aborting.')
    sys.exit(1)

with open('vdirsyncer.config.template', 'r') as template:
    content = template.read()
    content = content.replace('VDIRSYNC_URL', url)
    content = content.replace('VDIRSYNC_USER', username)
    content = content.replace('VDIRSYNC_PASS', password)

with open('vdirsyncer.config', 'w') as config:
    config.write(content)

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

files_list = os.listdir("./carddav")
for file_name in files_list:
    file_detail = file_name.split('_')
    if len(file_detail) == 4:
        print(file_detail)
        args.tag = 'Adressbuch-'+file_detail[0]
        args.user = file_detail[0]+'.'+file_detail[2]
        args.dir = ['carddav/{}/'.format(file_name)]
        parser = HatchbuckParser(args)
        parser.main()
    else:
        print('File not compatible. Skipping: %s'
              % file_detail)
        continue
