#!/usr/bin/env python3
"""Check a package's actual current version on PyPI before pinning or citing
it as "current" anywhere in this repo, or inspect its declared dependency
footprint (`requires_dist`) before pinning a new one.

This exists because CLAUDE.md's dependency-version-claims rule ("don't trust
training-data recall for fast-moving/pre-1.0 dependencies — verify via
WebFetch or `gh api` before asserting a version is current") gets applied by
hand almost every time a dependency version comes up (specs/13-decision-log.md
DEC-131/132/133/136/138 are all real cases this caught). This script is that
same one-line urllib.request call, promoted to a reusable tool instead of
being retyped as an inline `python -c "..."` each time.

The `--requires`/`--version` options exist for the same reason, one level
deeper: DEC-143 (2026-07-15) needed a *specific pinned version's* declared
dependencies (does `unstructured==0.18.32`'s PDF module actually pull in
torch?) via three separate hand-rolled `curl | python -c "..."` calls in one
session — the exact "retyped more than once" signal tools/README.md says to
promote on, just for `requires_dist` instead of `info.version`.

Uses only the standard library, per tools/README.md's "how to write a good
script for this repo" convention: runs anywhere Python 3 does, no extra
install step before you can use it.

Exit codes:
  0 - looked up successfully; result printed to stdout
  1 - the package (or package==version) doesn't exist on PyPI, or the request failed
"""

import argparse
import json
import sys
import urllib.error
import urllib.request

PYPI_URL = "https://pypi.org/pypi/{package}/json"
PYPI_VERSION_URL = "https://pypi.org/pypi/{package}/{version}/json"


def fetch_metadata(package: str, version: str | None, timeout: int = 15) -> dict[str, object]:
    url = (
        PYPI_VERSION_URL.format(package=package, version=version)
        if version
        else PYPI_URL.format(package=package)
    )
    with urllib.request.urlopen(url, timeout=timeout) as response:
        data: dict[str, object] = json.load(response)
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", help="PyPI package name, e.g. ruff")
    parser.add_argument(
        "--version", help="Look up a specific pinned version instead of the latest (e.g. 0.18.32)"
    )
    parser.add_argument(
        "--requires",
        action="store_true",
        help="Print the package's declared dependencies (requires_dist) instead of its version",
    )
    args = parser.parse_args()

    try:
        data = fetch_metadata(args.package, args.version)
    except urllib.error.HTTPError as e:
        target = f"{args.package}=={args.version}" if args.version else args.package
        print(f"{target}: PyPI lookup failed (HTTP {e.code}) — does this package/version exist?", file=sys.stderr)
        return 1
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        print(f"{args.package}: PyPI lookup failed: {e}", file=sys.stderr)
        return 1

    info = data["info"]
    assert isinstance(info, dict)

    if args.requires:
        for requirement in info.get("requires_dist") or []:
            print(requirement)
    else:
        print(f"{args.package}=={info['version']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
