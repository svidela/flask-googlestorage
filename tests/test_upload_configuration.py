from pathlib import Path

import pytest

from flask_googlestorage import GoogleStorage, UploadSet
from flask_googlestorage.exceptions import NotFoundDestinationError
from flask_googlestorage.upload_configuration import UploadConfiguration


def test_missing_conf(app):
    files = UploadSet("files")

    with pytest.raises(NotFoundDestinationError) as e_info:
        GoogleStorage(files, app=app)

    assert str(e_info.value) == "Destination not found for UploadSet files"


def test_manual(app_manual):
    storage_config = app_manual.extensions["flask-google-storage"]["config"]
    assert storage_config["files"] == UploadConfiguration(
        Path("/var/files"), "http://localhost:6001/"
    )
    assert storage_config["photos"] == UploadConfiguration(
        Path("/mnt/photos"), "http://localhost:6002/"
    )


def test_serve(app_serve):
    storage_config = app_serve.extensions["flask-google-storage"]["config"]
    assert storage_config["files"] == UploadConfiguration(Path("/var/files"), None)
    assert storage_config["photos"] == UploadConfiguration(Path("/mnt/photos"), None)


def test_defaults(app_defaults):
    storage_config = app_defaults.extensions["flask-google-storage"]["config"]
    assert storage_config["files"] == UploadConfiguration(
        Path("/var/uploads/files"), "http://localhost:6000/files/"
    )
    assert storage_config["photos"] == UploadConfiguration(
        Path("/var/uploads/photos"), "http://localhost:6000/photos/"
    )


def test_default_serve(app_default_serve):
    storage_config = app_default_serve.extensions["flask-google-storage"]["config"]
    assert storage_config["files"] == UploadConfiguration(Path("/var/uploads/files"), None)
    assert storage_config["photos"] == UploadConfiguration(Path("/var/uploads/photos"), None)


def test_mixed_defaults(app_mixed_defaults):
    storage_config = app_mixed_defaults.extensions["flask-google-storage"]["config"]
    assert storage_config["files"] == UploadConfiguration(
        Path("/var/uploads/files"), "http://localhost:6001/files/"
    )
    assert storage_config["photos"] == UploadConfiguration(
        Path("/mnt/photos"), "http://localhost:6002/"
    )


def test_callable_default_dest(app_callable_default_dest):
    storage_config = app_callable_default_dest.extensions["flask-google-storage"]["config"]
    assert storage_config["files"] == UploadConfiguration(Path("/custom/path/files"), None)
    assert storage_config["photos"] == UploadConfiguration(
        Path("/mnt/photos"), "http://localhost:6002/"
    )


def test_google_cloud_storage(app_cloud):
    storage_config = app_cloud.extensions["flask-google-storage"]["config"]
    assert storage_config["files"].bucket
    assert storage_config["photos"].bucket
