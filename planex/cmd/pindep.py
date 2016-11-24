"""
planex-pindep: Generate Makefile-format dependencies for links and pins
"""

import argparse
import glob
import os

import argcomplete
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

    # Should be a path variable or multiple overriding args
    pins = []
    if args.pins_dir:
        pins_glob = os.path.join(args.pins_dir, "*.pin")
        pins = glob.glob(pins_glob)

    specs = [arg for arg in args.specs if arg.endswith(".spec")]
    links = [arg for arg in args.specs if arg.endswith(".lnk")]

    for pin in pins:
        print "%s.spec: %s" % (os.path.join("_build/SPECS", pkgname(pin)), pin)
        print "%s: %s" % (os.path.join("_build/SOURCES", pkgname(pin), "patches.tar"),
                          pin)
        print "%s: %s" % (os.path.join("_build/SOURCES", pkgname(pin), "patches.tar"),
                          os.path.join("SPECS", pkgname(pin) + ".spec"))
        print "_build/deps: %s.spec" % os.path.join("_build/SPECS", pkgname(pin))

    for link in links:
        if pkgname(link) not in [pkgname(pin) for pin in pins]:
            print "%s.spec: %s" % (os.path.join("_build/SPECS", pkgname(link)),
                                   link)
            print "_build/deps: %s.spec" % os.path.join("_build/SPECS",
                                                        pkgname(link))
            print "_build/deps: %s" % link

    for spec in specs:
        print "%s.spec: %s" % (os.path.join("_build/SPECS", pkgname(spec)),
                               spec)
        print "_build/deps: %s.spec" % os.path.join("_build/SPECS",
                                                    pkgname(spec))
