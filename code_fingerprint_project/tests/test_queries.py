"""Every curated query must compile against the live grammar and find the expected names."""

import pytest
import tree_sitter_language_pack as pack
from tree_sitter import Query

from code_fingerprint.queries import QUERIES
from code_fingerprint.symbols import extract_symbols
from tests.sample_code import SAMPLES


def _grammar(name):
    try:
        return pack.get_language(name)
    except Exception as exc:                       # offline: grammars are downloaded on demand
        pytest.skip(f"grammar {name!r} unavailable: {exc}")


@pytest.mark.parametrize("language", sorted(QUERIES))
def test_all_curated_patterns_compile(language):
    grammar = _grammar(language)
    for pattern in QUERIES[language]:
        Query(grammar, pattern)                    # raises if a node type is wrong


def names(language, code=None):
    got = extract_symbols(code or SAMPLES[language], language)
    return {(s["kind"], s["name"]) for s in got}


EXPECTED = {
    "terraform": {("class", "aws_instance"), ("variable", "web"), ("variable", "env"),
                  ("variable", "ip"), ("class", "vpc"), ("variable", "name"), ("class", "aws")},
    "hcl": {("class", "job"), ("class", "web"), ("variable", "region")},
    "csharp": {("class", "Circle"), ("class", "IShape"), ("function", "Area"), ("variable", "radius")},
    "bash": {("function", "greet"), ("function", "other"), ("variable", "GREETING")},
    "dockerfile": {("class", "base"), ("class", "final"), ("variable", "VERSION"), ("variable", "APP_HOME")},
    "make": {("function", "all"), ("function", "clean"), ("variable", "CC")},
    "cmake": {("function", "add_thing"), ("function", "my_macro"), ("variable", "SRC")},
    "sql": {("class", "users"), ("class", "v_users"), ("function", "add_one")},
    "powershell": {("function", "Get-Thing"), ("class", "Foo")},
    "scala": {("class", "Circle"), ("class", "Main"), ("function", "area"), ("variable", "radius")},
    "lua": {("function", "helper"), ("function", "add"), ("function", "inner")},
    "perl": {("class", "Foo"), ("function", "greet")},
    "dart": {("class", "Animal"), ("function", "add"), ("variable", "answer")},
    "julia": {("class", "Point"), ("function", "area"), ("function", "sq"), ("variable", "LIMIT")},
    "elixir": {("class", "Demo.Greeter"), ("function", "hello"), ("function", "secret")},
    "haskell": {("class", "Shape"), ("function", "area"), ("variable", "total")},
    "zig": {("class", "Point"), ("function", "add"), ("variable", "counter")},
    "solidity": {("class", "Token"), ("function", "transfer"), ("variable", "total")},
    "objc": {("class", "Foo"), ("function", "bar"), ("function", "helper")},
    "proto": {("class", "User"), ("class", "Api"), ("function", "Get")},
    "graphql": {("class", "User"), ("class", "Role"), ("function", "GetUser")},
    "fsharp": {("class", "Point"), ("function", "add"), ("variable", "total")},
    "ocaml": {("class", "shape"), ("function", "area"), ("variable", "total")},
    "clojure": {("function", "greet"), ("variable", "answer"), ("class", "Person")},
    "erlang": {("class", "demo"), ("function", "add"), ("function", "sub")},
    "nix": {("function", "add"), ("variable", "name")},
    "bicep": {("class", "sa"), ("variable", "location"), ("variable", "id")},
}


@pytest.mark.parametrize("language", sorted(EXPECTED))
def test_sample_yields_expected_symbols(language):
    _grammar(language)
    missing = EXPECTED[language] - names(language)
    assert not missing, f"{language}: missing {sorted(missing)}"


def test_make_special_targets_are_not_functions():
    assert ("function", ".PHONY") not in names("make")


def test_one_node_gets_one_kind():
    # Zig: `const Point = struct {...}` is a class, not also a variable.
    got = extract_symbols(SAMPLES["zig"], "zig")
    assert [s["kind"] for s in got if s["name"] == "Point"] == ["class"]


def test_no_grammar_or_unknown_language_gives_empty_fingerprint():
    assert extract_symbols("{}", "jupyter") == []
    assert extract_symbols("x", "definitely-not-a-language") == []


def test_aliases_and_line_numbers():
    got = extract_symbols("\n\nclass A:\n    pass\n", "Python")
    assert got == [{"kind": "class", "name": "A", "line": 3}]
    assert extract_symbols("int main() { return 0; }", "C++")[0]["name"] == "main"
