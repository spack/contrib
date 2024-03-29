# Copyright 2013-2019 Lawrence Livermore National Security, LLC and other
# Spack Project Developers. See the top-level COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)

from __future__ import division

import argparse
import bisect
import collections
import contextlib
import glob
import json
import sys
import re
import os
import datetime
import errno
import subprocess
import string
import time
import multiprocessing

import dateutil.parser
import matplotlib.colors
import matplotlib.pyplot as plt
import matplotlib.cm as cmx

import contrib.config

# parallel blame jobs to run at once.
blame_jobs = multiprocessing.cpu_count()
blame_pool = None

# Location to cache per-commit stats in
cache_dir = "line-data"
parts_dir = "line-data/parts"
blame_dir = "line-data/blame"

# Patterns to ignore
ignore = [r"^\s*\#", r"^\s*$"]  # comments  # blank lines
ignore = [re.compile(s) for s in ignore]

#: global for location of repo
git_repo_dir = None

#: global for verbosity
verbose = False


def die(message):
    sys.stderr.write("==> Error: %s" % message)
    sys.stderr.write("\n")
    sys.exit(1)


def mkdirp(*paths):
    """Creates a directory, as well as parent directories if needed."""
    for path in paths:
        if not os.path.exists(path):
            os.makedirs(path)
        elif not os.path.isdir(path):
            raise OSError(errno.EEXIST, "File already exists", path)


@contextlib.contextmanager
def working_dir(directory):
    pwd = os.getcwd()
    os.chdir(directory)
    yield pwd
    os.chdir(pwd)


def git(*args, split=True):
    cmd = ["git"]
    cmd.extend(args)

    if verbose:
        print("    " + git_repo_dir + ": " + " ".join(cmd))

    with working_dir(git_repo_dir):
        output = subprocess.check_output(cmd)
        output = output.decode("utf-8")
        if split:
            output = output.strip().split("\n")
        return output


def git_blame_file(args):
    commit, filename, cache_file = args

    if os.path.exists(cache_file):
        with open(cache_file, "r") as f:
            return f.read()

    parent = os.path.dirname(cache_file)
    mkdirp(parent)

    tmp_file = cache_file + (".tmp.%d" % os.getpid())
    blame_cmd = [
        "blame",
        "-w",
        "-M",
        "-C",
        "--line-porcelain",
    ]

    ignore_revs_file = os.path.abspath(
        os.path.join(git_repo_dir, ".git-blame-ignore-revs")
    )
    if os.path.exists(ignore_revs_file):
        blame_cmd += ["--ignore-revs-file", ignore_revs_file]

    blame_cmd += [
        commit,
        "--",
        filename,
    ]

    blame_output = git(*blame_cmd, split=False)

    with open(tmp_file, "w") as stream:
        stream.write(blame_output)
        stream.flush()
    os.rename(tmp_file, cache_file)
    return blame_output


def files_for_commit(commit, places):
    """Get only files from a commit that match the places list"""
    files = git("ls-tree", "-r", "--name-only", "--full-tree", commit)
    results = []
    for regex in places:
        results.extend(f for f in files if regex.search(f))
    return results


def iter_blame(output):
    """Parses ``git blame --line-porcelain`` output."""
    commit = author = None
    for line in output.strip().split("\n"):
        if line.startswith("author "):
            author = line[7:]

        elif line.startswith("\t"):
            text = line[1:]
            yield (commit, author, text)

        else:
            prefix = line[:40]
            if " " not in prefix and all(c in string.hexdigits for c in prefix):
                commit = prefix


def git_blame(commit, places, name):
    """Get blame statsistics for all files in a place list."""
    files = files_for_commit(commit, places)

    arguments = [
        (commit, filename, os.path.join(blame_dir, filename, "%s.txt" % commit))
        for filename in files
    ]
    nblames = len(arguments)

    outputs = blame_pool.imap_unordered(git_blame_file, arguments)
    blame = {}

    start = time.time()
    times = []
    for i, output in enumerate(outputs):
        now = time.time()
        times.append(now)

        est = times[-30:]
        est_start = est[0] if len(est) > 1 else start
        rate = len(est) / (now - est_start)

        if not verbose:
            # write summary here (verbose prints out all git commands)
            sys.stdout.write(
                "\r    %s: processed %d/%d blames (%.2f/s)     "
                % (name, i + 1, nblames, rate)
            )
            sys.stdout.flush()

        for _, author, line in iter_blame(output):
            if not any(ig.search(line) for ig in ignore):
                blame.setdefault(author, 0)
                blame[author] += 1
    if not verbose:
        sys.stdout.write("\n")
        sys.stdout.flush()
    return blame


