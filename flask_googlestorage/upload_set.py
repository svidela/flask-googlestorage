import base64
import hashlib
import uuid
from datetime import timedelta
from pathlib import Path, PurePath
from typing import Tuple, Union

from flask import current_app, url_for
from google import cloud
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
from werkzeug.datastructures import FileStorage

from .extensions import DEFAULTS
from .exceptions import NotAllowedUploadError, NotFoundUploadSetError
from .utils import secure_filename_ext, get_state
from .upload_configuration import UploadConfiguration


class UploadSet:
    """
    This represents a single set of uploaded files. Each upload set is independent of the others.
    This can be reused across multiple application instances, as all configuration is stored on the
    application object itself and found using `flask.current_app`.

    :param name: The name of this upload set. It defaults to ``files``, but you can pick any
                 alphanumeric name you want. (For simplicity, it's best to use a plural noun.)
    :param extensions: The extensions to allow uploading in this set. The easiest way to do this is
                       to add together the extension presets (for example, ``TEXT + DOCUMENTS +
                       IMAGES``). It can be overridden by the configuration with the
                       `UPLOADED_X_ALLOW` and `UPLOADED_X_DENY` configuration variables.
    """

    def __init__(self, name: str = "files", extensions: Tuple[str, ...] = DEFAULTS):
        if not name.isalnum():
            raise ValueError("Name must be alphanumeric (no underscores)")

        self.name = name
        self.extensions = extensions
        self._config = None

    @property
    def config(self) -> UploadConfiguration:
        """
        Returns the configuration for this `UploadSet`. Normally it will read the corresponding
        `UploadConfiguration` stored in the `flask.current_app` object unless you set another
        configuration manually.
        """
        if self._config is not None:
            return self._config

        cfg = get_state(current_app)["config"]
        try:
            return cfg[self.name]
        except KeyError:
            raise NotFoundUploadSetError(f"UploadSet {self.name} was not found")

    @config.setter
    def config(self, config: Union[UploadConfiguration, None]):
        """
        Sets the configuration object for this `UploadSet`.

        :param config: Either a `UploadConfiguration` object or None
        """
        if config and not isinstance(config, UploadConfiguration):
            raise TypeError("You must pass an 'UploadConfiguration' object")

        self._config = config

    def root(self, folder: str = None) -> Path:
        """
        Returns the root destination for this upload set given an optional folder

        :param: folder: Optional folder name
        """
        return self.config.destination if folder is None else self.config.destination / folder

    def blob(self, name: str) -> Union[cloud.storage.Blob, None]:
        """
        Returns the `google.cloud.storage.Blob` object for the given name or `None` if either the
        `UploadSet` doesn't have a bucket or the blob object is not found in the bucket.

        :param filename: The blob name
        """
        bucket = self.config.bucket
        if bucket:
            return bucket.get_blob(name)

    def url(self, filename: str) -> str:
        """
        Returns the URL for the given filename. If the corresponding blob object exists, it returns
        its public URL. Otherwise the URL served by the Flask app is returned

        :param filename: The filename to return the URL for.
        """
        blob = self.blob(filename)
        if blob:
            return blob.public_url
        else:
            return url_for(
                "_uploads.download_file", name=self.name, filename=filename, _external=True
            )

    def signed_url(self, filename: str) -> str:
        """
        Returns the signed URL for the given filename. If the corresponding blob object exists, it
        returns a signed URL using the configuration found in the configuration variable
        `SIGNED_URL_EXPIRATION`. Otherwise the (unsigned) URL served by the Flask app is returned

        :param filename: The filename to return the URL for.
        """
        blob = self.blob(filename)
        if blob:
            ext = get_state(current_app)["ext_obj"]
            return blob.generate_signed_url(timedelta(**ext.signed_url_config))
        else:
            return self.url(filename)

    def path(self, filename: str, folder: str = None) -> Path:
        """
        This returns the absolute path of a file uploaded to this set. It doesn't actually check
        whether said file exists.

        :param filename: The filename to return the path for.
        :param folder: The subfolder within the upload set previously used to save to.
        """
        return self.root(folder) / filename

    def file_allowed(self, storage: FileStorage, basename: PurePath) -> bool:
        """
        This tells whether a file is allowed. It should return `True` if the given
        `werkzeug.FileStorage` object can be saved with the given basename, and `False` if it can't.
        The default implementation just checks the extension, so you can override this if you want.

        :param storage: The `werkzeug.FileStorage` to check.
        :param basename: The basename it will be saved under.
        """
        return self.extension_allowed(basename.suffix[1:])

    def extension_allowed(self, ext: str) -> bool:
        """
        This determines whether a specific extension is allowed. It is called by `file_allowed`, so
        if you override that but still want to check extensions, call back into this.

        :param ext: The extension to check, without the dot.
        """
        return (ext in self.config.allow) or (
            ext in self.extensions and ext not in self.config.deny
        )

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type(cloud.exceptions.GoogleCloudError),
    )
    def save(
        self,
        storage: FileStorage,
        folder: str = None,
        name: str = None,
        public: bool = False,
        keep_local: bool = False,
        resolve_conflict: bool = False,
    ) -> PurePath:
        """
        This saves a `werkzeug.FileStorage` into this upload set. If the upload is not allowed, an
        `NotAllowedUploadError` error will be raised. Otherwise, the file will be saved and its name
        (including the folder) will be returned. If the `UploadSet` has a configured
        `google.cloud.storage.bucket`` this file will be uploaded to that bucket as well.

        :param storage: The uploaded file to save. :param folder: The subfolder within the upload
                        set to save to.
        :param name: The name to save the file as. If it ends with a dot, the file's extension will
                     be appended to the end. (If you are using `name`, you can include the folder in
                     the `name` instead of explicitly using `folder`, i.e. ``uset.save(file,
                     name="someguy/photo_123.")``
        :param public: Whether to mark the file as public in the bucket.
        :param keep_local: Whether to keep local file after uploading to the bucket.
        :param resolve_conflict: Whether to resolve name conflict or simply overwrite.
        """
        if not isinstance(storage, FileStorage):
            raise TypeError("The given storage must be a werkzeug.FileStorage instance")

        if folder is None and name is not None and "/" in name:
            folder, name = PurePath(name).parts

        basename = secure_filename_ext(storage.filename)

        if not self.file_allowed(storage, basename):
            raise NotAllowedUploadError("The given file extension is not allowed")

        if name:
            if name.endswith("."):
                basename = PurePath(name[:-1]).with_suffix(basename.suffix)
            else:
                basename = PurePath(name)

        root = self.root(folder)
        root.mkdir(parents=True, exist_ok=True)

        filepath = root / basename
        if resolve_conflict and filepath.exists():
            basename = self.resolve_conflict(root, basename)
            filepath = root / basename

        storage.save(filepath)
        fullname = PurePath(folder, basename) if folder else PurePath(basename)

        bucket = self.config.bucket
        if bucket:
            fullpath = self.path(fullname)
            blob_name = fullname if name else f"{uuid.uuid4()}{basename.suffix}"
            blob = bucket.blob(str(blob_name))
            fullname = PurePath(blob.name)

            try:
                md5_hash = hashlib.md5(fullpath.read_bytes())
                blob.md5_hash = base64.b64encode(md5_hash.digest()).decode()
                blob.upload_from_filename(fullpath)  # it may raise GoogleCloudError
                if public:
                    blob.make_public()
            finally:
                if not keep_local:
                    fullpath.unlink()

        return fullname

    def resolve_conflict(self, root: Path, basename: PurePath) -> PurePath:
        """
        If a file with the selected name already exists in the target folder, this method may be
        called to resolve the conflict. It should return a new basename for the file. Default
        implementation splits the name and extension and adds a suffix to the name consisting of an
        underscore and a number, and tries that until it finds one that doesn't exist.

        :param target_folder: The absolute path to the target.
        :param basename: The file's original basename.
        """
        stem, suffix = basename.stem, basename.suffix
        count = 0
        while True:
            count += 1
            new_name = basename.with_name(f"{stem}_{count}{suffix}")
            if not (root / new_name).exists():
                return new_name

    def delete(self, filename: str):
        """
        Deletes either the corresponding `google.cloud.storage.Blob` object or the local file.

        :param filename: The file name to be deleted.
        """
        blob = self.blob(filename)
        if blob:
            blob.delete()
        else:
            fullpath = self.path(filename)
            if fullpath.is_file():
                fullpath.unlink()
