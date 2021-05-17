from os import path

from setuptools import setup

here = path.abspath(path.dirname(__file__))
with open(path.join(here, "README.md"), encoding="utf-8") as fp:
    long_description = fp.read()

setup(
    name="astrobotany",
    description="A plant-based app for jetforce gemini servers",
    version="0.0.1",
    license="ISC License",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/michael-lazar/astrobotany",
    author="Michael Lazar",
    author_email="lazar.michael22@gmail.com",
    keywords="gemini",
    packages=["astrobotany"],
    python_requires=">=3.7, <4",
    install_requires=[
        "jetforce",
        "peewee",
        "jinja2",
        "faker",
        "bcrypt",
        "emoji @ git+https://github.com/carpedm20/emoji.git@v.1.2.1#egg=emoji-1.2.1",
    ],
    extras_require={
        "test": ["pytest", "black", "isort", "mypy", "freezegun"],
    },
    package_data={
        "astrobotany": [
            "art/*",
            "templates/*",
            "templates/fragments/*",
            "static/*",
            "static/changes/*",
            "mail/*",
        ]
    },
)
