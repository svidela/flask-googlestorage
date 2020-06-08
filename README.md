# Flask-GoogleStorage

[![codecov](https://codecov.io/gh/svidela/flask-googlestorage/branch/master/graph/badge.svg)](https://codecov.io/gh/svidela/flask-googlestorage) ![GitHub](https://img.shields.io/github/license/svidela/flask-googlestorage) [![Documentation Status](https://readthedocs.org/projects/flask-googlestorage/badge/?version=latest)](https://flask-googlestorage.readthedocs.io/en/latest/?badge=latest)

Flask-GoogleStorage provides file uploads to Google Cloud Storage for [Flask](https://palletsprojects.com/p/flask/)

## Installation

```sh
pip install git+https://github.com/svidela/flask-googlestorage.git
```

## Documentation

Full documentation is available at <http://flask-googlestorage.readthedocs.io>

## About

This project started as a fork of [Flask-Uploads](https://github.com/maxcountryman/flask-uploads). In fact, the way in which buckets are defined and how files are saved locally before uploading them to Google Cloud was mainly inspired by the class `UploadSet` in Flask-Uploads. Although is not its main focus, this extension could be used for local storage and serve uploaded files with Flask similarly to what Flask-Uploads does. Such a feature is provided mainly to support files uploads/downloads without using Google Cloud Storage during development.

## License

MIT licensed. See the [LICENSE](https://github.com/svidela/flask-googlestorage/blob/master/LICENSE>) file for more details.
