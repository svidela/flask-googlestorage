import os
from pathlib import Path
from typing import Tuple

from flask import Flask

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

        app.extensions = getattr(app, "extensions", {})
        ext = app.extensions.setdefault("flask-google-storage", {})
        ext["ext_obj"] = self
        ext["config"] = {}

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

        return UploadConfiguration(Path(destination), base_url, allow_extns, deny_extns)

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
