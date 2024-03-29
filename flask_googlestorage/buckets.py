import base64
import hashlib
from contextlib import contextmanager
from typing import Union, Callable
from pathlib import PurePath, Path

from flask import current_app, url_for
from google.cloud import storage
from google.cloud.exceptions import GoogleCloudError
from tenacity import retry, retry_if_exception_type
from werkzeug.datastructures import FileStorage

from .exceptions import NotFoundBucketError, NotAllowedUploadError
from .utils import get_state, secure_path


class LocalBucket:
    """
    This class represents a local bucket and is mainly used for temporary storage before uploading
    to Google Cloud Storage. However, if the authentication with Google Cloud Storage fails or the
    bucket id is not found, this class provides local storage. This is particularly useful in
    development.

    :param name: The name for this bucket.

    :param destination: The absolute path to use for local storage.

    :param resolve_conflicts: Whether to resolve name conflicts or not.
    """

    def __init__(
        self,
        name: str,
        destination: Path,
        resolve_conflicts: bool = False,
    ):
        #: The name of this bucket
        self.name = name

        #: The destination root path of this bucket
        self.destination = destination

        #: Whether to resolve name conflicts or not
        self.resolve_conflicts = resolve_conflicts

    def url(self, filename: str) -> str:
        """
        Returns the URL served by the :py:class:`flask.Flask` application.

        :param filename: The filename to be downloaded from the bucket.

        :returns: The URL to download the file.
        """
        return url_for(f"{self.name}_uploads.download_file", filename=filename, _external=True)

    signed_url = url

    def save(self, storage: FileStorage, path: PurePath, **kwargs) -> PurePath:
        """
        Save the given file in this bucket and returns its relative path

        :param storage: The file to be saved

        :param path: The relative path where to save the file in this bucket. It will be modified in
                     case of conflicts if
                     :py:attr:`flask_googlestorage.LocalBucket.resolve_conflicts` is set to
                     ``True``. Note that the path should be secured beforehand. You may use
                     :py:func:`flask_googlestorage.utils.secure_path` for this.

        :returns: The relative path where the file was saved. You may use this value to get the URL
                  or delete the file later.
        """
        (self.destination / path.parent).mkdir(parents=True, exist_ok=True)
        filepath = self.destination / path
        if self.resolve_conflicts and filepath.exists():
            stem, suffix = path.stem, path.suffix
            count = 0
            while filepath.exists():
                count += 1
                path = path.with_name(f"{stem}_{count}{suffix}")
                filepath = self.destination / path

        storage.save(filepath)
        return path

    def delete(self, filename: str):
        """
        Delete the file with the given filename if it exists.

        :param filename: The name of the file to be deleted.
        """
        filepath = self.destination / filename
        if filepath.is_file():
            filepath.unlink()


class CloudBucket:
    """
    This class represents a bucket in Google Cloud Storage. Apart from the
    :py:class:`google.cloud.storage.Bucket` instance, it takes all the arguments required and
    accepted by :py:class:`flask_googlestorage.LocalBucket` in order to create a local bucket for
    temporary storage. Uploaded files will be first saved locally using the local bucket and then
    uploaded to the cloud.

    :param name: The name for the local bucket.

    :param bucket: The bucket instance.

    :param destination: The absolute path to use for local storage.

    :param resolve_conflicts: Whether to resolve name conflicts or not when saving locally.

    :param delete_local: Whether to delete local files after uploading to the cloud.

    :param signature: A dictionary specifying the keyword arguments for building the signed url
                      using :py:func:`google.cloud.storage.blob.Blob.generate_signed_url`.

    :param tenaicy: A dictionary specifying the keyword arguments for the :py:func:`tenacity.retry`
                    decorator.
    """

    def __init__(
        self,
        name: str,
        bucket: storage.Bucket,
        destination: Path,
        resolve_conflicts: bool = False,
        delete_local: bool = True,
        signature: dict = None,
        tenacity: dict = None,
    ):
        #: The :py:class:`google.cloud.storage.Bucket` instance.
        self.bucket = bucket

        #: Whether to delete local files after uploading to the cloud.
        self.delete_local = delete_local

        #: Keyword arguments passed to :py:func:`google.cloud.storage.blob.Blob.generate_signed_url`
        self.signature = signature or {}

        #: Keyword arguments passed to :py:func:`tenacity.retry`.
        self.tenacity = tenacity or {}

        #: The :py:class:`flask_googlestorage.LocalBucket` instance used for temporary storage.
        self.local = LocalBucket(name, destination, resolve_conflicts=resolve_conflicts)

    def get_blob(self, name: str) -> storage.Blob:
        """
        Get a :py:class:`google.cloud.storage.blob.Blob` instance by name.

        :param name: The blob name.

        :returns: The :py:class:`google.cloud.storage.blob.Blob` instance.
        """
        return self.bucket.get_blob(name)

    def url(self, name: str) -> str:
        """
        Returns the public URL served by Google Cloud Storage. The blob should be publicly available
        in order to actually use this URL.

        :param name: The blob name to be downloaded from the bucket

        :returns: The public URL to download the file.
        """
        blob = self.get_blob(name)
        if blob:
            return blob.public_url

    def signed_url(self, name: str) -> str:
        """
        Returns the signed URL served by Google Cloud Storage. Use either
        ``GOOGLE_STORAGE_SIGNATURE`` (for all buckets) or ``GOOGLE_STORAGE_X_SIGNATURE`` (for bucket
        ``X``) to configure the arguments passed to
        :py:func:`google.cloud.storage.blob.Blob.generate_signed_url`.

        :param name: The blob name to be downloaded from the bucket

        :returns: The signed URL to download the file.
        """
        blob = self.get_blob(name)
        if blob:
            return blob.generate_signed_url(**self.signature)

    def save(self, storage: FileStorage, path: PurePath, public: bool = False) -> PurePath:
        """
        Save the given file in this bucket and returns its relative path

        :param storage: The file to be saved.

        :param path: The relative path where to save the file in this bucket. It may be modified
                     when calling :py:func:`flask_googlestorage.LocalBucket.save`. Note that the
                     path should be secured beforehand. You may use
                     :py:func:`flask_googlestorage.utils.secure_path` for this.

        :param public: Whether to make the uploaded file publicly available or not.

        :returns: The relative path where the file was saved.
        """
        path = self.local.save(storage, path)
        filepath = self.local.destination / path

        blob = self.bucket.blob(str(path))
        md5_hash = hashlib.md5(filepath.read_bytes())  # nosec
        blob.md5_hash = base64.b64encode(md5_hash.digest()).decode()

        try:
            if self.tenacity:
                retry(
                    reraise=True,
                    retry=retry_if_exception_type(GoogleCloudError),
                    **self.tenacity,
                )(lambda: blob.upload_from_filename(filepath))()
            else:
                blob.upload_from_filename(filepath)
        finally:
            if self.delete_local:
                filepath.unlink()

        if public:
            blob.make_public()

        return path

    def delete(self, name: str):
        """
        Delete the blob with the given name if it exists.

        :param name: The name of the blob to be deleted.
        """
        blob = self.get_blob(name)
        if blob:
            blob.delete()

        self.local.delete(name)


