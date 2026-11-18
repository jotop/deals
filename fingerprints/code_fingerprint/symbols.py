"""Extract class / function / variable names from source code with tree-sitter."""

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

KINDS = ("class", "function", "variable")

#: When one name node is captured as several kinds, the lowest number wins
#: (matters for R's ``f <- function() ...`` and Zig's ``const T = struct {}``).
_PRIORITY = {"class": 0, "function": 1, "variable": 2}

#: Used for languages without curated queries.
_GENERIC_KINDS = (
    ("class", re.compile(r"(class|struct|interface|enum|trait|protocol|module|object)_(declaration|definition|specifier|item)$")),
    ("function", re.compile(r"(function|method|func|fn|procedure|subroutine)_(declaration|definition|item|statement)$")),
    ("variable", re.compile(r"(variable|var|let|const|field|property)_(declaration|declarator|definition|item|spec)$")),
)


@dataclass(frozen=True)
class _Grammar:
    language: object
    parser: object
    queries: Tuple[Query, ...]          # empty -> use the generic fallback


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
    return _Grammar(grammar, parser, tuple(compiled))


def _generic_extract(root) -> List[Tuple[str, object]]:
    found = []
    stack = [root]
    while stack:
        node = stack.pop()
        for kind, rx in _GENERIC_KINDS:
            if rx.search(node.type):
                name = node.child_by_field_name("name")
                if name is not None:
                    found.append((kind, name))
                break
        stack.extend(node.children)
    return found


def _query_extract(queries: Iterable[Query], root) -> List[Tuple[str, object]]:
    found = []
    for query in queries:
        for capture_name, nodes in QueryCursor(query).captures(root).items():
            if capture_name.startswith("_"):      # helper captures used by predicates
                continue
            kind = capture_name.split(".")[0]
            found.extend((kind, node) for node in nodes)
    return found


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

    best: Dict[Tuple[int, int], Tuple[str, object]] = {}
    for kind, node in found:
        key = (node.start_byte, node.end_byte)
        if key not in best or _PRIORITY[kind] < _PRIORITY[best[key][0]]:
            best[key] = (kind, node)

    results = [
        {
            "kind": kind,
            "name": node.text.decode("utf8", errors="replace"),
            "line": node.start_point[0] + 1,
        }
        for kind, node in sorted(best.values(), key=lambda kn: kn[1].start_byte)
    ]

    if log.isEnabledFor(logging.DEBUG):
        counts = {k: sum(1 for r in results if r["kind"] == k) for k in KINDS}
        log.debug("  parsed with %s grammar (%s): %d classes, %d functions, %d variables%s in %.1f ms",
                  language, source, counts["class"], counts["function"], counts["variable"],
                  " [syntax errors present]" if tree.root_node.has_error else "",
                  (time.perf_counter() - started) * 1000)
    return results
