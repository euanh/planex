"""Classes for handling RPM spec files.   The classes defined here
   are mostly just wrappers around rpm.rpm, adding information which
   the rpm library does not currently provide."""
from __future__ import print_function

import contextlib
import os
import re
import urlparse
import sys
import tempfile

import rpm

from planex.link import Link


@contextlib.contextmanager
def rpm_macros(*macros):
    """
    Context manager to add and remove stacked RPM macro 'environments'.
    Macro definitions which occur later in 'macros' override definitions
    made earlier.
    """
    for macro in macros:
        for key, value in macro.items():
            rpm.addMacro(key, value)
    yield
    for macro in reversed(macros):
        for key in macro.keys():
            rpm.delMacro(key)


def nevra(package):
    """
    Returns a dictionary of macro definitions for the Name, Epoch, Version,
    Release and Architecture of package.   This dictionary can be passed to
    rpm_macros() to set up an appropriate environment for macro expansion.
    """
    return {
        'name':    package['name'],
        'epoch':   str(package['epoch'] or 1),
        'version': package['version'],
        'release': package['release'],
        'arch':    package['arch']
    }


class SpecNameMismatch(Exception):
    """Exception raised when a spec file's name does not match the name
       of the package defined within it"""
    pass


def parse_spec_quietly(path):
    """
    Parse spec file at 'path' and return an rpm.spec object.
    This function suppresses any errors about missing sources which
    librpm writes to stderr.
    """
    with tempfile.TemporaryFile() as nullfh:
        try:
            # collect all output to stderr then filter out
            # errors about missing sources
            errcpy = os.dup(2)
            try:
                os.dup2(nullfh.fileno(), 2)
                return rpm.ts().parseSpec(path)
            finally:
                os.dup2(errcpy, 2)
                os.close(errcpy)

        except ValueError as exn:
            nullfh.seek(0, os.SEEK_SET)
            # https://github.com/PyCQA/pylint/issues/1435
            # pylint: disable=E1133
            for line in nullfh:
                line = line.strip()
                if not line.endswith(': No such file or directory'):
                    print(line, file=sys.stderr)
            exn.args = (exn.args[0].rstrip() + ' ' + path, )
            raise


class Source(object):
    """Represents an RPM source file"""
    def __init__(self, parent, source):
        self.parent = parent
        self._url = source[0]
        self.order = source[1]
        self.sourcetype = source[2]  # 1 = source, 2 = patch

    def __str__(self):
        fmt = "Source%d: %s" if self.is_source() else "Patch%d: %s"
        return fmt % (self.order, self.url())

    def is_local(self):
        """Returns true if the source URL points to a local file"""
        return urlparse.urlparse(self._url).netloc == ''

    def is_remote(self):
        """Returns true if the source URL points to a remote server"""
        return not self.is_local()

    def is_source(self):
        """Returns true if the source is a plain source file"""
        return self.sourcetype == 1

    def is_patch(self):
        """Returns true if the source is a patch"""
        return self.sourcetype == 2

    def url(self):
        """Returns the source's URL"""
        return self._url

    def path(self):
        """Returns the local path where RPM expects to find the source"""
        # RPM only looks at the basename part of the Source URL - the
        # part after the rightmost /.   We must match this behaviour.
        #
        # Examples:
        #    http://www.example.com/foo/bar.tar.gz -> bar.tar.gz
        #    http://www.example.com/foo/bar.cgi#/baz.tbz -> baz.tbz

        with rpm_macros(self.parent.macros,
                        nevra(self.parent.spec.sourceHeader)):
            return os.path.join(rpm.expandMacro("%_sourcedir"),
                                os.path.basename(self._url))


