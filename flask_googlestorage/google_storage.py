from pathlib import Path
from typing import Union, Tuple

from flask import Flask
from google import auth, cloud

from .exceptions import NotFoundDestinationError
from .buckets import LocalBucket, CloudBucket, Bucket


class GoogleStorage:
    def __init__(self, *buckets: Tuple[Bucket, ...], app: Flask = None):
        self.buckets = buckets

        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask):
        self._app = app
        self._prefix = "GOOGLE_STORAGE"

        try:
            uploads_dest = Path(self._app.config[f"{self._prefix}_LOCAL_DEST"])
        except KeyError:
            raise NotFoundDestinationError(
                "You must set the 'GOOGLE_STORAGE_LOCAL_DEST' configuration variable"
            )

        try:
            self._client = cloud.storage.Client()
        except auth.exceptions.DefaultCredentialsError:
            app.logger.warning("Could not authenticate the Google Cloud Storage client")
            self._client = None

        app.extensions = getattr(app, "extensions", {})
        ext = app.extensions.setdefault("google-storage", {})
        ext["ext_obj"] = self
        ext["buckets"] = {}

        self._resolve_conflicts = app.config.get(f"{self._prefix}_RESOLVE_CONFLICTS", False)
        self._delete_local = app.config.get(f"{self._prefix}_DELETE_LOCAL", True)
        self._signed_url = app.config.get(f"{self._prefix}_SIGNED_URL")
        self._retry = app.config.get(f"{self._prefix}_RETRY")

        for bucket in self.buckets:
            ext["buckets"][bucket.name] = self._create_bucket(uploads_dest, bucket)

    def _create_bucket(self, uploads_dest: Path, bucket: Bucket) -> Union[LocalBucket, CloudBucket]:
        cfg = self._app.config
        prefix = f"{self._prefix}_{bucket.name.upper()}"

        destination = uploads_dest / bucket.name
        allow = tuple(cfg.get(f"{prefix}_ALLOW", ()))
        deny = tuple(cfg.get(f"{prefix}_DENY", ()))
        extensions = tuple(ext for ext in bucket.extensions + allow if ext not in deny)
        resolve_conflicts = cfg.get(f"{prefix}_RESOLVE_CONFLICTS", self._resolve_conflicts)

        cloud_bucket = None
        bucket_name = cfg.get(f"{prefix}_BUCKET")
        if self._client and bucket_name:
            try:
                cloud_bucket = CloudBucket(
                    bucket.name,
                    self._client.get_bucket(bucket_name),
                    destination,
                    extensions=extensions,
                    resolve_conflicts=resolve_conflicts,
                    delete_local=cfg.get(f"{prefix}_DELETE_LOCAL", self._delete_local),
                    signed_url=cfg.get(f"{prefix}_SIGNED_URL", self._signed_url),
                    retry=cfg.get(f"{prefix}_RETRY", self._retry),
                )

                return cloud_bucket
            except cloud.exceptions.NotFound:
                self._app.logger.warning(f"Could not found the bucket for {bucket.name}")

        local_bucket = LocalBucket(bucket.name, destination, extensions, resolve_conflicts)

        return local_bucket
