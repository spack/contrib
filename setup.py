# Copyright 2017-2019 Lawrence Livermore National Security, LLC and other
# Hatchet Project Developers. See the top-level LICENSE file for details.
#
# SPDX-License-Identifier: MIT

import setuptools
from os import path

here = path.abspath(path.dirname(__file__))
with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="contrib",
    version="0.1.0",
    author="Todd Gamblin",
    author_email="tgamblin@llnl.gov",
    description=(
        "A python package for making stacked area plots of contributions over time."
    ),
    url="https://github.com/spack/contrib",
    long_description=long_description,
    long_description_content_type="text/markdown",
    license="Apache-2.0 OR MIT",
    classifiers=["Development Status :: 3 - Alpha"],
    keywords="",
    packages=setuptools.find_packages(),
    python_requires=">=3.6",
    install_requires=[
        "python-dateutil",
        "jsonschema",
        "matplotlib",
        "pyyaml",
        "setuptools",
    ],
)
