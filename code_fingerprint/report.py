"""Human-readable rendering of an analysis result."""

from __future__ import annotations

from typing import Any, Dict


def human_bytes(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} GB"          # unreachable; keeps type checkers happy


def format_report(label: str, kind: str, summary: Dict[str, Dict[str, Any]], by: str) -> str:
    """Table with one row per language: share, bar, files, lines, size."""
    width = max(len(lang) for lang in summary)
    lines = [f"\nLanguages in {label} [{kind}]  (by {by})\n"]
    for lang, v in summary.items():
        pct = v["percent"]
        bar = "█" * max(1, round(pct / 2.5)) if pct > 0 else ""
        lines.append(f"{lang:<{width}}  {pct:6.2f}%  {bar:<40}  "
                     f"{v['files']:>5} files  {v['lines']:>8} lines  {human_bytes(v['bytes']):>9}")
    lines.append("")
    return "\n".join(lines)
