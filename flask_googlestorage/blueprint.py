from flask import Blueprint, current_app, send_from_directory, abort

from .utils import get_state

bp = Blueprint("_uploads", __name__, url_prefix="/_uploads")


@bp.route("/<name>/<path:filename>")
def download_file(name, filename):
    config = get_state(current_app)["config"].get(name)
    if config is None:
        abort(404)

    return send_from_directory(config.destination, filename)
