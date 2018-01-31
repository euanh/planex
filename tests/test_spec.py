"""Tests for Spec class"""

import unittest
import platform
import planex.spec


def get_rpm_machine():
    """Return the RPM architecture name for the local machine"""
    if platform.machine() == 'x86_64':
        return 'x86_64'
    return 'i386'


class RpmTests(unittest.TestCase):
    """Basic Spec class tests"""

    def setUp(self):
        rpm_defines = [("dist", ".el6"),
                       ("_topdir", "."),
                       ("_sourcedir", "%_topdir/SOURCES/%name")]
        self.spec = planex.spec.Spec("tests/data/ocaml-cohttp.spec",
                                     defines=rpm_defines)

    def test_bad_filename(self):
        """Exception is raised if filenname does not match package name"""
        self.assertRaises(planex.spec.SpecNameMismatch, planex.spec.Spec,
                          "tests/data/bad-name.spec")

    def test_name(self):
        """Package name is correct"""
        self.assertEqual(self.spec.name(), "ocaml-cohttp")

    def test_specpath(self):
        """Path to spec file on disk is correct"""
        self.assertEqual(self.spec.specpath(), "tests/data/ocaml-cohttp.spec")

    def test_version(self):
        """Package version is correct"""
        self.assertEqual(self.spec.version(), "0.9.8")

    def test_provides(self):
        """Package provides are correct"""
        self.assertItemsEqual(
            self.spec.provides(),
            ["ocaml-cohttp", "ocaml-cohttp-devel"])

    def test_sources(self):
        """Package source paths and URLs are correct"""
        self.assertItemsEqual(
            [(source.path(), source.url()) for source in self.spec.sources()],
            [("./SOURCES/ocaml-cohttp/ocaml-cohttp-0.9.8.tar.gz",
              "https://github.com/mirage/ocaml-cohttp/archive/"
              "ocaml-cohttp-0.9.8/ocaml-cohttp-0.9.8.tar.gz"),
             ("./SOURCES/ocaml-cohttp/ocaml-cohttp-init",
              "ocaml-cohttp-init"),
             ("./SOURCES/ocaml-cohttp/ocaml-cohttp-service",
              "ocaml-cohttp-service"),
             ("./SOURCES/ocaml-cohttp/cohttp0.patch", "cohttp0.patch"),
             ("./SOURCES/ocaml-cohttp/cohttp1.patch", "cohttp1.patch")])

    def test_source(self):
        """URLs for individual sources are correct"""
        self.assertEqual(
            (self.spec.source("path/to/ocaml-cohttp-0.9.8.tar.gz").path(),
             self.spec.source("path/to/ocaml-cohttp-0.9.8.tar.gz").url()),
            ("./SOURCES/ocaml-cohttp/ocaml-cohttp-0.9.8.tar.gz",
             "https://github.com/mirage/ocaml-cohttp/archive/"
             "ocaml-cohttp-0.9.8/ocaml-cohttp-0.9.8.tar.gz"))
        self.assertEqual(
            (self.spec.source("ocaml-cohttp-init").path(),
             self.spec.source("ocaml-cohttp-init").url()),
            ("./SOURCES/ocaml-cohttp/ocaml-cohttp-init", "ocaml-cohttp-init"))
        self.assertEqual(
            (self.spec.source("somewhere/cohttp0.patch").path(),
             self.spec.source("somewhere/cohttp0.patch").url()),
            ("./SOURCES/ocaml-cohttp/cohttp0.patch", "cohttp0.patch"))

    def test_source_nonexistent(self):
        """Nonexistent sources are handled correctly"""
        with self.assertRaises(KeyError):
            self.spec.source("nonexistent")

    def test_requires(self):
        """Package runtime requirements are correct"""
        self.assertEqual(
            self.spec.requires(),
            set(["ocaml", "ocaml-findlib"]))

    def test_buildrequires(self):
        """Package build-time requirements are correct"""
        self.assertEqual(
            self.spec.buildrequires(),
            set(["ocaml", "ocaml-findlib", "ocaml-re-devel",
                 "ocaml-uri-devel", "ocaml-cstruct-devel",
                 "ocaml-lwt-devel", "ocaml-ounit-devel",
                 "ocaml-ocamldoc", "ocaml-camlp4-devel",
                 "openssl", "openssl-devel"]))

    def test_source_package_path(self):
        """Path to resulting source RPM is correct"""
        self.assertEqual(
            self.spec.source_package_path(),
            "./SRPMS/ocaml-cohttp-0.9.8-1.el6.src.rpm")

    def test_binary_package_paths(self):
        """Paths to resulting binary RPMs are correct"""
        machine = get_rpm_machine()

        self.assertItemsEqual(
            self.spec.binary_package_paths(),
            [path.format(machine=machine) for path in
             ["./RPMS/{machine}/ocaml-cohttp-0.9.8-1.el6.{machine}.rpm",
              "./RPMS/{machine}/" +
              "ocaml-cohttp-devel-0.9.8-1.el6.{machine}.rpm"]]
        )