class Spec(object):
    """Represents an RPM spec file"""

    def __init__(self, path, link=None, check_package_name=True, defines=None):

        self.macros = dict(defines) if defines else {}
        self.path = path
        self.link = None
        if link:
            self.link = Link(link)

        # _topdir defaults to $HOME/rpmbuild
        # If present, it needs to be applied once at the beginning
        if '_topdir' in self.macros:
            rpm.addMacro('_topdir', self.macros['_topdir'])

        # '%dist' in the host (where we build the source package)
        # might not match '%dist' in the chroot (where we build
        # the binary package).   We must override it on the host,
        # otherwise the names of packages in the dependencies won't
        # match the files actually produced by mock.
        if 'dist' not in self.macros:
            self.macros['dist'] = ""

        with rpm_macros(self.macros):
            self.path = path
            with open(path) as spec:
                self.spectext = spec.readlines()
            self.spec = parse_spec_quietly(path)

            if check_package_name:
                file_basename = os.path.basename(path).split(".")[0]
                if file_basename != self.name():
                    raise SpecNameMismatch(
                        "spec file name '%s' does not match package name '%s'"
                        % (path, self.name()))

    def specpath(self):
        """Return the path to the spec file"""
        return self.path

    def provides(self):
        """Return a list of package names provided by this spec"""
        provides = sum([pkg.header['provides'] + [pkg.header['name']]
                        for pkg in self.spec.packages], [])

        # RPM 4.6 adds architecture constraints to dependencies.  Drop them.
        provides = [re.sub(r'\(x86-64\)$', '', pkg) for pkg in provides]
        return set(provides)

    def name(self):
        """Return the package name"""
        return self.spec.sourceHeader['name']

    def version(self):
        """Return the package version"""
        return self.spec.sourceHeader['version']

    def expand_macro(self, macro):
        """Return the value of macro, expanded in the package's context"""
        with rpm_macros(self.macros, nevra(self.spec.sourceHeader)):
            return rpm.expandMacro(macro)

    # RPM runtime dependencies.   These are not required to build this
    # package, but will need to be installed when building any other
    # package which BuildRequires this one.
    def requires(self):
        """Return the set of packages needed by this package at runtime
           (Requires)"""
        return set.union(*[set(p.header['REQUIRES'])
                           for p in self.spec.packages])

    # RPM build dependencies.   The 'requires' key for the *source* RPM is
    # actually the 'buildrequires' key from the spec
    def buildrequires(self):
        """Return the set of packages needed to build this spec
           (BuildRequires)"""
        return set(self.spec.sourceHeader['requires'])

    def source_package_path(self):
        """
        Return the path of the source package which building this spec
        will produce
        """
        # There doesn't seem to be a macro for the name of the source rpm
        # but we can construct one using the 'NVR' RPM tag which returns the
        # package's name-version-release string.  Naming is not critically
        # important as these source RPMs are only used internally - mock
        # will write a new source RPM along with the binary RPMS.
        srpmname = self.spec.sourceHeader['nvr'] + ".src.rpm"
        return rpm.expandMacro(os.path.join('%_srcrpmdir', srpmname))

    def sources(self):
        """
        List all sources defined in the spec file
        """
        return [Source(self, source) for source
                in reversed(self.spec.sources)]

    def source(self, target):
        """
        Find the URL from which source should be downloaded
        """
        target_basename = os.path.basename(target)
        for source in self.sources():
            if os.path.basename(source.path()) == target_basename:
                return source

        raise KeyError(target_basename)

    def patches(self):
        """
        List all patches defined in the link file
        """
        if self.link.schema_version == 1:
            return []
        return self.link.patch_sources

    def patchqueues(self):
        """
        List all patchqueues defined in the link file
        """
        if self.link.schema_version == 1:
            return ["patches"]
        return self.link.patchqueue_sources

    def binary_package_paths(self):
        """Return a list of binary packages built by this spec"""

        def rpm_name_from_header(hdr):
            """
            Return the name of the binary package file which
            will be built from hdr
            """
            with rpm_macros(self.macros, nevra(hdr)):
                rpmname = hdr.sprintf(rpm.expandMacro("%{_build_name_fmt}"))
                return rpm.expandMacro(os.path.join('%_rpmdir', rpmname))

        return [rpm_name_from_header(pkg.header) for pkg in self.spec.packages]

    def highest_patch(self):
        """Return the number the highest numbered patch or -1"""
        patches = [num for (_, num, sourcetype) in self.spec.sources
                   if sourcetype == 2]
        patches.append(-1)
        return max(patches)
