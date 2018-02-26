from distutils.core import setup

desc = "Declarative processing, transforming, and validating of data."

kwargs = {
    "name": "fulford.data",
    "description": desc,
    "author": "James Patrick Fulford",
    "author_email": "james.patrick.fulford@gmail.com",
    "url": "https://github.com/jamesfulford/fulford.data",
    "license": "Apache-2.0",

    "version": "1.0.0",

    "packages": ["fulforddata"],
}

setup(
    **kwargs
)
