# Copyright 2013-2019 Lawrence Livermore National Security, LLC and other
# Spack Project Developers. See the top-level COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)

import collections
import os
import re

import pytest

import contrib.main as main


def test_die(capsys):
    with pytest.raises(SystemExit):
        main.die("foobar")
    output = capsys.readouterr()
    assert "foobar" in output.err


def test_working_dir(tmpdir):
    start_dir = os.getcwd()
    with main.working_dir(str(tmpdir)) as directory:
        assert directory == start_dir


def test_mkdirp(tmpdir):
    with tmpdir.as_cwd():
        main.mkdirp("foo/bar/baz")
        assert os.path.isdir("foo")
        assert os.path.isdir("foo/bar")
        assert os.path.isdir("foo/bar/baz")

        # make sure this does not raise
        main.mkdirp("foo/bar/baz")


def test_git_blame_file(tmpdir, repo_dir):
    with tmpdir.as_cwd():
        output = main.git_blame_file(
            ("c569f5d895c44d6bf7023b7b2d8915a0e9fd17a9", "setup.py", "cache/setup.py")
        )
        assert os.path.isdir("cache")
        assert os.path.exists("cache/setup.py")

    lines = [
        "c569f5d895c44d6bf7023b7b2d8915a0e9fd17a9 9 9",
        "author Todd Gamblin",
        "author-mail <tgamblin@llnl.gov>",
        "author-time 1569118250",
        "author-tz -0700",
        "committer Todd Gamblin",
        "committer-mail <tgamblin@llnl.gov>",
        "committer-time 1569118250",
        "committer-tz -0700",
        "summary Initial commit",
        "boundary",
        "filename setup.py",
        "here = path.abspath(path.dirname(__file__))",
    ]

    assert all(line in output for line in lines)

    with tmpdir.as_cwd():
        output = main.git_blame_file(
            ("c569f5d895c44d6bf7023b7b2d8915a0e9fd17a9", "setup.py", "cache/setup.py")
        )
        assert all(line in output for line in lines)


def test_files_for_commit(repo_dir):
    files = main.files_for_commit(
        "c569f5d895c44d6bf7023b7b2d8915a0e9fd17a9",
        [re.compile(r"contrib/test/data/config/.*\.yaml"), re.compile(r"bin/.*")],
    )

    assert set(files) == set(
        [
            "contrib/test/data/config/contrib-no-parts.yaml",
            "contrib/test/data/config/contrib.yaml",
            "bin/contrib",
        ]
    )


def test_iter_blame(tmpdir, repo_dir):
    with tmpdir.as_cwd():
        output = main.git_blame_file(
            (
                "c7e96950440a3d3f7ac2b13d0a8da0239c1debe3",
                "contrib/test/data/config/author-to-org.json",
                "cache/cache.txt",
            )
        )

    counts = collections.defaultdict(lambda: 0)
    for triple in main.iter_blame(output):
        _, name, _ = triple
        counts[name] += 1

    assert counts == {"Todd Gamblin": 339, "Adam J. Stewart": 1}
