# Copyright 2013-2019 Lawrence Livermore National Security, LLC and other
# Spack Project Developers. See the top-level COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)

import os.path

import json
import jsonschema
import yaml

#: Schema for contrib.yaml
contrib_yaml_schema = {
    "$schema": "http://json-schema.org/schema#",
    "title": "Contrib configuration file schema",
    "type": "object",
    "additionalProperties": False,
    "properties": {
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
    },
}


#: Schema for author-to-org mapping
orgmap_schema = {
    "$schema": "http://json-schema.org/schema#",
    "title": "Contrib configuration file schema",
    "type": "object",
    "additionalProperties": False,
    "patternProperties": {
        r".*": {
            "type": "string",
            "description": "name of organization, keyed by commit author name",
        }
    },
}


class ContribConfig(object):
    def __init__(self, path):
        with open(path) as config_file:
            data = yaml.safe_load(config_file)
        jsonschema.validate(contrib_yaml_schema, data)

        data = data["contrib"]

        config_dir = os.path.dirname(path)
        self.repo = os.path.normpath(os.path.join(config_dir, data["repo"]))

        self.orgmap = {}
        self.orgmap_file = None

        # load orgmap if present
        orgmap_file = data.get("orgmap")
        if orgmap_file:
            orgmap_file = os.path.normpath(os.path.join(config_dir, orgmap_file))
            if os.path.exists(orgmap_file):
                with open(orgmap_file) as f:
                    self.orgmap = json.load(f)
            self.orgmap_file = orgmap_file
            jsonschema.validate(orgmap_schema, self.orgmap)

        self.parts = data.get("parts", {"all": [r"^.*$"]})
