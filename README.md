# Contrib

[![PyPI version](https://badge.fury.io/py/contrib.svg)](https://badge.fury.io/py/contrib)
[![Build Status](https://travis-ci.com/spack/contrib.svg?branch=master)](https://travis-ci.com/spack/contrib)
[![codecov](https://codecov.io/gh/spack/contrib/branch/master/graph/badge.svg)](https://codecov.io/gh/spack/contrib)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A python package for making stacked area plots of contributions to a git
repository over time.  Plots can show contributions by authors, or by
organizations.

<p align="center">
  <img src="https://raw.githubusercontent.com/spack/contrib/master/data/spack-pkgs-plot.png" width=600>
</p>

## Installation

`contrib` is on PyPI, so you can just `pip install` it:

```console
$ pip install contrib
```

Alternately, you can clone this project, add its directory to your
`PYTHONPATH`, and add the `bin` directory to your `PATH`.

## Usage

To use `contrib`, you'll need to create a configuration file telling it
where to find your code.  Below is an example for Spack; you can find
complete code in the
[spack-contributions](https://github.com/spack/spack-contributions) repo.


Here's an example `contrib.yaml`:

```yaml
contrib:
  # Path to your git repository. to run git blame on.
  # Consider making this a git submodule.
  repo:   ./spack

  # JSON file mapping authors to organizations (optional)
  orgmap: ./author-to-org.json

  # Separate parts of the repository to process (optional).  For each
  # commit, contrib will look for files that match the patterns in each
  # part.  For a simple repo, you may only need one regular expression
  # per part.  In Spack, the packages have moved around in the repo over
  # time, so we provide multiple patterns.  Contrib will use the first
  # pattern matched by any file in each commit.
  parts:
    packages:
      - ^var/spack/repos/builtin/packages/.*\.py$
      - ^var/spack/packages/.*\.py$
      - ^lib/spack/spack/packages/.*\.py$
```

The `repo` needs to be in your local filesystem, preferably in the same
directory as `contrib.yaml`.  `orgmap` is optional (see below for how to
generate it).  `parts` is also optional; if you do not specify it, there
will be one part called `all` that matches everything:

```yaml
    parts:
      all:
        - ^.*$
```

You can name your parts anything; see the example above for how to model
a repository where different logical parts have moved around in
subdirectories.


### Mapping authors to organizations


The `orgmap` (`author-to-org.json` in the example above) is optional.  If
you choose to provide it, it should be simple `json` dictionary mapping
authors to organizations:

```json
{
  "Author 1": "UIUC",
  "Author 2": "LBL",
  ...
  "Author N": "LLNL"
}
```

You can run `contrib --update-org-map` to generate an `orgmap` to start
with.  `contrib` will look at your repository's history and generate the
file automatically:

```console
$ contrib --update-org-map
==> Added 503 new authors to 'author-to-org.json'
==> New orgmap file created in 'author-to-org.json'.
==> Add it to './contrib.yaml' like this:

    contrib:
        orgmap: author-to-org.json

```

If you then add this file to your `contrib.yaml`, you can update it later
as your repository evolves:

```console
$ contrib --update-org-map
==> Added 10 new authors to 'author-to-org.json'
```

Newly added authors will be labeled as `unknown <email from git>` in the
`json` file:

```json
  "Author 1": "unknown <foo@bar.com>",
  "Author 2": "unknown <444532+someusername@users.noreply.github.com>",
  "Author 3": "unknown <user@example.com>",
```

You can replace these with valid organizations, or just leave them and
they'll show up as "unknown" in the `contrib`  plots.

### Running

Once you've got all of that set up, you can run `contrib` in the
directory where `contrib.yaml` lives:

```console
$ ls
author-to-org.json  contrib.yaml
$ contrib
==> Indexing 49 commits.

STARTED       0/49 53ab298e88f80454f7f7c20ef200a3dbd0870473
    packages: processed 45/3487 blames (9.04/s)
...
```

By default, `contrib` will sample 50 commits from your repository and
plot them.  If you want it to plot fewer samples, you can run `contrib
--samples SAMPLES` where `SAMPLES` is a number of your choosing.
`contrib` tries to use the available processors on the machine it is
run, and by default it will run parallel `git blame` jobs.  You can
control the parallelism with the `--jobs JOBS` argument.

`contrib` has to run `git blame` for each sampled commit and for each
file matched by the `parts` section of your `contrib.yaml` file (or for
all files if `parts` is not provided), so it can take a long time to run
if your repo's history is long.  `contrib`'s output shows how many `git
blame` calls remain and how fast blames are currently completing.

### Cached data

`contrib` caches results of `git blame` in a directory called
`line-data`.  For large repositories, this can get to be quite large, so
make sure you have a decent amount of space available (gigabytes for
large repositories).

## License

Contrib is part of the Spack project. Spack is distributed under the
terms of both the MIT license and the Apache License (Version 2.0). Users
may choose either license, at their option.

All new contributions must be made under both the MIT and Apache-2.0
licenses.

See [LICENSE-MIT](https://github.com/spack/contrib/blob/master/LICENSE-MIT),
[LICENSE-APACHE](https://github.com/spack/contrib/blob/master/LICENSE-APACHE),
[COPYRIGHT](https://github.com/spack/contrib/blob/master/COPYRIGHT), and
[NOTICE](https://github.com/spack/contrib/blob/master/NOTICE) for details.

SPDX-License-Identifier: (Apache-2.0 OR MIT)

LLNL-CODE-647188
