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
import subprocess
import sys
import time
from dotenv import load_dotenv

from .carddavsync import HatchbuckArgs, HatchbuckParser


def run():
    """Main entry point"""
    args = parse_commandline_args()
    config = get_configuration(args)
    run_carddav_sync(**config)


def parse_commandline_args():
    """Evaluate the command line"""
    parser = argparse.ArgumentParser(
        description='sync carddav address books and synchonize'
                    ' each of them with hatchbuck')
    parser.add_argument('-n', '--noop',
                        help='dont actually post anything to hatchbuck,'
                             ' just log what would have been posted',
                        action='store_true', default=False)

    args = parser.parse_args()
    return args


def get_configuration(commandline_args):
    """Collect configuration data from environment"""
    load_dotenv()

    now = time.strftime('%Y-%m-%d %H:%M:%S')
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
        args.verbose = False
        args.update = True
        args.noop = commandline_args.noop

    except KeyError:
        print('Environment variables must be set:'
              ' VDIRSYNC_URL, VDIRSYNC_USER, VDIRSYNC_PASS')
        print('Aborting.')
        sys.exit(1)

    config = dict(args=args,
                  carddav_dir=carddav_dir,
                  url=url,
                  username=username,
                  password=password)
    return config


def run_carddav_sync(**config):
    """Fetch contacts from CardDAV source and sync with Hatchbuck"""
    sync_template = 'vdirsyncer.config.template'
    sync_config = 'vdirsyncer.config'

    with open(sync_template, 'r') as template:
        content = template.read()
        content = content.replace('VDIRSYNC_URL', config['url'])
        content = content.replace('VDIRSYNC_USER', config['username'])
        content = content.replace('VDIRSYNC_PASS', config['password'])

    with open(sync_config, 'w') as config:
        config.write(content)

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

    args, carddav_dir = config['args'], config['carddav_dir']
    files_list = os.listdir(carddav_dir.name)

    for file_name in files_list:
        file_detail = file_name.split('_')
        if len(file_detail) == 4:
            args.tag = 'Adressbuch-' + file_detail[0]
            args.user = file_detail[0] + '.' + file_detail[2]
            args.dir = ['carddav/{}/'.format(file_name)]
            parser = HatchbuckParser(args)
            parser.main()
        else:
            print('File not compatible. Skipping: %s' % file_detail)
            continue


if __name__ == "__main__":
    run()
