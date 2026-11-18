"""Exceptions raised by the package.

Library code raises these instead of calling ``sys.exit`` so callers (notebooks,
services, tests) decide how to react.
"""

from __future__ import annotations


class FingerprintError(Exception):
    """Base class for all errors raised by this package."""


class GcsObjectNotFound(FingerprintError):
    """The requested object / prefix does not exist in the bucket."""


class GcsAccessError(FingerprintError):
    """A Google Cloud Storage request failed (permissions, network, auth)."""


class ArchiveReadError(FingerprintError):
    """An archive could not be read (corrupt, encrypted or unsupported)."""


class MissingDependencyError(FingerprintError, ImportError):
    """An optional dependency needed for the requested operation is missing."""
