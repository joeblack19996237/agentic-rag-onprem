"""Documentation-drift checks.

Two failure classes this project has already hit by hand once each:
(1) a `DEC-###` cited somewhere that doesn't resolve to a real row in
    `specs/13-decision-log.md` (typo, or a row renumbered/never landed), and
(2) `README.md`'s issue-status markers (✅/⏳) going stale relative to the
    `.scratch/*/issues/*.md` file's own `Status:` line (exactly what happened
    to Issue 03 before it was hand-fixed).

Scope: `specs/`, `docs/`, `.scratch/`, `CLAUDE.md`, `README.md`. Deliberately
excludes `.claude/skills/` — that directory holds generic, reusable skill
prose that may cite illustrative `DEC-###` ids as worked examples, not real
decisions from this project's own log.
"""

import re
from pathlib import Path

DEC_ID_RE = re.compile(r"\bDEC-\d+\b")
DEC_ROW_RE = re.compile(r"^\|\s*(DEC-\d+)\s*\|")
ISSUE_STATUS_RE = re.compile(r"^Status:\s*(\S+)")
ISSUE_FILENAME_RE = re.compile(r"^(\d+)-")
README_ISSUE_LINE_RE = re.compile(r"^-\s*(✅|⏳)?\s*Issue (\d+)\b")

DONE_STATUSES = {"ready-for-human"}
DOC_DIRS = ("specs", "docs", ".scratch")
DOC_ROOT_FILES = ("CLAUDE.md", "README.md")


def _doc_files(repo_root: Path) -> list[Path]:
    files: list[Path] = []
    for dirname in DOC_DIRS:
        directory = repo_root / dirname
        if directory.is_dir():
            files.extend(sorted(directory.rglob("*.md")))
    for name in DOC_ROOT_FILES:
        f = repo_root / name
        if f.is_file():
            files.append(f)
    return files


def _canonical_dec_ids(repo_root: Path) -> set[str]:
    log = repo_root / "specs" / "13-decision-log.md"
    if not log.is_file():
        return set()
    ids = set()
    for line in log.read_text(encoding="utf-8").splitlines():
        match = DEC_ROW_RE.match(line)
        if match:
            ids.add(match.group(1))
    return ids


def find_duplicate_dec_ids(repo_root: Path) -> list[str]:
    """Return one message per DEC-### id defined more than once in the log."""
    log = repo_root / "specs" / "13-decision-log.md"
    if not log.is_file():
        return []
    seen: dict[str, int] = {}
    violations = []
    for lineno, line in enumerate(log.read_text(encoding="utf-8").splitlines(), start=1):
        match = DEC_ROW_RE.match(line)
        if not match:
            continue
        dec_id = match.group(1)
        if dec_id in seen:
            violations.append(
                f"{log.relative_to(repo_root)}:{lineno}: `{dec_id}` already defined "
                f"at line {seen[dec_id]} — decision IDs must be unique and never reused"
            )
        else:
            seen[dec_id] = lineno
    return violations


def find_dangling_dec_references(repo_root: Path) -> list[str]:
    """Return one message per DEC-### cited somewhere with no matching row."""
    canonical = _canonical_dec_ids(repo_root)
    if not canonical:
        return []
    violations = []
    for doc in _doc_files(repo_root):
        for lineno, line in enumerate(doc.read_text(encoding="utf-8").splitlines(), start=1):
            for match in DEC_ID_RE.finditer(line):
                dec_id = match.group(0)
                if dec_id not in canonical:
                    violations.append(
                        f"{doc.relative_to(repo_root)}:{lineno}: references `{dec_id}`, "
                        f"which has no row in specs/13-decision-log.md"
                    )
    return violations


def find_issue_status_mismatches(repo_root: Path) -> list[str]:
    """Return one message per README.md issue marker that disagrees with the
    referenced .scratch/*/issues/*.md file's own Status: line."""
    scratch = repo_root / ".scratch"
    readme = repo_root / "README.md"
    if not scratch.is_dir() or not readme.is_file():
        return []

    statuses: dict[str, str] = {}
    for issue_file in scratch.rglob("issues/*.md"):
        match = ISSUE_FILENAME_RE.match(issue_file.name)
        if not match:
            continue
        number = str(int(match.group(1)))
        first_line = issue_file.read_text(encoding="utf-8").splitlines()[0]
        status_match = ISSUE_STATUS_RE.match(first_line)
        if status_match:
            statuses[number] = status_match.group(1)

    violations = []
    for lineno, line in enumerate(readme.read_text(encoding="utf-8").splitlines(), start=1):
        match = README_ISSUE_LINE_RE.match(line)
        if not match:
            continue
        marker, number = match.group(1), str(int(match.group(2)))
        status = statuses.get(number)
        if status is None:
            continue
        is_done = status in DONE_STATUSES
        if is_done and marker != "✅":
            violations.append(
                f"README.md:{lineno}: Issue {number} shows {marker or 'no marker'} but its "
                f"issue file's Status is `{status}` (done) — README is stale"
            )
        elif not is_done and marker == "✅":
            violations.append(
                f"README.md:{lineno}: Issue {number} shows ✅ but its issue file's Status "
                f"is `{status}` (not done) — README overclaims"
            )
    return violations
