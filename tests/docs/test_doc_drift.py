from pathlib import Path

from doc_drift import (
    find_dangling_dec_references,
    find_duplicate_dec_ids,
    find_issue_status_mismatches,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_current_repo_has_no_dangling_dec_references():
    assert find_dangling_dec_references(REPO_ROOT) == []


def test_current_repo_has_no_duplicate_dec_ids():
    assert find_duplicate_dec_ids(REPO_ROOT) == []


def test_current_repo_has_no_issue_status_mismatches():
    assert find_issue_status_mismatches(REPO_ROOT) == []


def test_detects_a_dangling_dec_reference(tmp_path):
    specs = tmp_path / "specs"
    specs.mkdir()
    (specs / "13-decision-log.md").write_text(
        "| ID | Date |\n|---|---|\n| DEC-001 | 2026-01-01 |\n", encoding="utf-8"
    )
    (specs / "04-architecture.md").write_text(
        "See DEC-999 for rationale.\n", encoding="utf-8"
    )

    violations = find_dangling_dec_references(tmp_path)

    assert len(violations) == 1
    assert "DEC-999" in violations[0]


def test_ignores_dec_ids_that_do_resolve(tmp_path):
    specs = tmp_path / "specs"
    specs.mkdir()
    (specs / "13-decision-log.md").write_text(
        "| ID | Date |\n|---|---|\n| DEC-001 | 2026-01-01 |\n", encoding="utf-8"
    )
    (specs / "04-architecture.md").write_text(
        "See DEC-001 for rationale.\n", encoding="utf-8"
    )

    assert find_dangling_dec_references(tmp_path) == []


def test_detects_duplicate_dec_ids(tmp_path):
    specs = tmp_path / "specs"
    specs.mkdir()
    (specs / "13-decision-log.md").write_text(
        "| ID | Date |\n|---|---|\n| DEC-001 | 2026-01-01 |\n| DEC-001 | 2026-01-02 |\n",
        encoding="utf-8",
    )

    violations = find_duplicate_dec_ids(tmp_path)

    assert len(violations) == 1
    assert "DEC-001" in violations[0]


def test_detects_a_closed_issue_still_shown_pending_in_readme(tmp_path):
    (tmp_path / "README.md").write_text(
        "- ⏳ Issue 03 — some task (next up)\n", encoding="utf-8"
    )
    issues_dir = tmp_path / ".scratch" / "feature" / "issues"
    issues_dir.mkdir(parents=True)
    (issues_dir / "03-some-task.md").write_text(
        "Status: ready-for-human\n", encoding="utf-8"
    )

    violations = find_issue_status_mismatches(tmp_path)

    assert len(violations) == 1
    assert "Issue 3" in violations[0]


def test_detects_a_premature_done_claim_in_readme(tmp_path):
    (tmp_path / "README.md").write_text(
        "- ✅ Issue 05 — some task\n", encoding="utf-8"
    )
    issues_dir = tmp_path / ".scratch" / "feature" / "issues"
    issues_dir.mkdir(parents=True)
    (issues_dir / "05-some-task.md").write_text(
        "Status: needs-triage\n", encoding="utf-8"
    )

    violations = find_issue_status_mismatches(tmp_path)

    assert len(violations) == 1
    assert "Issue 5" in violations[0]


def test_no_mismatch_when_readme_and_status_agree(tmp_path):
    (tmp_path / "README.md").write_text(
        "- ✅ Issue 03 — some task\n", encoding="utf-8"
    )
    issues_dir = tmp_path / ".scratch" / "feature" / "issues"
    issues_dir.mkdir(parents=True)
    (issues_dir / "03-some-task.md").write_text(
        "Status: ready-for-human\n", encoding="utf-8"
    )

    assert find_issue_status_mismatches(tmp_path) == []
