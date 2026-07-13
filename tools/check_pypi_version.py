#!/usr/bin/env python3
"""Check a package's actual current version on PyPI before pinning or citing
it as "current" anywhere in this repo.

This exists because CLAUDE.md's dependency-version-claims rule ("don't trust
training-data recall for fast-moving/pre-1.0 dependencies — verify via
WebFetch or `gh api` before asserting a version is current") gets applied by
hand almost every time a dependency version comes up (specs/13-decision-log.md
DEC-131/132/133/136/138 are all real cases this caught). This script is that
same one-line urllib.request call, promoted to a reusable tool instead of
being retyped as an inline `python -c "..."` each time.

Uses only the standard library, same reasoning as tools/call_peer_review_model.py:
runs anywhere Python 3 does, no extra install step before you can use it.

Exit codes:
  0 - looked up successfully; latest version printed to stdout
  1 - the package doesn't exist on PyPI, or the request failed
"""

import argparse
import json
import sys
import urllib.error
import urllib.request

PYPI_URL = "https://pypi.org/pypi/{package}/json"


def latest_version(package: str, timeout: int = 15) -> str:
    url = PYPI_URL.format(package=package)
    with urllib.request.urlopen(url, timeout=timeout) as response:
        data = json.load(response)
    return str(data["info"]["version"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", help="PyPI package name, e.g. ruff")
    args = parser.parse_args()

    try:
        version = latest_version(args.package)
    except urllib.error.HTTPError as e:
        print(f"{args.package}: PyPI lookup failed (HTTP {e.code}) — does this package exist?", file=sys.stderr)
        return 1
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        print(f"{args.package}: PyPI lookup failed: {e}", file=sys.stderr)
        return 1

    print(f"{args.package}=={version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
