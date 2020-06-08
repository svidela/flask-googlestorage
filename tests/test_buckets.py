import pathlib
from unittest import mock

import pytest
from flask import url_for
from google.cloud.exceptions import GoogleCloudError
from werkzeug.datastructures import FileStorage


from flask_googlestorage import Bucket
from flask_googlestorage.exceptions import NotFoundBucketError, NotAllowedUploadError


def test_name_alnum():
    with pytest.raises(ValueError) as e_info:
        Bucket("my_files")

    assert str(e_info.value) == "Name must be alphanumeric (no underscores)"


def test_config_runtime_error(bucket):
    with pytest.raises(RuntimeError) as e_info:
        bucket.storage

    assert "Working outside of application context." in str(e_info.value)


def test_config_not_init_error(app, bucket):
    with pytest.raises(AssertionError) as e_info:
        bucket.storage

    assert str(e_info.value) == (
        "The googlestorage extension was not registered to the current "
        "application. Please make sure to call init_app() first."
    )


def test_config_not_found_error(app_init):
    with pytest.raises(NotFoundBucketError) as e_info:
        bucket = Bucket("music")
        bucket.storage

    assert str(e_info.value) == "Storage for bucket 'music' not found"


def test_save_error(bucket):
    with pytest.raises(TypeError) as e_info:
        bucket.save("not a FileStorage instance")

    assert str(e_info.value) == (
        "The given storage must be a werkzeug.datastructures.FileStorage instance"
    )


@pytest.mark.parametrize("filename", ("filename.exe", "filename.txt", "filename.jpg"))
def test_bucket_save_all_allowed(filename, bucket):
    with bucket.storage_ctx(mock.MagicMock()) as storage_mock:
        bucket.save(FileStorage(filename=filename))

    storage_mock.save.assert_called_once()


@pytest.mark.parametrize("filename", ("filename.exe", "filename.txt", "filename.jpg"))
def test_bucket_save_none_allowed(filename):
    bucket = Bucket("files", allows=lambda f, p: False)
    with pytest.raises(NotAllowedUploadError) as e_info:
        bucket.save(FileStorage(filename=filename))

    assert str(e_info.value) == "The given file is not allowed in this bucket"


def test_bucket_save_images_allowed(datadir, images_bucket, local_bucket):
    orig_file = datadir / "flask.jpg"
    uploaded_file = local_bucket.destination / "flask.jpg"

    assert not uploaded_file.exists()
    with images_bucket.storage_ctx(local_bucket):
        images_bucket.save(FileStorage(orig_file.open("rb")), name="flask.jpg")

    assert uploaded_file.exists()
    assert uploaded_file.read_bytes() == orig_file.read_bytes()

    with pytest.raises(NotAllowedUploadError) as e_info:
        images_bucket.save(FileStorage((datadir / "foo.zip").open("rb")), name="foo.jpg")

    assert str(e_info.value) == "Custom validation error message"


@pytest.mark.parametrize(
    "filename, allowed", [("filename.exe", False), ("filename.txt", True), ("filename.jpg", True)]
)
def test_bucket_allows_by_extension(filename, allowed, empty_txt):
    bucket = Bucket("files", allows=lambda f, p: p.suffix != ".exe")
    assert bucket.allows(empty_txt, pathlib.PurePath(filename)) == allowed


def test_storage_mocking(bucket):
    with bucket.storage_ctx(mock.MagicMock()) as storage_mock:
        assert bucket.storage is storage_mock


@pytest.mark.parametrize(
    "uuid_name, public", [(True, True), (False, True), (True, False), (False, False)]
)
def test_bucket_save(uuid_name, public, empty_txt, bucket):
    secured_path = pathlib.PurePath("secured.txt")
    with bucket.storage_ctx(mock.MagicMock()) as storage_mock:
        storage_mock.save.side_effect = lambda fs, path, public: path
        with mock.patch("flask_googlestorage.buckets.secure_path", mock.MagicMock()) as secure_path:
            secure_path.return_value = secured_path
            bucket.save(empty_txt, name="bar.txt", uuid_name=uuid_name, public=public)

    secure_path.assert_called_with("empty.txt", "bar.txt", uuid_name)
    storage_mock.save.assert_called_with(empty_txt, secured_path, public=public)


