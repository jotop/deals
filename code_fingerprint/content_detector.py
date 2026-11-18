"""Content-based programming-language detection.

A two-stage heuristic that needs no parser:

1. *Is this code at all?*  Language-independent signals (symbol density, share
   of lines that look like code / comments / prose) produce an "instruction
   score".
2. *Which language?*  Every language in :data:`~.signatures.SIGNATURES` is
   scored by weighted regex signatures; the best score wins.

Language names are ``tree_sitter_language_pack`` identifiers.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .signatures import SIGNATURES, Sig

MIN_BYTES = 512           # default minimum snippet size
MAX_CHARS = 200_000       # analyse at most this much text (head of the snippet)
CODE_THRESHOLD = 3.5      # stage-1 evidence needed to call the snippet "code"
MIN_LANG_SCORE = 10.0     # below this, we say "code, but language unknown"

#: Languages the detector has signatures for.
DETECTABLE_LANGUAGES = frozenset(SIGNATURES)


@dataclass
class Detection:
    contains_instructions: bool
    language: Optional[str]                 # None if no code or language unknown
    confidence: float                       # confidence in `language` (0..1)
    verdict_confidence: float               # confidence in the yes/no verdict (0..1)
    alternatives: List[str]                 # other languages that score almost as high
    candidates: List[Tuple[str, float]]     # top-5 (language, raw score)
    metrics: Dict[str, float]
    note: str


# --------------------------------------------------------------------------- #
# Stage 1 helpers: language-independent "does this look like code?" signals
# --------------------------------------------------------------------------- #
_STRUCT = re.compile(r"[{}()\[\];=<>+*%&|^~\\$@#]")
_COMMENT_START = re.compile(
    r"^(//|/\*|\*/|--\s|--$|#!|#\s|#$|;;|%\s|REM\s|rem\s|<!--|\"\"\"|''')"
)
_KEYWORD_START = re.compile(
    r"^(if|else|elif|elsif|for|foreach|while|switch|case|default|return|def|class|"
    r"function|fn|func|fun|import|from|using|package|include|public|private|protected|"
    r"static|const|let|var|val|try|catch|except|finally|do|end|then|fi|done|esac|begin|"
    r"local|struct|enum|interface|namespace|SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|"
    r"DROP|FROM|WHERE|JOIN)\b"
)
_ASSIGNMENT = re.compile(r"^[\w.\[\]\"']+\s*([:+\-*/|&]|<)?=\s*\S")
_OPCODE = re.compile(r"^[a-z]{2,6}\s+[%$\w\[\]+\-*.]+\s*,\s*\S")
_PLAIN_WORD = re.compile(r"[\"'(“‘]?[^\W\d_][^\W\d_'’-]*(-[^\W\d_]+)*[\"')”’,.;:!?]*")
_STOPWORDS = frozenset(
    # English
    "the a an and or of to in is are was were be been it this that for on with as by at "
    "from not but we you they he she his her their our your its which who what when where "
    "how can could will would should may might do does did have has had if then so than "
    "there these those them also into about more most other some such only over any each "
    # a few common words of other European languages (the code check must not
    # mistake non-English prose for code)
    "i w z na do się nie to jest że po jak czy ale oraz dla przez "
    "der die das und ist nicht ein eine mit von zu "
    "el la los las de que y en un una es por con para "
    "le les des et est une du pour dans qui".split()
)


def _classify_line(s: str, in_block_comment: bool = False) -> str:
    """Return 'code', 'comment', 'prose' or 'other' for one stripped line."""
    if _COMMENT_START.match(s) or (in_block_comment and s.startswith("*")):
        return "comment"
    tokens = s.split()
    n_struct = len(_STRUCT.findall(s))
    if len(tokens) >= 5 and n_struct <= 1 + len(tokens) // 20:
        plain = sum(1 for t in tokens if _PLAIN_WORD.fullmatch(t))
        stops = sum(1 for t in tokens if t.strip(".,;:!?\"'()").lower() in _STOPWORDS)
        if plain / len(tokens) >= 0.8 and stops >= 2 and stops / len(tokens) >= 0.2:
            return "prose"
    if s[-1] in ";{}":
        return "code"
    if n_struct >= 2 and n_struct / len(s) >= 0.08:
        return "code"
    if _KEYWORD_START.match(s) and (n_struct >= 1 or len(tokens) <= 4):
        return "code"
    if _ASSIGNMENT.match(s):
        return "code"
    if len(tokens) <= 3 and _OPCODE.match(s):       # e.g. "mov eax, 4"
        return "code"
    return "other"


def _text_metrics(text: str) -> Dict[str, float]:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    n = max(len(lines), 1)
    kinds = []
    in_block = False                      # inside a /* ... */ comment?
    for ln in lines:
        kinds.append(_classify_line(ln, in_block))
        if ln.startswith("/*") and "*/" not in ln:
            in_block = True
        elif "*/" in ln:
            in_block = False
    non_ws = sum(len(ln.replace(" ", "")) for ln in lines) or 1
    struct = sum(len(_STRUCT.findall(ln)) for ln in lines)
    return {
        "lines": float(len(lines)),
        "symbol_density": struct / non_ws,
        "code_line_ratio": (kinds.count("code") + 0.5 * kinds.count("comment")) / n,
        "prose_line_ratio": kinds.count("prose") / n,
    }


# --------------------------------------------------------------------------- #
# Stage 2: language scoring
# --------------------------------------------------------------------------- #
def _count(sig: Sig, text: str) -> int:
    n = 0
    for _ in sig.rx.finditer(text):
        n += 1
        if n >= sig.cap:
            break
    return n


def score_languages(text: str) -> Dict[str, float]:
    scores: Dict[str, float] = {}
    for lang, sigs in SIGNATURES.items():
        total = sum(sig.weight * _count(sig, text) for sig in sigs)
        scores[lang] = max(total, 0.0)
    return scores

# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
class SnippetTooShort(ValueError):
    pass


def _normalize(snippet: str) -> str:
    text = snippet.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    # unwrap a Markdown code fence if the whole snippet is one
    m = re.match(r"^\s*```[\w+#.-]*[ \t]*\n(.*?)\n?```\s*$", text, re.S)
    if m:
        text = m.group(1)
    return text[:MAX_CHARS]


# Languages that are strict supersets of another: a tie means "no extra syntax
# found", which favours the simpler language, so they must not count as rivals.
_FAMILIES = [{"javascript", "typescript"}, {"c", "cpp"}]
_SUPERSET_OF = {"javascript": "typescript", "c": "cpp"}


def _family(lang: str) -> set:
    for fam in _FAMILIES:
        if lang in fam:
            return fam
    return {lang}


def _looks_like_markup(text: str) -> bool:
    head = text.lstrip()[:20].lower()
    if head.startswith(("<?php", "<?=", "<%")):
        return False
    if head.startswith(("<!doctype", "<html", "<?xml", "<svg")):
        return True
    lines = [ln for ln in text.splitlines() if ln.strip()]
    tagged = sum(1 for ln in lines if re.match(r"\s*</?[A-Za-z!][^>]*>", ln))
    return bool(lines) and head.startswith("<") and tagged / len(lines) >= 0.7


def _analyze(text: str) -> Detection:
    """Stage 1 + 2 on already-normalised text (no size check)."""
    metrics = _text_metrics(text)
    scores = score_languages(text)
    ranked = sorted(scores.items(), key=lambda kv: -kv[1])   # stable -> tie order
    top_lang, top = ranked[0]
    family = _family(top_lang)
    rivals = [(k, v) for k, v in ranked if k not in family]
    second = rivals[0][1] if rivals else 0.0

    # How much language evidence is there per "statement-sized" chunk of text?
    # (~40 chars per statement, so long prose lines are not over-weighted.)
    size = max(len(text) / 40.0, metrics["lines"], 1.0)
    lang_evidence = min(top / (size * 1.5), 1.0)
    evidence = (
        2.0 * min(metrics["symbol_density"] / 0.06, 1.0)
        + 3.0 * metrics["code_line_ratio"]
        + 4.0 * lang_evidence
        - 3.0 * metrics["prose_line_ratio"]
    )
    metrics["language_evidence"] = lang_evidence
    metrics["top_score"] = top
    metrics["instruction_score"] = evidence
    p_code = 1.0 / (1.0 + math.exp(-(evidence - CODE_THRESHOLD)))
    candidates = [(k, round(v, 1)) for k, v in ranked[:5]]

    if evidence < CODE_THRESHOLD:
        return Detection(False, None, 0.0, 1.0 - p_code, [], candidates, metrics,
                        "no programming instructions found (looks like prose or plain data)")

    if top < MIN_LANG_SCORE:
        return Detection(True, None, 0.0, p_code, [], candidates, metrics,
                        "looks like code, but no supported language matches well")

    strength = 1.0 - math.exp(-top / 30.0)
    margin = (top - second) / top
    confidence = strength * (0.5 + 0.5 * margin)
    alternatives = [k for k, v in rivals if v >= 0.8 * top]
    notes = []
    sup = _SUPERSET_OF.get(top_lang)
    if sup and scores[sup] >= top:
        notes.append(f"no {sup}-specific syntax found")
    if alternatives:
        notes.append("also plausible: " + ", ".join(alternatives))
    return Detection(True, top_lang, confidence, p_code, alternatives, candidates,
                    metrics, "; ".join(notes))


def detect(snippet: str, min_bytes: int = MIN_BYTES) -> Detection:
    size = len(snippet.encode("utf-8", errors="replace"))
    if size < min_bytes:
        raise SnippetTooShort(
            f"snippet is {size} bytes; at least {min_bytes} bytes are required"
        )
    text = _normalize(snippet)

    # JSON is data, not instructions.
    stripped = text.strip()
    if stripped[:1] in "{[":
        try:
            json.loads(stripped)
            return Detection(False, None, 0.0, 0.99, [], [], {},
                            "valid JSON document: data, not instructions")
        except ValueError:
            pass

    # HTML/XML describes structure; only embedded <script> code is instructions.
    if _looks_like_markup(text):
        scripts = "\n".join(re.findall(r"<script\b[^>]*>(.*?)</script>", text, re.S | re.I))
        if len(scripts.strip()) < 40:
            return Detection(False, None, 0.0, 0.95, [], [], {},
                            "markup (HTML/XML): describes structure, contains no instructions")
        inner = _analyze(scripts)
        inner.note = ("found inside <script> tags of a markup document"
                      + ("; " + inner.note if inner.note else ""))
        return inner

    return _analyze(text)

def detect_programming_language(snippet: str, min_bytes: int = MIN_BYTES) -> Detection:
    """Detect whether ``snippet`` contains code and, if so, in which language.

    Raises :class:`SnippetTooShort` if the snippet is smaller than ``min_bytes``.
    """
    return detect(snippet, min_bytes)


# Backwards-compatible alias for the original (misspelled) name.
detect_programmin_language = detect_programming_language
