#!/usr/bin/env python3
"""Verify/install a private Game Data Pack once; never touch app, saves or config."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import stat
import sys
import uuid
import zipfile

from game_data_pack import PackError, EXPECTED_EXE_SHA

MAX_FILES = 60000
MAX_BYTES = 14 * 1024**3
CHUNK = 1024**2


def _hash(stream):
    h = hashlib.sha256()
    while True:
        b = stream.read(CHUNK)
        if not b:
            return h.hexdigest()
        h.update(b)


def _parts(path):
    if not isinstance(path, str) or not path or path.startswith("/") or "\\" in path:
        raise PackError("Unsafe path")
    parts = path.split("/")
    if any(x in ("", ".", "..") or ":" in x or any(ord(c) < 32 for c in x) for x in parts):
        raise PackError("Unsafe path component")
    return parts


def _validate(z):
    if len(z.infolist()) > MAX_FILES + 1:
        raise PackError("Too many members")
    if sum(i.filename == "game-data-manifest.json" for i in z.infolist()) != 1:
        raise PackError("Expected exactly one manifest")
    info = z.getinfo("game-data-manifest.json")
    if ((info.external_attr >> 16) & 0o170000) not in (0, stat.S_IFREG):
        raise PackError("Manifest must be a regular file")
    if info.file_size > 16 * 1024**2:
        raise PackError("Manifest too large")
    manifest = json.loads(z.read(info))
    if not isinstance(manifest, dict) or manifest.get("schema") != "nfsu2-private-data/v2":
        raise PackError("Unsupported data schema")
    if manifest.get("upstream_exe_sha256") != EXPECTED_EXE_SHA:
        raise PackError("Wrong version in manifest")
    entries = manifest.get("files")
    if not isinstance(entries, list) or not (2 <= len(entries) <= MAX_FILES):
        raise PackError("Invalid files list")
    seen, total = set(), 0
    for ent in entries:
        if not isinstance(ent, dict) or set(ent) != {"path", "bytes", "sha256"}:
            raise PackError("Invalid manifest record")
        rel = ent["path"]
        _parts(rel)
        key = rel.casefold()
        if key == "manifest.json" or key.startswith("manifest.json/"):
            raise PackError("Reserved manifest path")
        if key in seen:
            raise PackError("Case collision")
        seen.add(key)
        if not isinstance(ent["bytes"], int) or isinstance(ent["bytes"], bool) or ent["bytes"] < 0:
            raise PackError("Invalid file length")
        if not isinstance(ent["sha256"], str) or len(ent["sha256"]) != 64 or any(c not in "0123456789abcdef" for c in ent["sha256"]):
            raise PackError("Invalid SHA-256")
        total += ent["bytes"]
        if total > MAX_BYTES:
            raise PackError("Data exceeds safety limit")
    archive_files = {}
    for info in z.infolist():
        if info.filename == "game-data-manifest.json":
            continue
        _parts(info.filename)
        typ = (info.external_attr >> 16) & 0o170000
        if info.is_dir() or typ not in (0, stat.S_IFREG):
            raise PackError("Archive has nonregular member")
        if not info.filename.startswith("game-data/"):
            raise PackError("File outside game-data/")
        rel = info.filename[len("game-data/"):]
        key = rel.casefold()
        if key in archive_files:
            raise PackError("Duplicate archive member")
        archive_files[key] = info
    if set(archive_files) != seen:
        raise PackError("Archive and manifest differ")
    for ent in entries:
        if archive_files[ent["path"].casefold()].file_size != ent["bytes"]:
            raise PackError("File length mismatch")
    exe = next((x for x in entries if x["path"].casefold() == "speed2.exe"), None)
    if not exe or exe["bytes"] != 4800512 or exe["sha256"] != EXPECTED_EXE_SHA:
        raise PackError("Incompatible SPEED2.EXE")
    if "server.dll" not in seen:
        raise PackError("Missing server.dll")
    return manifest, archive_files


def verify(pack):
    with zipfile.ZipFile(pack) as z:
        manifest, items = _validate(z)
        for ent in manifest["files"]:
            with z.open(items[ent["path"].casefold()]) as source:
                if _hash(source) != ent["sha256"]:
                    raise PackError("Wrong SHA256: " + ent["path"])
    return {"status": "PASS", "verified_files": len(manifest["files"])}


def install(pack, dest):
    dest = Path(dest).resolve()
    dest.mkdir(parents=True, exist_ok=True)
    lock = dest / ".game-data-install.lock"
    try:
        lock.mkdir(mode=0o700)
    except FileExistsError as exc:
        raise PackError("Another data installation is active or needs recovery") from exc
    try:
        return _install_locked(pack, dest)
    finally:
        lock.rmdir()


def _install_locked(pack, dest):
    game = dest / "game-data"
    receipt = dest / "game-data-manifest.json"
    alternate = dest / "game_data"
    if (game.exists() or game.is_symlink() or alternate.exists() or alternate.is_symlink()
            or receipt.exists() or receipt.is_symlink()):
        raise PackError("Existing Game Data Pack must not be overwritten")
    result = verify(pack)
    dest.mkdir(parents=True, exist_ok=True)
    stage = dest / (".game-data-stage-" + uuid.uuid4().hex)
    stage.mkdir(mode=0o700)
    committed = False
    try:
        with zipfile.ZipFile(pack) as z:
            manifest, items = _validate(z)
            for ent in manifest["files"]:
                rel = ent["path"]
                out = stage.joinpath(*_parts(rel))
                out.parent.mkdir(parents=True, exist_ok=True)
                with z.open(items[rel.casefold()]) as source, out.open("xb") as sink:
                    h = hashlib.sha256()
                    while True:
                        b = source.read(CHUNK)
                        if not b:
                            break
                        sink.write(b); h.update(b)
                    if h.hexdigest() != ent["sha256"]:
                        raise PackError("Data changed while copying")
            # Manifest is written inside stage and copied after atomically naming game-data.
            (stage / "manifest.json").write_text(json.dumps(manifest, sort_keys=True) + "\n")
        if (game.exists() or game.is_symlink() or alternate.exists() or alternate.is_symlink()
                or receipt.exists() or receipt.is_symlink()):
            raise PackError("Game data appeared during installation")
        stage.rename(game)
        committed = True
        with receipt.open("x", encoding="utf-8") as sink:
            sink.write(json.dumps({"schema": manifest["schema"],
                "source_exe_sha256": EXPECTED_EXE_SHA, "files": len(manifest["files"])}, sort_keys=True) + "\n")
    finally:
        if not committed and stage.exists():
            shutil.rmtree(stage)
    return {"installed": str(game), **result}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("action", choices=("verify", "install"))
    p.add_argument("pack", type=Path)
    p.add_argument("--target", type=Path)
    a = p.parse_args()
    try:
        if a.action == "install":
            if a.target is None:
                p.error("--target required")
            out = install(a.pack, a.target)
        else:
            out = verify(a.pack)
        print(json.dumps(out, ensure_ascii=False, indent=2))
    except (OSError, ValueError, KeyError, json.JSONDecodeError, zipfile.BadZipFile, PackError) as e:
        print("ERROR:", e, file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