class AuthorStats(object):
    """Cache of line stats by commit."""

    def __init__(self, name, places):
        self.name = name
        self.commits = {}
        self.places = places
        self.cache = os.path.join(parts_dir, name)
        if not os.path.isdir(self.cache):
            mkdirp(self.cache)

    def _path(self, sha1):
        return os.path.join(self.cache, "%s.json" % sha1)

    def _sha1(self, commit):
        return git("rev-parse", commit, split=False).strip()

    def __contains__(self, commit):
        sha1 = self._sha1(commit)
        return sha1 in self.commits or os.path.exists(self._path(sha1))

    def __getitem__(self, commit):
        """Get author-to-line-mapping for a SHA1 hash"""
        sha1 = self._sha1(commit)
        if sha1 in self.commits:
            return self.commits[sha1]

        path = self._path(sha1)
        if os.path.exists(path):
            with open(path) as f:
                stats = json.load(f)
                self.commits[sha1] = stats
                return stats

        stats = git_blame(sha1, self.places, self.name)
        temp_name = path + ".tmp"
        with open(temp_name, "w") as temp:
            json.dump(stats, temp, indent=True, separators=(",", ": "))
        os.rename(temp_name, path)

        self.commits[sha1] = stats
        return stats


class OrgStats(object):
    def __init__(self, author_stats, authors_to_orgs):
        self.author_stats = author_stats
        self.authors_to_orgs = authors_to_orgs
        self.cache = {}

    def __getitem__(self, commit):
        if commit not in self.cache:
            author_stats = self.author_stats[commit]
            org_stats = {}
            for author, count in author_stats.items():
                org = self.authors_to_orgs.get(author, "unknown")
                if org.startswith("unknown"):
                    org = "unknown"
                org_stats[org] = org_stats.setdefault(org, 0) + count
            self.cache[commit] = org_stats
        return self.cache[commit]


def linear_history(length=sys.maxsize):
    """Yield tuples of (commit, date) on the current branch, from newest to
    oldest.  Date used is commit date, because it is monotonic."""
    output = git("log", "--first-parent", "--no-merges", "--format=%H %cI")
    for i, line in enumerate(output):
        if i >= length:
            break
        commit, date = re.split(r"\s+", line)
        yield commit, dateutil.parser.parse(date)


def sampled_history(ndates):
    """Yield tuples of (commit, date) on the current branch, from newest to
    oldest.

    Samples the date range from first commit to today evenly, but
    always includes the latest commit.

    """
    commits = []

    output = git("log", "--first-parent", "--no-merges", "--format=%H %cI")
    for i, line in enumerate(output):
        commit, date = re.split(r"\s+", line)
        commits.append((commit, dateutil.parser.parse(date)))

    if len(commits) == 1:
        return commits

    end, start = commits[0][1], commits[-1][1]

    dt_s = (end - start).total_seconds() / (ndates - 1)
    dt = datetime.timedelta(seconds=dt_s)

    samples = []
    c = iter(reversed(commits))
    commit, date = next(c)
    try:
        for i in range(ndates):
            while date < start + (i * dt):
                commit, date = next(c)
            if not samples or commit != samples[-1][0]:
                samples.append((commit, date))
    except StopIteration:
        pass

    if commit != samples[-1][0]:
        samples.append((commit, date))

    return list(reversed(samples))


def _build_index(history, stats):
    stats_by_name = {}
    for name, places in stats.items():
        regexes = []
        for regex in places:
            regexes.append(re.compile(regex))
        stats_by_name[name] = AuthorStats(name, regexes)

    todo = set()
    for commit, date in history:
        if any(commit not in gs for gs in stats_by_name.values()):
            todo.add(commit)

    total = len(history)
    remaining = len(todo)
    completed = total - remaining

    print("==> %d commits already complete." % completed)
    print("==> %d commits remaining to index." % remaining)

    then = time.time()
    for i, (commit, date) in enumerate(history):
        if commit not in todo:
            continue

        print("STARTED %5d/%d %s" % (i + 1, len(history), commit))
        for gs in stats_by_name.values():
            gs[commit]

        now = time.time()
        delta = now - then
        print("    COMPLETED in %.2fs" % delta)
        then = now

    return stats_by_name


def build_index(history, stats):
    global blame_pool

    if blame_pool is None:
        blame_pool = multiprocessing.Pool(blame_jobs)

    try:
        return _build_index(history, stats)
    finally:
        blame_pool.terminate()
        blame_pool = None


