import base64
import hashlib
import uuid
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
from .utils import get_state, secure_filename_ext


class LocalBucket:
    def __init__(
        self,
        name: str,
        destination: Path,
        extensions: Tuple[str, ...] = DEFAULTS,
        resolve_conflicts: bool = False,
    ):
        self.name = name
        self.destination = destination
        self.extensions = extensions
        self.resolve_conflicts = resolve_conflicts

    def root(self, folder: str = None) -> Path:
        return self.destination if folder is None else self.destination / folder

    def url(self, filename: str) -> str:
        return url_for(f"{self.name}_uploads.download_file", filename=filename, _external=True)

    signed_url = url

    def file_allowed(self, storage: FileStorage, basename: PurePath) -> bool:
        return basename.suffix[1:] in self.extensions

    def save(self, storage: FileStorage, name: str = None, **kwargs) -> PurePath:
        if not isinstance(storage, FileStorage):
            raise TypeError("The given storage must be a werkzeug.FileStorage instance")

        folder = None
        if name is not None and "/" in name:
            # TODO: We could handle nested folders
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
        if self.resolve_conflicts and filepath.exists():
            stem, suffix = basename.stem, basename.suffix
            count = 0
            while filepath.exists():
                count += 1
                basename = basename.with_name(f"{stem}_{count}{suffix}")
                filepath = root / basename

        storage.save(filepath)
        return PurePath(folder, basename) if folder else PurePath(basename)

    def delete(self, filename: str):
        filepath = self.root() / filename
        if filepath.is_file():
            filepath.unlink()


class CloudBucket:
    def __init__(
        self,
        name: str,
        bucket: storage.Bucket,
        destination: Path,
        extensions: Tuple[str, ...] = DEFAULTS,
        resolve_conflicts: bool = False,
        delete_local: bool = True,
        signature: dict = None,
        tenacity: dict = None,
    ):
        self.bucket = bucket
        self.delete_local = delete_local
        self.signature = signature or {}
        self.tenacity = tenacity or {}
        self.local = LocalBucket(
            name, destination, extensions=extensions, resolve_conflicts=resolve_conflicts
        )

    def get_blob(self, name):
        return self.bucket.get_blob(name)

    def url(self, filename: str) -> str:
        return self.get_blob(filename).public_url

    def signed_url(self, filename: str) -> str:
        return self.get_blob(filename).generate_signed_url(**self.signature)

    def save(self, storage: FileStorage, name: str = None, public: bool = False) -> PurePath:
        filename = self.local.save(storage, name=name)
        filepath = self.local.root() / filename

        blob_name = str(filename) if name else f"{uuid.uuid4()}{filename.suffix}"
        blob = self.bucket.blob(blob_name)
        md5_hash = hashlib.md5(filepath.read_bytes())
        blob.md5_hash = base64.b64encode(md5_hash.digest()).decode()

        try:
            if self.tenacity:
                retry(
                    reraise=True, retry=retry_if_exception_type(GoogleCloudError), **self.tenacity
                )(lambda: blob.upload_from_filename(filename))()
            else:
                blob.upload_from_filename(filepath)
        finally:
            if self.delete_local:
                filepath.unlink()

        if public:
            blob.make_public()

        return PurePath(blob.name)

    def delete(self, filename: str):
        blob = self.get_blob(filename)
        if blob:
            blob.delete()

        self.local.delete(filename)


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
        yield
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

    def save(self, file_storage: FileStorage, name: str = None, public: bool = False) -> PurePath:
        return self.storage.save(file_storage, name=name, public=public)

    def delete(self, filename: str):
        return self.storage.delete(filename)

    def url(self, filename: str) -> str:
        return self.storage.url(filename)

    def signed_url(self, filename: str) -> str:
        return self.storage.signed_url(filename)
