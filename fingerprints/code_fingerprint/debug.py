"""Verbose / debug output.

All modules log through ``logging.getLogger(__name__)`` under the package
logger.  :func:`debug_logging` switches DEBUG output on for the duration of one
call and writes it to stderr, so stdout (and the returned JSON) stay clean.
"""

from __future__ import annotations

import logging
import sys
from contextlib import contextmanager
from typing import Iterator

PACKAGE_LOGGER = "code_fingerprint"


@contextmanager
def debug_logging(verbose: bool) -> Iterator[None]:
    """Emit DEBUG-level records of this package to stderr while active."""
    if not verbose:
        yield
        return

    logger = logging.getLogger(PACKAGE_LOGGER)
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("[fingerprint] %(message)s"))
    previous_level, previous_propagate = logger.level, logger.propagate
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False            # avoid duplicate lines if root is configured
    try:
        yield
    finally:
        logger.removeHandler(handler)
        logger.setLevel(previous_level)
        logger.propagate = previous_propagate
