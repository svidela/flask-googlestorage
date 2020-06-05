"""
Flask-GoogleStorage
-------------------
Flask-GoogleStorage provides flexible and efficient upload to google cloud storage
for Flask applications. It lets you divide your uploads into sets that the application
user can publish separately.

Links
`````
* `development version <https://github.com/svidela/flask-googlestorage>`_


"""
from setuptools import setup, find_packages


setup(
    name="Flask-GoogleStorage",
    version="0.1.0",
    url="https://github.com/svidela/flask-googlestorage",
    license="MIT",
    author="Santiago Videla",
    author_email="santiago.videla@gmail.com",
    description="Flexible and efficient upload to google cloud storage for Flask",
    long_description=__doc__,
    packages=find_packages(exclude=["tests*"]),
    python_requires=">=3.5",
    platforms="any",
    install_requires=["flask>=1.1.0", "google-cloud-storage>=1.28.1", "tenacity>=6.2.0"],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
)
