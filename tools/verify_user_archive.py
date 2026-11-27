"""Verify a user-supplied data ZIP against a generic integrity manifest.

No game-specific input, executable recognition, extraction or execution.
A matching digest establishes integrity, not authorship or license.
"""
import argparse
import hashlib
import json
import re
import stat
import sys
import zipfile
from pathlib import PurePosixPath

MAX_FILES = 60000
MAX_BYTES = 14 * 1024**3
MANIFEST = "manifest.json"


class ArchiveError(ValueError):
    pass


def safe_path(path):
    if not isinstance(path, str) or not path or len(path) > 1024 or "\\" in path:
        raise ArchiveError("Unsafe path")
    for part in path.split("/"):
        stem = part.split(".", 1)[0].rstrip(" ").upper()
        if (not part or part in (".", "..") or part.endswith((".", " "))
                or any(ord(c) < 32 or c in '<>:"|?*' for c in part)
                or re.fullmatch(r"CON|PRN|AUX|NUL|CONIN\$|CONOUT\$|(?:COM|LPT)[1-9\u00b9\u00b2\u00b3]", stem)):
            raise ArchiveError("Unsafe path component")
    return path


def parse_manifest_json(raw):
    """Reject duplicate object keys before interpreting a manifest."""
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ArchiveError("Duplicate JSON key: " + key)
            result[key] = value
        return result

    try:
        return json.loads(raw, object_pairs_hook=unique)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ArchiveError("Invalid manifest JSON") from exc


def verify(pack):
    with zipfile.ZipFile(pack) as archive:
        infos = archive.infolist()
        if len(infos) > MAX_FILES + 1:
            raise ArchiveError("Too many files")
        members, folded = {}, set()
        for info in infos:
            name = safe_path(info.filename)
            if info.orig_filename != info.filename or info.flag_bits & 1:
                raise ArchiveError("Truncated or encrypted archive member")
            kind = (info.external_attr >> 16) & 0o170000
            if info.is_dir() or kind not in (0, stat.S_IFREG) or name.casefold() in folded:
                raise ArchiveError("Nonregular or duplicate member")
            folded.add(name.casefold())
            members[name] = info
        if MANIFEST not in members or members[MANIFEST].file_size > 16 * 1024**2:
            raise ArchiveError("Missing or oversized manifest")
        manifest = parse_manifest_json(archive.read(MANIFEST))
        if (not isinstance(manifest, dict) or set(manifest) != {"schema", "files"}
                or manifest.get("schema") != "ug2-user-data/v1"):
            raise ArchiveError("Unsupported schema")
        files = manifest.get("files")
        if not isinstance(files, list) or not 1 <= len(files) <= MAX_FILES:
            raise ArchiveError("Invalid files")
        seen, parents, total = set(), {}, 0
        for ent in files:
            if not isinstance(ent, dict) or set(ent) != {"path", "bytes", "sha256"}:
                raise ArchiveError("Invalid entry")
            name = safe_path(ent["path"])
            key = name.casefold()
            if key == MANIFEST or key.startswith(MANIFEST + "/") or key in seen or key in parents:
                raise ArchiveError("Duplicate or reserved path")
            for parent in PurePosixPath(name).parents:
                if str(parent) == ".":
                    continue
                p = str(parent)
                if p.casefold() in seen or parents.setdefault(p.casefold(), p) != p:
                    raise ArchiveError("Conflicting parent")
            seen.add(key)
            length, digest = ent["bytes"], ent["sha256"]
            if type(length) is not int or length < 0 or not isinstance(digest, str) or not re.fullmatch("[0-9a-f]{64}", digest):
                raise ArchiveError("Invalid size or digest")
            total += length
            if total > MAX_BYTES or name not in members or members[name].file_size != length:
                raise ArchiveError("Size or member mismatch")
        if folded != seen | {MANIFEST}:
            raise ArchiveError("Unmanifested member")
        for ent in files:
            h = hashlib.sha256()
            size = 0
            with archive.open(ent["path"]) as stream:
                while True:
                    chunk = stream.read(1024**2)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > ent["bytes"]:
                        raise ArchiveError("Stream exceeds declared size")
                    h.update(chunk)
            if size != ent["bytes"] or h.hexdigest() != ent["sha256"]:
                raise ArchiveError("Digest mismatch")
    return {"verified_files": len(files), "bytes": total}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive")
    args = parser.parse_args(argv)
    try:
        result = verify(args.archive)
    except (OSError, ValueError, RuntimeError, NotImplementedError, zipfile.BadZipFile) as exc:
        print("ERROR:", exc, file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
