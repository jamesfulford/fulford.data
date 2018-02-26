from distutils.core import setup

desc = "Declarative processing, transforming, and validating of data."

kwargs = {
    "name": "fulford.data",
    "description": desc,
    "author": "James Patrick Fulford",
    "author_email": "james.patrick.fulford@gmail.com",
    "url": "https://github.com/jamesfulford/fulford.data",

    "version": "0.1.0",

    "packages": ["fulforddata"],
}

setup(
    **kwargs
)
