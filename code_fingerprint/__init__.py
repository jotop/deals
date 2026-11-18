"""Fingerprint the source code stored in Google Cloud Storage objects.

    from code_fingerprint import analyze_gcs_object

    result = analyze_gcs_object(["repo-a.zip", "repo-b/"], verbose=False)

Languages are identified by their ``tree_sitter_language_pack`` names
everywhere (``cpp``, ``csharp``, ``bash``, ``terraform`` ...).
"""

from .api import analyze_gcs_object
from .content_detector import (
    Detection,
    SnippetTooShort,
    detect_programmin_language,      # original (misspelled) name, kept as an alias
    detect_programming_language,
)
from .errors import (
    ArchiveReadError,
    FingerprintError,
    GcsAccessError,
    GcsObjectNotFound,
    MissingDependencyError,
)
from .gcs import DEFAULT_BUCKET
from .languages import LANGUAGES, Kind, Language, normalize_language
from .resolver import resolve_language
from .symbols import extract_symbols

__version__ = "2.0.0"

__all__ = [
    "analyze_gcs_object",
    "detect_programming_language",
    "detect_programmin_language",
    "Detection",
    "SnippetTooShort",
    "extract_symbols",
    "resolve_language",
    "normalize_language",
    "LANGUAGES",
    "Language",
    "Kind",
    "DEFAULT_BUCKET",
    "FingerprintError",
    "GcsObjectNotFound",
    "GcsAccessError",
    "ArchiveReadError",
    "MissingDependencyError",
]
