import uuid
from unittest import mock

import pytest

from flask_googlestorage.utils import secure_path


@pytest.mark.parametrize(
    "filename, name, uuid_name, expected",
    [
        ("foo.txt", None, False, "foo.txt"),
        ("FOO.TXT", None, False, "FOO.txt"),
        ("../foo", None, False, "foo"),
        ("FOO", None, False, "FOO"),
        ("archive.tar.gz", None, False, "archive.tar.gz"),
        ("../../ARCHIVE.TAR.GZ", None, False, "ARCHIVE.TAR.gz"),
        ("foo.txt", None, True, "a53d500f-bf6a-4978-9240-922a763d31cb.txt"),
        ("foo.", None, True, "a53d500f-bf6a-4978-9240-922a763d31cb"),
        ("foo", None, True, "a53d500f-bf6a-4978-9240-922a763d31cb"),
        ("ignored.txt", "preferred.JPG", False, "preferred.jpg"),
        ("ignored.txt", "../../Preferred.JPG", False, "Preferred.jpg"),
        ("ignored.TXT", "../../Preferred.", False, "Preferred.txt"),
        ("ignored.jpg", "foo/bar/preferred.txt", False, "foo/bar/preferred.txt"),
        ("ignored.jpg", "../foo/bar/preferred.txt", False, "foo/bar/preferred.txt"),
        ("ignored.jpg", "../foo/../bar/preferred.txt", False, "foo/bar/preferred.txt"),
        ("ignored.jpg", "../../", False, "a53d500f-bf6a-4978-9240-922a763d31cb.jpg"),
        ("../../", None, False, "a53d500f-bf6a-4978-9240-922a763d31cb"),
        ("ignored.jpg", "/preferred.txt", False, "preferred.txt"),
        ("ignored.jpg", "/bar/preferred.txt", False, "bar/preferred.txt"),
        ("天安门.jpg", None, False, "jpg.jpg"),
        ("天安门a.jpg", None, False, "a.jpg"),
        ("ignored.jpg", "天安门.jpg", False, "jpg.jpg"),
    ],
)
def test_secure_path(filename, name, uuid_name, expected):
    fixed_uuid = uuid.UUID("a53d500f-bf6a-4978-9240-922a763d31cb")
    with mock.patch("flask_googlestorage.utils.uuid.uuid4", return_value=fixed_uuid):
        assert str(secure_path(filename, name, uuid_name)) == expected
