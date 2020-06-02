from pathlib import PurePath

from werkzeug.utils import secure_filename


def secure_filename_ext(filename: str) -> PurePath:
    """
    This is a helper used by UploadSet.save to provide lowercase extensions for
    all processed files, to compare with configured extensions in the same
    case.

    :param filename: The filename to ensure has a lowercase extension.
    """
    ext = PurePath(filename).suffix
    secured = PurePath(secure_filename(filename))

    return secured if not ext else secured.with_suffix(ext.lower())
