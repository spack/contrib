# Copyright 2013-2019 Lawrence Livermore National Security, LLC and other
# Spack Project Developers. See the top-level COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)

import os.path

import jsonschema
import yaml

#: Properties of the contrib config schema
properties = {
    "contrib": {
        "type": "object",
        "default": {},
        "additionalProperties": False,
        "description": "All contrib.yaml files start with 'contrib'",
        "properties": {
            "repo": {
                "type": "string",
                "description": "URL of the repository we're plotting",
            },
            "commit": {
                "type": "string",
                "description": "revision (branch, tag, commit, etc.)  within the repo",
            },
            "orgmap": {
                "type": "string",
                "description": "optional json file mapping authors to organizations",
            },
            "parts": {
                "type": "object",
                "default": {},
                "additionalProperties": False,
                "description": "named lists of directories for logical parts of repo",
                "patternProperties": {
                    r"\w[\w-]*": {
                        "type": "array",
                        "default": [],
                        "items": {"type": "string"},
                    }
                },
            },
        },
        "required": ["repo", "commit"],
    }
}


#: Full schema with metadata
schema = {
    "$schema": "http://json-schema.org/schema#",
    "title": "Contrib configuration file schema",
    "type": "object",
    "additionalProperties": False,
    "properties": properties,
}


class ContribConfig(object):
    def __init__(self, path):
        with open(path) as config_file:
            data = yaml.safe_load(config_file)
        jsonschema.validate(schema, data)

        data = data["contrib"]

        config_dir = os.path.dirname(path)
        self.repo = os.path.normpath(os.path.join(config_dir, data["repo"]))

        orgmap = data.get("orgmap")
        if orgmap:
            orgmap = os.path.normpath(os.path.join(config_dir, orgmap))
            if not os.path.exists(orgmap):
                raise IOError("No such file or directory: '%s'" % orgmap)
        self.orgmap = orgmap
        self.parts = data.get("parts", {"all": r"^.*\.py$"})
