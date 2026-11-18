"""Public entry point: :func:`analyze_gcs_object`."""

from __future__ import annotations

import contextlib
import logging
import time
from typing import Any, Dict, Iterable, Iterator, List, Optional, Sequence, Tuple, Union

from .analyzer import analyze_files, summarize
from .debug import debug_logging
from .gcs import DEFAULT_BUCKET, GcsRef, default_client, namespaced_name, open_gcs_ref
from .report import format_report
from .sources import FileStream, ScanContext, guard_reads

log = logging.getLogger(__name__)

GcsObjects = Union[str, Iterable[str]]


def _parse_refs(gcs_object: GcsObjects, bucket: str) -> List[GcsRef]:
    """Normalise the ``gcs_object`` argument to a de-duplicated list of references."""
    if gcs_object is None:
        raise ValueError("gcs_object is required (use '' to analyse a whole bucket)")
    texts = [gcs_object] if isinstance(gcs_object, str) else list(gcs_object)
    refs: List[GcsRef] = []
    for text in texts:
        if not isinstance(text, str):
            raise TypeError(f"GCS object names must be strings, got {type(text).__name__}")
        ref = GcsRef.parse(text, bucket)
        if ref not in refs:
            refs.append(ref)
    return refs


def _open_all(client: Any, refs: Sequence[GcsRef], ctx: ScanContext,
              stack: contextlib.ExitStack) -> Tuple[FileStream, List[str]]:
    """Open every reference and chain their files into one stream.

    Returns the combined stream and a list that receives the kind of each
    source as it is opened.  With several references the result behaves like
    one archive containing all of them: member names are prefixed with the
    object they came from.
    """
    multiple = len(refs) > 1
    multi_bucket = len({r.bucket for r in refs}) > 1
    kinds: List[str] = []

    def chain() -> Iterator[Tuple[str, bytes]]:
        seen = set()
        for ref in refs:
            ctx.origin = ref.uri
            source = open_gcs_ref(client, ref, ctx, stack)
            kinds.append(source.kind)
            for member, data in guard_reads(source.files, ref.uri):
                name = namespaced_name(ref, source.kind, member, multi_bucket) if multiple else member
                if multiple:
                    if name in seen:                 # overlapping references
                        log.debug("skip %s: already read from another object", name)
                        continue
                    seen.add(name)
                yield name, data

    return chain(), kinds       # `kinds` is filled in while the stream is consumed


def _describe(refs: Sequence[GcsRef], kinds: Sequence[str], multi_bucket_names: bool) -> Tuple[str, str]:
    names = [r.name or r.bucket for r in refs] if not multi_bucket_names else [r.uri for r in refs]
    label = ", ".join(names[:3]) + (f" and {len(names) - 3} more" if len(names) > 3 else "")
    unique = sorted(set(kinds))
    kind = f"gcs {unique[0]}" if len(unique) == 1 else f"gcs, {len(refs)} objects"
    return label, kind


def analyze_gcs_object(
    gcs_object: GcsObjects,
    print_only: bool = False,
    only_top: Optional[int] = None,
    max_file_size: float = 50,
    exclude: Union[str, Iterable[str], None] = (),
    all: bool = False,                       # noqa: A002 - public name kept for compatibility
    by: str = "bytes",
    verbose: bool = False,
    *,
    bucket: str = DEFAULT_BUCKET,
    client: Any = None,
) -> Optional[Dict[str, Dict[str, Any]]]:
    """Fingerprint the source code found in one or more GCS objects.

    Parameters
    ----------
    gcs_object:
        An object name (file or archive: zip / tar / 7z / rar), a prefix
        ("folder", trailing ``/`` optional), ``""`` for the whole bucket, a full
        ``gs://bucket/path`` URI - or a **list** of any of those.  A list is
        analysed as a *single archive*: all files are merged into one result
        and their names are prefixed with the object they came from, so equal
        paths in different objects do not collide.
    print_only:
        Print a language table instead of returning the result.
    only_top:
        Keep only the N largest languages.
    max_file_size:
        Skip individual files larger than this many MB.
    exclude:
        Extra directory names or glob patterns to ignore.
    all:
        Also count data and prose languages (JSON, YAML, Markdown ...).
    by:
        Rank / weigh languages by ``"bytes"`` or ``"lines"``.
    verbose:
        Write debugging data (what was opened, why files were skipped, how each
        file was classified and parsed, timings) to stderr.
    bucket:
        Bucket used for references that are not full ``gs://`` URIs.
    client:
        An existing ``google.cloud.storage.Client`` (default: create one).

    Returns
    -------
    ``{language: {"bytes", "lines", "files", "file_names", "file_fingerprints",
    "percent"}}`` with languages named as in ``tree_sitter_language_pack``, or
    an **empty dict** if no code was found (nothing to fingerprint).  With
    ``print_only=True`` the table is printed and ``None`` is returned, except
    that an empty result is still returned as ``{}``.

    Raises
    ------
    GcsObjectNotFound, GcsAccessError, ArchiveReadError, MissingDependencyError
        (all subclasses of :class:`~code_fingerprint.errors.FingerprintError`)
    """
    if by not in ("bytes", "lines"):
        raise ValueError(f"by must be 'bytes' or 'lines', not {by!r}")
    refs = _parse_refs(gcs_object, bucket)
    excludes = (exclude,) if isinstance(exclude, str) else tuple(exclude or ())
    ctx = ScanContext(max_size=int(max_file_size * 1024 * 1024), excludes=excludes)

    with debug_logging(verbose):
        started = time.perf_counter()
        if not refs:
            log.debug("no GCS objects given; nothing to analyse")
            return _empty(print_only)
        log.debug("analysing %d object(s): %s", len(refs), ", ".join(r.uri for r in refs))
        log.debug("options: only_top=%s max_file_size=%sMB exclude=%s all=%s by=%s",
                  only_top, max_file_size, list(excludes), all, by)

        if client is None:
            client = default_client()
        kinds: List[str] = []
        with contextlib.ExitStack() as stack:      # owns temp dirs for downloaded archives
            files, kinds = _open_all(client, refs, ctx, stack)
            stats = analyze_files(files, include_all=all)

        if ctx.unreadable:
            shown = "; ".join(f"{n} ({r})" for n, r in ctx.unreadable[:3])
            more = f" and {len(ctx.unreadable) - 3} more" if len(ctx.unreadable) > 3 else ""
            log.warning("%d item(s) could not be read and are NOT included: %s%s",
                        len(ctx.unreadable), shown, more)

        summary = summarize(stats, by, only_top)
        for lang, v in summary.items():
            log.debug("result %s: %d files, %d lines, %d bytes (%.2f%%)",
                      lang, v["files"], v["lines"], v["bytes"], v["percent"])
        log.debug("finished in %.2fs", time.perf_counter() - started)

        if not summary:
            log.debug("no recognised source files found; returning an empty result")
            return _empty(print_only)

        if print_only:
            multi_bucket = len({r.bucket for r in refs}) > 1
            label, kind = _describe(refs, kinds, multi_bucket)
            print(format_report(label, kind, summary, by))
            return None
        return summary


def _empty(print_only: bool) -> Dict[str, Dict[str, Any]]:
    if print_only:
        print("No recognised source files found.")
    return {}
