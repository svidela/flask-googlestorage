import base64
import hashlib
from contextlib import contextmanager
from typing import Union, Tuple
from pathlib import PurePath, Path

from flask import current_app, url_for
from google.cloud import storage
from google.cloud.exceptions import GoogleCloudError
from tenacity import retry, retry_if_exception_type
from werkzeug.datastructures import FileStorage

from .exceptions import NotFoundBucketError, NotAllowedUploadError
from .extensions import DEFAULTS
from .utils import get_state, secure_path


class LocalBucket:
    def __init__(
        self, name: str, destination: Path, resolve_conflicts: bool = False,
    ):
        self.name = name
        self.destination = destination
        self.resolve_conflicts = resolve_conflicts

    def url(self, filename: str) -> str:
        return url_for(f"{self.name}_uploads.download_file", filename=filename, _external=True)

    signed_url = url

    def save(self, storage: FileStorage, path: PurePath, **kwargs) -> PurePath:
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
        filepath = self.destination / filename
        if filepath.is_file():
            filepath.unlink()


class CloudBucket:
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
        self.bucket = bucket
        self.delete_local = delete_local
        self.signature = signature or {}
        self.tenacity = tenacity or {}
        self.local = LocalBucket(name, destination, resolve_conflicts=resolve_conflicts)

    def get_blob(self, name):
        return self.bucket.get_blob(name)

    def url(self, name: str) -> str:
        return self.get_blob(name).public_url

    def signed_url(self, name: str) -> str:
        return self.get_blob(name).generate_signed_url(**self.signature)

    def save(self, storage: FileStorage, path: PurePath, public: bool = False) -> PurePath:
        path = self.local.save(storage, path)
        filepath = self.local.destination / path

        blob = self.bucket.blob(str(path))
        md5_hash = hashlib.md5(filepath.read_bytes())
        blob.md5_hash = base64.b64encode(md5_hash.digest()).decode()

        try:
            if self.tenacity:
                retry(
                    reraise=True, retry=retry_if_exception_type(GoogleCloudError), **self.tenacity
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
        blob = self.get_blob(name)
        if blob:
            blob.delete()

        self.local.delete(name)


class Bucket:
    def __init__(self, name: str, extensions: Tuple[str, ...] = DEFAULTS):
        if not name.isalnum():
            raise ValueError("Name must be alphanumeric (no underscores)")

        self.name = name
        self.extensions = extensions
        self._storage = None

    @contextmanager
    def storage_ctx(self, storage: Union[LocalBucket, CloudBucket]):
        self._storage = storage
        yield storage
        self._storage = None

    @property
    def storage(self) -> Union[LocalBucket, CloudBucket]:
        if self._storage:
            return self._storage

        cfg = get_state(current_app)["buckets"]
        try:
            return cfg[self.name]
        except KeyError:
            raise NotFoundBucketError(f"Storage for bucket '{self.name}' not found")

    def allows(self, path: PurePath, storage: FileStorage) -> bool:
        return path.suffix[1:] in self.extensions

    def save(
        self,
        file_storage: FileStorage,
        name: str = None,
        public: bool = False,
        uuid_name: bool = True,
    ) -> PurePath:
        if not isinstance(file_storage, FileStorage):
            raise TypeError("The given storage must be a werkzeug.FileStorage instance")

        secured_path = secure_path(file_storage.filename, name, uuid_name)

        if not self.allows(secured_path, file_storage):
            raise NotAllowedUploadError("The given file extension is not allowed")

        return self.storage.save(file_storage, secured_path, public=public)

    def delete(self, filename: str):
        return self.storage.delete(filename)

    def url(self, filename: str) -> str:
        return self.storage.url(filename)

    def signed_url(self, filename: str) -> str:
        return self.storage.signed_url(filename)
