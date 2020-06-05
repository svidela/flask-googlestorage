# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

from pallets_sphinx_themes import get_version
from pallets_sphinx_themes import ProjectLink

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
# import os
# import sys
# sys.path.insert(0, os.path.abspath('.'))


# -- Project information -----------------------------------------------------

project = "Flask-GoogleStorage"
copyright = "2020, Santiago Videla"
author = "Santiago Videla"
release, version = get_version("Flask-GoogleStorage")


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "pallets_sphinx_themes",
    "sphinx_issues",
]

intersphinx_mapping = {
    "python": ("https://docs.python.org/3/", None),
    "flask": ("http://flask.pocoo.org/docs/", None),
    "google-cloud-storage": ("https://googleapis.dev/python/storage/latest/index.html", None),
}
issues_github_path = "svidela/flask-googlestorage"

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "flask"
html_theme_options = {"index_sidebar_logo": False}
html_context = {
    "project_links": [
        ProjectLink("Flask Website", "https://palletsprojects.com/p/flask/"),
        ProjectLink("PyPI releases", "https://pypi.org/project/Flask-GoogleStorage/"),
        ProjectLink("Source Code", "https://github.com/svidela/flask-googlestorage/"),
        ProjectLink("Issue Tracker", "https://github.com/svidela/flask-googlestorage/issues/"),
    ]
}
html_title = f"Flask-GoogleStorage Documentation ({version})"
html_show_sourcelink = False

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]
