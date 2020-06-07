import io
import pathlib
from unittest import mock

import pytest
from flask import Flask
from google.cloud.exceptions import NotFound, GoogleCloudError
from tenacity import wait_fixed, stop_after_attempt
from werkzeug.datastructures import FileStorage

from flask_googlestorage import (
    GoogleStorage,
    Bucket,
    LocalBucket,
    CloudBucket,
    NotAllowedUploadError,
)


@pytest.fixture
def app():
    app = Flask("test")
    app.config["TESTING"] = True

    ctx = app.app_context()
    ctx.push()
    yield app
    ctx.pop()


@pytest.fixture
def app_init(app):
    app.config.update({"GOOGLE_STORAGE_LOCAL_DEST": "/var/uploads"})

    files, photos = Bucket("files"), Bucket("photos")

    storage = GoogleStorage(files, photos)
    storage.init_app(app)

    return app


@pytest.fixture
def app_local(app, tmpdir):
    app.config.update({"GOOGLE_STORAGE_LOCAL_DEST": str(tmpdir)})

    files = Bucket("files")

    storage = GoogleStorage(files)
    storage.init_app(app)

    files.save(FileStorage(stream=io.BytesIO(b"Foo content"), filename="foo.txt"), uuid_name=False)
    files.save(FileStorage(stream=io.BytesIO(b"Bar content"), filename="bar.txt"), uuid_name=False)

    return app


@pytest.fixture
def bucket():
    return Bucket("files")


class CustomBucket(Bucket):
    def allows(self, path, storage):
        if path.suffix[1:] == "txt":
            return True
        else:
            raise NotAllowedUploadError("Custom validation error message")


@pytest.fixture
def custom_bucket():
    return CustomBucket("files")


@pytest.fixture
def local_bucket(tmpdir):
    return LocalBucket("files", pathlib.Path(tmpdir))


@pytest.fixture
def empty_txt():
    return FileStorage(io.BytesIO(), filename="empty.txt")


@pytest.fixture
def google_bucket_mock():
    bucket = mock.MagicMock()
    blob = mock.MagicMock()
    public_url = mock.PropertyMock(return_value="http://google-storage-url/foo.txt")

    type(blob).public_url = public_url
    blob.generate_signed_url.return_value = "http://google-storage-signed-url/foo.txt"

    def get_named_blob(name):
        type(blob).name = name
        return blob

    def get_blob(name):
        if name == "foo.txt":
            return blob

    bucket.blob.side_effect = get_named_blob
    bucket.get_blob.side_effect = get_blob

    return bucket


@pytest.fixture
def google_storage_mock(google_bucket_mock):
    client = mock.MagicMock()

    def get_bucket(name):
        if name == "files-bucket":
            return google_bucket_mock
        else:
            raise NotFound("Bucket not found")

    client.get_bucket.side_effect = get_bucket
    with mock.patch("google.cloud.storage.Client", return_value=client):
        yield


@pytest.fixture
def cloud_bucket(google_bucket_mock, tmpdir):
    return CloudBucket("files", google_bucket_mock, pathlib.Path(tmpdir))


@pytest.fixture
def app_cloud(google_storage_mock, app, tmpdir):
    app.config.update(
        {
            "GOOGLE_STORAGE_LOCAL_DEST": str(tmpdir),
            "GOOGLE_STORAGE_FILES_BUCKET": "files-bucket",
            "GOOGLE_STORAGE_FILES_DELETE_LOCAL": False,
            "GOOGLE_STORAGE_PHOTOS_BUCKET": "photos-bucket",
        }
    )

    files, photos = Bucket("files"), Bucket("photos")

    storage = GoogleStorage(files, photos)
    storage.init_app(app)

    files.save(FileStorage(stream=io.BytesIO(b"Foo content"), filename="foo.txt"), uuid_name=False)
    files.save(FileStorage(stream=io.BytesIO(b"Bar content"), filename="bar.txt"), uuid_name=False)

    return app


@pytest.fixture
def app_cloud_default(google_storage_mock, app, tmpdir):
    app.config.update(
        {
            "GOOGLE_STORAGE_LOCAL_DEST": str(tmpdir),
            "GOOGLE_STORAGE_FILES_BUCKET": "files-bucket",
            "GOOGLE_STORAGE_PHOTOS_BUCKET": "photos-bucket",
        }
    )

    files, photos = Bucket("files"), Bucket("photos")

    storage = GoogleStorage(files, photos)
    storage.init_app(app)

    return app


@pytest.fixture
def google_bucket_error_mock():
    bucket = mock.MagicMock()
    blob = mock.MagicMock()
    blob.upload_from_filename.side_effect = [
        GoogleCloudError("error 1"),
        GoogleCloudError("error 2"),
        None,
    ]

    def get_named_blob(name):
        type(blob).name = name
        return blob

    bucket.blob.side_effect = get_named_blob
    bucket.get_blob.return_value = blob

    return bucket


@pytest.fixture
def google_storage_error_mock(google_bucket_error_mock):
    client = mock.MagicMock()
    client.get_bucket.return_value = google_bucket_error_mock
    with mock.patch("google.cloud.storage.Client", return_value=client):
        yield


@pytest.fixture
def app_cloud_retry(google_storage_error_mock, app, tmpdir):
    app.config.update(
        {
            "GOOGLE_STORAGE_LOCAL_DEST": str(tmpdir),
            "GOOGLE_STORAGE_TENACITY": {"stop": stop_after_attempt(2)},
            "GOOGLE_STORAGE_FILES_BUCKET": "files-bucket",
            "GOOGLE_STORAGE_PHOTOS_BUCKET": "photos-bucket",
            "GOOGLE_STORAGE_FILES_TENACITY": {"stop": stop_after_attempt(4), "wait": wait_fixed(1)},
        }
    )

    files, photos = Bucket("files"), Bucket("photos")

    storage = GoogleStorage(files, photos)
    storage.init_app(app)

    return app
