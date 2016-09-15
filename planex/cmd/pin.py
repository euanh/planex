"""
planex-pin: Create a patchqueue tarball from a pin file
"""

import argparse
import os
import shutil
import tempfile

import argcomplete

from planex.link import Link
from planex.spec import Spec
import planex.git as git
import planex.tarball as tarball
import planex.util as util


def parse_args_or_exit(argv=None):
    """
    Parse command line options
    """
    parser = argparse.ArgumentParser(description='Planex SRPM building')
    util.add_common_parser_options(parser)
    parser.add_argument("pin", metavar="PIN", help="pin file")
    parser.add_argument("tarball", metavar="TARBALL", help="tarball")
    parser.add_argument("--keeptmp", action="store_true",
                        help="Do not clean up working directory")
    argcomplete.autocomplete(parser)
    return parser.parse_args(argv)


def main(argv=None):
    """
    Entry point
    """
    args = parse_args_or_exit(argv)
    pin = Link(args.pin)

    # Repo and ending tag are specified in the pin file
    repo = pin.url
    end_tag = pin.commitish

    # Start tag is based on the version specified in the spec file,
    # but the tag name may be slightly different (v1.2.3 rather than 1.2.3)
    # If the pin file does not list a spec file, assume that there is one in
    # the usual place
    spec_path = pin.specfile
    if not spec_path:
        basename = os.path.splitext(os.path.basename(args.pin))[0]
        spec_path = os.path.join("SPECS", "%s.spec" % basename)
    spec = Spec(spec_path)
    start_tag = spec.version()
    if start_tag not in git.tags(repo):
        start_tag = "v%s" % start_tag

    try:
        # Assemble the contents of the patch queue in a temporary directory
        tmpdir = tempfile.mkdtemp()
        patchqueue = os.path.join(tmpdir, pin.patchqueue)
        os.makedirs(patchqueue)
        patches = git.format_patch(repo, start_tag, end_tag, patchqueue)
        with open(os.path.join(patchqueue, "series"), "w") as series:
            for patch in patches:
                series.write(os.path.basename(patch) + "\n")

        # Archive the assembled patch queue
        tarball.make(tmpdir, args.tarball)

    finally:
        if args.keeptmp:
            print "Working directory retained at %s" % tmpdir
        else:
            shutil.rmtree(tmpdir)
