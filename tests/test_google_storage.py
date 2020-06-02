from pathlib import Path

import pytest

from flask_googlestorage import GoogleStorage, UploadSet
from flask_googlestorage.exceptions import NotFoundDestinationError
from flask_googlestorage.upload_configuration import UploadConfiguration


def test_missing_conf(app):
    files = UploadSet("files")

    with pytest.raises(NotFoundDestinationError) as e_info:
        GoogleStorage(files, app=app)

    assert str(e_info.value) == "You must set the 'UPLOADS_DEST' configuration variable"


def test_defaults(app_init):
    storage_config = app_init.extensions["flask-google-storage"]["config"]
    assert storage_config["files"] == UploadConfiguration(Path("/var/uploads/files"))
    assert storage_config["photos"] == UploadConfiguration(Path("/var/uploads/photos"))


def test_google_cloud_storage(app_cloud):
    storage_config = app_cloud.extensions["flask-google-storage"]["config"]
    assert storage_config["files"].bucket
    assert storage_config["photos"].bucket is None
