from distutils.core import setup
from setuptools import find_packages


desc = """Declarative processing, transforming, and validating of data.

New in 1.0.4:
-   Fixed process.Trickler iteration to not be internally recursive, sometimes
    throwing stack overflow errors on long waits.
"""

kwargs = {
    "name": "fulford.data",
    "description": desc,
    "author": "James Patrick Fulford",
    "author_email": "james.patrick.fulford@gmail.com",
    "url": "https://github.com/jamesfulford/fulford.data",
    "license": "Apache-2.0",

    "version": "1.0.4",

    "packages": find_packages()
}

setup(
    **kwargs
)
