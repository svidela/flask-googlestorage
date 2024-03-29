from setuptools import setup, find_packages

# Get the long description from the README file
with open("README.rst", encoding="utf-8") as f:
    long_description = f.read()


setup(
    name="Flask-GoogleStorage",
    version="0.1.2",
    url="https://github.com/svidela/flask-googlestorage",
    license="MIT",
    author="Santiago Videla",
    author_email="santiago.videla@gmail.com",
    description="Google Cloud Storage for Flask",
    long_description=long_description,
    packages=find_packages(exclude=["tests*"]),
    python_requires=">=3.8",
    platforms="any",
    install_requires=[
        "flask>=1.1.0",
        "google-cloud-storage>=2.16",
        "tenacity>=8.0.0",
    ],
    classifiers=[
        "Intended Audience :: Developers",
        "Topic :: Internet :: WWW/HTTP",
        "Environment :: Web Environment",
        "Framework :: Flask",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    keywords=["flask", "google", "cloud", "storage"],
)
