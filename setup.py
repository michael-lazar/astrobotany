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
    python_requires=">=3.10, <4",
    install_requires=[
        "jetforce",
        "peewee",
        "jinja2",
        "faker",
        "bcrypt",
        "emoji>=2",
        "MIDIUtil",
    ],
    extras_require={
        "test": [
            "pytest",
            "black",
            "isort",
            "mypy",
            "freezegun",
            "types-emoji",
            "types-freezegun",
        ],
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
    entry_points={
        "console_scripts": [
            "astrobotany-tasks=astrobotany.tasks:main",
        ]
    },
)
