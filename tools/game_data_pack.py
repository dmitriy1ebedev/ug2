#!/usr/bin/env python3
"""Safe private NFSU2 game data audit and pack builder. Never executes Windows binaries."""
import argparse
from collections import defaultdict
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import zipfile

EXPECTED_EXE_SIZE = 4800512
EXPECTED_EXE_SHA = "f9dd86c054878ce6276beb07c1fd61874f7a1e4bf1f241b084c65b73e24168a7"
ALLOW_ROOT = {"speed2.exe", "server.dll", "server.cfg"}
ALLOW_DIRS = {"cars", "credits", "frontend", "global", "languages", "memcard",
              "movies", "nis", "pfdata", "sound", "speech", "subtitles",
              "tracks", "langpacks", "texpacks"}
ESSENTIAL = {"cars", "frontend", "global", "tracks"}
CHUNK = 1024 * 1024


class PackError(ValueError):
    pass


def sha(stream):
    h = hashlib.sha256()
    for chunk in iter(lambda: stream.read(CHUNK), b""):
        h.update(chunk)
    return h.hexdigest()


def members(source, skip_movies=False):
    """Return inspected selected ZIP entries; no extraction or file writes."""
    with zipfile.ZipFile(source) as z:
        infos = z.infolist()
        if len(infos) > 60000:
            raise PackError("Too many ZIP members")
        parsed, keys, exe_roots = [], set(), []
        total = 0
        for info in infos:
            name = info.filename
            if not name or name.startswith("/") or "\\" in name or "\x00" in name:
                raise PackError("Unsafe ZIP path")
            parts = name.rstrip("/").split("/")
            if any(x in ("", ".", "..") or ":" in x or any(ord(c) < 32 for c in x) for x in parts):
                raise PackError("Unsafe ZIP component")
            ty = info.external_attr >> 16 & 0o170000
            if ty not in (0, stat.S_IFREG, stat.S_IFDIR):
                raise PackError("Unsupported ZIP entry type (symlink/device)")
            normalized = "/".join(x.casefold() for x in parts)
            if normalized in keys:
                raise PackError("Duplicate case-insensitive ZIP member")
            keys.add(normalized)
            if not info.is_dir():
                total += info.file_size
                if info.file_size > 4 * 1024**3 or total > 14 * 1024**3:
                    raise PackError("Oversized ZIP")
                if info.file_size > CHUNK and info.compress_size and info.file_size / info.compress_size > 5000:
                    raise PackError("Suspicious compression ratio")
            if not info.is_dir() and parts[-1].casefold() == "speed2.exe":
                exe_roots.append(parts[:-1])
            parsed.append((info, parts))
        if len(exe_roots) != 1:
            raise PackError("Expected exactly one SPEED2.EXE, got " + str(len(exe_roots)))
        root = exe_roots[0]
        chosen, removed, summary = [], [], defaultdict(lambda: [0, 0])
        for info, parts in parsed:
            if info.is_dir():
                continue
            if [x.casefold() for x in parts[:len(root)]] != [x.casefold() for x in root]:
                removed.append((info, "outside-install"))
                continue
            rel = parts[len(root):]
            if not rel:
                continue
            head = rel[0].casefold()
            keep = (len(rel) == 1 and head in ALLOW_ROOT) or (len(rel) > 1 and head in ALLOW_DIRS)
            if skip_movies and head == "movies":
                keep = False
            if any(x.startswith(".") or x.casefold() in ("thumbs.db", "desktop.ini", "__macosx") for x in rel):
                keep = False
            if keep:
                normalized = "/".join(rel)
                chosen.append((info, normalized))
                summary[head][0] += 1
                summary[head][1] += info.file_size
            else:
                removed.append((info, head))
        found_root = {rel.casefold() for _, rel in chosen if "/" not in rel}
        if not {"speed2.exe", "server.dll"} <= found_root:
            raise PackError("Required SPEED2.EXE or server.dll missing in root")
        found_dirs = {x.split("/", 1)[0].casefold() for _, x in chosen if "/" in x}
        missing = sorted(ESSENTIAL - found_dirs)
        exe_info = next(i for i, rel in chosen if rel.casefold() == "speed2.exe")
        with z.open(exe_info) as f:
            exe_sha = sha(f)
        removed_by_kind = defaultdict(lambda: [0, 0])
        for info, reason in removed:
            removed_by_kind[reason][0] += 1
            removed_by_kind[reason][1] += info.file_size
        report = {
            "schema": "nfsu2-owner-source-audit/v1",
            "source_members": len(infos),
            "source_uncompressed_bytes": total,
            "root": "/".join(root),
            "exe_bytes": exe_info.file_size,
            "exe_sha256": exe_sha,
            "exe_matches_upstream": exe_info.file_size == EXPECTED_EXE_SIZE and exe_sha == EXPECTED_EXE_SHA,
            "missing_essential_dirs": missing,
            "kept_files": len(chosen),
            "kept_bytes": sum(i.file_size for i, _ in chosen),
            "excluded_files": len(removed),
            "excluded_bytes": sum(i.file_size for i, _ in removed),
            "kept_by_category": dict(sorted(summary.items())),
            "excluded_by_category": dict(sorted(removed_by_kind.items())),
            "movies_included": not skip_movies,
        }
        return report, chosen


