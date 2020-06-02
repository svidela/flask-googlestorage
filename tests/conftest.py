import io
import os
import pathlib
from unittest import mock

import pytest
from flask import Flask
from werkzeug.datastructures import FileStorage

from flask_googlestorage import UploadSet, GoogleStorage
from flask_googlestorage.upload_configuration import UploadConfiguration


@pytest.fixture
def app():
    app = Flask("test")
    app.config["TESTING"] = True

    ctx = app.app_context()
    ctx.push()
    yield app
    ctx.pop()


@pytest.fixture
def app_defaults(app):
    app.config.update(
        {"UPLOADS_DEFAULT_DEST": "/var/uploads", "UPLOADS_DEFAULT_URL": "http://localhost:6000/"}
    )

    files, photos = UploadSet("files"), UploadSet("photos")

    storage = GoogleStorage(files, photos)
    storage.init_app(app)

    return app


@pytest.fixture
def app_default_serve(app):
    app.config.update({"UPLOADS_DEFAULT_DEST": "/var/uploads"})

    files, photos = UploadSet("files"), UploadSet("photos")

    storage = GoogleStorage(files, photos)
    storage.init_app(app)

    return app


@pytest.fixture
def app_mixed_defaults(app):
    app.config.update(
        {
            "UPLOADS_DEFAULT_DEST": "/var/uploads",
            "UPLOADS_DEFAULT_URL": "http://localhost:6001/",
            "UPLOADED_PHOTOS_DEST": "/mnt/photos",
            "UPLOADED_PHOTOS_URL": "http://localhost:6002/",
        }
    )

    files, photos = UploadSet("files"), UploadSet("photos")

    storage = GoogleStorage(files, photos)
    storage.init_app(app)

    return app


@pytest.fixture
def app_callable_default_dest(app):
    app.config.update(
        {
            "CUSTOM": "/custom/path",
            "UPLOADED_PHOTOS_DEST": "/mnt/photos",
            "UPLOADED_PHOTOS_URL": "http://localhost:6002/",
        }
    )

    files = UploadSet("files", default_dest=lambda app: os.path.join(app.config["CUSTOM"], "files"))
    photos = UploadSet("photos")

    storage = GoogleStorage(files, photos)
    storage.init_app(app)

    return app


@pytest.fixture
def app_manual(app):
    app.config.update(
        {
            "UPLOADED_FILES_DEST": "/var/files",
            "UPLOADED_FILES_URL": "http://localhost:6001/",
            "UPLOADED_PHOTOS_DEST": "/mnt/photos",
            "UPLOADED_PHOTOS_URL": "http://localhost:6002/",
        }
    )

    files, photos = UploadSet("files"), UploadSet("photos")

    storage = GoogleStorage(files, photos)
    storage.init_app(app)

    return app


@pytest.fixture
def app_serve(app):
    app.config.update({"UPLOADED_FILES_DEST": "/var/files", "UPLOADED_PHOTOS_DEST": "/mnt/photos"})

    files, photos = UploadSet("files"), UploadSet("photos")

    GoogleStorage(files, photos, app=app)

    return app


@pytest.fixture
def app_tmp(app, tmpdir):
    app.config.update({"UPLOADED_FILES_DEST": str(tmpdir)})

    foo = pathlib.Path(tmpdir) / "foo.txt"
    foo.write_text("Foo content")

    bar = pathlib.Path(tmpdir) / "bar.txt"
    bar.write_text("Bar content")

    files = UploadSet("files")

    storage = GoogleStorage(files)
    storage.init_app(app)

    return app


@pytest.fixture
def file_storage_cls():
    def save_mock(dst, buffer_size=16384):
        FileStorage.saved = dst

    with mock.patch.object(FileStorage, "save", side_effect=save_mock):
        yield FileStorage


@pytest.fixture
def tmp_uploadset(tmpdir):
    dst = str(tmpdir)
    upload_set = UploadSet("files")
    upload_set._config = UploadConfiguration(pathlib.Path(dst))

    return upload_set


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
    client.get_bucket.return_value = google_bucket_mock

    with mock.patch("google.cloud.storage.Client", return_value=client):
        yield


@pytest.fixture
def bucket_uploadset(google_bucket_mock, tmpdir):
    dst = pathlib.Path(tmpdir)
    upload_set = UploadSet("files")
    upload_set._config = UploadConfiguration(dst, bucket=google_bucket_mock)

    return upload_set


@pytest.fixture
def app_cloud(google_storage_mock, app):
    app.config.update(
        {
            "UPLOADS_DEFAULT_DEST": "/var/uploads",
            "UPLOADED_FILES_BUCKET": "files-bucket",
            "UPLOADED_PHOTOS_BUCKET": "photos-bucket",
        }
    )

    files, photos = UploadSet("files"), UploadSet("photos")

    storage = GoogleStorage(files, photos)
    storage.init_app(app)

    return app
