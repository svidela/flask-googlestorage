import uuid
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


def secure_path(filename: str, name: str = None, uuid_name: bool = True) -> PurePath:
    """
    This is a helper used by :py:func:`flask_googlestorage.Bucket.save` to get a secured path. Also,
    lowercase extensions are enforced for all processed files in order to compare them with
    configured extensions in the same case.

    :param filename: The original filename.

    :param name: A name preferred over the original filename which could contain nested folders.

    :uuid_name: If set to ``True`` a UUID name is preferred over the original filename.

    :returns: A secured filename with the extension in lower case
    """
    ext = PurePath(filename).suffix

    if name:
        path = PurePath(name)
        parent, stem, suffix = path.parent, path.stem, path.suffix
        if stem.endswith("."):
            stem = stem[:-1]

        if suffix:
            ext = suffix

        secure_parent = PurePath(*(secure_filename(part) for part in parent.parts if part != ".."))
        secure_name = secure_filename(path.name)
    else:
        secure_parent = ""
        secure_name = str(uuid.uuid4()) if uuid_name else secure_filename(filename)

    if not secure_name:
        secure_name = str(uuid.uuid4())

    return secure_parent / PurePath(secure_name).with_suffix(ext.lower())
