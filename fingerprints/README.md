# code_fingerprint

Fingerprints the source code stored in Google Cloud Storage objects: language
breakdown plus the class / function / variable names found in every file.

```python
from code_fingerprint import analyze_gcs_object

analyze_gcs_object("repo.zip")                         # one object, prefix or archive
analyze_gcs_object(["repo-a.zip", "repo-b.tar.gz", "infra/"])   # ONE combined archive
analyze_gcs_object("repo.zip", verbose=True)           # debug output on stderr
analyze_gcs_object("gs://other-bucket/app/")           # full URIs work too
```

* Returns `{language: {bytes, lines, files, file_names, file_fingerprints, percent}}`.
* Returns `{}` when there is no code to fingerprint.
* With a list, member names are prefixed with the object they came from
  (`repo-a.zip/src/app.py`), so equal paths in different objects stay distinct.
* Errors are exceptions (`GcsObjectNotFound`, `GcsAccessError`, `ArchiveReadError`,
  `MissingDependencyError`, all subclasses of `FingerprintError`); nothing calls `sys.exit`.

## Layout

| module | responsibility |
|---|---|
| `api.py` | `analyze_gcs_object` - argument handling, multi-object chaining, output |
| `gcs.py` | GCS references, object / prefix opening, parallel download |
| `sources.py` | directory and archive readers (zip, tar, 7z, rar) |
| `analyzer.py` | classify files, aggregate per-language stats |
| `resolver.py` | which language is this file? (name -> content -> extension -> shebang) |
| `languages.py` | **the language registry** - names, extensions, file names, shebangs |
| `content_detector.py`, `signatures.py` | regex-based content detection |
| `symbols.py`, `queries.py` | tree-sitter extraction and its per-language queries |
| `filters.py`, `report.py`, `debug.py`, `errors.py` | small helpers |

## Language names

Every layer uses `tree_sitter_language_pack` names: `cpp`, `csharp`, `bash`,
`make`, `asm`, `objc`, `tsx`, `terraform` ... Old display names still work in
`normalize_language()` (`"C++"` -> `cpp`, `"Shell"` -> `bash`, ...). Only
`jupyter`, `sass` and `text` have no grammar in the pack; they are counted but
yield no symbols. `tests/test_languages.py` fails if a name drifts from the pack.

## Adding a language

1. Add a `Language(...)` line to `languages.py` (name must be a pack name).
2. Run `pytest`. If the generic fallback finds nothing for it, add patterns to
   `queries.py` and a sample to `tests/sample_code.py` / `tests/test_queries.py`.

## Tests

`pytest` (the first run downloads the grammars it needs).
