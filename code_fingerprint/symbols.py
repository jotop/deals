"""Extract class / function / variable / import names from source code with tree-sitter.

Symbol kinds in a fingerprint: ``class``, ``function``, ``variable`` and
``import`` (the library or module a file pulls in: ``os`` for ``import os`` in
Python, ``stdio.h`` for ``#include <stdio.h>``, ``fmt`` for Go's ``import "fmt"``).
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, Iterable, List, Optional, Tuple, Union

from tree_sitter import Query, QueryCursor
from tree_sitter_language_pack import get_language, get_parser

from .languages import LANGUAGES, normalize_language
from .queries import QUERIES

log = logging.getLogger(__name__)

KINDS = ("class", "function", "variable", "import")

#: When one name node is captured as several kinds, the lowest number wins
#: (matters for R's ``f <- function() ...`` and Zig's ``const T = struct {}``).
_PRIORITY = {"class": 0, "function": 1, "variable": 2, "import": 3}

#: Node types that are an import statement, across languages (verified per language in
#: ``tests/test_imports.py``).  One node = one import statement, or one import spec for
#: Go / CUE, whose ``import_declaration`` only wraps the specs.
_IMPORT_NODE_TYPES = (
    "import_statement", "import_from_statement", "future_import_statement",  # Python, JS/TS, Julia, CSS
    "using_statement",                                        # Julia ``using LinearAlgebra``
    "import_declaration", "import_header", "import_spec",     # Java, Scala, Swift, Odin, C++ / Kotlin / Go, CUE
    "import_specification",                                   # Dart
    "import_directive",                                       # Solidity
    "import_decl", "open_module", "include_module",           # F# / OCaml
    "importStmt", "includeStmt",                              # Nim
    "import",                                                 # Haskell, Gleam, Lean, Protobuf, Jsonnet, PureScript
    "using_directive",                                        # C#
    "use_declaration", "extern_crate_declaration",            # Rust
    "namespace_use_clause",                                   # PHP ``use A\B;``
    "require_expression", "require_once_expression",          # PHP / Perl ``require``
    "include_expression", "include_once_expression",          # PHP
    "use_statement",                                          # Perl, Fortran, SCSS
    "preproc_include", "module_import",                       # C / C++ / Objective-C ``#include`` / ``@import``
    "pp_include", "pp_include_lib", "import_attribute",       # Erlang ``-include`` / ``-import``
    "require",                                                # Crystal
)

#: Same node type, different meaning in some grammars: not a library import there.
_IMPORT_NOT_IN = {
    "php": frozenset({"use_declaration"}),             # trait use inside a class
    "fortran": frozenset({"import_statement"}),        # host association, not a module
    "cobol": frozenset({"use_statement"}),             # USE ... ERROR handling
}

#: Used for languages without curated queries (and, for ``import``, for all languages).
_GENERIC_KINDS = (
    ("class", re.compile(r"(class|struct|interface|enum|trait|protocol|module|object)_(declaration|definition|specifier|item)$")),
    ("function", re.compile(r"(function|method|func|fn|procedure|subroutine)_(declaration|definition|item|statement)$")),
    ("variable", re.compile(r"(variable|var|let|const|field|property)_(declaration|declarator|definition|item|spec)$")),
    ("import", re.compile(r"^(?:" + "|".join(_IMPORT_NODE_TYPES) + r")$")),
)
_IMPORT_RX = _GENERIC_KINDS[-1][1]
_GENERIC_NAMED_KINDS = _GENERIC_KINDS[:-1]      # the kinds found by walking the tree


@dataclass(frozen=True)
class _Grammar:
    language: object
    parser: object
    queries: Tuple[Query, ...]          # empty -> use the generic fallback
    imports: Optional[Query] = None     # matches import statements (None: grammar has none)


@lru_cache(maxsize=None)
def _load_grammar(language: str) -> Optional[_Grammar]:
    """Load the grammar and compile the curated queries once per language.

    Returns ``None`` when the language has no usable grammar (not in the pack,
    or it could not be downloaded).
    """
    meta = LANGUAGES.get(language)
    if meta is not None and not meta.has_grammar:
        log.debug("no tree-sitter grammar for %r (by design)", language)
        return None
    try:
        grammar = get_language(language)
        parser = get_parser(language)
    except Exception as exc:                      # not in the pack / download failed
        log.debug("grammar %r unavailable: %s", language, exc)
        return None

    compiled: List[Query] = []
    for pattern in QUERIES.get(language, ()):
        try:
            compiled.append(Query(grammar, pattern))
        except Exception as exc:    # node type missing in this grammar version
            log.debug("skipped %s pattern %s... (%s)", language, pattern[:60], exc)
    if QUERIES.get(language) and not compiled:
        log.debug("every curated query for %r failed; using generic fallback", language)
    return _Grammar(grammar, parser, tuple(compiled), _compile_import_query(grammar, language))


def _compile_import_query(grammar, language: str) -> Optional[Query]:
    """One query matching every import node type that exists in this grammar."""
    excluded = _IMPORT_NOT_IN.get(language, frozenset())
    kinds = set()
    for i in range(grammar.node_kind_count):
        if grammar.node_kind_is_named(i) and grammar.node_kind_is_visible(i):
            kind = grammar.node_kind_for_id(i)
            if kind and kind not in excluded and _IMPORT_RX.search(kind):
                kinds.add(kind)
    if not kinds:
        return None
    try:
        return Query(grammar, "[" + " ".join(f"({k})" for k in sorted(kinds)) + "] @import.statement")
    except Exception as exc:                      # defensive: odd node names
        log.debug("could not compile import query for %r: %s", language, exc)
        return None


# A found symbol: (kind, node, name).  ``name`` is None when it is just the node's text.
_Found = Tuple[str, object, Optional[str]]


def _generic_extract(root) -> List[_Found]:
    """Walk the tree for class / function / variable declarations that have a ``name`` field."""
    found: List[_Found] = []
    stack = [root]
    while stack:
        node = stack.pop()
        for kind, rx in _GENERIC_NAMED_KINDS:
            if rx.search(node.type):
                name = node.child_by_field_name("name")
                if name is not None:
                    found.append((kind, name, None))
                break
        stack.extend(node.children)
    return found


def _query_extract(queries: Iterable[Query], root) -> List[_Found]:
    found: List[_Found] = []
    for query in queries:
        for capture_name, nodes in QueryCursor(query).captures(root).items():
            if capture_name.startswith("_"):      # helper captures used by predicates
                continue
            kind = capture_name.split(".")[0]
            found.extend((kind, node, None) for node in nodes)
    return found


# --------------------------------------------------------------------------
# Imports
#
# Import statements look different in every grammar, so the module name is
# located with a few ordered rules instead of one field name:
#   1. a field that names the module        (JS ``source``, Python ``module_name``,
#                                            Rust ``argument``, Gleam/OCaml ``module`` ...)
#   2. ``path`` segments joined with "."    (Scala ``scala.collection.mutable``; C and Go
#                                            have a single ``path``)
#   3. unfielded children that look like a module name   (Java, Swift, C#, Dart, Nim ...)
#   4. ``name`` fields, one import each     (Python ``import a, b``)
# The *library* is reported: aliases and imported members are left out.
# --------------------------------------------------------------------------
_MODULE_FIELDS = ("source", "module_name", "module", "file", "argument")

_STRING_TYPES = frozenset({
    "string", "string_literal", "string_value", "interpreted_string_literal",
    "raw_string_literal", "encapsed_string", "system_lib_string", "configurable_uri",
})
_MODULE_TYPES = _STRING_TYPES | frozenset({
    "identifier", "scoped_identifier", "qualified_name", "dotted_name", "module_path",
    "module_name", "long_identifier", "qualified_module", "namespace_name", "name",
    "package", "bareword", "module", "expr",
})
#: Wrapper nodes: the module name is the ``name`` / ``path`` field (or the first child).
_UNWRAP = {
    "aliased_import": "name",              # Python ``import numpy as np``
    "scoped_use_list": "path",             # Rust ``use std::{fs, io}``
    "use_as_clause": "path",               # Rust ``use a::b as c``
    "use_wildcard": None,                  # Rust ``use rand::*``
    "selected_import": None,               # Julia ``import Base: show``
    "import_require_clause": None,         # TypeScript ``import fs = require("fs")``
    "namespace_use_clause": None,
}


def _unwrap(node):
    for _ in range(4):
        if node.type not in _UNWRAP:
            break
        field = _UNWRAP[node.type]
        inner = node.child_by_field_name(field) if field else None
        if inner is None:
            inner = next(iter(node.named_children), None)
        if inner is None:
            break
        node = inner
    return node


def _import_targets(statement) -> List[Tuple[object, Optional[str]]]:
    """``[(node, name_or_None), ...]`` for the module(s) one import statement pulls in."""
    if statement.type == "future_import_statement":     # ``from __future__ import annotations``
        return [(statement, "__future__")]

    for field in _MODULE_FIELDS:
        target = statement.child_by_field_name(field)
        if target is not None:
            return [(_unwrap(target), None)]

    segments = [seg for seg in statement.children_by_field_name("path") if seg.is_named]
    if segments:
        return [(segments[0], ".".join(seg.text.decode("utf8", errors="replace") for seg in segments))]

    candidates = [
        child for i, child in enumerate(statement.children)
        if child.is_named and statement.field_name_for_child(i) is None
        and (child.type in _MODULE_TYPES or child.type in _UNWRAP)
    ]
    if candidates:
        if candidates[0].type in _STRING_TYPES:          # Dart: a string, then maybe an alias
            candidates = candidates[:1]
        return [(_unwrap(child), None) for child in candidates]

    return [(_unwrap(child), None) for child in statement.children_by_field_name("name")]


def _import_extract(query: Query, root) -> List[_Found]:
    found: List[_Found] = []
    for nodes in QueryCursor(query).captures(root).values():
        for statement in nodes:
            found.extend(("import", node, name) for node, name in _import_targets(statement))
    return found


_MAX_IMPORT_NAME = 200


def _clean_import(text: str) -> str:
    """``"react"`` -> ``react``, ``<stdio.h>`` -> ``stdio.h``, collapse whitespace."""
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) >= 2 and text[0] == "<" and text[-1] == ">":
        text = text[1:-1]
    text = text.strip("\"'`")
    return text[:_MAX_IMPORT_NAME]


def extract_symbols(data: Union[str, bytes], language: str) -> List[Dict[str, object]]:
    """Return ``[{"kind", "name", "line"}, ...]`` in source order.

    ``language`` may be a canonical name or any alias accepted by
    :func:`~.languages.normalize_language`.  Languages that have no grammar
    yield an empty list rather than an error.
    """
    if isinstance(data, str):
        data = data.encode("utf8")
    language = normalize_language(language)

    grammar = _load_grammar(language)
    if grammar is None:
        return []

    started = time.perf_counter()
    tree = grammar.parser.parse(data)
    if grammar.queries:
        found = _query_extract(grammar.queries, tree.root_node)
        source = f"{len(grammar.queries)} curated queries"
    else:
        found = _generic_extract(tree.root_node)
        source = "generic fallback"
    if grammar.imports is not None:                 # imports: all languages, curated or not
        found += _import_extract(grammar.imports, tree.root_node)

    best: Dict[Tuple[int, int], _Found] = {}
    for item in found:
        kind, node, _ = item
        key = (node.start_byte, node.end_byte)
        if key not in best or _PRIORITY[kind] < _PRIORITY[best[key][0]]:
            best[key] = item

    results = []
    for kind, node, name in sorted(best.values(), key=lambda item: item[1].start_byte):
        if name is None:
            name = node.text.decode("utf8", errors="replace")
        if kind == "import":
            name = _clean_import(name)
            if not name:
                continue
        results.append({"kind": kind, "name": name, "line": node.start_point[0] + 1})

    if log.isEnabledFor(logging.DEBUG):
        n = {k: sum(1 for r in results if r["kind"] == k) for k in KINDS}
        log.debug("  parsed with %s grammar (%s): %d classes, %d functions, %d variables, %d imports%s in %.1f ms",
                  language, source, n["class"], n["function"], n["variable"], n["import"],
                  " [syntax errors present]" if tree.root_node.has_error else "",
                  (time.perf_counter() - started) * 1000)
    return results
