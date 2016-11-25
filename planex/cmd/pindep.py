"""
planex-pindep: Generate Makefile-format dependencies for links and pins
"""

from collections import OrderedDict
import argparse
import glob
import os
import sys

import argcomplete
from planex.spec import add_macro, rpm_macros, append_macros
from planex.spec import specdir, sourcedir, topdir
from planex.util import add_common_parser_options
from planex.util import setup_sigint_handler


def parse_args_or_exit(argv=None):
    """
    Parse command line options
    """
    parser = argparse.ArgumentParser(
        description="Generate Makefile dependencies from RPM Spec files")
    add_common_parser_options(parser)
    parser.add_argument("specs", metavar="SPEC", nargs="+", help="spec file")
    parser.add_argument(
        "-D", "--define", default=[], action="append",
        help="--define='MACRO EXPR' define MACRO with value EXPR")
    parser.add_argument("-P", "--pins-dir", default="PINS",
                        help="Directory containing pin overlays")
    argcomplete.autocomplete(parser)
    return parser.parse_args(argv)


def pkgname(path):
    """
    Return the name of the package at path
    """
    return os.path.splitext(os.path.basename(path))[0]


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

    # _topdir defaults to $HOME/rpmbuild
    # If present, it needs to be applied once at the beginning
    if '_topdir' in macros:
        add_macro('_topdir', macros['_topdir'])

    pins = []
    if args.pins_dir:
        pins_glob = os.path.join(args.pins_dir, "*.pin")
        pins = glob.glob(pins_glob)

    specs = [arg for arg in args.specs if arg.endswith(".spec")]
    links = [arg for arg in args.specs if arg.endswith(".lnk")]

    for pin in pins:
        local_macros = OrderedDict([
            ('name', pkgname(pin)),
        ])
        with rpm_macros(append_macros(OrderedDict(macros), local_macros)):
            print "%s.spec: %s" % (specdir(pkgname(pin)), pin)
            print "%s: %s" % (sourcedir("patches.tar"), pin)
            print "%s: %s" % (sourcedir("patches.tar"),
                              os.path.join("SPECS", pkgname(pin) + ".spec"))
            print "%s: %s.spec" % (topdir("deps"), specdir(pkgname(pin)))

    for link in links:
        with rpm_macros(OrderedDict(macros)):
            if pkgname(link) not in [pkgname(pin) for pin in pins]:
                print "%s.spec: %s" % (specdir(pkgname(link)), link)
                print "%s: %s.spec" % (topdir("deps"), specdir(pkgname(link)))
                print "%s: %s" % (topdir("deps"), link)

    for spec in specs:
        with rpm_macros(OrderedDict(macros)):
            print "%s.spec: %s" % (specdir(pkgname(spec)), spec)
            print "%s: %s.spec" % (topdir("deps"), specdir(pkgname(spec)))
