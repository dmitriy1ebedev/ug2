import contextlib
import hashlib
import io
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from verify_user_archive import ArchiveError, main, parse_manifest_json, verify


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
        for name in ("../a", "/a", "CON.txt", "CON .txt", "a/../b", "a. /b", "a\\b"):
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

    def test_duplicate_json_keys(self):
        for raw in (b'{"schema":"ug2-user-data/v1","schema":"other","files":[]}',
                    b'{"files":[{"path":"a","path":"b"}]}'):
            with self.subTest(raw=raw), self.assertRaisesRegex(ArchiveError, "Duplicate JSON key"):
                parse_manifest_json(raw)

    def test_invalid_json(self):
        with self.assertRaisesRegex(ArchiveError, "Invalid manifest JSON"):
            parse_manifest_json(b'{broken')

    def test_unknown_manifest_field(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "fixture.zip"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("manifest.json", json.dumps({
                    "schema": "ug2-user-data/v1", "files": [self.entry("a")], "unknown": True}))
                archive.writestr("a", b"test")
            with self.assertRaisesRegex(ArchiveError, "Unsupported schema"):
                verify(path)

    def test_cli_exit_codes(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "fixture.zip"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("manifest.json", json.dumps({
                    "schema": "ug2-user-data/v1", "files": [self.entry("a")]}))
                archive.writestr("a", b"test")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(main([str(path)]), 0)
            self.assertEqual(json.loads(out.getvalue()), {"verified_files": 1, "bytes": 4})
            path.write_bytes(b"not a zip")
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main([str(path)]), 2)
