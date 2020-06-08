from setuptools import setup, find_packages

# Get the long description from the README file
with open("README.rst", encoding="utf-8") as f:
    long_description = f.read()


setup(
    name="Flask-GoogleStorage",
    version="0.1.0",
    url="https://github.com/svidela/flask-googlestorage",
    license="MIT",
    author="Santiago Videla",
    author_email="santiago.videla@gmail.com",
    description="Google Cloud Storage for Flask",
    long_description=long_description,
    packages=find_packages(exclude=["tests*"]),
    python_requires=">=3.6",
    platforms="any",
    install_requires=["flask>=1.1.0", "google-cloud-storage>=1.28.1", "tenacity>=6.2.0"],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Internet :: WWW/HTTP",
        "Environment :: Web Environment",
        "Framework :: Flask",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
    keywords=["flask", "google", "cloud" "storage"],
)
