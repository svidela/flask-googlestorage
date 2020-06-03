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

        try:
            uploads_dest = Path(self._app.config["UPLOADS_DEST"])
        except KeyError:
            raise NotFoundDestinationError("You must set the 'UPLOADS_DEST' configuration variable")

        try:
            self.client = cloud.storage.Client()
        except auth.exceptions.DefaultCredentialsError:
            app.logger.warning("Could not authenticate the Google Cloud Storage client")
            self.client = None

        app.extensions = getattr(app, "extensions", {})
        ext = app.extensions.setdefault("google-storage", {})
        ext["ext_obj"] = self
        ext["buckets"] = {}

        self.signed_url_config = app.config.get("SIGNED_URL_EXPIRATION", {"minutes": 5})

        for bucket in self.buckets:
            ext["buckets"][bucket.name] = self._create_bucket(uploads_dest, bucket)

    def _create_bucket(self, uploads_dest: Path, bucket: Bucket) -> Union[LocalBucket, CloudBucket]:
        cfg = self._app.config
        prefix = f"UPLOADED_{bucket.name.upper()}_"

        destination = uploads_dest / bucket.name
        allow = tuple(cfg.get(prefix + "ALLOW", ()))
        deny = tuple(cfg.get(prefix + "DENY", ()))
        extensions = tuple(ext for ext in bucket.extensions + allow if ext not in deny)
        resolve_conflicts = cfg.get(prefix + "RESOLVE_CONFLICTS", False)

        cloud_bucket = None
        bucket_name = cfg.get(prefix + "BUCKET")
        if self.client and bucket_name:
            delete_local = cfg.get(prefix + "DELETE_LOCAL", True)
            try:
                google_bucket = self.client.get_bucket(bucket_name)
                cloud_bucket = CloudBucket(
                    bucket.name,
                    google_bucket,
                    destination,
                    extensions,
                    resolve_conflicts,
                    delete_local,
                )

                return cloud_bucket
            except cloud.exceptions.NotFound:
                self._app.logger.warning(f"Could not found the bucket for {bucket.name}")

        local_bucket = LocalBucket(bucket.name, destination, extensions, resolve_conflicts)

        return local_bucket
