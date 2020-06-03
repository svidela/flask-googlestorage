import pathlib

import pytest
from flask import url_for
from google.cloud.exceptions import GoogleCloudError

from flask_googlestorage import GoogleStorage, Bucket
from flask_googlestorage.buckets import LocalBucket
from flask_googlestorage.extensions import ALL
from flask_googlestorage.exceptions import NotFoundBucketError, NotAllowedUploadError


def test_name_alnum():
    with pytest.raises(ValueError) as e_info:
        Bucket("my_files")

    assert str(e_info.value) == "Name must be alphanumeric (no underscores)"


def test_config_runtime_error():
    with pytest.raises(RuntimeError) as e_info:
        bucket = Bucket("files")
        bucket.storage

    assert "Working outside of application context." in str(e_info.value)


def test_config_not_init_error(app):
    with pytest.raises(AssertionError) as e_info:
        bucket = Bucket("files")
        bucket.storage

    assert str(e_info.value) == (
        "The google-storage extension was not registered to the current "
        "application. Please make sure to call init_app() first."
    )


def test_config_not_found_error(app_init):
    with pytest.raises(NotFoundBucketError) as e_info:
        bucket = Bucket("music")
        bucket.storage

    assert str(e_info.value) == "Storage for bucket 'music' not found"


@pytest.mark.parametrize(
    "name, expected_return",
    [
        (None, "foo.txt"),
        ("bar.txt", "bar.txt"),
        ("bar.", "bar.txt"),
        ("someguy/bar.", "someguy/bar.txt"),
        ("someguy/bar.txt", "someguy/bar.txt"),
    ],
)
def test_local_save(name, expected_return, file_storage_cls, local_bucket):
    tfs = file_storage_cls(filename="foo.txt")
    res = local_bucket.save(tfs, name=name)

    assert res == pathlib.PurePath(expected_return)
    assert tfs.saved == local_bucket.destination / pathlib.PurePath(expected_return)


def test_save_error(local_bucket):
    with pytest.raises(TypeError) as e_info:
        local_bucket.save("not a FileStorage instance")

    assert str(e_info.value) == "The given storage must be a werkzeug.FileStorage instance"


def test_save_not_allowed(file_storage_cls, local_bucket):
    with pytest.raises(NotAllowedUploadError) as e_info:
        local_bucket.save(file_storage_cls(filename="not-allowed.exe"))

    assert str(e_info.value) == "The given file extension is not allowed"


@pytest.mark.parametrize(
    "filename, expected", [("/etc/passwd", "etc_passwd"), ("../../myapp.wsgi", "myapp.wsgi")]
)
def test_secured_filename(filename, expected, file_storage_cls, tmpdir):
    dst = pathlib.Path(tmpdir)
    bucket = LocalBucket("files", dst, extensions=ALL)
    tfs = file_storage_cls(filename=filename)
    res = bucket.save(tfs)

    assert res.name == expected
    assert tfs.saved == dst / expected


def test_url_generated(app_init):
    bucket = LocalBucket("files", None)
    with app_init.test_request_context():
        url = bucket.url("foo.txt")
        gen = url_for("files_uploads.download_file", filename="foo.txt", _external=True)

        assert url == gen


@pytest.mark.parametrize("resolve, expected", [(True, "foo_1.txt"), (False, "foo.txt")])
def test_conflict(resolve, expected, file_storage_cls, local_bucket):
    tfs = file_storage_cls(filename="foo.txt")
    foo = pathlib.Path(local_bucket.destination) / "foo.txt"
    foo.touch()
    local_bucket.resolve_conflicts = resolve
    res = local_bucket.save(tfs)

    assert res.name == expected


@pytest.mark.parametrize("resolve, expected", [(True, "foo_6.txt"), (False, "foo.txt")])
def test_multi_conflict(resolve, expected, file_storage_cls, local_bucket):
    tfs = file_storage_cls(filename="foo.txt")
    foo = pathlib.Path(local_bucket.destination) / "foo.txt"
    foo.touch()
    for n in range(1, 6):
        foo_n = pathlib.Path(local_bucket.destination) / f"foo_{n}.txt"
        foo_n.touch()

    local_bucket.resolve_conflicts = resolve
    res = local_bucket.save(tfs)

    assert res.name == expected


@pytest.mark.parametrize("resolve, expected", [(True, "foo_1"), (False, "foo")])
def test_conflict_without_extension(resolve, expected, file_storage_cls, tmpdir):
    bucket = LocalBucket("files", pathlib.Path(tmpdir), extensions=(""), resolve_conflicts=resolve)

    tfs = file_storage_cls(filename="foo")
    (bucket.destination / "foo").touch()

    assert bucket.save(tfs) == pathlib.PurePath(expected)


@pytest.mark.parametrize(
    "filename, expected", [("foo.txt", True), ("boat.jpg", True), ("warez.exe", False)]
)
def test_filenames(filename, expected, file_storage_cls, local_bucket):
    tfs = file_storage_cls(filename=filename)
    assert local_bucket.file_allowed(tfs, pathlib.PurePath(filename)) == expected


def test_non_ascii_filename(file_storage_cls, local_bucket):
    tfs = file_storage_cls(filename="天安门.jpg")
    res = local_bucket.save(tfs)
    assert res.name == "jpg.jpg"
    res = local_bucket.save(tfs, name="secret.")
    assert res.name == "secret.jpg"


