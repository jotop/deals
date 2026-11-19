"""Aggregate files into per-language statistics and fingerprints."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Tuple

from .filters import BINARY_SNIFF_BYTES, is_binary
from .languages import CODE_KINDS, LANGUAGES
from .resolver import HEAD_BYTES, resolve_language
from .symbols import extract_symbols

log = logging.getLogger(__name__)


@dataclass
class LanguageStats:
    bytes: int = 0
    lines: int = 0
    files: int = 0
    file_names: List[str] = field(default_factory=list)
    #: file name -> [{"kind": "class"|"function"|"variable"|"import", "name": str, "line": int}, ...]
    file_fingerprints: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bytes": self.bytes,
            "lines": self.lines,
            "files": self.files,
            "file_names": self.file_names,
            "file_fingerprints": self.file_fingerprints,
        }


def analyze_files(files: Iterable[Tuple[str, bytes]],
                  include_all: bool = False) -> Dict[str, LanguageStats]:
    """Classify each ``(name, data)`` pair and fingerprint the code files.

    With ``include_all`` false only programming and markup languages are
    counted; data and prose (JSON, YAML, Markdown ...) are skipped.
    """
    stats: Dict[str, LanguageStats] = {}
    for name, data in files:
        if not data or data.isspace():
            log.debug("skip %s: empty", name)
            continue
        if is_binary(data[:BINARY_SNIFF_BYTES]):
            log.debug("skip %s: binary", name)
            continue

        resolution = resolve_language(name, data[:HEAD_BYTES])
        language = resolution.language
        if language is None:
            log.debug("skip %s: language unknown (%s)", name, resolution.method)
            continue
        meta = LANGUAGES.get(language)
        if not include_all and (meta is None or meta.kind not in CODE_KINDS):
            log.debug("skip %s: %s is %s, not code (use all=True to count it)",
                      name, language, meta.kind.value if meta else "unclassified")
            continue

        log.debug("%s: %s via %s, %d bytes", name, language, resolution.method, len(data))
        entry = stats.setdefault(language, LanguageStats())
        entry.bytes += len(data)
        entry.lines += data.count(b"\n") + (0 if data.endswith(b"\n") else 1)
        entry.files += 1
        entry.file_names.append(name)
        entry.file_fingerprints[name] = extract_symbols(data, language)
    return stats


def summarize(stats: Dict[str, LanguageStats], by: str = "bytes",
              only_top: int | None = None) -> Dict[str, Dict[str, Any]]:
    """Turn raw stats into the result mapping, largest language first.

    Returns ``{}`` when there is nothing to report (no recognised code).
    """
    total = sum(getattr(v, by) for v in stats.values())
    if total == 0:
        return {}
    rows = sorted(stats.items(), key=lambda kv: getattr(kv[1], by), reverse=True)
    if only_top:
        rows = rows[:only_top]
    return {
        lang: {**v.to_dict(), "percent": round(100 * getattr(v, by) / total, 2)}
        for lang, v in rows
    }
