import pytest

from code_fingerprint import detect_programming_language, detect_programmin_language
from code_fingerprint.content_detector import SnippetTooShort
from code_fingerprint.resolver import could_be_source, resolve_language
from tests.sample_code import SAMPLES


def test_original_misspelled_name_still_works():
    assert detect_programmin_language is detect_programming_language


def test_detector_returns_pack_names():
    cpp = "#include <iostream>\nusing namespace std;\ntemplate <typename T> class Box { public: T v; };\nint main() { std::cout << 1 << std::endl; return 0; }\n" * 2
    assert detect_programming_language(cpp, 50).language == "cpp"
    sh = "#!/bin/bash\nset -e\nfor f in *.txt; do\n  echo \"$f\"\ndone\nif [ -f x ]; then echo hi; fi\n"
    assert detect_programming_language(sh, 50).language == "bash"


def test_detects_terraform_from_content():
    d = detect_programming_language(SAMPLES["terraform"], 50)
    assert d.contains_instructions and d.language == "terraform"


def test_terraform_signatures_do_not_claim_ordinary_code():
    js = "const data = require('x');\nmodule.exports = { run() { console.log(data.items); } };\nfunction f(a) { return a === 1; }\n" * 3
    assert detect_programming_language(js, 50).language == "javascript"


def test_short_snippet_rejected():
    with pytest.raises(SnippetTooShort):
        detect_programming_language("x = 1", 512)


@pytest.mark.parametrize("path,head,expected", [
    ("Dockerfile", b"", "dockerfile"),
    ("Dockerfile.dev", b"", "dockerfile"),
    ("a\\b\\Makefile", b"", "make"),
    ("main.tf", SAMPLES["terraform"].encode(), "terraform"),
    ("prod.tfvars", b'region = "eu"\nname = "x"\n', "terraform"),
    ("job.hcl", SAMPLES["hcl"].encode(), "hcl"),
    ("a.dart", SAMPLES["dart"].encode(), "dart"),
    ("App.tsx", b"export const A = (p: {x: number}) => <div>{p.x}</div>;\nconst b = 3;\nconsole.log(b);\n" * 2, "tsx"),
    ("x.m", b"function r = f(x)\n  r = x * 2;\nend\n" * 3, "matlab"),
    ("x.h", b"#import <Foundation/Foundation.h>\n@interface A : NSObject\n@end\n", "objc"),
    ("run", b"#!/usr/bin/env python3.11\nprint('hi')\n" * 3, "python"),
    ("tool", b"#!/bin/sh\necho hi\n", "bash"),
    ("notes.md", b"# Title\n\n```python\nimport os\nprint(os.getcwd())\n```\n" * 4, "markdown"),
    ("data.bin", b"\x01\x02", None),
    ("weird.xyz", b"just some words here, nothing else to see in this file at all.\n", None),
])
def test_resolve_language(path, head, expected):
    assert resolve_language(path, head).language == expected


def test_precheck_skips_unknown_binaries_but_keeps_scripts():
    assert not could_be_source("img/logo.png")
    assert could_be_source("infra/main.tf")
    assert could_be_source("bin/run")          # may be a shebang script
    assert could_be_source("Dockerfile.dev")
