"""
planex-build-mock: Wrapper around mock
"""

import os
import pty
import shutil
import subprocess
import sys
import tempfile
from uuid import uuid4
from planex import util

import argparse
import argcomplete
from planex.util import add_common_parser_options


def parse_args_or_exit(argv=None):
    """
    Parse command line options
    """
    parser = argparse.ArgumentParser(
        description='Planex build system in a chroot (a mock wrapper)')
    add_common_parser_options(parser)
    parser.add_argument(
        "--configdir", metavar="CONFIGDIR", default="/etc/mock",
        help="Change where the config files are found")
    parser.add_argument(
        "--root", "-r", metavar="CONFIG", default="default",
        help="Change where the config files are found")
    parser.add_argument(
        "--resultdir", metavar="RESULTDIR", default=None,
        help="Path for resulting files to be put")
    parser.add_argument(
        "--keeptmp", action="store_true",
        help="Keep temporary files")
    parser.add_argument(
        "-D", "--define", default=[], action="append",
        help="--define='MACRO EXPR' \
              define MACRO with value EXPR for the build")
    parser.add_argument(
        "--init", action="store_true",
        help="initialize the chroot, do not build anything")
    parser.add_argument(
        "--rebuild", metavar="SRPM", nargs="+", dest="srpms",
        help='rebuild the specified SRPM(s)')
    parser.add_argument(
        "--loopback-config-extra", action='append', default=[],
        help='add extra lines to the loopback repo stanza')
    argcomplete.autocomplete(parser)
    return parser.parse_args(argv)


def pty_check_call(cmd):
    """
    Runs the given command in a subprocess with I/O redirected through a pty.
    This ensures isatty(3) will return 1.
    An exception is raised if the command exits with non-zero status.
    """
    # python2.7 doesn't return the exitcode here:
    pty.spawn(cmd)
    # get exit status of first child
    (pid, status) = os.waitpid(-1, 0)
    returncode = 1
    if status == 0:
        returncode = 0
    elif os.WIFEXITED(status):
        returncode = os.WEXITSTATUS(status)
        print "PID %d exited with status %d" % (pid, returncode)
    elif os.WIFSIGNALED(status):
        signal = os.WTERMSIG(status)
        print "PID %d exited with signal %d" % (pid, signal)
    else:
        print "PID %d exited with non-zero status 0x%02x" % (pid, status)
    if returncode > 0:
        raise subprocess.CalledProcessError(returncode, cmd)


def koji(args, resultdir, root, *extra_params):
    """
    Return koji command line and arguments
    """
    util.makedirs(resultdir)
    # XXX Should compare the srpm from koji with ours
    tmpdir = tempfile.mkdtemp(prefix="px-koji-")
    cmd = ['koji', 'download-build', os.path.basename(extra_params[0])]
    # XXX should download to a tmpdir, copy to resultdir and update timestamps
    ret = subprocess.call(cmd, cwd=tmpdir)
    if ret == 0:
       names = os.listdir(tmpdir)
       for name in names:
           srcname = os.path.join(tmpdir, name)
           dstname = os.path.join(resultdir, name)
           shutil.move(srcname, dstname)
           os.utime(dstname, None)
       shutil.rmtree(tmpdir)
       return

    cmd = ['koji', 'build', root, extra_params[0]]
    ret = subprocess.call(cmd)
    if ret != 0:
       sys.exit(1)

    cmd = ['koji', 'download-build', os.path.basename(extra_params[0])]
    ret = subprocess.call(cmd, cwd=resultdir)
    if ret != 0:
       sys.exit(1)
     
    cmd = ['koji', 'regen-repo', '--target', root]
    ret = subprocess.call(cmd)
    if ret != 0:
       sys.exit(1)


def main(argv=None):
    """
    Entry point
    """

    args = parse_args_or_exit(argv)

    try:
        koji(args, args.resultdir, args.root, *args.srpms)

    except subprocess.CalledProcessError as cpe:
        sys.exit(cpe.returncode)
