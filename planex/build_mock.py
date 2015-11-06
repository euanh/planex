#!/usr/bin/python

"""
planex-cache: A caching wrapper around mock for building RPMs
"""

import argparse
import logging
import os
import shutil
import sys
import tempfile

import argcomplete
from planex import util


def parse_args_or_exit(argv=None):
    """
    Parse command line options
    """
    parser = argparse.ArgumentParser(description='Cache package building')
    util.add_common_parser_options(parser)

    # Overridden mock arguments.  Help text taken directly from mock.
    parser.add_argument(
        '--configdir', default="/etc/mock",
        help='Change where config files are found')
    parser.add_argument(
        '--resultdir', default="/tmp/badger",
        help='path for resulting files to be put')
    parser.add_argument(
        '-r', '--root', default="default",
        help='chroot name/config file name default: default')
    argcomplete.autocomplete(parser)
    return parser.parse_known_args(argv)


def build_package(configdir, root, passthrough_args):
    """
    Spawn a mock process to build the package.   Some arguments
    are intercepted and rewritten, for instance --resultdir.
    """
    working_directory = tempfile.mkdtemp(prefix="planex-mock-build")
    logging.debug("Mock working directory: %s", working_directory)

    cmd = ["mock", "--configdir=%s" % configdir, "-v",
           "--root=%s" % root,
           "--resultdir=%s" % working_directory] + passthrough_args

    logfiles = [os.path.join(working_directory, "root.log"),
                os.path.join(working_directory, "build.log")]
    util.run(cmd, logfiles=logfiles)

    return working_directory


def main(argv):
    """
    Main function.  Parse spec file and iterate over its sources, downloading
    them as appropriate.
    """
    util.setup_sigint_handler()
    intercepted_args, passthrough_args = parse_args_or_exit(argv)
    util.setup_logging(intercepted_args)

    # Expand default resultdir as done in mock.backend.Root
    resultdir = intercepted_args.resultdir

    if not os.path.isdir(resultdir):
        os.makedirs(resultdir)

    build_output = build_package(intercepted_args.configdir,
                                 intercepted_args.root, passthrough_args)

    for cached_file in os.listdir(build_output):
        dest = os.path.join(resultdir, cached_file)

        if os.path.exists(dest):
            os.unlink(dest)
        shutil.move(os.path.join(build_output, cached_file), resultdir)


def _main():
    """
    Entry point for setuptools CLI wrapper
    """
    main(sys.argv[1:])

# Entry point when run directly
if __name__ == "__main__":
    _main()
