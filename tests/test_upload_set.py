import pathlib

import pytest
from flask import url_for

from flask_googlestorage import UploadSet
from flask_googlestorage.upload_configuration import UploadConfiguration
from flask_googlestorage.extensions import ALL
from flask_googlestorage.exceptions import (
    NotInitializedStorageError,
    NotFoundUploadSetError,
    NotAllowedUploadError,
)


def test_name_alnum():
    with pytest.raises(ValueError) as e_info:
        UploadSet("my_files")

    assert str(e_info.value) == "Name must be alphanumeric (no underscores)"


def test_config_runtime_error():
    with pytest.raises(RuntimeError) as e_info:
        uset = UploadSet("files")
        uset.config

    assert "Working outside of application context." in str(e_info.value)


def test_config_not_init_error(app):
    with pytest.raises(NotInitializedStorageError) as e_info:
        uset = UploadSet("files")
        uset.config

    assert str(e_info.value) == "Flask-GoogleStorage extension was not initialized"


def test_config_not_found_error(app_defaults):
    with pytest.raises(NotFoundUploadSetError) as e_info:
        uset = UploadSet("music")
        uset.config

    assert str(e_info.value) == "UploadSet music was not found"


@pytest.mark.parametrize(
    "save_kwargs, expected_return",
    [
        ({}, "foo.txt"),
        ({"folder": "someguy"}, "someguy/foo.txt"),
        ({"name": "bar.txt"}, "bar.txt"),
        ({"name": "bar."}, "bar.txt"),
        ({"folder": "someguy", "name": "bar."}, "someguy/bar.txt"),
        ({"name": "someguy/bar.txt"}, "someguy/bar.txt"),
    ],
)
def test_save(save_kwargs, expected_return, file_storage_cls, tmp_uploadset):
    tfs = file_storage_cls(filename="foo.txt")
    res = tmp_uploadset.save(tfs, **save_kwargs)

    assert res == pathlib.PurePath(expected_return)
    assert tfs.saved == tmp_uploadset.config.destination / pathlib.PurePath(expected_return)


def test_save_error(tmp_uploadset):
    with pytest.raises(TypeError) as e_info:
        tmp_uploadset.save("not a FileStorage instance")

    assert str(e_info.value) == "The given storage must be a werkzeug.FileStorage instance"


def test_save_not_allowed(file_storage_cls, tmp_uploadset):
    with pytest.raises(NotAllowedUploadError) as e_info:
        tmp_uploadset.save(file_storage_cls(filename="not-allowed.exe"))

    assert str(e_info.value) == "The given file extension is not allowed"


@pytest.mark.parametrize(
    "filename, expected", [("/etc/passwd", "etc_passwd"), ("../../myapp.wsgi", "myapp.wsgi")]
)
def test_secured_filename(filename, expected, file_storage_cls, tmpdir):
    dst = pathlib.Path(tmpdir)
    uset = UploadSet("files", ALL)
    uset._config = UploadConfiguration(dst)
    tfs = file_storage_cls(filename=filename)
    res = uset.save(tfs)
    assert res.name == expected
    assert tfs.saved == dst / expected


@pytest.mark.parametrize(
    "filename, folder",
    [
        ("foo.txt", None),
        ("someguy/foo.txt", None),
        ("foo.txt", "someguy"),
        ("foo/bar.txt", "someguy"),
    ],
)
def test_path(filename, folder, tmp_uploadset):
    dst = tmp_uploadset.config.destination
    parts = [folder] if folder else []
    parts += filename.split("/")

    assert tmp_uploadset.path(filename, folder=folder) == dst / pathlib.PurePath(*parts)


def test_url_generated(app_serve):
    uset = UploadSet("files")
    with app_serve.test_request_context():
        url = uset.url("foo.txt")
        gen = url_for("_uploads.download_file", name="files", filename="foo.txt", _external=True)
        assert url == gen


def test_url_based(app_manual):
    uset = UploadSet("files")
    with app_manual.test_request_context():
        url = uset.url("foo.txt")
        assert url == "http://localhost:6001/foo.txt"

    assert "_uploads" not in app_manual.blueprints


@pytest.mark.parametrize("resolve, expected", [(True, "foo_1.txt"), (False, "foo.txt")])
def test_conflict(resolve, expected, file_storage_cls, tmp_uploadset):
    tfs = file_storage_cls(filename="foo.txt")
    foo = pathlib.Path(tmp_uploadset.config.destination) / "foo.txt"
    foo.touch()
    res = tmp_uploadset.save(tfs, resolve_conflict=resolve)
    assert res.name == expected


