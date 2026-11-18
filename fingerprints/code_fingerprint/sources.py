"""Readers that turn a file, directory or archive into ``(name, bytes)`` pairs.

Every reader is a generator yielding ``(relative_name, data)``.  Files that
are filtered out (ignored path, too large) are skipped; members that exist but
cannot be read (password protected, corrupt) are recorded on the
:class:`ScanContext` so the caller can report that the result is incomplete.

Readers never call ``sys.exit``; fatal problems raise the exceptions from
:mod:`.errors`.
"""

from __future__ import annotations

import logging
import tarfile
import tempfile
import zipfile
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Iterator, List, NamedTuple, Optional, Sequence, Tuple

from .errors import ArchiveReadError, MissingDependencyError
from .filters import IGNORED_DIRS, is_ignored

log = logging.getLogger(__name__)

FileStream = Iterator[Tuple[str, bytes]]


class Source(NamedTuple):
    """An opened input: its files plus what kind of thing it is."""

    files: FileStream
    kind: str          # "file", "directory", "zip archive", "tar archive", "prefix", ...


@dataclass
class ScanContext:
    """Settings and bookkeeping shared by all readers of one analysis."""

    max_size: int                                   # bytes; larger members are skipped
    excludes: Tuple[str, ...] = ()                  # extra directory names / glob patterns
    unreadable: List[Tuple[str, str]] = field(default_factory=list)
    origin: str = ""                                # object being read (for debug messages)

    def _where(self, name: str) -> str:
        return f"{name} (in {self.origin})" if self.origin else name

    def accepts(self, name: str, size: Optional[int]) -> bool:
        """True if a member should be read (not ignored, not too large)."""
        if is_ignored(name, self.excludes):
            log.debug("skip %s: ignored path", self._where(name))
            return False
        if size is not None and size > self.max_size:
            log.debug("skip %s: %d bytes exceeds the %d byte limit",
                      self._where(name), size, self.max_size)
            return False
        return True

    def mark_unreadable(self, name: str, reason: str) -> None:
        log.debug("cannot read %s: %s", self._where(name), reason)
        self.unreadable.append((name, reason))


# --------------------------------------------------------------------------
# Plain files and directories
# --------------------------------------------------------------------------
def iter_single_file(path: Path, ctx: ScanContext) -> FileStream:
    if path.stat().st_size <= ctx.max_size:
        yield path.name, path.read_bytes()
    else:
        log.debug("skip %s: larger than the %d byte limit", path.name, ctx.max_size)


def iter_directory(root: Path, ctx: ScanContext) -> FileStream:
    """Walk ``root`` iteratively, pruning ignored directories (symlinks are not followed)."""
    stack = [root]
    while stack:
        try:
            entries = sorted(stack.pop().iterdir())
        except OSError:
            continue
        for entry in entries:
            if entry.is_symlink():
                continue
            if entry.is_dir():
                if entry.name not in IGNORED_DIRS:
                    stack.append(entry)
                continue
            if not entry.is_file():
                continue
            rel = entry.relative_to(root).as_posix()
            try:
                if not ctx.accepts(rel, entry.stat().st_size):
                    continue
                yield rel, entry.read_bytes()
            except OSError as exc:
                ctx.mark_unreadable(rel, str(exc))


# --------------------------------------------------------------------------
# Archives
# --------------------------------------------------------------------------
def detect_archive(path: Path) -> Optional[str]:
    """Identify an archive by its magic bytes. Returns a kind or ``None``.

    Raises :class:`ArchiveReadError` for files that start like a zip but are broken.
    """
    try:
        with path.open("rb") as fh:
            magic = fh.read(8)
    except OSError:
        return None
    if magic.startswith(b"Rar!"):
        return "rar"
    if magic.startswith(b"7z\xbc\xaf\x27\x1c"):
        return "7z"
    if zipfile.is_zipfile(path):
        return "zip"
    if magic.startswith(b"PK\x03\x04"):
        # A zip header without a readable central directory: truncated or corrupt.
        # Say so rather than reporting "no code found".
        raise ArchiveReadError(f"'{path.name}' looks like a zip archive but is truncated or corrupt")
    try:
        if tarfile.is_tarfile(path):     # handles .gz / .bz2 / .xz compression
            return "tar"
    except (OSError, EOFError):
        pass
    return None


def iter_zip(path: Path, ctx: ScanContext) -> FileStream:
    with zipfile.ZipFile(path) as zf:
        for info in zf.infolist():
            if info.is_dir() or not ctx.accepts(info.filename, info.file_size):
                continue
            try:
                yield info.filename, zf.read(info)
            except (RuntimeError, NotImplementedError, zipfile.BadZipFile) as exc:
                reason = "password protected" if info.flag_bits & 0x1 else (str(exc) or type(exc).__name__)
                ctx.mark_unreadable(info.filename, reason)