def plot(filename, title, counts, dates, top_n=20):
    """Makes a stacked line plot of contributions over time.

    Plot will be stored in PDF named ``filename``, with the given
    ``title``, using data in ``counts`` and ``dates``.

    ``counts`` is a list of dictionaries, each mapping the contributor
    name (author, organization, etc.) to line count for a
    commit. ``dates`` is a list of dates, for the commits. The two lists
    should be the same length.

    The stacked plots will explicitly show data for the top N
    contributors.  N defaults to 20.
    """
    print("==> Creating plot: %s" % filename)
    # Sort data ascending by date.
    sorted_list = sorted(zip(dates, counts))
    dates, counts = zip(*sorted_list)

    # Get sorted lists of top contributors (by line) from the last commit.
    contributors = sorted(counts[-1].keys(), key=lambda c: counts[-1][c])
    with open(filename + ".json", "w") as all_counts:
        json.dump(
            [(c, counts[-1][c]) for c in reversed(contributors)],
            all_counts,
            indent=2,
            separators=(",", ": "),
        )

    top_contributors = contributors[-top_n:]
    if "unknown" in top_contributors:
        top_contributors = contributors[-top_n - 1 :]
        top_contributors.remove("unknown")

    labels = top_contributors

    # List of series, one for each top contributor. Each element is a
    # count for a commit.
    series = [[cdict.get(c, 0) for cdict in counts] for c in top_contributors]

    # List of summed line counts from "other", non-top contributors
    other = [
        sum(count for c, count in cdict.items() if c not in top_contributors)
        for cdict in counts
    ]
    if other:
        series.insert(0, other)
        labels = ["Other"] + labels

    # Use a nice color scheme.
    cm = plt.get_cmap("Paired")
    c_norm = matplotlib.colors.Normalize(vmin=0, vmax=len(series) - 1)
    scalar_map = cmx.ScalarMappable(norm=c_norm, cmap=cm)

    # Try to add contrast by shuffling the initially smooth-ish gradient.
    nc = len(series)
    colors = [scalar_map.to_rgba(i + 1) for i in range(nc)]
    colors.reverse()
    colors = colors[::3] + colors[1::3] + colors[2::3]

    plt.figure(figsize=(8, 4), dpi=320)
    plt.title(title, fontname="Arial")

    # Do the plot
    plt.stackplot(dates, series, labels=labels, lw=0, colors=colors)
    locs, labels = plt.xticks()
    plt.setp(labels, rotation=45)

    # Set up a legend with contributor names
    ax = plt.gca()
    handles, labels = ax.get_legend_handles_labels()
    ax.legend(handles[::-1], labels[::-1], ncol=3, fontsize=10, loc="upper left")

    plt.tight_layout()
    plt.savefig(filename)


def update_org_map(filename, authors_to_orgs):
    lines = git("log", "--no-merges", "--pretty=format:%aN|%ae")

    new_authors = 0
    for line in lines:
        name, email = line.split("|")
        if name not in authors_to_orgs or authors_to_orgs[name] == "unknown":
            authors_to_orgs[name] = "unknown <%s>" % email
            new_authors += 1

    if new_authors:
        temp_name = "%s.tmp.%d" % (filename, os.getpid())
        with open(temp_name, "w") as temp:
            sorted_dict = collections.OrderedDict(sorted(authors_to_orgs.items()))
            json.dump(sorted_dict, temp, indent=2, separators=(",", ": "))
            temp.write("\n")  # add back trailing newline
        os.rename(temp_name, filename)

        print("==> Added %d new authors to '%s'" % (new_authors, filename))
    else:
        print("==> No new authors.")


def create_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-i",
        "--index",
        action="store_true",
        default=False,
        help="build the commit index and display progress, but do not plot",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=False,
        help="print out each commit as it is processed",
    )
    parser.add_argument(
        "-f",
        "--file",
        action="store",
        default="./contrib.yaml",
        help="path to valid contrib.yaml (default './contrib.yaml')",
    )
    parser.add_argument(
        "-n",
        "--topn",
        action="store",
        type=int,
        default=20,
        help="number of contributors to show before collapsing into 'other'",
    )
    parser.add_argument(
        "-s",
        "--samples",
        action="store",
        type=int,
        default=50,
        help="number of commits to sample for the chart (0 for all commits)",
    )
    parser.add_argument(
        "--fuzz",
        action="store",
        type=int,
        default=10,
        help="find already-blamed commits within X percent of samples (default 10%%)",
    )
    parser.add_argument(
        "-j",
        "--jobs",
        action="store",
        type=int,
        default=multiprocessing.cpu_count(),
        help="number of concurrent blame jobs (default #cpus)",
    )
    parser.add_argument(
        "-u",
        "--update-org-map",
        action="store_true",
        default=False,
        help="update or create an author-to-organization mapping",
    )
    parser.add_argument(
        "--format",
        action="store",
        choices=("pdf", "svg", "png", "jpg", "gif"),
        default="pdf",
        help="format for images (default pdf)",
    )
    return parser