def test_delete_local(file_storage_cls, tmpdir):
    dst = pathlib.Path(tmpdir)
    bucket = LocalBucket("files", dst)
    foo = dst / "foo.txt"
    foo.touch()
    bucket.delete("foo.txt")

    assert not foo.exists()


@pytest.mark.parametrize("name, delete_local", [("empty.txt", True), ("files/empty.txt", False)])
def test_save_google_storage(name, delete_local, empty_txt, cloud_bucket):
    cloud_bucket.delete_local = delete_local
    res = cloud_bucket.save(empty_txt, name=name)
    assert res == pathlib.PurePath(name)
    if delete_local:
        assert not (cloud_bucket.local.destination / name).exists()
    else:
        assert (cloud_bucket.local.destination / name).exists()


@pytest.mark.parametrize("public", (True, False))
def test_save_public_google_storage(public, google_bucket_mock, empty_txt, cloud_bucket):
    cloud_bucket.save(empty_txt, public=public)
    if public:
        google_bucket_mock.get_blob().make_public.assert_called_once()
    else:
        google_bucket_mock.get_blob().make_public.assert_not_called()


def test_delete_google_storage(cloud_bucket, google_bucket_mock):
    cloud_bucket.delete("foo.txt")
    google_bucket_mock.get_blob().delete.assert_called_once()


@pytest.mark.parametrize(
    "name, url",
    [
        ("files", "http://google-storage-url/"),
        ("photos", "http://localhost/photos_uploads/foo.txt"),
    ],
)
def test_bucket_url(name, url, app_cloud):
    bucket = Bucket(name)
    with app_cloud.test_request_context():
        bucket.url("foo.txt") == url


@pytest.mark.parametrize(
    "name, url",
    [
        ("files", "http://google-storage-signed-url/"),
        ("photos", "http://localhost/photos_uploads/foo.txt"),
    ],
)
def test_bucket_signed_url(name, url, app_cloud):
    bucket = Bucket(name)
    with app_cloud.test_request_context():
        bucket.signed_url("foo.txt") == url


@pytest.mark.parametrize(
    "name, filename", [("files", "foo.txt"), ("photos", "img.jpg")],
)
def test_bucket_delete(name, filename, app_cloud, tmpdir):
    filepath = pathlib.Path(tmpdir) / name / filename

    assert filepath.exists()
    bucket = Bucket(name)
    bucket.delete(filename)
    assert not filepath.exists()


@pytest.mark.parametrize("name", ("files", "photos"))
def test_bucket_save_default(name, app_cloud_default, tmpdir, empty_txt):
    filepath = pathlib.Path(tmpdir) / name / "empty.txt"

    assert not filepath.exists()
    bucket = Bucket(name)
    bucket.save(empty_txt)
    if name == "photos":
        assert filepath.exists()
    else:
        assert not filepath.exists()


@pytest.mark.parametrize("name", ("files", "photos"))
def test_bucket_save(name, app_cloud, tmpdir, empty_txt):
    filepath = pathlib.Path(tmpdir) / name / "empty.txt"

    assert not filepath.exists()
    bucket = Bucket(name)
    bucket.save(empty_txt)
    assert filepath.exists()


@pytest.mark.parametrize("name", ("files", "photos"))
def test_bucket_save_retry(name, app_cloud_retry, tmpdir, empty_txt, google_bucket_error_mock):
    filepath = pathlib.Path(tmpdir) / name / "empty.txt"

    assert not filepath.exists()

    bucket = Bucket(name)
    if name == "photos":
        with pytest.raises(GoogleCloudError):
            bucket.save(empty_txt)

        assert google_bucket_error_mock.get_blob().upload_from_filename.call_count == 2
    else:
        bucket.save(empty_txt)
        assert google_bucket_error_mock.get_blob().upload_from_filename.call_count == 3


@pytest.mark.parametrize("file, content", [("foo.txt", "Foo content"), ("bar.txt", "Bar content")])
def test_get_file(file, content, app_tmp):
    with app_tmp.test_client() as client:
        rv = client.get(f"/_uploads/files/{file}")
        assert rv.status_code == 200
        assert rv.get_data(as_text=True) == content


@pytest.mark.parametrize("url", ("/_uploads/files/biz.txt", "/_uploads/photos/foo.jpg"))
def test_get_file_not_found(url, app_tmp):
    with app_tmp.test_client() as client:
        rv = client.get(url)
        assert rv.status_code == 404


@pytest.mark.parametrize("url", ("/files/foo.txt", "/photos/img.jpg"))
def test_get_file_keeped(url, app_cloud):
    with app_cloud.test_client() as client:
        rv = client.get(url)
        assert rv.status_code == 404


def test_storage_mocking(app, local_bucket):
    app.config.update({"GOOGLE_STORAGE_LOCAL_DEST": "/var/uploads"})

    files = Bucket("files")

    storage = GoogleStorage(files)
    storage.init_app(app)

    assert files.storage.destination == pathlib.Path("/var/uploads/files")
    with files.storage_ctx(local_bucket):
        assert files.storage is local_bucket

    assert files.storage.destination == pathlib.Path("/var/uploads/files")
