# Copyright 2013-2019 Lawrence Livermore National Security, LLC and other
# Spack Project Developers. See the top-level COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)

import os

import py
import pytest

import contrib.main as main


@pytest.fixture
def data_dir():
    mydir = os.path.dirname(__file__)
    path = py.path.local(os.path.join(mydir, "data"))
    yield path


@pytest.fixture
def config_dir(tmpdir, data_dir, request):
    config = data_dir.join("config")
    for f in config.listdir():
        f.copy(tmpdir)
    yield tmpdir


@pytest.fixture(autouse=True)
def repo_dir():
    old_repo_dir = main.git_repo_dir
    main.git_repo_dir = os.getcwd()
    yield
    main.git_repo_dir = old_repo_dir
