"""Packaging for code_fingerprint.

    pip install .                 # core: tree-sitter + Google Cloud Storage
    pip install ".[archives]"     # + .7z and .rar archive support
    pip install -e ".[dev]"       # editable install with the test dependencies
"""

import re
from pathlib import Path

from setuptools import find_packages, setup

HERE = Path(__file__).resolve().parent


def read_version() -> str:
    """Read __version__ without importing the package (its dependencies may not be installed yet)."""
    init = (HERE / "code_fingerprint" / "__init__.py").read_text(encoding="utf-8")
    match = re.search(r'^__version__\s*=\s*["\']([^"\']+)["\']', init, re.M)
    if not match:
        raise RuntimeError("could not find __version__ in code_fingerprint/__init__.py")
    return match.group(1)


setup(
    name="code_fingerprint",
    version=read_version(),
    description="Fingerprint the source code stored in Google Cloud Storage objects.",
    long_description=(HERE / "README.md").read_text(encoding="utf-8"),
    long_description_content_type="text/markdown",
    packages=find_packages(include=["code_fingerprint", "code_fingerprint.*"]),
    # tree-sitter-language-pack 1.25 (the version this code was tested with) needs 3.11+.
    python_requires=">=3.11",
    install_requires=[
        "tree-sitter>=0.25",                  # QueryCursor API
        "tree-sitter-language-pack>=1.25",    # grammars are downloaded on first use
        "google-cloud-storage",
    ],
    extras_require={
        "7z": ["py7zr"],
        # RAR also needs an `unrar` or `unar` executable on PATH.
        "rar": ["rarfile"],
        "archives": ["py7zr", "rarfile"],
        "dev": ["pytest"],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
)
