"""Strict path allowlist for the reviewed independent public snapshot."""
import subprocess

ALLOWED = {
    "README.md",
    "LICENSE",
    ".gitverse/workflows/ci.yml",
    "docs/UPSTREAM-LICENSE.txt",
    "docs/PUBLIC-SCOPE.md",
    "tools/verify_user_archive.py",
    "tools/public_source_gate.py",
    "tests/test_verify_user_archive.py",
    ".github/workflows/ci.yml",
}


def main():
    paths = subprocess.check_output(["git", "ls-files", "-z"]).decode("utf-8").split("\0")
    actual = set(filter(None, paths))
    if actual != ALLOWED:
        raise SystemExit(f"Unexpected public paths: {sorted(actual - ALLOWED)}; missing: {sorted(ALLOWED - actual)}")
    print("PASS: reviewed public path allowlist (not a legal or history audit)")


if __name__ == "__main__":
    main()
