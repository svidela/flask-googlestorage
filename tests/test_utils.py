import pytest
from flask_googlestorage.utils import secure_filename_ext


def test_tfs(file_storage_cls):
    tfs = file_storage_cls(filename="foo.bar")
    assert tfs.filename == "foo.bar"
    assert tfs.name is None
    tfs.save("foo_bar.txt")
    assert tfs.saved == "foo_bar.txt"


@pytest.mark.parametrize(
    "filename, expected",
    [
        ("foo.txt", "foo.txt"),
        ("FOO.TXT", "FOO.txt"),
        ("foo", "foo"),
        ("FOO", "FOO"),
        ("archive.tar.gz", "archive.tar.gz"),
        ("ARCHIVE.TAR.GZ", "ARCHIVE.TAR.gz"),
        ("audio.m4a", "audio.m4a"),
        ("AUDIO.M4A", "AUDIO.m4a"),
    ],
)
def test_lowercase_ext(filename, expected):
    assert secure_filename_ext(filename).name == expected
