"""The registry is the single source of truth: keep it consistent with the pack."""

import tree_sitter_language_pack as pack

from code_fingerprint.content_detector import DETECTABLE_LANGUAGES
from code_fingerprint.languages import (
    ALIASES, EXTENSIONS, LANGUAGES, normalize_language, language_for_filename,
)
from code_fingerprint.queries import QUERIES

NO_GRAMMAR_BY_DESIGN = {"jupyter", "sass", "text"}


def test_every_name_is_a_pack_name_unless_explicitly_exempt():
    manifest = set(pack.manifest_languages())
    outside = {n for n, lang in LANGUAGES.items() if lang.has_grammar and n not in manifest}
    assert not outside, f"not tree_sitter_language_pack names: {sorted(outside)}"
    assert {n for n, lang in LANGUAGES.items() if not lang.has_grammar} == NO_GRAMMAR_BY_DESIGN


def test_detector_and_query_keys_use_registry_names():
    assert DETECTABLE_LANGUAGES <= set(LANGUAGES)
    assert set(QUERIES) <= set(LANGUAGES)
    assert all(LANGUAGES[k].has_grammar for k in QUERIES)


def test_aliases_point_at_registered_languages():
    assert {v for v in ALIASES.values()} <= set(LANGUAGES)


def test_extensions_are_lowercase_and_unique_per_language():
    seen = {}
    for lang in LANGUAGES.values():
        for ext in lang.extensions:
            assert ext == ext.lower() and ext.startswith(".")
            assert ext not in seen, f"{ext} claimed by {seen[ext]} and {lang.name}"
            seen[ext] = lang.name
    assert seen == EXTENSIONS


def test_old_display_names_still_normalise():
    for old, new in {"C++": "cpp", "C#": "csharp", "Shell": "bash", "Assembly": "asm",
                     "Makefile": "make", "Objective-C": "objc", "Batchfile": "batch",
                     "Jupyter Notebook": "jupyter", "Vim Script": "vim", "F#": "fsharp"}.items():
        assert normalize_language(old) == new
    assert normalize_language("Python") == "python"


def test_filenames():
    assert language_for_filename("Dockerfile") == "dockerfile"
    assert language_for_filename("Dockerfile.prod") == "dockerfile"
    assert language_for_filename("CMakeLists.txt") == "cmake"
    assert language_for_filename("main.tf") is None