def merge(count_dict, merge_list):
    for user_list in merge_list:
        total = 0
        present = False
        for user in user_list:
            if user in count_dict:
                present = True
                total += count_dict[user]
                del count_dict[user]
        if present:
            count_dict[user_list[0]] = total


def fuzz_history(history, fuzz, parts):
    """Find commits that are close to the ones we sampled, so that we do not have to
    compute blame if we have something nearby."""
    # usually all parts have same cached commits -- just assume that here. Worst that
    # happens is we have to blame more if the commit exists in multiple sections
    part = list(parts)[0]
    parts_cache = os.path.join(parts_dir, part)

    cached = []
    for filename in os.listdir(parts_cache):
        match = re.match(r"([0-9a-f]{40})\.json", filename)
        if match:
            commit = match.group(1)
            date = git("show", "-s", "--format=%ci", commit)[0].strip()
            cached.append((commit, dateutil.parser.parse(date)))

    # sort by date
    cached.sort(key=lambda x: x[1])

    # lists of just the cached commits and cached dates
    commits, dates = zip(*cached)

    # average time bt/w two samples
    total = dates[1] - dates[0]
    for i in range(1, len(dates) - 1):
        total += dates[i + 1] - dates[i]
    avg_window = total / (len(dates) - 1)
    print(avg_window)
    acceptable = fuzz / 100.0 * avg_window

    fuzzed = []
    for h, (commit, date) in enumerate(history):
        hi = bisect.bisect_left(dates, date)
        lo = hi - 1

        lo_delta = None
        if lo > 0 and lo < len(cached):
            if commits[lo] == commit:
                fuzzed.append((commit, date))
                continue
            lo_delta = date - dates[lo]

        hi_delta = None
        if hi > 0 and hi < len(cached):
            hi_delta = dates[hi] - date

        if not lo_delta and not hi_delta:
            fuzzed.append((commit, date))
            continue

        if not lo_delta:
            delta, i = hi_delta, hi
        elif not hi_delta:
            delta, i = lo_delta, lo
        else:
            delta, i = min(((hi_delta, hi), (lo_delta, lo)))

        if delta <= acceptable:
            fuzzed.append((commits[i], dates[i]))
        else:
            fuzzed.append((commit, date))

    return fuzzed


def main():
    global verbose
    global blame_jobs
    global git_repo_dir

    multiprocessing.set_start_method("fork")

    parser = create_parser()
    args = parser.parse_args()

    # read config out of git root
    if not os.path.exists(args.file):
        die("no such file: '%s'" % args.file)

    config = contrib.config.ContribConfig(args.file)
    verbose = args.verbose
    blame_jobs = args.jobs
    git_repo_dir = config.repo

    if not os.path.exists(os.path.join(config.repo, ".git")):
        die("not a git repo: '%s'" % config.repo)

    # update mapping from authors to orgs
    if args.update_org_map:
        filename = config.orgmap_file
        if not filename:
            filename = "author-to-org.json"

        update_org_map(filename, config.orgmap)

        if not config.orgmap_file:
            print("==> New orgmap file created in '%s'." % filename)
            print("==> Add it to '%s' like this:" % args.file)
            print()
            print("    contrib:")
            print("        orgmap: %s" % filename)
            print()

        return

    # get the list of commits we're going to plot
    if args.samples == 0:
        history = list(linear_history())
    else:
        history = list(sampled_history(args.samples))
        if args.fuzz:
            history = fuzz_history(history, args.fuzz, config.parts)

    # build index
    index = build_index(history, config.parts)

    # if --index, just return after building
    if args.index:
        return

    # now do plots by author and by organization
    for part in config.parts:
        for by in ["author", "organization"]:
            cur_index = index
            if by == "organization":
                if not config.orgmap:
                    print("==> No orgmap specified. Skipping.")
                    continue
                cur_index = {
                    name: OrgStats(s, config.orgmap) for name, s in index.items()
                }

            counts = [cur_index[part][commit] for commit, date in history]
            for count_dict in counts:
                merge(count_dict, config.merge)

            dates = [date for commit, date in history]

            plot(
                "loc-in-%s-by-%s.%s" % (part, by, args.format),
                "Contributions (lines of code) over time in %s, by %s" % (part, by),
                counts,
                dates,
                args.topn,
            )
