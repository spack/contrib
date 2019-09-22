# Copyright 2017-2019 Lawrence Livermore National Security, LLC and other
# Hatchet Project Developers. See the top-level LICENSE file for details.
#
# SPDX-License-Identifier: MIT

from setuptools import setup
from os import path

here = path.abspath(path.dirname(__file__))

setup(
    name="contrib",
    version="0.1.0",
    description=(
        "A python package for making stacked area plots of contributions over time."
    ),
    url="https://github.com/spack/contrib",
    author="Todd Gamblin",
    author_email="tgamblin@llnl.gov",
    license="Apache-2.0 OR MIT",
    classifiers=["Development Status :: 3 - Alpha"],
    keywords="",
    packages=["contrib", "contrib.config"],
    install_requires=[
        "python-dateutil",
        "jsonschema",
        "matplotlib",
        "pyyaml",
        "setuptools",
    ],
)
