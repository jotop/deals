"""Language registry: the single source of truth for language names.

Every language is identified by its ``tree_sitter_language_pack`` name
(``cpp``, ``csharp``, ``bash``, ``make``, ``asm``, ``objc`` ...).  The same
identifier is used for file classification, content detection, the grammar
passed to tree-sitter and the keys of the final result, so nothing needs to be
translated between layers.

A handful of formats have no tree-sitter grammar in the pack (Jupyter
notebooks, Sass, plain text).  They are still counted, with ``has_grammar``
set to ``False`` so no symbols are extracted for them.

To add a language, add one :class:`Language` entry to ``_LANGUAGES``; the
extension / filename / shebang lookup tables below are derived from it.
"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional, Tuple


class Kind(str, Enum):
    """Coarse category, used to decide what counts as "code"."""

    PROGRAMMING = "programming"
    MARKUP = "markup"
    MARKUP_CODELESS = "markup-codeless"
    DATA = "data"
    PROSE = "prose"


#: Kinds that are counted unless the caller asks for everything.
CODE_KINDS = frozenset({Kind.PROGRAMMING, Kind.MARKUP})


@dataclass(frozen=True)
class Language:
    name: str                              # tree_sitter_language_pack identifier
    kind: Kind
    extensions: Tuple[str, ...] = ()       # lower-case, with the leading dot
    filenames: Tuple[str, ...] = ()        # exact file names (no extension needed)
    shebangs: Tuple[str, ...] = ()         # interpreter names (for ``#!`` lines)
    has_grammar: bool = True               # False -> no tree-sitter grammar in the pack


P, M, Mc D, T = Kind.PROGRAMMING, Kind.MARKUP, Kind.MARKUP_CODELESS, Kind.DATA, Kind.PROSE

_LANGUAGES: Tuple[Language, ...] = (
    # --- general-purpose programming -------------------------------------
    Language("python", P, (".py", ".pyw", ".pyi"), shebangs=("python", "python2", "python3", "pypy")),
    Language("javascript", P, (".js", ".mjs", ".cjs", ".jsx"), shebangs=("node", "nodejs")),
    Language("typescript", P, (".ts", ".mts", ".cts"), shebangs=("deno", "ts-node")),
    Language("tsx", P, (".tsx",)),
    Language("java", P, (".java",)),
    Language("kotlin", P, (".kt", ".kts")),
    Language("scala", P, (".scala", ".sc")),
    Language("c", P, (".c", ".h")),
    Language("cpp", P, (".cpp", ".cc", ".cxx", ".c++", ".hpp", ".hh", ".hxx", ".h++")),
    Language("csharp", P, (".cs",)),
    Language("objc", P, (".m", ".mm")),
    Language("go", P, (".go",)),
    Language("rust", P, (".rs",)),
    Language("swift", P, (".swift",)),
    Language("dart", P, (".dart",)),
    Language("ruby", P, (".rb", ".rake", ".gemspec"),
             filenames=("Rakefile", "Gemfile", "Vagrantfile", "Podfile", "Brewfile"),
             shebangs=("ruby",)),
    Language("php", P, (".php", ".phtml"), shebangs=("php",)),
    Language("perl", P, (".pl", ".pm"), shebangs=("perl",)),
    Language("lua", P, (".lua",), shebangs=("lua", "luajit")),
    Language("r", P, (".r",), shebangs=("Rscript",)),
    Language("julia", P, (".jl",), shebangs=("julia",)),
    Language("matlab", P),                     # ".m" is shared with objc; see resolver
    Language("haskell", P, (".hs",)),
    Language("elixir", P, (".ex", ".exs"), shebangs=("elixir",)),
    Language("erlang", P, (".erl", ".hrl"), shebangs=("escript",)),
    Language("clojure", P, (".clj", ".cljs", ".cljc")),
    Language("ocaml", P, (".ml", ".mli")),
    Language("fsharp", P, (".fs", ".fsx")),
    Language("gleam", P, (".gleam",)),
    Language("elm", P, (".elm",)),
    Language("racket", P, (".rkt",)),
    Language("scheme", P, (".scm",)),
    Language("commonlisp", P, (".lisp", ".lsp")),
    Language("elisp", P, (".el",)),
    Language("crystal", P, (".cr",)),
    Language("zig", P, (".zig",)),
    Language("nim", P, (".nim",)),
    Language("groovy", P, (".groovy", ".gradle"), filenames=("Jenkinsfile",)),
    Language("fortran", P, (".f", ".f90", ".f95", ".f03", ".f08", ".for")),
    Language("ada", P, (".adb", ".ads")),
    Language("cobol", P, (".cob", ".cbl")),
    Language("pascal", P, (".pas",)),
    Language("haxe", P, (".hx",)),
    Language("lean", P, (".lean",)),
    Language("odin", P, (".odin",)),
    Language("purescript", P, (".purs",)),
    Language("solidity", P, (".sol",)),
    Language("gdscript", P, (".gd",)),
    Language("cuda", P, (".cu", ".cuh")),
    Language("glsl", P, (".glsl",)),
    Language("hlsl", P, (".hlsl",)),
    Language("wgsl", P, (".wgsl",)),
    Language("systemverilog", P, (".sv", ".svh")),
    Language("vhdl", P, (".vhd", ".vhdl")),
    Language("asm", P, (".asm", ".s")),
    # --- shells, build and automation ------------------------------------
    Language("bash", P, (".sh", ".bash", ".ksh"),
             filenames=(".bashrc", ".bash_profile", ".profile"),
             shebangs=("bash", "sh", "ksh", "dash")),
    Language("zsh", P, (".zsh",), filenames=(".zshrc", ".zprofile"), shebangs=("zsh",)),
    Language("fish", P, (".fish",), shebangs=("fish",)),
    Language("powershell", P, (".ps1", ".psm1", ".psd1"), shebangs=("pwsh",)),
    Language("batch", P, (".bat", ".cmd")),
    Language("awk", P, (".awk",), shebangs=("awk", "gawk")),
    Language("tcl", P, (".tcl",), shebangs=("tclsh",)),
    Language("vim", P, (".vim",)),
    Language("make", P, (".mk",), filenames=("Makefile", "makefile", "GNUmakefile")),
    Language("cmake", P, (".cmake",), filenames=("CMakeLists.txt",)),
    Language("just", P, (".just",), filenames=("justfile", "Justfile")),
    Language("starlark", P, (".bzl", ".star"),
             filenames=("BUILD", "BUILD.bazel", "WORKSPACE", "MODULE.bazel")),
    Language("dockerfile", P, (".dockerfile",), filenames=("Dockerfile", "Containerfile")),
    # --- infrastructure / configuration as code --------------------------
    Language("terraform", P, (".tf", ".tfvars")),
    Language("hcl", P, (".hcl",)),
    Language("bicep", P, (".bicep",)),
    Language("nix", P, (".nix",)),
    Language("rego", P, (".rego",)),
    Language("cue", P, (".cue",)),
    Language("jsonnet", P, (".jsonnet", ".libsonnet")),
    Language("pkl", P, (".pkl",)),
    Language("dhall", P, (".dhall",)),
    # --- query and interface-definition languages ------------------------
    Language("sql", P, (".sql",)),
    Language("proto", P, (".proto",)),
    Language("graphql", P, (".graphql", ".gql")),
    Language("prisma", P, (".prisma",)),
    # --- markup ----------------------------------------------------------
    Language("html", M, (".html", ".htm", ".xhtml")),
    Language("sass", M, (".sass",), has_grammar=False),
    Language("less", M, (".less",)),
    Language("vue", M, (".vue",)),
    Language("svelte", M, (".svelte",)),
    Language("astro", M, (".astro",)),
    Language("jupyter", M, (".ipynb",), has_grammar=False),
    # --- markup -- no code----------------------------------------------------------
    Language("css", Mc, (".css",)),
    Language("scss", Mc, (".scss",)),
    # --- data ------------------------------------------------------------
    Language("xml", D, (".xml", ".xsd", ".xsl", ".xslt", ".svg")),
    Language("json", D, (".json", ".jsonc")),
    Language("json5", D, (".json5",)),
    Language("yaml", D, (".yml", ".yaml")),
    Language("toml", D, (".toml",)),
    Language("csv", D, (".csv",)),
    Language("tsv", D, (".tsv",)),
    Language("ini", D, (".ini", ".cfg")),
    Language("properties", D, (".properties",)),
    # --- prose -----------------------------------------------------------
    Language("markdown", T, (".md", ".markdown")),
    Language("rst", T, (".rst",)),
    Language("asciidoc", T, (".adoc", ".asciidoc")),
    Language("text", T, (".txt",), has_grammar=False),
)


# --------------------------------------------------------------------------
# Derived lookup tables
# --------------------------------------------------------------------------
LANGUAGES: Dict[str, Language] = {lang.name: lang for lang in _LANGUAGES}

#: extension (lower-case, with dot) -> language name.  First definition wins.
EXTENSIONS: Dict[str, str] = {}
#: exact file name -> language name.
FILENAMES: Dict[str, str] = {}
#: shebang interpreter -> language name.
SHEBANGS: Dict[str, str] = {}
for _lang in _LANGUAGES:
    for _ext in _lang.extensions:
        EXTENSIONS.setdefault(_ext, _lang.name)
    for _fn in _lang.filenames:
        FILENAMES.setdefault(_fn, _lang.name)
    for _sb in _lang.shebangs:
        SHEBANGS.setdefault(_sb, _lang.name)
del _lang, _ext, _fn, _sb

#: Glob patterns for file names that carry a suffix (``Dockerfile.dev``).
FILENAME_PATTERNS: Tuple[Tuple[str, str], ...] = (
    ("Dockerfile.*", "dockerfile"),
)

#: Alternative spellings (including the display names used by earlier versions
#: of this code) -> canonical name.  Keys are lower-case.
ALIASES: Dict[str, str] = {
    "js": "javascript", "jsx": "javascript", "node": "javascript",
    "ts": "typescript",
    "py": "python", "python3": "python",
    "rs": "rust", "golang": "go", "rb": "ruby", "kt": "kotlin",
    "c++": "cpp", "cc": "cpp", "cplusplus": "cpp",
    "c#": "csharp", "cs": "csharp", "c_sharp": "csharp",
    "f#": "fsharp",
    "objective-c": "objc", "objective c": "objc", "obj-c": "objc", "objectivec": "objc",
    "shell": "bash", "sh": "bash",
    "assembly": "asm", "assembler": "asm",
    "makefile": "make",
    "batchfile": "batch",
    "ps1": "powershell", "pwsh": "powershell",
    "tf": "terraform", "tfvars": "terraform",
    "docker": "dockerfile",
    "yml": "yaml",
    "md": "markdown",
    "txt": "text",
    "restructuredtext": "rst",
    "vim script": "vim", "vimscript": "vim",
    "jupyter notebook": "jupyter", "ipynb": "jupyter",
}


def normalize_language(name: str) -> str:
    """Return the canonical (tree-sitter-language-pack) name for ``name``.

    Accepts canonical names, common aliases and the old display names
    ("C++", "C#", "Shell", "Assembly", ...).  Unknown names are returned
    lower-cased and unchanged.
    """
    key = name.strip().lower()
    return ALIASES.get(key, key)


def get_kind(language: str) -> Optional[Kind]:
    lang = LANGUAGES.get(language)
    return lang.kind if lang else None


def language_for_filename(name: str) -> Optional[str]:
    """Language for an exact file name or filename pattern, else ``None``."""
    if name in FILENAMES:
        return FILENAMES[name]
    for pattern, language in FILENAME_PATTERNS:
        if fnmatch.fnmatchcase(name, pattern):
            return language
    return None


def language_for_extension(ext: str) -> Optional[str]:
    """Language for an extension such as ``".py"`` (case-insensitive)."""
    return EXTENSIONS.get(ext.lower()) if ext else None
