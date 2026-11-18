"""Shared fixtures: an in-memory stand-in for ``google.cloud.storage.Client``."""

import io
import tarfile
import zipfile
from pathlib import Path

import pytest


class FakeBlob:
    def __init__(self, name: str, data: bytes):
        self.name, self._data, self.size = name, data, len(data)

    def download_as_bytes(self) -> bytes:
        return self._data

    def download_to_filename(self, filename: str) -> None:
        Path(filename).write_bytes(self._data)


class FakeBucket:
    def __init__(self, objects):
        self._objects = objects

    def get_blob(self, name):
        return FakeBlob(name, self._objects[name]) if name in self._objects else None


class FakeClient:
    """``buckets`` maps bucket name -> {object name: bytes}."""

    def __init__(self, buckets):
        self.buckets = buckets

    def bucket(self, name):
        return FakeBucket(self.buckets[name])

    def list_blobs(self, bucket, prefix="", max_results=None):
        names = sorted(n for n in self.buckets[bucket] if n.startswith(prefix))
        if max_results:
            names = names[:max_results]
        return iter([FakeBlob(n, self.buckets[bucket][n]) for n in names])


def make_zip(files: dict) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, data in files.items():
            zf.writestr(name, data)
    return buf.getvalue()


def make_tar_gz(files: dict) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        for name, data in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tf.addfile(info, io.BytesIO(data))
    return buf.getvalue()


PY_APP = b'''import os


class Greeter:
    def hello(self, name):
        return "hi " + name


def main():
    g = Greeter()
    print(g.hello(os.getcwd()))


if __name__ == "__main__":
    main()
'''

TF_MAIN = b'''terraform {
  required_version = ">= 1.5"
}

variable "env" {
  type    = string
  default = "dev"
}

resource "aws_instance" "web" {
  ami           = "ami-123"
  instance_type = "t3.micro"
}

output "ip" {
  value = aws_instance.web.public_ip
}
'''

GO_MAIN = b'''package main

import "fmt"

type Server struct{ port int }

func (s *Server) Start() { fmt.Println(s.port) }

func main() {
	s := &Server{port: 80}
	s.Start()
}
'''


@pytest.fixture
def client():
    return FakeClient({
        "uda-source": {
            "repo-a.zip": make_zip({"src/app.py": PY_APP, "README.md": b"# hi\n" * 20,
                                    "logo.png": b"\x89PNG\x00\x00"}),
            "repo-b.tar.gz": make_tar_gz({"src/app.py": PY_APP, "main.go": GO_MAIN}),
            "infra/main.tf": TF_MAIN,
            "infra/modules/net/vars.tf": TF_MAIN,
            "infra/.terraform/providers/x.py": PY_APP,         # must be ignored
            "docs/guide.md": b"# Guide\n" * 30,
            "single.py": PY_APP,
            "blank.py": b"\n\n   \n",
        },
        "other-bucket": {"lib/util.go": GO_MAIN},
    })
