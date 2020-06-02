from flask import Blueprint, current_app, send_from_directory, abort


bp = Blueprint("_uploads", __name__, url_prefix="/_uploads")


@bp.route("/<name>/<path:filename>")
def download_file(name, filename):
    config = current_app.extensions["flask-google-storage"]["config"].get(name)
    if config is None:
        abort(404)

    return send_from_directory(config.destination, filename)
