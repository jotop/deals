"""Decide which language a file is written in.

Resolution order (first rule that produces an answer wins):

1. **Exact file name** (``Dockerfile``, ``Makefile``, ``CMakeLists.txt`` ...).
2. **Content heuristics**, but only where they can add information: when the
   extension is missing/unknown, or maps to a language the detector has
   signatures for.  An extension that names a language the detector knows
   nothing about (``.tf``, ``.dart``, ``.zig`` ...) is trusted as is, because
   the detector could only ever answer with some *other* language.
3. **Extension**.
4. **Shebang** (extensionless scripts only).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Optional

from .content_detector import DETECTABLE_LANGUAGES, detect_programming_language
from .languages import (
    SHEBANGS,
    language_for_extension,
    language_for_filename,
)

log = logging.getLogger(__name__)

#: How many leading bytes of a file are used for classification.
HEAD_BYTES = 4096
#: Heads shorter than this are not worth running the content heuristics on.
MIN_CONTENT_BYTES = 50
#: Minimum confidence in the "this is code" verdict to accept a content result.
MIN_VERDICT_CONFIDENCE = 0.5

#: For a file whose extension names language X, a content result that is a
#: strict subset of X says nothing new (the detector can't tell TSX from
#: TypeScript, or C++ from C-looking C++), so the extension wins.
_SUBSET_LANGUAGES = {
    "cpp": {"c"},
    "typescript": {"javascript"},
    "tsx": {"javascript", "typescript"},
}

_OBJC_HINT = re.compile(rb"@interface|@implementation|#import\s*[<\"]")


@dataclass(frozen=True)
class Resolution:
    language: Optional[str]
    method: str                 # how the answer was reached (for debug output)


def _from_extension(ext: str, head: bytes) -> Optional[str]:
    """Extension -> language, disambiguating the extensions several share."""
    ext = ext.lower()
    if ext == ".m":                         # Objective-C vs MATLAB
        return "objc" if _OBJC_HINT.search(head) else "matlab"
    if ext == ".h":                         # C vs Objective-C (C++ is left to content)
        return "objc" if _OBJC_HINT.search(head) else "c"
    return language_for_extension(ext)


def _from_shebang(head: bytes) -> Optional[str]:
    if not head.startswith(b"#!"):
        return None
    first = head.split(b"\n", 1)[0].decode("utf-8", errors="replace")
    parts = first[2:].strip().split()
    if not parts:
        return None
    interp = PurePosixPath(parts[0]).name
    if interp == "env" and len(parts) > 1:
        interp = parts[1]
    if interp not in SHEBANGS:               # python3.11 -> python3 -> python
        interp = re.sub(r"[\d.]+$", "", interp)
    return SHEBANGS.get(interp)


def _from_content(head: bytes) -> Optional[str]:
    detection = detect_programming_language(
        head.decode("utf-8", errors="replace"), MIN_CONTENT_BYTES)
    if (detection.contains_instructions
            and detection.verdict_confidence > MIN_VERDICT_CONFIDENCE
            and detection.language):
        return detection.language
    return None


def resolve_language(path: str, head: bytes) -> Resolution:
    """Return the language of ``path`` (``language=None`` if unknown).

    ``head`` is the first few KB of the file's bytes (see :data:`HEAD_BYTES`).
    """
    # Archive members may use backslashes (zips made on Windows): normalise.
    name = PurePosixPath(str(path).replace("\\", "/")).name

    ext = PurePosixPath(name).suffix
    by_ext = _from_extension(ext, head) if ext else None
    by_name = language_for_filename(name)

    if len(head) > MIN_CONTENT_BYTES:
        by_content = _from_content(head)
        if by_content:
            if by_ext and by_content in _SUBSET_LANGUAGES.get(by_ext, ()):
                return Resolution(by_ext, f"extension (content only showed {by_content})")
            return Resolution(by_content, "content")


    if by_name:
        return Resolution(by_name, "filename")

    if by_ext:
        return Resolution(by_ext, "extension")
    if ext:
        return Resolution(None, f"unknown extension {ext!r}")

    by_shebang = _from_shebang(head)
    if by_shebang:
        return Resolution(by_shebang, "shebang")
    return Resolution(None, "no extension, no shebang")


def could_be_source(rel_path: str) -> bool:
    """Cheap name-only pre-check, so objects that can never be counted
    (``.png``, ``.zip``, ``.pdf`` ...) are not downloaded.

    True for known file names and extensions, and for names without an
    extension (which may be shebang scripts).
    """
    name = PurePosixPath(rel_path).name
    ext = PurePosixPath(name).suffix
    if language_for_filename(name) or not ext:
        return True
    return language_for_extension(ext) is not None