def test_bucket_delete(bucket):
    with bucket.storage_ctx(mock.MagicMock()) as storage_mock:
        bucket.delete("bar.txt")

    storage_mock.delete.assert_called_with("bar.txt")


def test_bucket_url(bucket):
    with bucket.storage_ctx(mock.MagicMock()) as storage_mock:
        bucket.url("bar.txt")

    storage_mock.url.assert_called_with("bar.txt")


def test_bucket_signed_url(bucket):
    with bucket.storage_ctx(mock.MagicMock()) as storage_mock:
        bucket.signed_url("bar.txt")

    storage_mock.signed_url.assert_called_with("bar.txt")


@pytest.mark.parametrize("path", ("foo.txt", "foo/file.txt", "foo/bar/file.tx"))
def test_local_save(path, empty_txt, local_bucket):
    path = pathlib.PurePath(path)

    assert local_bucket.save(empty_txt, path) == path
    assert (local_bucket.destination / path).exists()


@pytest.mark.parametrize(
    "resolve, path, expected",
    [
        (True, "foo.txt", "foo_1.txt"),
        (False, "foo.txt", "foo.txt"),
        (True, "foo/foo.txt", "foo/foo_1.txt"),
        (False, "foo/foo.txt", "foo/foo.txt"),
        (True, "foo/bar/foo.txt", "foo/bar/foo_1.txt"),
        (False, "foo/bar/foo.txt", "foo/bar/foo.txt"),
    ],
)
def test_local_save_conflict(resolve, path, expected, empty_txt, local_bucket):
    path = pathlib.PurePath(path)

    if path.parent.parts:
        (pathlib.Path(local_bucket.destination) / path.parent).mkdir(exist_ok=True, parents=True)

    foo = pathlib.Path(local_bucket.destination) / path
    foo.touch()

    local_bucket.resolve_conflicts = resolve

    assert local_bucket.save(empty_txt, path) == pathlib.PurePath(expected)


@pytest.mark.parametrize(
    "resolve, path, expected",
    [
        (True, "foo", "foo_6"),
        (False, "foo", "foo"),
        (True, "foo.txt", "foo_6.txt"),
        (False, "foo.txt", "foo.txt"),
    ],
)
def test_local_save_multi_conflict(resolve, path, expected, empty_txt, local_bucket):
    path = pathlib.PurePath(path)
    foo = pathlib.Path(local_bucket.destination) / path
    foo.touch()
    for n in range(1, 6):
        foo_n = pathlib.Path(local_bucket.destination) / f"foo_{n}.txt"
        foo_n.touch()

    local_bucket.resolve_conflicts = resolve
    local_bucket.save(empty_txt, path) == pathlib.PurePath(expected)


def test_local_delete(local_bucket):
    foo = local_bucket.destination / "foo.txt"
    foo.touch()

    assert foo.exists()
    local_bucket.delete("foo.txt")
    assert not foo.exists()


def test_local_delete_not_exists(local_bucket):
    foo = local_bucket.destination / "foo.txt"

    assert not foo.exists()
    local_bucket.delete("foo.txt")


@pytest.mark.parametrize("file, content", [("foo.txt", "Foo content"), ("bar.txt", "Bar content")])
def test_local_download(file, content, app_local):
    with app_local.test_client() as client:
        rv = client.get(f"/_uploads/files/{file}")
        assert rv.status_code == 200
        assert rv.get_data(as_text=True) == content


