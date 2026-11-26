import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import install_data_pack as inst
from game_data_pack import PackError


class DataInstallTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.archive = self.root / "data.zip"
        self.target = self.root / "owner"
        self.exe = b"A" * 4800512
        self.patcher = patch.object(inst, "EXPECTED_EXE_SHA", hashlib.sha256(self.exe).hexdigest())
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        self.files = {
            "SPEED2.EXE": self.exe,
            "server.dll": b"server",
            "CARS/CIVIC/GEOMETRY.BIN": b"civic",
        }
        self.create()

    def create(self):
        entries = []
        with zipfile.ZipFile(self.archive, "w", compression=zipfile.ZIP_DEFLATED) as z:
            for name, data in self.files.items():
                z.writestr("game-data/" + name, data)
                entries.append({"path": name, "bytes": len(data),
                                "sha256": hashlib.sha256(data).hexdigest()})
            z.writestr("game-data-manifest.json", json.dumps({
                "schema": "nfsu2-private-data/v2",
                "upstream_exe_sha256": hashlib.sha256(self.exe).hexdigest(),
                "files": entries}))
 
    def test_install_and_preserve_app_and_saves(self):
        self.target.mkdir()
        (self.target / "app").mkdir()
        (self.target / "saves").mkdir()
        (self.target / "config").mkdir()
        (self.target / "saves" / "career.sav").write_bytes(b"career")
        (self.target / "app" / "VERSION").write_text("0.1.a.9")
        report = inst.install(self.archive, self.target)
        self.assertEqual(report["verified_files"], len(self.files))
        self.assertEqual((self.target/"game-data"/"CARS"/"CIVIC"/"GEOMETRY.BIN").read_bytes(), b"civic")
        self.assertEqual((self.target/"app"/"VERSION").read_text(), "0.1.a.9")
        self.assertEqual((self.target/"saves"/"career.sav").read_bytes(), b"career")
        self.assertTrue((self.target/"game-data-manifest.json").exists())

    def test_reinstallation_refused(self):
        inst.install(self.archive, self.target)
        with self.assertRaisesRegex(PackError, "must not be overwritten"):
            inst.install(self.archive, self.target)

    def test_manifest_tampering_refused_without_writes(self):
        with zipfile.ZipFile(self.archive, "a") as z:
            z.writestr("game-data/extra.exe", b"unmanifested")
        with self.assertRaises(PackError):
            inst.install(self.archive, self.target)
        self.assertFalse((self.target/"game-data").exists())

    def test_duplicate_manifest_refused(self):
        with zipfile.ZipFile(self.archive, "a") as z:
            manifest = z.read("game-data-manifest.json")
            with self.assertWarns(UserWarning):
                z.writestr("game-data-manifest.json", manifest)
        with self.assertRaisesRegex(PackError, "exactly one manifest"):
            inst.verify(self.archive)

    def test_reserved_internal_manifest_refused(self):
        self.files["MANIFEST.JSON"] = b"owner data"
        self.create()
        with self.assertRaisesRegex(PackError, "Reserved manifest path"):
            inst.install(self.archive, self.target)
        self.assertFalse((self.target / "game-data").exists())
        self.assertFalse((self.target / ".game-data-install.lock").exists())

    def test_existing_portable_data_refused(self):
        existing = self.target / "game_data"
        existing.mkdir(parents=True)
        (existing / "sentinel").write_bytes(b"keep")
        with self.assertRaisesRegex(PackError, "must not be overwritten"):
            inst.install(self.archive, self.target)
        self.assertEqual((existing / "sentinel").read_bytes(), b"keep")
        self.assertFalse((self.target / "game-data").exists())

    def test_concurrent_installation_lock_refused(self):
        lock = self.target / ".game-data-install.lock"
        lock.mkdir(parents=True)
        with self.assertRaisesRegex(PackError, "Another data installation"):
            inst.install(self.archive, self.target)
        self.assertTrue(lock.is_dir())
        self.assertFalse((self.target / "game-data").exists())

    def test_incompatible_exe_refused(self):
        with patch.object(inst, "EXPECTED_EXE_SHA", "0"*64):
            with self.assertRaises(PackError):
                inst.verify(self.archive)


if __name__ == "__main__":
    unittest.main()
