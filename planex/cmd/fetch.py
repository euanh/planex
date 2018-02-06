"""
planex-fetch: Download sources referred to by a spec file
"""

import argparse
import logging
import os
import shutil
import sys
import urlparse

import argcomplete
import pkg_resources
from urlgrabber.grabber import URLGrabber, URLGrabError

from planex.link import Link
from planex.cmd.args import common_base_parser, rpm_define_parser
from planex.util import run
from planex.util import setup_logging
from planex.util import setup_sigint_handler
import planex.spec


# This should include all of the extensions in the Makefile.rules for fetch
SUPPORTED_EXT_TO_MIME = {
    '.tar': 'application/x-tar',
    '.gz': 'application/x-gzip',
    '.tgz': 'application/x-gzip',
    '.txz': 'application/x-gzip',
    '.bz2': 'application/x-bzip2',
    '.tbz': 'application/x-bzip2',
    '.zip': 'application/zip',
    '.pdf': 'application/pdf',
    '.patch': 'text/x-diff'
}

SUPPORTED_URL_SCHEMES = ["http", "https", "file", "ftp"]


def best_effort_file_verify(path):
    """
    Given a path, check if the file at that path has a sensible format.
    If the file has an extension then it checks that the mime-type of this file
    matches that of the file extension as defined by the IANA:
        http://www.iana.org/assignments/media-types/media-types.xhtml
    """
    _, ext = os.path.splitext(path)
    if ext and ext in SUPPORTED_EXT_TO_MIME:
        # output of `file` is of form: "<path>: <mime-type>"
        cmd = ["file", "--mime-type", path]
        stdout = run(cmd, check=False)['stdout'].strip()
        _, _, mime_type = stdout.partition(': ')

        if SUPPORTED_EXT_TO_MIME[ext] != mime_type:
            sys.exit("%s: Fetched file format looks incorrect: %s: %s" %
                     (sys.argv[0], path, mime_type))


def parse_args_or_exit(argv=None):
    """
    Parse command line options
    """
    parser = argparse.ArgumentParser(description='Download package sources',
                                     parents=[common_base_parser(),
                                              rpm_define_parser()])
    parser.add_argument('spec_or_link', help='RPM Spec or link file')
    parser.add_argument("source", metavar="SOURCE",
                        help="Source file to fetch")
    parser.add_argument('--retries', '-r',
                        help='Number of times to retry a failed download',
                        type=int, default=5)
    parser.add_argument('--no-package-name-check', dest="check_package_names",
                        action="store_false", default=True,
                        help="Don't check that package name matches spec "
                        "file name")
    argcomplete.autocomplete(parser)
    return parser.parse_args(argv)


def fetch_url(url, filename, retries):
    """Fetch from specified URL"""
    planex_version = pkg_resources.require("planex")[0].version
    user_agent = "planex-fetch/%s" % planex_version
    try:
        # Using urlgrab() sometimes results in a 0 byte file;
        # urlread() anfd shutil.copyfileobj() are more reliable
        source = URLGrabber().urlopen(url, retry=retries,
                                      user_agent=user_agent)
        with open(filename, "wb") as destination:
            shutil.copyfileobj(source, destination)

    except URLGrabError as exn:
        # Download failed
        sys.exit("%s: Failed to fetch %s: %s" %
                 (sys.argv[0], url, exn.strerror))

    except IOError as exn:
        # IO error saving source file
        sys.exit("%s: %s: %s" %
                 (sys.argv[0], exn.strerror, exn.filename))

    finally:
        source.close()


def fetch_source(args):
    """
    Download requested source using URL from spec file.
    """

    spec = planex.spec.Spec(args.spec_or_link,
                            check_package_name=args.check_package_names,
                            defines=args.define)

    try:
        path, url = spec.source(args.source)
    except KeyError as exn:
        sys.exit("%s: No source corresponding to %s" % (sys.argv[0], exn))

    parsed = urlparse.urlparse(url)
    if parsed.scheme in SUPPORTED_URL_SCHEMES:
        fetch_url(url, path, args.retries + 1)

    elif parsed.scheme == '' and os.path.dirname(parsed.path) == '':
        if not os.path.exists(path):
            sys.exit("%s: Source not found: %s" % (sys.argv[0], path))

        # Source file is pre-populated in the SOURCES directory (part of
        # the repository - probably a patch or local include).   Update
        # its timestamp to placate make, but don't try to download it.
        logging.debug("Refreshing timestamp for local source %s", path)
        os.utime(path, None)

    else:
        sys.exit("%s: Unsupported url scheme %s" %
                 (sys.argv[0], parsed.scheme))


def fetch_via_link(args):
    """
    Parse link file and download patch tarball.
    """
    link = Link(args.spec_or_link)

    if link.schema_version == 1:
        fetch_url(link.url, args.source, args.retries + 1)
    else:
        target, _ = os.path.splitext(os.path.basename(args.source))
        patch_urls = link.patch_sources
        if target in patch_urls:
            patch_url = patch_urls.get(target)['URL']
            fetch_url(patch_url, args.source, args.retries + 1)

        patchqueues = link.patchqueue_sources
        if target in patchqueues:
            patchqueue_url = patchqueues.get(target)['URL']
            fetch_url(patchqueue_url, args.source, args.retries + 1)


def main(argv=None):
    """
    Main function.  Fetch sources directly or via a link file.
    """
    setup_sigint_handler()
    args = parse_args_or_exit(argv)
    setup_logging(args)

    if args.spec_or_link.endswith('.spec'):
        fetch_source(args)
    elif args.spec_or_link.endswith('.lnk'):
        fetch_via_link(args)
    else:
        sys.exit("%s: Unsupported file type: %s" % (sys.argv[0],
                                                    args.spec_or_link))
