from typing import Tuple
from pathlib import Path
from dataclasses import dataclass

from google.cloud.storage import Bucket


@dataclass
class UploadConfiguration:
    """
    This holds the configuration for a single `UploadSet`. The constructor's
    arguments are also the attributes.

    :param destination: The directory to save files to.
    :param base_url: The URL (ending with a /) that files can be downloaded
                     from. If this is `None`, Flask-Uploads will serve the
                     files itself.
    :param allow: Tuple of extensions to allow, even if they're not in the `UploadSet` extensions.
    :param deny: Tuple of extensions to deny, even if they are in the `UploadSet` extensions.
    :param bucket: Google cloud storage bucket object for the `UploadSet`
    """

    destination: Path
    base_url: str = None
    allow: Tuple[str, ...] = ()
    deny: Tuple[str, ...] = ()
    bucket: Bucket = None