def package(source, output, skip_movies=False):
    report, selected = members(source, skip_movies)
    if not report["exe_matches_upstream"]:
        raise PackError("Incompatible SPEED2.EXE (upstream needs NA v1.2; refusing private pack)")
    if report["missing_essential_dirs"]:
        raise PackError("Missing essential game folders: " + ",".join(report["missing_essential_dirs"]))
    output = Path(output)
    if output.exists():
        raise PackError("Refusing to overwrite existing pack")
    output.parent.mkdir(parents=True, exist_ok=True)
    temp = output.with_name(output.name + ".partial")
    if temp.exists():
        raise PackError("Refusing to overwrite partial build")
    manifest = []
    try:
        with zipfile.ZipFile(source) as inp, zipfile.ZipFile(temp, "w", allowZip64=True) as out:
            for info, rel in sorted(selected, key=lambda x: x[1].casefold()):
                dest = rel
                if rel.casefold() == "speed2.exe":
                    dest = "SPEED2.EXE"
                zi = zipfile.ZipInfo("game-data/" + dest, (2020, 1, 1, 0, 0, 0))
                zi.compress_type = zipfile.ZIP_DEFLATED
                zi.external_attr = 0o100644 << 16
                h = hashlib.sha256()
                with inp.open(info) as src, out.open(zi, "w", force_zip64=True) as dst:
                    for b in iter(lambda: src.read(CHUNK), b""):
                        dst.write(b)
                        h.update(b)
                manifest.append({"path": dest, "size": info.file_size, "sha256": h.hexdigest()})
            zi = zipfile.ZipInfo("game-data-manifest.json", (2020, 1, 1, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o100644 << 16
            out.writestr(zi, json.dumps({
                "schema": "nfsu2-private-data/v1",
                "upstream_exe_sha256": EXPECTED_EXE_SHA,
                "files": manifest,
                "bytes": sum(v["size"] for v in manifest)
            }, sort_keys=True, separators=(",", ":")) + "\n")
        os.replace(temp, output)
    except BaseException:
        try:
            temp.unlink()
        except FileNotFoundError:
            pass
        raise
    with output.open("rb") as f:
        return {"pack": str(output), "size": output.stat().st_size, "sha256": sha(f)}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=["inspect", "build"])
    p.add_argument("source", type=Path)
    p.add_argument("--output", type=Path)
    p.add_argument("--skip-movies", action="store_true", help="Opt-in: remove movies (changes presentation)")
    a = p.parse_args(argv)
    try:
        if a.action == "inspect":
            report, _ = members(a.source, a.skip_movies)
        else:
            if not a.output:
                p.error("--output is required for build")
            report = package(a.source, a.output, a.skip_movies)
        print(json.dumps(report, sort_keys=True, indent=2))
        return 0
    except (PackError, OSError, zipfile.BadZipFile) as e:
        print("ERROR:", e, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
