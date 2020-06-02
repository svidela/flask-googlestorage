import os
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
            config = self._configure_upload_set(uset)
            ext["config"][uset.name] = config

        if any(s.base_url is None for s in ext["config"].values()):
            app.register_blueprint(bp)

    def _configure_upload_set(self, uset: UploadSet) -> UploadConfiguration:
        cfg = self._app.config

        prefix = f"UPLOADED_{uset.name.upper()}_"
        allow_extns = tuple(cfg.get(prefix + "ALLOW", ()))
        deny_extns = tuple(cfg.get(prefix + "DENY", ()))

        destination = cfg.get(prefix + "DEST")
        base_url = cfg.get(prefix + "URL")
        if destination is None:
            destination, default_config = self._default_destination(uset)
            if base_url is None and default_config:
                base_url = self._default_base_url(uset)

        bucket = None
        if self.client:
            bucket_name = cfg.get(prefix + "BUCKET")
            try:
                bucket = self.client.get_bucket(bucket_name)
            except cloud.exceptions.NotFound:
                self._app.logger.warning(f"Could not found the bucket for {uset.name}")

        return UploadConfiguration(Path(destination), base_url, allow_extns, deny_extns, bucket)

    def _default_destination(self, uset: UploadSet) -> str:
        if uset.default_dest:
            return uset.default_dest(self._app), False
        else:
            try:
                return os.path.join(self._app.config["UPLOADS_DEFAULT_DEST"], uset.name), True
            except KeyError:
                raise NotFoundDestinationError(f"Destination not found for UploadSet {uset.name}")

    def _default_base_url(self, uset: UploadSet) -> str:
        try:
            return self._app.config["UPLOADS_DEFAULT_URL"] + uset.name + "/"
        except KeyError:
            pass
