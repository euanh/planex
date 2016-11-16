"""
planex-grab: Download files referred to by a link file
"""

import argparse
import os
import urlgrabber

from planex.link import Link
from planex.tarball import Tarball


def parse_args_or_exit(argv=None):
    """
    Parse command line options
    """
    parser = argparse.ArgumentParser(description='Download package sources')
    parser.add_argument('link', metavar="LINK", help='Link file')
    parser.add_argument("source", metavar="SOURCE",
                        help="Source file to fetch")
    parser.add_argument('--stdout', action="store_true", default=False,
                        help="Write fetched file to stdout")
    parser.add_argument('--output', '-o', metavar="FILE", default=None,
                        help="Write fetched file to FILE")
    return parser.parse_args(argv)


def main():
    """
    Main function.  Fetch sources directly or via a link file.
    """
    args = parse_args_or_exit()
    link = Link(args.link)
    sock = urlgrabber.urlopen(link.url)
    tarball = Tarball(fileobj=sock)

    to_extract = args.source
    if to_extract.endswith(".spec"):
        to_extract = link.specfile

    tarball.extract(to_extract, os.path.dirname(args.source))
