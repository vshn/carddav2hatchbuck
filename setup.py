"""
Packaging setup for carddav2hatchbuck
"""
from os.path import abspath, dirname, join
from setuptools import find_packages, setup

import carddav2hatchbuck as package


def read_file(filename):
    """Read the contents of a file"""
    here = abspath(dirname(__file__))
    with open(join(here, filename), encoding="utf-8") as file:
        return file.read()


setup(
    name=package.__name__,
    version=package.__version__,
    author=package.__author__,
    author_email=package.__email__,
    description=package.__doc__.strip(),
    long_description=read_file("README.md"),
    long_description_content_type="text/markdown",
    url=package.__url__,
    packages=find_packages(exclude=["tests"]),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
)
