from pathlib import Path
from typing import Tuple

from flask import Flask
from google import auth, cloud

from .blueprint import bp
from .exceptions import NotFoundDestinationError
from .upload_set import UploadSet
from .upload_configuration import UploadConfiguration


class GoogleStorage:
    def __init__(self, *upload_sets: Tuple[UploadSet, ...], app: Flask = None):
        self.upload_sets = upload_sets

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
        ext = app.extensions.setdefault("flask-google-storage", {})
        ext["ext_obj"] = self
        ext["config"] = {}

        self.signed_url_config = app.config.get("SIGNED_URL_EXPIRATION", {"minutes": 5})

        for uset in self.upload_sets:
            config = self._configure_upload_set(uploads_dest, uset)
            ext["config"][uset.name] = config

        if any(s.bucket is None for s in ext["config"].values()):
            app.register_blueprint(bp)

    def _configure_upload_set(self, uploads_dest: Path, uset: UploadSet) -> UploadConfiguration:
        cfg = self._app.config

        prefix = f"UPLOADED_{uset.name.upper()}_"

        allow_extns = tuple(cfg.get(prefix + "ALLOW", ()))
        deny_extns = tuple(cfg.get(prefix + "DENY", ()))

        bucket = None
        bucket_name = cfg.get(prefix + "BUCKET")
        if self.client and bucket_name:
            try:
                bucket = self.client.get_bucket(bucket_name)
            except cloud.exceptions.NotFound:
                self._app.logger.warning(f"Could not found the bucket for {uset.name}")

        return UploadConfiguration(uploads_dest / uset.name, allow_extns, deny_extns, bucket)