class Bucket:
    """
    This class represents a bucket of files with either local or cloud storage under the hood.

    :param name: The name for the bucket.

    :param allows: An optional callable to decide whether a given file is allowed in this bucket or
                   not. If given it will be called passing the file to be saved and the secured path
                   to be used.
    """

    def __init__(self, name: str, allows: Callable = None):
        if not name.isalnum():
            raise ValueError("Name must be alphanumeric (no underscores)")

        #: The name of this bucket
        self.name = name

        self._allows = allows
        self._storage = None

    @contextmanager
    def storage_ctx(self, storage: Union[LocalBucket, CloudBucket]):
        """
        Context manager to set the given storage object as the current storage for this bucket. Note
        that is your responsability to set a storage object that implements the required API. This
        is particulary useful for testing::

            bucket = Bucket("files")
            with bucket.storage_ctx(mock.MagicMock()) as storage_mock:
                assert bucket.storage is storage_mock
                bucket.save(file_storage)

            storage_mock.save.assert_called_once()

        :param storage: The storage object to be set

        :yields: The current being set
        """
        self._storage = storage
        yield storage
        self._storage = None

    @property
    def storage(self) -> Union[LocalBucket, CloudBucket]:
        """
        Returns either ``self._storage`` or the storage object for this bucket from the extension
        state for the current application instance.

        :returns: The current configured storage for this bucket
        """
        if self._storage:
            return self._storage

        cfg = get_state(current_app)["buckets"]
        try:
            return cfg[self.name]
        except KeyError:
            raise NotFoundBucketError(f"Storage for bucket '{self.name}' not found")

    def allows(self, file_storage: FileStorage, path: PurePath) -> bool:
        """
        Returns whether the given file is allowed in this bucket. By default, all files are allowed
        unless you create the bucket passing the ``allows`` parameter. In that case, it returns the
        value returned by such a callable.

        :param file_storage: The file to be saved.

        :param path: The secured path where to be used.

        :returns: Whether the file is allowed in this bucket or not.
        """
        return self._allows is None or self._allows(file_storage, path)

    def save(
        self,
        file_storage: FileStorage,
        name: str = None,
        public: bool = False,
        uuid_name: bool = True,
    ) -> PurePath:
        """
        Save the given file in this bucket and returns its relative path

        :param storage: The file to be saved.

        :param name: The relative path to be used. It could contain nested folders to be created.
                     This name will be passed to :py:func:`flask_googlestorage.utils.secure_path` to
                     ensure it's safe to use it or to get a secure version of it. If not given,
                     either a UUID name or the original filename (or a secure version of it) will be
                     used.

        :param public: Whether to make the uploaded file publicly available or not.

        :param uuid_name: If set to ``True`` and ``name`` is not give a UUID name is preferred over
                          the original filename.

        :returns: The relative path where the file was saved.

        :raises TypeError: If the given file is not an instance of
                 :py:class:`werkzeug.datastructures.FileStorage`.

        :raises NotAllowedUploadError: If the given file is not allowed in this bucket.
        """

        if not isinstance(file_storage, FileStorage):
            raise TypeError(
                "The given storage must be a werkzeug.datastructures.FileStorage instance"
            )

        secured_path = secure_path(file_storage.filename, name, uuid_name)

        if not self.allows(file_storage, secured_path):
            raise NotAllowedUploadError("The given file is not allowed in this bucket")

        return self.storage.save(file_storage, secured_path, public=public)

    def delete(self, filename: str):
        """
        Delete the file with the given name if it exists.

        :param name: The name of the file to be deleted.
        """
        self.storage.delete(filename)

    def url(self, filename: str) -> str:
        """
        Returns the public URL returned by the current storage object.

        :param name: The name of the file to be downloaded from the bucket

        :returns: The public URL to download the file.
        """
        return self.storage.url(filename)

    def signed_url(self, filename: str) -> str:
        """
        Returns the signed URL returned by the current storage object.

        :param name: The name of the file to be downloaded from the bucket

        :returns: The signed URL to download the file.
        """
        return self.storage.signed_url(filename)
