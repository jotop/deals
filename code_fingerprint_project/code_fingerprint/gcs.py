"""Google Cloud Storage access.

A GCS reference is either

* an **object** (``"projects/app.zip"``) - downloaded and read as a file or
  archive (zip / tar / 7z / rar), or
* a **prefix** (``"projects/app/"``) or the whole bucket (``""``) - every
  object below it is listed and the plausible source files are downloaded in
  parallel.

References are relative to a bucket (``DEFAULT_BUCKET`` unless given) or are
full ``gs://bucket/path`` URIs.
"""

from __future__ import annotations

import contextlib
import logging
import re
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Tuple

from .errors import GcsAccessError, GcsObjectNotFound, MissingDependencyError
from .resolver import could_be_source
from .sources import FileStream, ScanContext, Source, open_local

log = logging.getLogger(__name__)

DEFAULT_BUCKET = "uda-source"
GCS_WORKERS = 16

_GCS_URI = re.compile(r"^gs://([^/]+)(?:/(.*))?$", re.S)


@dataclass(frozen=True)
class GcsRef:
    bucket: str
    name: str            # object name or prefix; "" means the whole bucket

    @property
    def uri(self) -> str:
        return f"gs://{self.bucket}/{self.name}"

    @classmethod
    def parse(cls, text: str, default_bucket: str = DEFAULT_BUCKET) -> "GcsRef":
        match = _GCS_URI.match(text)
        if match:
            return cls(match.group(1), match.group(2) or "")
        return cls(default_bucket, text)


def _gcs_errors() -> Tuple[type, ...]:
    """Exception classes that mean "the GCS request failed"."""
    try:
        from google.api_core import exceptions as api_exc
        from google.auth import exceptions as auth_exc
    except ImportError as exc:
        raise MissingDependencyError(
            "Google Cloud Storage access needs google-cloud-storage:  "
            "pip install google-cloud-storage") from exc
    return (api_exc.GoogleAPIError, auth_exc.GoogleAuthError)


def default_client() -> Any:
    """A ``google.cloud.storage.Client`` using application-default credentials."""
    errors = _gcs_errors()
    try:
        from google.cloud import storage
        return storage.Client()
    except ImportError as exc:
        raise MissingDependencyError(
            "Google Cloud Storage access needs google-cloud-storage:  "
            "pip install google-cloud-storage") from exc
    except errors as exc:                      # e.g. no application-default credentials
        raise GcsAccessError(f"could not create a Google Cloud Storage client: {exc}") from exc


def iter_gcs_prefix(client: Any, ref: GcsRef, prefix: str, ctx: ScanContext,
                    errors: Tuple[type, ...]) -> FileStream:
    """Download every plausible source object under ``prefix`` (in parallel)."""
    candidates = []
    listed = 0
    try:
        for blob in client.list_blobs(ref.bucket, prefix=prefix):
            listed += 1
            rel = blob.name[len(prefix):]
            if not rel or rel.endswith("/") or not blob.size:
                continue
            if not ctx.accepts(rel, blob.size):
                continue
            if not could_be_source(rel):
                log.debug("skip %s: extension is not a known source type", rel)
                continue
            candidates.append((rel, blob))
    except errors as exc:
        raise GcsAccessError(f"listing {ref.uri} failed: {exc}") from exc
    log.debug("%s: %d objects listed, %d worth downloading", ref.uri, listed, len(candidates))

    def fetch(item):
        rel, blob = item
        try:
            return rel, blob.download_as_bytes()
        except errors as exc:
            ctx.mark_unreadable(rel, f"download failed: {exc}")
            return rel, b""

    with ThreadPoolExecutor(max_workers=GCS_WORKERS) as pool:
        yield from pool.map(fetch, candidates)


def open_gcs_ref(client: Any, ref: GcsRef, ctx: ScanContext,
                 stack: contextlib.ExitStack) -> Source:
    """Open one reference as an object (file / archive) or as a prefix.

    Temporary downloads live in directories registered on ``stack``; keep the
    stack open until the returned files have been consumed.
    """
    errors = _gcs_errors()
    try:
        # 1) An exact object: download it (it may be an archive) and reuse the
        #    local readers.  Keep the original file name for language detection.
        blob = None
        if ref.name and not ref.name.endswith("/"):
            blob = client.bucket(ref.bucket).get_blob(ref.name)
        if blob is not None:
            tmp = Path(stack.enter_context(tempfile.TemporaryDirectory()))
            local = tmp / (PurePosixPath(blob.name).name or "object")
            log.debug("%s: object found (%s bytes), downloading", ref.uri, blob.size)
            blob.download_to_filename(str(local))
            source = open_local(local, ctx)
            log.debug("%s: opened as %s", ref.uri, source.kind)
            return source

        # 2) Otherwise treat it as a prefix ("folder") or a whole bucket.
        prefix = ref.name if (not ref.name or ref.name.endswith("/")) else ref.name + "/"
        if next(iter(client.list_blobs(ref.bucket, prefix=prefix, max_results=1)), None) is None:
            raise GcsObjectNotFound(f"no object or prefix found at {ref.uri}")
        log.debug("%s: no such object; treating it as a prefix (%r)", ref.uri, prefix)
        return Source(iter_gcs_prefix(client, ref, prefix, ctx, errors), "prefix")
    except errors as exc:
        raise GcsAccessError(f"Google Cloud Storage request failed for {ref.uri}: {exc}") from exc


def namespaced_name(ref: GcsRef, kind: str, member: str, include_bucket: bool) -> str:
    """Name of ``member`` inside a combined multi-object analysis.

    Names are qualified with the object they came from, so equal paths in two
    objects (``src/main.py`` in two zips) stay distinct.  For a prefix this
    reproduces the full GCS object name.
    """
    base = ref.name.rstrip("/")
    if include_bucket:
        base = f"{ref.bucket}/{base}" if base else ref.bucket
    if kind == "file":                  # a plain object: its own name is the full path
        return base
    return f"{base}/{member}" if base else member


__all__ = ("DEFAULT_BUCKET", "GcsRef", "default_client", "open_gcs_ref", "namespaced_name")