@pytest.mark.parametrize("url", ("/_uploads/files/biz.txt", "/_uploads/photos/foo.jpg"))
def test_local_download_not_found(url, app_local):
    with app_local.test_client() as client:
        rv = client.get(url)
        assert rv.status_code == 404


def test_local_url(app_local, local_bucket):
    with app_local.test_request_context():
        url = local_bucket.url("foo.txt")

        assert url == url_for("files_uploads.download_file", filename="foo.txt", _external=True)
        assert url == local_bucket.signed_url("foo.txt")


@pytest.mark.parametrize("path, delete_local", [("empty.txt", True), ("files/empty.txt", False)])
def test_cloud_save(path, delete_local, empty_txt, cloud_bucket):
    cloud_bucket.delete_local = delete_local
    path = pathlib.PurePath(path)
    res = cloud_bucket.save(empty_txt, path)
    assert res == path

    if delete_local:
        assert not (cloud_bucket.local.destination / path).exists()
    else:
        assert (cloud_bucket.local.destination / path).exists()


@pytest.mark.parametrize("public", (True, False))
def test_cloud_save_public(public, google_bucket_mock, empty_txt, cloud_bucket):
    cloud_bucket.save(empty_txt, pathlib.PurePath("foo.txt"), public=public)
    if public:
        google_bucket_mock.get_blob("foo.txt").make_public.assert_called_once()
    else:
        google_bucket_mock.get_blob("foo.txt").make_public.assert_not_called()


def test_cloud_delete(cloud_bucket, google_bucket_mock):
    cloud_bucket.delete("foo.txt")
    google_bucket_mock.get_blob("foo.txt").delete.assert_called_once()

    cloud_bucket.delete("bar.txt")


def test_cloud_url(app_cloud, cloud_bucket):
    with app_cloud.test_request_context():
        assert cloud_bucket.url("foo.txt") == "http://google-storage-url/foo.txt"
        assert cloud_bucket.url("bar.txt") is None


def test_cloud_signed_url(app_cloud, cloud_bucket):
    with app_cloud.test_request_context():
        assert cloud_bucket.signed_url("foo.txt") == "http://google-storage-signed-url/foo.txt"
        assert cloud_bucket.signed_url("bar.txt") is None


@pytest.mark.parametrize("name", ("files", "photos"))
def test_cloud_save_default(name, app_cloud_default, tmpdir, empty_txt):
    filepath = pathlib.Path(tmpdir) / name / "empty.txt"

    assert not filepath.exists()
    bucket = Bucket(name)
    bucket.save(empty_txt, name="empty.txt")
    if name == "photos":
        assert filepath.exists()
    else:
        assert not filepath.exists()


@pytest.mark.parametrize("name", ("files", "photos"))
def test_cloud_save_retry(name, app_cloud_retry, tmpdir, empty_txt, google_bucket_error_mock):
    filepath = pathlib.Path(tmpdir) / name / "empty.txt"

    assert not filepath.exists()

    bucket = Bucket(name)
    if name == "photos":
        with pytest.raises(GoogleCloudError):
            bucket.save(empty_txt)

        calls = [mock.call(filepath), mock.call(filepath)]
        assert google_bucket_error_mock.get_blob().upload_from_filename.call_count == 2
        assert google_bucket_error_mock.get_blob().upload_from_filename.has_calls(calls)
    else:
        bucket.save(empty_txt)

        calls = [mock.call(filepath), mock.call(filepath), mock.call(filepath)]
        assert google_bucket_error_mock.get_blob().upload_from_filename.call_count == 3
        assert google_bucket_error_mock.get_blob().upload_from_filename.has_calls(calls)


@pytest.mark.parametrize("file, content", [("foo.txt", "Foo content"), ("bar.txt", "Bar content")])
def test_cloud_download(file, content, app_cloud):
    with app_cloud.test_client() as client:
        rv = client.get(f"/_uploads/files/{file}")
        assert rv.status_code == 200
        assert rv.get_data(as_text=True) == content
