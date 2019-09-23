# Copyright 2013-2019 Lawrence Livermore National Security, LLC and other
# Spack Project Developers. See the top-level COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)

import os.path

from contrib.config import ContribConfig


def test_read_config(config_dir):
    config_file = config_dir.join("contrib.yaml")
    config_file.check(file=1)
    config_dir.join("authors.json").check(file=1)

    config = ContribConfig(str(config_file))
    config_dir = os.path.normpath(os.path.dirname(str(config_file)))
    assert config.repo == os.path.normpath(os.path.join(config_dir, "./spack"))

    assert config.orgmap == {
        "Author 1": "Org 1",
        "Author 2": "Org 2",
        "Author 3": "Org 3",
    }
    assert config.orgmap_file == os.path.normpath(
        os.path.join(config_dir, "author-to-org.json")
    )
    assert config.parts == {
        "packages": ["^pkg_regex_1$", "^pkg_regex_2$", "^pkg_regex_3$"],
        "core": ["^core_regex_1$", "^core_regex_2$", "^core_regex_3$"],
    }


def test_read_config_no_parts(config_dir):
    config_file = config_dir.join("contrib-no-parts.yaml")
    config_file.check(file=1)

    config = ContribConfig(str(config_file))
    config_dir = os.path.normpath(os.path.dirname(str(config_file)))
    assert config.repo == os.path.normpath(os.path.join(config_dir, "./spack"))

    assert config.orgmap is None
    assert config.parts == {"all": r"^.*\.py$"}
