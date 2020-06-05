from pathlib import PurePath

from flask import Flask
from werkzeug.utils import secure_filename


def get_state(app: Flask) -> dict:
    """
    Gets the extension state for the given application

    :param app: The :py:class:`flask.Flask` application instance
    :returns: A dictionary describing the extension state for the given application
    """

    assert "googlestorage" in app.extensions, (
        "The googlestorage extension was not registered to the current "
        "application. Please make sure to call init_app() first."
    )
    return app.extensions["googlestorage"]


def secure_filename_ext(filename: str) -> PurePath:
    """
    This is a helper used by :py:func:`flask_googlestorage.LocalBucket.save` to provide lowercase
    extensions for all processed files in order to compare them with configured extensions in the
    same case.

    :param filename: The filename to ensure has a lowercase extension.

    :returns: A secured filename with the extension in lower case
    """
    ext = PurePath(filename).suffix
    secured = PurePath(secure_filename(filename))

    return secured if not ext else secured.with_suffix(ext.lower())
