"""
Command line interface implementation.
"""
import argparse
import os
from dotenv import load_dotenv


def parse_arguments():
    """
    Parse arguments from command line
    """
    load_dotenv(verbose=True)

    key = os.environ.get('HATCHBUCK_KEY')
    source = os.environ.get('HATCHBUCK_SOURCE')
    vdirsync_user = os.environ.get('VDIRSYNC_USER')
    vdirsync_pass = os.environ.get('VDIRSYNC_PASS')
    vdirsync_url = os.environ.get('VDIRSYNC_URL')

    usage_style = argparse.ArgumentDefaultsHelpFormatter \
        if key or source or vdirsync_user or vdirsync_pass or vdirsync_url \
        else argparse.HelpFormatter

    parser = argparse.ArgumentParser(
        description='parse vcard (.vcf) contact files',
        formatter_class=usage_style)
    parser.add_argument('--hatchbuck', type=str,
                        help='Hatchbuck API key (env: HATCHBUCK_KEY)',
                        default=key, required=not key)
    parser.add_argument('-s', '--source', type=str,
                        help='Hatchbuck contact source (env: HATCHBUCK_SOURCE)',
                        default=source, required=not source)
    parser.add_argument('--vdirsync-user', type=str,
                        help='vdirsync user name (env: VDIRSYNC_USER)',
                        default=vdirsync_user, required=not vdirsync_user)
    parser.add_argument('--vdirsync-pass', type=str,
                        help='vdirsync password (env: VDIRSYNC_PASS)',
                        default=vdirsync_pass, required=not vdirsync_pass)
    parser.add_argument('--vdirsync-url', type=str,
                        help='vdirsync URL (env: VDIRSYNC_URL)',
                        default=vdirsync_url, required=not vdirsync_url)
    parser.add_argument('-t', '--tag', help='Hatchbuck contact tag')
    parser.add_argument('--user', help='Hatchbuck sales rep username')
    parser.add_argument('-v', '--verbose', help='output verbose debug logging',
                        action='store_true', default=False)
    parser.add_argument('-u', '--update',
                        help='only update existing contacts in hatchbuck,'
                             " don't add new ones",
                        action='store_true', default=False)
    parser.add_argument('-n', '--noop',
                        help="don't actually post anything to hatchbuck,"
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
