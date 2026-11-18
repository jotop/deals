"""Rules for deciding which files are worth looking at."""

from __future__ import annotations

import fnmatch
import re
from typing import Iterable

#: Directories that are vendored, generated or VCS / tool metadata.
IGNORED_DIRS = frozenset({
    ".git", ".hg", ".svn", "node_modules", "bower_components", "vendor",
    "venv", ".venv", "env", "__pycache__", ".idea", ".vscode", "dist",
    "build", "target", ".tox", ".mypy_cache", ".pytest_cache", ".next",
    ".gradle", "Pods", "site-packages", "coverage",
    # Terraform provider / module caches
    ".terraform", ".terragrunt-cache",
})

#: Generated, minified or lock files.
IGNORED_FILE_PATTERNS = (
    "*.min.js", "*.min.css", "*.map", "package-lock.json", "yarn.lock",
    "pnpm-lock.yaml", "poetry.lock", "Cargo.lock", "*.pb.go", "*_pb2.py",
    "Gemfile.lock", "Pipfile.lock", "composer.lock", "go.sum",
    # Terraform state and lock files are generated, not authored
    ".terraform.lock.hcl", "*.tfstate", "*.tfstate.backup",
)

#: How many leading bytes are checked for NUL bytes (binary detection).
BINARY_SNIFF_BYTES = 8192


def is_binary(sample: bytes) -> bool:
    return b"\x00" in sample


def should_skip_file(name: str) -> bool:
    return any(fnmatch.fnmatch(name, p) for p in IGNORED_FILE_PATTERNS)


def is_ignored(rel_path: str, extra_excludes: Iterable[str] = ()) -> bool:
    """True if a path (relative, '/' or '\\' separated) should not be counted."""
    parts = [p for p in re.split(r"[\\/]+", rel_path) if p not in ("", ".")]
    if not parts or ".." in parts:       # empty or path-traversal attempt
        return True
    *dirs, name = parts
    if any(d in IGNORED_DIRS for d in dirs):
        return True
    if should_skip_file(name):
        return True
    norm = "/".join(parts)
    for pat in extra_excludes:
        if fnmatch.fnmatch(norm, pat) or any(fnmatch.fnmatch(p, pat) for p in parts):
            return True
    return False