def iter_tar(path: Path, ctx: ScanContext) -> FileStream:
    with tarfile.open(path, "r:*") as tf:
        for member in tf:                # sequential read: fast for .tar.gz
            if not member.isfile() or not ctx.accepts(member.name, member.size):
                continue
            fh = tf.extractfile(member)
            if fh is not None:
                yield member.name, fh.read()


def iter_7z(path: Path, ctx: ScanContext) -> FileStream:
    try:
        import py7zr
        from py7zr import exceptions as p7e
    except ImportError as exc:
        raise MissingDependencyError(
            "reading .7z archives needs py7zr:  pip install py7zr") from exc

    errors = (p7e.ArchiveError, p7e.PasswordRequired, p7e.AbsolutePathError)
    try:
        with py7zr.SevenZipFile(str(path)) as z:
            wanted = [i.filename for i in z.list()
                      if not i.is_directory and ctx.accepts(i.filename, i.uncompressed)]
        if not wanted:
            return
        with py7zr.SevenZipFile(str(path)) as z:      # reopen: readers are single-use
            if hasattr(z, "read"):                    # py7zr < 1.0
                contents = z.read(targets=wanted)
            else:                                     # py7zr >= 1.0: extract into memory
                from py7zr.io import BytesIOFactory
                factory = BytesIOFactory(ctx.max_size)
                z.extract(targets=wanted, factory=factory)
                contents = factory.products
            for name, bio in contents.items():
                bio.seek(0)
                yield name, bio.read()
    except errors as exc:
        raise ArchiveReadError(
            f"could not read 7z archive '{path.name}': {exc or type(exc).__name__} "
            "(password-protected archives are not supported)") from exc


def iter_rar(path: Path, ctx: ScanContext) -> FileStream:
    """Read a RAR archive via ``rarfile``, using only ``unrar`` or ``unar``.

    7z and bsdtar are deliberately not used as backends: in testing, Ubuntu's
    p7zip cannot decompress RAR ("Unsupported Method") and bsdtar returned
    truncated data through rarfile, which silently produced wrong totals.
    All members are extracted in ONE call into a temp dir (fast for solid
    archives, unlike one tool invocation per member) and then scanned.
    """
    try:
        import rarfile
    except ImportError as exc:
        raise MissingDependencyError(
            "reading .rar archives needs rarfile:  pip install rarfile "
            "(it also needs an `unrar` or `unar` binary on your PATH)") from exc

    try:
        rarfile.tool_setup(unrar=True, unar=True, bsdtar=False,
                           sevenzip=False, sevenzip2=False, force=True)
        with rarfile.RarFile(str(path)) as rf:
            if not rf.infolist() and rf.needs_password():       # encrypted headers
                raise rarfile.PasswordRequired("encrypted headers")
            wanted = []
            for info in rf.infolist():
                if info.is_dir() or not ctx.accepts(info.filename, info.file_size):
                    continue
                if info.needs_password():
                    ctx.mark_unreadable(info.filename, "password protected")
                    continue
                wanted.append(info)
            if not wanted:
                return
            with tempfile.TemporaryDirectory() as tmp:
                rf.extractall(tmp, members=wanted)
                got = 0
                # Already filtered above; walk the extracted tree without extra excludes.
                for item in iter_directory(Path(tmp), replace(ctx, excludes=())):
                    got += 1
                    yield item
                if got < len(wanted):          # e.g. symlinks or tool-side failures
                    ctx.mark_unreadable(f"{len(wanted) - got} RAR member(s)",
                                        "not extracted by the RAR tool")
    except rarfile.PasswordRequired as exc:
        raise ArchiveReadError(
            f"'{path.name}' has encrypted headers; password-protected archives "
            "are not supported") from exc
    except rarfile.RarCannotExec as exc:
        raise MissingDependencyError(
            "no working RAR extraction tool found. Install `unrar` (or `unar`) "
            "and make sure it is on your PATH.") from exc
    except rarfile.Error as exc:
        raise ArchiveReadError(f"could not read rar archive '{path.name}': {exc}") from exc


ARCHIVE_READERS = {"zip": iter_zip, "tar": iter_tar, "7z": iter_7z, "rar": iter_rar}


def open_local(path: Path, ctx: ScanContext) -> Source:
    """Pick the right reader for a local file, directory or archive."""
    if path.is_dir():
        return Source(iter_directory(path, ctx), "directory")
    kind = detect_archive(path)
    if kind:
        return Source(ARCHIVE_READERS[kind](path, ctx), f"{kind} archive")
    return Source(iter_single_file(path, ctx), "file")


def guard_reads(files: FileStream, label: str) -> FileStream:
    """Re-raise low-level read errors from an archive as :class:`ArchiveReadError`."""
    try:
        yield from files
    except (zipfile.BadZipFile, tarfile.TarError, EOFError, OSError) as exc:
        raise ArchiveReadError(f"could not read '{label}': {exc}") from exc


__all__: Sequence[str] = (
    "ScanContext", "Source", "FileStream", "open_local", "iter_directory",
    "iter_single_file", "detect_archive", "guard_reads",
)
