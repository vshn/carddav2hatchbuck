#!/usr/bin/env python3
"""
Downloads address book(s) from CardDAV sources to synchronize the contacts
with hatchbuck CRM

Reads the CardDAV login credentials from environment variables
VDIRSYNC_USER and VDIRSYNC_PASS
"""
import logging
import os
import os.path
import pathlib
import subprocess
import time

import sentry_sdk

from .carddavsync import HatchbuckParser
from .cli import parse_arguments


def run_carddav_sync(args):
    """Fetch contacts from CardDAV source and sync with Hatchbuck"""
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    logging.info("Starting carddav sync at %s with arguments: %s", now, args)

    carddav_dir = pathlib.Path("carddav")
    carddav_dir.mkdir(parents=True, exist_ok=True)

    sync_template = "vdirsyncer.config.template"
    sync_config = "vdirsyncer.config"

    with open(sync_template, "r") as template:
        content = template.read()
        content = content.replace("VDIRSYNC_URL", args.vdirsync_url)
        content = content.replace("VDIRSYNC_USER", args.vdirsync_user)
        content = content.replace("VDIRSYNC_PASS", args.vdirsync_pass)

    with open(sync_config, "w") as config_file:
        config_file.write(content)

    # NOTE: This should be done with Python module calls
    # see https://github.com/pimutils/vdirsyncer/issues/770
    subprocess.run(
        "yes | vdirsyncer -c vdirsyncer.config discover",
        shell=True,
        check=True,
        stdout=subprocess.PIPE,
    )

    subprocess.run(
        "vdirsyncer -c vdirsyncer.config sync",
        shell=True,
        check=True,
        stdout=subprocess.PIPE,
    )

    os.remove(sync_config)

    logging.info("CardDAV sync done, starting carddavsync")

    files_list = os.listdir(carddav_dir.name)

    for file_name in files_list:
        file_detail = file_name.split("_")
        if len(file_detail) == 4:
            firstname, _, lastname, _ = file_detail
            args.tag = "Adressbuch-%s" % firstname
            args.user = "%s.%s" % (firstname, lastname)
            args.dir = [os.path.join("carddav", file_name)]
            parser = HatchbuckParser(args)
            parser.main()
        else:
            logging.info(
                "File naming scheme not compatible." " Skipping: %s", file_detail
            )
            continue


def run():
    """Main entry point"""
    args = parse_arguments()
    args.update = True
    sentry_sdk.init()
    logformat = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log = logging.getLogger()
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG, format=logformat)
        log.setLevel(logging.DEBUG)
    else:
        print("nonverbose")
        logging.basicConfig(level=logging.INFO, format=logformat)
        log.setLevel(logging.INFO)
        logging.getLogger("requests.packages.urllib3.connectionpool").setLevel(
            logging.WARNING
        )
    run_carddav_sync(args)


if __name__ == "__main__":
    run()
