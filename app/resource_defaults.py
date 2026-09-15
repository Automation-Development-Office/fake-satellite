"""
Default fields returned for Satellite/Katello API resources.

Ansible modules expect many Katello objects to include fields that are not
always stored in our SQLite payload. Merge these defaults into responses.
"""

from __future__ import annotations

import re
from typing import Any


def _slugify_label(name: str) -> str:
    label = re.sub(r"[^A-Za-z0-9_]+", "_", name.strip())
    return label.strip("_").lower()


RESOURCE_DEFAULTS: dict[str, dict[str, Any]] = {
    "content_views": {
        "composite": False,
        "auto_publish": False,
        "solve_dependencies": False,
        "import_only": False,
        "environments": [],
        "content_view_components": [],
        "repository_ids": [],
        "component_ids": [],
    },
    "products": {
        "description": "",
        "label": None,
        "sync_plan": None,
        "repository_ids": [],
    },
    "repositories": {
        "description": "",
        "label": None,
        "content_type": "yum",
        "url": "",
        "mirror_on_sync": True,
        "download_policy": "immediate",
        "unprotected": False,
    },
    "activation_keys": {
        "description": "",
        "label": None,
        "unlimited_hosts": True,
        "max_hosts": None,
        "usage_count": 0,
        "service_level": None,
        "release_version": None,
    },
    "lifecycle_environments": {
        "description": "",
        "label": None,
        "prior": None,
    },
    "environments": {
        "description": "",
        "label": None,
    },
    "content_view_versions": {
        "description": "",
        "version": "0.0",
        "environments": [],
        "package_count": 0,
        "errata_count": 0,
    },
}


def enrich_resource(resource: str, record: dict[str, Any]) -> dict[str, Any]:
    defaults = RESOURCE_DEFAULTS.get(resource, {})
    for key, value in defaults.items():
        record.setdefault(key, value)

    if resource in (
        "content_views",
        "content_view_versions",
        "products",
        "repositories",
        "activation_keys",
        "lifecycle_environments",
        "environments",
    ):
        if record.get("label") is None and record.get("name"):
            record["label"] = _slugify_label(record["name"])

    return record
