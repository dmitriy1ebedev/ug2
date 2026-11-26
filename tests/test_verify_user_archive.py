import hashlib
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from verify_user_archive import ArchiveError, verify


class ArchiveTests(unittest.TestCase):
    def check(self, entries, payloads, extra=None):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "fixture.zip"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("manifest.json", json.dumps({"schema": "ug2-user-data/v1", "files": entries}))
                for name, data in payloads:
                    archive.writestr(name, data)
                if extra:
                    archive.writestr(*extra)
            return verify(path)

    def entry(self, name, data=b"test"):
        return {"path": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}

    def test_generic_fixture(self):
        self.assertEqual(self.check([self.entry("data/a.txt")], [("data/a.txt", b"test")]), {"verified_files": 1, "bytes": 4})

    def test_wrong_digest(self):
        with self.assertRaises(ArchiveError):
            self.check([self.entry("a.txt")], [("a.txt", b"fail")])

    def test_extra_member(self):
        with self.assertRaises(ArchiveError):
            self.check([self.entry("a.txt")], [("a.txt", b"test")], ("extra.txt", b"x"))

    def test_unsafe_paths(self):
        for name in ("../a", "/a", "CON.txt", "a/../b", "a. /b", "a\\b"):
            with self.subTest(name=name), self.assertRaises(ArchiveError):
                self.check([self.entry(name)], [(name, b"test")])

    def test_conflicting_parent(self):
        for names in (("a", "a/b"), ("a/b", "a"), ("Dir/a", "dir/b")):
            with self.subTest(names=names), self.assertRaises(ArchiveError):
                self.check([self.entry(n) for n in names], [(n, b"test") for n in names])

    def test_manifest_parent_refused(self):
        name = "MANIFEST.JSON/nested.txt"
        with self.assertRaises(ArchiveError):
            self.check([self.entry(name)], [(name, b"test")])

    def test_case_collision(self):
        with self.assertRaises(ArchiveError):
            self.check([self.entry("A"), self.entry("a")], [("A", b"test"), ("a", b"test")])
