import io
import pathlib
from unittest import mock

import pytest
from flask import Flask
from google.cloud.exceptions import NotFound
from werkzeug.datastructures import FileStorage

from flask_googlestorage import GoogleStorage, Bucket
from flask_googlestorage.buckets import LocalBucket, CloudBucket


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
    app.config.update({"UPLOADS_DEST": "/var/uploads"})

    files, photos = Bucket("files"), Bucket("photos")

    storage = GoogleStorage(files, photos)
    storage.init_app(app)

    return app


@pytest.fixture
def app_tmp(app, tmpdir):
    app.config.update({"UPLOADS_DEST": str(tmpdir)})

    files = Bucket("files")

    storage = GoogleStorage(files)
    storage.init_app(app)

    files.save(FileStorage(stream=io.BytesIO(b"Foo content"), filename="foo.txt"))
    files.save(FileStorage(stream=io.BytesIO(b"Bar content"), filename="bar.txt"))

    return app


@pytest.fixture
def file_storage_cls():
    def save_mock(dst, buffer_size=16384):
        FileStorage.saved = dst

    with mock.patch.object(FileStorage, "save", side_effect=save_mock):
        yield FileStorage


@pytest.fixture
def local_bucket(tmpdir):
    return LocalBucket("files", pathlib.Path(tmpdir), register_blueprint=False)


@pytest.fixture
def empty_txt():
    return FileStorage(io.BytesIO(), filename="empty.txt")


@pytest.fixture
def google_bucket_mock():
    bucket = mock.MagicMock()
    blob = mock.MagicMock()
    public_url = mock.PropertyMock(return_value="http://google-storage-url/")

    type(blob).public_url = public_url
    blob.generate_signed_url.return_value = "http://google-storage-signed-url/"

    def get_named_blob(name):
        type(blob).name = name
        return blob

    bucket.blob.side_effect = get_named_blob
    bucket.get_blob.return_value = blob

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
            "UPLOADS_DEST": str(tmpdir),
            "UPLOADED_FILES_BUCKET": "files-bucket",
            "UPLOADED_FILES_DELETE_LOCAL": False,
            "UPLOADED_PHOTOS_BUCKET": "photos-bucket",
        }
    )

    files, photos = Bucket("files"), Bucket("photos")

    storage = GoogleStorage(files, photos)
    storage.init_app(app)

    files.save(FileStorage(stream=io.BytesIO(b"Foo content"), filename="foo.txt"))
    photos.save(FileStorage(stream=io.BytesIO(b"Photo content"), filename="img.jpg"))

    return app


@pytest.fixture
def app_cloud_default(google_storage_mock, app, tmpdir):
    app.config.update(
        {
            "UPLOADS_DEST": str(tmpdir),
            "UPLOADED_FILES_BUCKET": "files-bucket",
            "UPLOADED_PHOTOS_BUCKET": "photos-bucket",
        }
    )

    files, photos = Bucket("files"), Bucket("photos")

    storage = GoogleStorage(files, photos)
    storage.init_app(app)

    files.save(FileStorage(stream=io.BytesIO(b"Foo content"), filename="foo.txt"))
    photos.save(FileStorage(stream=io.BytesIO(b"Photo content"), filename="img.jpg"))

    return app
