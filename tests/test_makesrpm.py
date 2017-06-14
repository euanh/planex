"""Test SRPM construction"""

import os
import shutil
import tarfile
import tempfile
import unittest

from hypothesis import given, settings, strategies as st
from nose.plugins.attrib import attr
import tests.template_spec

import planex.cmd.makesrpm as mksrpm
import planex.link
import planex.spec

FILENAME_ALPHABET = "abcdefghijklmnopqrstuvwxyz"
FILENAMES = st.text(alphabet=FILENAME_ALPHABET, min_size=1, max_size=5)
SOURCES = FILENAMES.map(lambda x: x + ".tar.gz")
PATCHES = FILENAMES.map(lambda x: x + ".patch")


class SrpmPackingTests(unittest.TestCase):
    """Test packing of sources into SRPMs"""

    def setUp(self):
        # Create a tmpdir for test runs.   Each testcase will create
        # its own directory within this one and can try to clean up but
        # it doesn't or can't the teardown fixture will delete everything.
        self.workspace = tempfile.mkdtemp(prefix="test_makesrpm")

    def tearDown(self):
        shutil.rmtree(self.workspace)

    @attr("wip")
    @given(sources=st.lists(elements=SOURCES, unique_by=hash,
                            min_size=1, max_size=5),
           patches=st.lists(elements=PATCHES, unique_by=hash, max_size=5))
    @settings(max_examples=25)
    def test_sources_are_packed(self, sources, patches):
        """All spec file sources and patches are packed into the SRPM"""

        inputs = tempfile.mkdtemp(dir=self.workspace)
        outputs = tempfile.mkdtemp(dir=self.workspace)

        spec = tests.template_spec.render({"sources": sources,
                                           "patches": patches})

        specpath = os.path.join(inputs, "dummy.spec")
        with open(specpath, "w") as specfile:
            specfile.writelines(spec)

        sourcepaths = [os.path.join(inputs, source) for source in sources]
        for source in sourcepaths:
            with tarfile.open(name=source, mode="w"):
                pass

        patchpaths = [os.path.join(inputs, patch) for patch in patches]
        for patch in patchpaths:
            with open(patch, "w") as patch:
                patch.writelines(FILENAME_ALPHABET)

        newspec = mksrpm.populate_working_directory(outputs, specpath, None,
                                                    sourcepaths + patchpaths,
                                                    None)
        parsed = planex.spec.Spec(newspec)

        self.assertItemsEqual(sources + patches, parsed.source_urls())
        self.assertItemsEqual(patches, parsed.patch_urls())

        self.assertEqual(mksrpm.rpmbuild(outputs, newspec, quiet=True,
                                         defines=["_topdir %s" % outputs]), 0)
