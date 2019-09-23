# Copyright 2013-2019 Lawrence Livermore National Security, LLC and other
# Spack Project Developers. See the top-level COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)

#
# Helper targets for building dist files and uploading them to PyPI
#

# clean up the stuff that setup.py won't.
dist:
	python3 setup.py

# upload distfiles to PyPI
upload: dist
	python3 -m twine upload dist/*

# clean up the stuff that setup.py won't.
clean:
	rm -rf *.egg-info dist build
