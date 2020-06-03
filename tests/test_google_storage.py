from pathlib import Path

import pytest

from flask_googlestorage import GoogleStorage, Bucket
from flask_googlestorage.buckets import LocalBucket, CloudBucket
from flask_googlestorage.exceptions import NotFoundDestinationError
from flask_googlestorage.extensions import DEFAULTS
from flask_googlestorage.utils import get_state


def test_missing_conf(app):
    files = Bucket("files")
    with pytest.raises(NotFoundDestinationError) as e_info:
        GoogleStorage(files, app=app)

    assert (
        str(e_info.value) == "You must set the 'GOOGLE_STORAGE_LOCAL_DEST' configuration variable"
    )


def test_defaults(app_init):
    storage_config = get_state(app_init)["buckets"]
    assert storage_config["files"].destination == Path("/var/uploads/files")
    assert storage_config["photos"].destination == Path("/var/uploads/photos")

    assert storage_config["files"].extensions == DEFAULTS
    assert storage_config["photos"].extensions == DEFAULTS


def test_google_cloud_storage(app_cloud):
    storage_config = get_state(app_cloud)["buckets"]
    assert isinstance(storage_config["files"], CloudBucket)
    assert isinstance(storage_config["photos"], LocalBucket)
