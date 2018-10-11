#!/usr/bin/env python3
"""
This script downloads address book(s) from CardDAV sources to
synchronize the contacts with hatchbuck CRM

It reads the CardDAV login credentials from environment variables
VDIRSYNC_USER and VDIRSYNC_PASS
"""

import argparse
import pathlib
import os
import os.path
import subprocess
import sys
import time
from dotenv import find_dotenv, load_dotenv

from .carddavsync import HatchbuckArgs, HatchbuckParser, parse_arguments


def run():
    """Main entry point"""
    args = parse_arguments()
    args.update = True
    run_carddav_sync(args)


def run_carddav_sync(args):
    """Fetch contacts from CardDAV source and sync with Hatchbuck"""
    now = time.strftime('%Y-%m-%d %H:%M:%S')
    print('Starting carddav sync at %s ...' % now)

    carddav_dir = pathlib.Path('carddav')
    carddav_dir.mkdir(parents=True, exist_ok=True)

    sync_template = 'vdirsyncer.config.template'
    sync_config = 'vdirsyncer.config'

    with open(sync_template, 'r') as template:
        content = template.read()
        content = content.replace('VDIRSYNC_URL', args.vdirsync_url)
        content = content.replace('VDIRSYNC_USER', args.vdirsync_user)
        content = content.replace('VDIRSYNC_PASS', args.vdirsync_pass)

    with open(sync_config, 'w') as config_file:
        config_file.write(content)

    # NOTE: This should be done with Python module calls
    # see https://github.com/pimutils/vdirsyncer/issues/770
    subprocess.run("yes | vdirsyncer -c vdirsyncer.config discover",
                   shell=True,
                   check=True,
                   stdout=subprocess.PIPE)

    subprocess.run("vdirsyncer -c vdirsyncer.config sync",
                   shell=True,
                   check=True,
                   stdout=subprocess.PIPE)

    os.remove(sync_config)

    print('CardDAV sync done, starting carddavsync')

    files_list = os.listdir(carddav_dir.name)

    for file_name in files_list:
        file_detail = file_name.split('_')
        if len(file_detail) == 4:
            firstname, _, lastname, _ = file_detail
            args.tag = 'Adressbuch-%s' % firstname
            args.user = '%s.%s' % (firstname, lastname)
            args.dir = [os.path.join('carddav', file_name)]
            parser = HatchbuckParser(args)
            parser.main()
        else:
            print('File naming scheme not compatible.'
                  ' Skipping: %s' % file_detail)
            continue


if __name__ == "__main__":
    run()
