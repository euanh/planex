"""
planex-resultname: Print the name of the binary package which will be produced
by building a spec file.
"""

import argparse
import os
import sys

import argcomplete
from planex.util import add_common_parser_options
from planex.util import setup_sigint_handler
import planex.spec as pkg


def parse_args_or_exit(argv=None):
    """
    Parse command line options
    """
    parser = argparse.ArgumentParser(
        description="Generate Makefile dependencies from RPM Spec files")
    add_common_parser_options(parser)
    parser.add_argument("specs", metavar="SPEC", nargs="+", help="spec file")
    parser.add_argument(
        "-p", "--path", default=False, action="store_true",
        help="Print full output file path")
    parser.add_argument(
        "-s", "--source", default=False, action="store_true",
        help="Print source package name ")
    parser.add_argument(
        "-D", "--define", default=[], action="append",
        help="--define='MACRO EXPR' define MACRO with value EXPR")
    argcomplete.autocomplete(parser)
    return parser.parse_args(argv)


def main(argv=None):
    """
    Entry point
    """
    setup_sigint_handler()
    args = parse_args_or_exit(argv)

    macros = [tuple(macro.split(' ', 1)) for macro in args.define]

    if any(len(macro) != 2 for macro in macros):
        _err = [macro for macro in macros if len(macro) != 2]
        print "error: malformed macro passed to --define: %r" % _err
        sys.exit(1)

    for spec_path in [spec for spec in args.specs if spec.endswith(".spec")]:
        spec = pkg.Spec(spec_path, check_package_name=False, defines=macros)
        if args.source:
            output = spec.source_package_path()
        else:
            output = spec.binary_package_paths()[-1]

        if args.path:
            print output
        else:
            print os.path.basename(output)