@pytest.mark.parametrize("resolve, expected", [(True, "foo_6.txt"), (False, "foo.txt")])
def test_multi_conflict(resolve, expected, file_storage_cls, tmp_uploadset):
    tfs = file_storage_cls(filename="foo.txt")
    foo = pathlib.Path(tmp_uploadset.config.destination) / "foo.txt"
    foo.touch()
    for n in range(1, 6):
        foo_n = pathlib.Path(tmp_uploadset.config.destination) / f"foo_{n}.txt"
        foo_n.touch()

    res = tmp_uploadset.save(tfs, resolve_conflict=resolve)
    assert res.name == expected


@pytest.mark.parametrize("resolve, expected", [(True, "foo_1"), (False, "foo")])
def test_conflict_without_extension(resolve, expected, file_storage_cls, tmpdir):
    dst = pathlib.Path(tmpdir)
    upload_set = UploadSet("files", extensions=(""))
    upload_set._config = UploadConfiguration(dst)

    tfs = file_storage_cls(filename="foo")
    foo = upload_set.config.destination / "foo"
    foo.touch()

    res = upload_set.save(tfs, resolve_conflict=resolve)
    assert res.name == expected


@pytest.mark.parametrize(
    "filename, expected", [("foo.txt", True), ("boat.jpg", True), ("warez.exe", False)]
)
def test_filenames(filename, expected, file_storage_cls, tmp_uploadset):
    tfs = file_storage_cls(filename=filename)
    assert tmp_uploadset.file_allowed(tfs, pathlib.PurePath(filename)) == expected


def test_non_ascii_filename(file_storage_cls, tmp_uploadset):
    tfs = file_storage_cls(filename="天安门.jpg")
    res = tmp_uploadset.save(tfs)
    assert res.name == "jpg.jpg"
    res = tmp_uploadset.save(tfs, name="secret.")
    assert res.name == "secret.jpg"


@pytest.mark.parametrize("extension, expected", [("txt", True), ("jpg", True), ("exe", False)])
def test_default_extensions(extension, expected, tmp_uploadset):
    assert tmp_uploadset.extension_allowed(extension) == expected


@pytest.mark.parametrize("name, keep_local", [("empty.txt", True), ("files/empty.txt", False)])
def test_save_google_storage(name, keep_local, empty_txt, bucket_uploadset):
    res = bucket_uploadset.save(empty_txt, name=name, keep_local=keep_local)
    assert res == pathlib.PurePath(name)
    if keep_local:
        assert (bucket_uploadset._config.destination / name).exists()
    else:
        assert not (bucket_uploadset._config.destination / name).exists()


@pytest.mark.parametrize("public", (True, False))
def test_save_public_google_storage(public, google_bucket_mock, empty_txt, bucket_uploadset):
    bucket_uploadset.save(empty_txt, public=public)
    if public:
        google_bucket_mock.get_blob().make_public.assert_called_once()
    else:
        google_bucket_mock.get_blob().make_public.assert_not_called()


def test_delete_local(file_storage_cls, tmpdir):
    dst = pathlib.Path(tmpdir)
    upload_set = UploadSet("files")
    upload_set._config = UploadConfiguration(dst)

    foo = dst / "foo.txt"
    foo.touch()

    upload_set.delete("foo.txt")

    assert not foo.exists()


def test_delete_google_storage(bucket_uploadset, google_bucket_mock):
    bucket_uploadset.delete("foo.txt")
    google_bucket_mock.get_blob().delete.assert_called_once()


def test_url_google_storage(app_cloud):
    uset = UploadSet("files")
    uset.url("foo.txt") == "http://google-storage-url/"


def test_signed_url_google_storage(app_cloud):
    uset = UploadSet("files")
    uset.signed_url("foo.txt") == "http://google-storage-signed-url/"


def test_signed_url_generated_fallback(app_serve):
    uset = UploadSet("files")
    with app_serve.test_request_context():
        url = uset.signed_url("foo.txt")
        gen = url_for("_uploads.download_file", name="files", filename="foo.txt", _external=True)
        assert url == gen


def test_sigend_url_based_fallback(app_manual):
    uset = UploadSet("files")
    with app_manual.test_request_context():
        url = uset.signed_url("foo.txt")
        assert url == "http://localhost:6001/foo.txt"

    assert "_uploads" not in app_manual.blueprints
