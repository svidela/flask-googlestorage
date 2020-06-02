from flask import Blueprint, current_app, send_from_directory, abort


bp = Blueprint("_uploads", __name__, url_prefix="/_uploads")


@bp.route("/<setname>/<path:filename>")
def download_file(setname, filename):
    config = current_app.extensions["flask-google-storage"]["config"].get(setname)
    if config is None:
        abort(404)

    return send_from_directory(config.destination, filename)
