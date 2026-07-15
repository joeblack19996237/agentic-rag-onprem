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
        "- ⏳ feature Issue 03 — some task (next up)\n", encoding="utf-8"
    )
    issues_dir = tmp_path / ".scratch" / "feature" / "issues"
    issues_dir.mkdir(parents=True)
    (issues_dir / "03-some-task.md").write_text(
        "Status: ready-for-human\n", encoding="utf-8"
    )

    violations = find_issue_status_mismatches(tmp_path)

    assert len(violations) == 1
    assert "feature Issue 3" in violations[0]


def test_detects_a_premature_done_claim_in_readme(tmp_path):
    (tmp_path / "README.md").write_text(
        "- ✅ feature Issue 05 — some task\n", encoding="utf-8"
    )
    issues_dir = tmp_path / ".scratch" / "feature" / "issues"
    issues_dir.mkdir(parents=True)
    (issues_dir / "05-some-task.md").write_text(
        "Status: needs-triage\n", encoding="utf-8"
    )

    violations = find_issue_status_mismatches(tmp_path)

    assert len(violations) == 1
    assert "feature Issue 5" in violations[0]


def test_no_mismatch_when_readme_and_status_agree(tmp_path):
    (tmp_path / "README.md").write_text(
        "- ✅ feature Issue 03 — some task\n", encoding="utf-8"
    )
    issues_dir = tmp_path / ".scratch" / "feature" / "issues"
    issues_dir.mkdir(parents=True)
    (issues_dir / "03-some-task.md").write_text(
        "Status: ready-for-human\n", encoding="utf-8"
    )

    assert find_issue_status_mismatches(tmp_path) == []


def test_distinguishes_same_numbered_issues_across_different_features(tmp_path):
    """Regression test: two features each restart numbering at 01 (the
    documented convention, docs/agents/issue-tracker.md) — this must not
    conflate them into one status lookup entry. This is the exact scenario
    that silently collided before feature-slug scoping was added: a fresh
    'data-foundation' Issue 01 landing alongside an existing
    'phase-1-bootstrap' Issue 01 with a different status."""
    (tmp_path / "README.md").write_text(
        "- ✅ alpha-feature Issue 01 — done task\n"
        "- ⏳ beta-feature Issue 01 — different, not-done task\n",
        encoding="utf-8",
    )
    alpha_dir = tmp_path / ".scratch" / "alpha-feature" / "issues"
    alpha_dir.mkdir(parents=True)
    (alpha_dir / "01-done-task.md").write_text(
        "Status: ready-for-human\n", encoding="utf-8"
    )
    beta_dir = tmp_path / ".scratch" / "beta-feature" / "issues"
    beta_dir.mkdir(parents=True)
    (beta_dir / "01-different-task.md").write_text(
        "Status: needs-triage\n", encoding="utf-8"
    )

    assert find_issue_status_mismatches(tmp_path) == []


def test_detects_a_real_mismatch_inside_a_cross_feature_number_collision(tmp_path):
    """The sibling test above only covers the no-false-positive direction:
    two colliding-numbered issues that each independently agree. This
    covers the other direction per docs/testing.md's "cover both
    directions" convention -- a real mismatch in ONE of two
    colliding-numbered issues must still be caught and attributed to the
    right feature, not masked by the other feature's clean agreement or
    misattributed to it."""
    (tmp_path / "README.md").write_text(
        "- ✅ alpha-feature Issue 01 — stale claim, issue is not actually done\n"
        "- ✅ beta-feature Issue 01 — genuinely done task\n",
        encoding="utf-8",
    )
    alpha_dir = tmp_path / ".scratch" / "alpha-feature" / "issues"
    alpha_dir.mkdir(parents=True)
    (alpha_dir / "01-stale-claim.md").write_text(
        "Status: needs-triage\n", encoding="utf-8"
    )
    beta_dir = tmp_path / ".scratch" / "beta-feature" / "issues"
    beta_dir.mkdir(parents=True)
    (beta_dir / "01-genuinely-done-task.md").write_text(
        "Status: ready-for-human\n", encoding="utf-8"
    )

    violations = find_issue_status_mismatches(tmp_path)

    assert len(violations) == 1
    assert "alpha-feature Issue 1" in violations[0]
    assert "beta-feature" not in violations[0]
