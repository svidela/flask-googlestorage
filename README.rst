===================
Flask-GoogleStorage
===================


.. image:: https://img.shields.io/pypi/v/flask-googlestorage.svg
    :target: https://pypi.org/project/flask-googlestorage/
    :alt: Latest version

.. image:: https://img.shields.io/pypi/pyversions/flask-googlestorage.svg
    :target: https://pypi.org/project/flask-googlestorage/
    :alt: Python versions

.. image:: https://img.shields.io/pypi/l/flask-googlestorage.svg
    :target: https://flask-googlestorage.readthedocs.io/en/latest/license.html
    :alt: License

.. image:: https://codecov.io/gh/svidela/flask-googlestorage/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/svidela/flask-googlestorage
    :alt: Code coverage

.. image:: https://readthedocs.org/projects/flask-googlestorage/badge/
    :target: http://flask-googlestorage.readthedocs.io/
    :alt: Documentation


Flask-GoogleStorage provides file uploads to Google Cloud Storage for `Flask <https://palletsprojects.com/p/flask/>`_

Installation
============

::

    pip install flask-googlestorage


Documentation
=============

Full documentation is available at http://flask-googlestorage.readthedocs.io

About
=====

This project started as a fork of `Flask-Uploads <https://github.com/maxcountryman/flask-uploads>`_. In fact, the way in which buckets are defined and how files are saved locally before uploading them to Google Cloud was mainly inspired by the class ``UploadSet`` in Flask-Uploads. Although is not its main focus, this extension could be used for local storage and serve uploaded files with Flask similarly to what Flask-Uploads does. However, it worth noting that such a feature is provided mainly to support files uploads/downloads without using Google Cloud Storage during development.

License
=======

MIT licensed. See the `LICENSE <https://github.com/svidela/flask-googlestorage/blob/master/LICENSE>`_ file for more details.
