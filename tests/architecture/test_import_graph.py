from pathlib import Path

from import_graph import FORBIDDEN_IMPORTS, MODULES, check_import_graph

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_no_violations_in_current_scaffold():
    violations = check_import_graph(REPO_ROOT)
    assert violations == []


def test_detects_a_forbidden_import(tmp_path):
    (tmp_path / "retrieve").mkdir()
    (tmp_path / "generate").mkdir()
    (tmp_path / "retrieve" / "__init__.py").write_text("import generate\n")
    (tmp_path / "generate" / "__init__.py").write_text("")

    violations = check_import_graph(tmp_path)

    assert len(violations) == 1
    assert "retrieve/" in violations[0]
    assert "generate/" in violations[0]


def test_forbidden_imports_only_names_known_modules():
    for module, forbidden in FORBIDDEN_IMPORTS.items():
        assert module in MODULES
        assert forbidden <= MODULES
