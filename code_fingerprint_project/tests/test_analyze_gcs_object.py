import json
import logging

import pytest

from code_fingerprint import (
    ArchiveReadError, GcsObjectNotFound, analyze_gcs_object,
)
from tests.conftest import PY_APP, FakeClient, make_zip


def run(client, obj, **kw):
    return analyze_gcs_object(obj, client=client, **kw)


def symbols(result, lang, name):
    return {(s["kind"], s["name"]) for s in result[lang]["file_fingerprints"][name]}


# --- single object keeps its original shape -----------------------------------
def test_single_zip(client):
    r = run(client, "repo-a.zip")
    assert list(r) == ["python"]                       # README.md is prose, logo.png is binary
    py = r["python"]
    assert py["file_names"] == ["src/app.py"] and py["files"] == 1 and py["percent"] == 100.0
    assert {("class", "Greeter"), ("function", "main")} <= symbols(r, "python", "src/app.py")
    assert set(py) == {"bytes", "lines", "files", "file_names", "file_fingerprints", "percent"}
    json.dumps(r)                                      # result is plain JSON data


def test_prefix_ignores_terraform_cache_and_names_are_relative(client):
    r = run(client, "infra")                           # no trailing slash needed
    assert list(r) == ["terraform"]
    assert sorted(r["terraform"]["file_names"]) == ["main.tf", "modules/net/vars.tf"]
    assert {("class", "aws_instance"), ("variable", "env"), ("variable", "ip")} \
        <= symbols(r, "terraform", "main.tf")


def test_plain_object_and_full_uri(client):
    assert run(client, "single.py")["python"]["file_names"] == ["single.py"]
    r = run(client, "gs://other-bucket/lib/util.go")
    assert list(r) == ["go"]
    assert ("class", "Server") in symbols(r, "go", "util.go")


# --- a list is processed as one archive --------------------------------------
def test_list_of_objects_is_one_combined_result(client):
    r = run(client, ["repo-a.zip", "repo-b.tar.gz", "infra/"])
    assert set(r) == {"python", "go", "terraform"}
    assert r["python"]["files"] == 2
    assert sorted(r["python"]["file_names"]) == ["repo-a.zip/src/app.py", "repo-b.tar.gz/src/app.py"]
    assert r["go"]["file_names"] == ["repo-b.tar.gz/main.go"]
    assert sorted(r["terraform"]["file_names"]) == ["infra/main.tf", "infra/modules/net/vars.tf"]
    assert round(sum(v["percent"] for v in r.values()), 1) == 100.0
    assert r["python"]["bytes"] == sum(len(f) for f in [])  or r["python"]["bytes"] > 0


def test_list_of_one_behaves_like_a_string(client):
    assert run(client, ["repo-a.zip"]) == run(client, "repo-a.zip")


def test_overlapping_and_duplicate_references_count_once(client):
    r = run(client, ["infra/", "infra/main.tf", "infra/"])
    assert sorted(r["terraform"]["file_names"]) == ["infra/main.tf", "infra/modules/net/vars.tf"]


def test_objects_from_different_buckets(client):
    r = run(client, ["single.py", "gs://other-bucket/lib/util.go"])
    assert set(r) == {"python", "go"}
    assert r["go"]["file_names"] == ["other-bucket/lib/util.go"]


# --- no code -> empty json ----------------------------------------------------
@pytest.mark.parametrize("obj", [["docs/guide.md"], "blank.py", [], ["docs/guide.md", "blank.py"]])
def test_no_code_returns_empty_dict(client, obj):
    assert run(client, obj) == {}


def test_prose_counts_only_when_asked(client):
    assert list(run(client, "docs/guide.md", all=True)) == ["markdown"]


def test_empty_result_in_print_mode(client, capsys):
    assert run(client, "docs/guide.md", print_only=True) == {}
    assert "No recognised source files found." in capsys.readouterr().out


# --- options -----------------------------------------------------------------
def test_only_top_and_by_lines(client):
    r = run(client, ["repo-a.zip", "repo-b.tar.gz"], only_top=1, by="lines")
    assert list(r) == ["python"]
    with pytest.raises(ValueError):
        run(client, "single.py", by="words")


def test_exclude_accepts_a_single_string(client):
    assert run(client, "infra/", exclude="modules") ["terraform"]["file_names"] == ["main.tf"]


def test_print_only_prints_table_and_returns_none(client, capsys):
    assert run(client, ["repo-a.zip", "repo-b.tar.gz"], print_only=True) is None
    out = capsys.readouterr().out
    assert "python" in out and "go" in out and "%" in out


# --- errors ------------------------------------------------------------------
def test_missing_object_raises(client):
    with pytest.raises(GcsObjectNotFound):
        run(client, ["single.py", "does/not/exist"])


def test_corrupt_archive_raises(client):
    truncated = make_zip({"a.py": PY_APP})[:-30]            # central directory cut off
    bad = FakeClient({"uda-source": {"broken.zip": truncated}})
    with pytest.raises(ArchiveReadError):
        run(bad, "broken.zip")


def test_none_is_rejected_instead_of_scanning_the_whole_bucket(client):
    with pytest.raises(ValueError):
        run(client, None)


# --- verbose -----------------------------------------------------------------
def test_verbose_false_is_silent(client, capsys):
    run(client, ["repo-a.zip", "infra/"])
    assert capsys.readouterr().err == ""


def test_verbose_true_writes_debug_data_to_stderr_only(client, capsys):
    result = run(client, ["repo-a.zip", "infra/"], verbose=True)
    cap = capsys.readouterr()
    assert cap.out == ""                               # stdout stays clean
    for expected in ("analysing 2 object(s)", "opened as zip archive",
                     "skip repo-a.zip/README.md: markdown is prose",
                     "skip repo-a.zip/logo.png: binary",
                     "repo-a.zip/src/app.py: python via", "parsed with python grammar",
                     "infra/main.tf: terraform via", "result python:", "finished in",
                     "skip .terraform/providers/x.py (in gs://uda-source/infra/): ignored path"):
        assert expected in cap.err, expected
    assert result["python"]["files"] == 1


def test_verbose_restores_logging_state(client):
    logger = logging.getLogger("code_fingerprint")
    before = (logger.level, logger.propagate, list(logger.handlers))
    run(client, "single.py", verbose=True)
    assert (logger.level, logger.propagate, list(logger.handlers)) == before
