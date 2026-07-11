"""Forbidden module-to-module import edges per specs/04-architecture.md §5.1.

Scope (Issue 02, 2026-07-11 correction): only true Python import bans between
first-party module directories. Excludes §5.1's non-import infra/service-access
constraints (e.g. "never persist directly to Qdrant/Postgres") — those aren't
enforceable via import-statement AST and are out of this check's scope.

Interpretive notes on §5.1's prose, so the encoding below is auditable rather
than a silent judgment call:
- "retrieval" / "generation" (no trailing slash, e.g. admin/'s "never call
  retrieval/generation directly") are read as the retrieve/ and generate/
  modules — the same modules named with slash notation elsewhere in the table.
- A module whose "May call" column names zero first-party module targets (it
  only reaches the rest of the system via an external service, or over HTTP
  rather than direct import — `rerank/`, `config/`, `eval/`, `widget/`) gets a
  blanket ban on every other first-party module: importing any of them
  in-process would bypass the very boundary (external service call, or the
  API surface) that row's Forbidden column exists to protect.
- Partial-access carve-outs (e.g. cdc/'s cache/ access being invalidation-only,
  not a full ban) are excluded — this check only encodes clean-cut forbidden
  edges, not partial-access nuances.
"""

import ast
from pathlib import Path

MODULES = {
    "api", "retrieve", "acl", "rerank", "generate", "verify", "audit",
    "ingest", "admin", "eval", "config", "widget", "cdc",
    "safety_input", "safety_output", "policy", "cache",
}


def _all_other_modules(module: str) -> set[str]:
    return MODULES - {module}


FORBIDDEN_IMPORTS: dict[str, set[str]] = {
    "api": set(),
    "retrieve": {"generate", "acl", "verify"},
    "acl": {"retrieve", "generate"},
    "rerank": _all_other_modules("rerank"),
    "generate": {"verify", "retrieve", "audit"},
    "verify": set(),
    "audit": {"generate"},
    "cdc": {"retrieve", "generate", "verify"},
    "ingest": {"verify"},
    "admin": {"retrieve", "generate"},
    "eval": _all_other_modules("eval"),
    "config": _all_other_modules("config"),
    "widget": _all_other_modules("widget"),
    "safety_input": {"retrieve", "acl", "generate", "verify"},
    "safety_output": {"verify", "generate", "retrieve"},
    "policy": {"generate", "retrieve", "rerank"},
    "cache": set(),
}


def _imported_first_party_modules(py_file: Path) -> set[str]:
    tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if top in MODULES:
                    found.add(top)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                top = node.module.split(".")[0]
                if top in MODULES:
                    found.add(top)
    return found


def check_import_graph(repo_root: Path) -> list[str]:
    """Return one message per forbidden import edge found under repo_root."""
    violations = []
    for module in sorted(MODULES):
        module_dir = repo_root / module
        if not module_dir.is_dir():
            continue
        forbidden = FORBIDDEN_IMPORTS.get(module, set())
        if not forbidden:
            continue
        for py_file in sorted(module_dir.rglob("*.py")):
            forbidden_hits = _imported_first_party_modules(py_file) & forbidden
            for target in sorted(forbidden_hits):
                violations.append(
                    f"{py_file.relative_to(repo_root)}: `{module}/` imports "
                    f"forbidden module `{target}/` (specs/04-architecture.md §5.1)"
                )
    return violations
