"""setup.py for packaging beiran"""
from setuptools import setup, find_packages
from beiran.version import get_version


REQUIREMENTS_PATH = 'beiran/requirements.txt'


def read_requirements(path):
    """Read requirements.txt and return a list of requirements."""
    with open(path, 'r') as file:
        reqs = file.read().splitlines()
    return reqs

def read_long_description():
    """Read a file written about long description of the package."""
    with open("README.md", "r") as file:
        long_description = file.read()
    return long_description


def find_beiran_packages():
    """Find beiran package."""
    return find_packages(
        exclude=["plugins", "doc", "helpers",]
    )

setup(
    name="beiran",
    version=get_version(component='library'),
    author="RainLab",
    author_email="info@rainlab.co.jp",
    description="A p2p package manager",
    keywords=['p2p package manager', 'system tools'],
    long_description=read_long_description(),
    long_description_content_type="text/markdown",
    url="https://beiran.io",

    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: System Administrators",
        "Topic :: System :: Software Distribution"
        "Topic :: System :: Systems Administration",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",  # ???
        "Operating System :: OS Independent",
    ],

    install_requires=read_requirements(REQUIREMENTS_PATH),
    python_requires='~=3.6',

    packages=find_beiran_packages(),
    entry_points={
        "console_scripts": [
            "beiran = beiran.__main__:main",
            "beirand = beiran.daemon.__main__:main"
        ]
    },
    data_files=[(REQUIREMENTS_PATH)],
)
