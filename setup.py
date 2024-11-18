#!/usr/bin/env python3
# -*-coding:Utf-8 -*

# To install the package, run :  `pip install -e . `

import setuptools
import codecs


from setuptools import setup, find_packages
from distutils.util import convert_path


main_ns = {}
ver_path = convert_path('src/sshicstuff/version.py')
with open(ver_path) as ver_file:
    exec(ver_file.read(), main_ns)
__version__ = main_ns['__version__']

CLASSIFIERS = [
    "Intended Audience :: Science/Research",
    "Programming Language :: Python :: 3 :: Only",
    "Programming Language :: Python :: 3.10",
    "Topic :: Scientific/Engineering",
    "Topic :: Scientific/Engineering :: Bio-Informatics",
    "Topic :: Scientific/Engineering :: Visualization",
    "Operating System :: Unix",
    "Operating System :: MacOS",
]

NAME = "sshicstuff"

MAJOR, MINOR, MAINTENANCE = __version__.split(".")

VERSION = "{}.{}.{}".format(MAJOR, MINOR, MAINTENANCE)

LICENSE = "GPLv3"
AUTHOR = "Nicolas Mendiboure"
AUTHOR_EMAIL = "nicolas.mendiboure@ens-lyon.fr"
URL = "https://github.com/nmendiboure/ssHiCstuff"

with codecs.open("README.md", encoding="utf-8") as f:
    LONG_DESCRIPTION = f.read()

with open("requirements.txt", "r") as f:
    REQUIREMENTS = f.read().splitlines()


setuptools.setup(
    name=NAME,
    version=VERSION,
    description="A package to ananlyze the data generated by Hi-C Capture for ssDNA, extension of HiCstuff package",
    long_description=LONG_DESCRIPTION,
    license=LICENSE,
    author=AUTHOR,
    author_email=AUTHOR_EMAIL,
    url=URL,
    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src"),
    classifiers=CLASSIFIERS,
    install_requires=REQUIREMENTS,
    include_package_data=True,
    zip_safe=False,
    entry_points={
        "console_scripts":
            ["sshicstuff=sshicstuff.main:main"
             ]
    }
)
