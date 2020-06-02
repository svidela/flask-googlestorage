from pathlib import PurePath

from flask import Flask
from werkzeug.utils import secure_filename


def get_state(app: Flask) -> dict:
    """
    Gets the state for the application
    """

    assert "google-storage" in app.extensions, (
        "The google-storage extension was not registered to the current "
        "application. Please make sure to call init_app() first."
    )
    return app.extensions["google-storage"]


def secure_filename_ext(filename: str) -> PurePath:
    """
    This is a helper used by UploadSet.save to provide lowercase extensions for all processed files,
    to compare with configured extensions in the same case.

    :param filename: The filename to ensure has a lowercase extension.
    """
    ext = PurePath(filename).suffix
    secured = PurePath(secure_filename(filename))

    return secured if not ext else secured.with_suffix(ext.lower())
