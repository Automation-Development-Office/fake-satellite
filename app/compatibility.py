"""
Backward-compatible Satellite API field aliases.

The redhat.satellite collection accepts newer Ansible parameter names while
still mapping to legacy Foreman/Katello API fields via flat_name and aliases.
Fake-satellite mirrors both sides so older and newer collection versions work.
"""

from __future__ import annotations

from typing import Any


def apply_read_aliases(resource: str, record: dict[str, Any]) -> dict[str, Any]:
    """Expose legacy API field names alongside current ones in responses."""

    if resource in ("organizations", "locations"):
        if "ignore_types" in record:
            record.setdefault("select_all_types", record["ignore_types"])
        elif "select_all_types" in record:
            record.setdefault("ignore_types", record["select_all_types"])

    if resource == "domains":
        if "fullname" in record:
            record.setdefault("description", record["fullname"])
        elif "description" in record:
            record.setdefault("fullname", record["description"])

    if resource == "operatingsystems":
        if "family" in record:
            record.setdefault("os_family", record["family"])
        elif "os_family" in record:
            record.setdefault("family", record["os_family"])

    if resource == "activation_keys":
        if "lifecycle_environment_id" in record:
            record.setdefault("environment_id", record["lifecycle_environment_id"])
        elif "environment_id" in record:
            record.setdefault("lifecycle_environment_id", record["environment_id"])

    if resource == "subnets":
        if "from" in record:
            record.setdefault("from_ip", record["from"])
        elif "from_ip" in record:
            record.setdefault("from", record["from_ip"])
        if "to" in record:
            record.setdefault("to_ip", record["to"])
        elif "to_ip" in record:
            record.setdefault("to", record["to_ip"])

    return record


def normalize_write_payload(resource: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Accept legacy API field names in create/update request bodies."""

    normalized = dict(payload)

    if resource in ("organizations", "locations"):
        if "select_all_types" in normalized and "ignore_types" not in normalized:
            normalized["ignore_types"] = normalized.pop("select_all_types")

    if resource == "domains":
        if "fullname" in normalized and "description" not in normalized:
            normalized["description"] = normalized["fullname"]
        elif "description" in normalized and "fullname" not in normalized:
            normalized["fullname"] = normalized["description"]

    if resource == "operatingsystems":
        if "os_family" in normalized and "family" not in normalized:
            normalized["family"] = normalized.pop("os_family")
        elif "family" in normalized and "os_family" not in normalized:
            normalized["os_family"] = normalized["family"]

    if resource == "activation_keys":
        if "environment_id" in normalized and "lifecycle_environment_id" not in normalized:
            normalized["lifecycle_environment_id"] = normalized.pop("environment_id")
        elif "lifecycle_environment_id" in normalized and "environment_id" not in normalized:
            normalized["environment_id"] = normalized["lifecycle_environment_id"]

    if resource == "subnets":
        if "from_ip" in normalized and "from" not in normalized:
            normalized["from"] = normalized.pop("from_ip")
        elif "from" in normalized and "from_ip" not in normalized:
            normalized["from_ip"] = normalized["from"]
        if "to_ip" in normalized and "to" not in normalized:
            normalized["to"] = normalized.pop("to_ip")
        elif "to" in normalized and "to_ip" not in normalized:
            normalized["to_ip"] = normalized["to"]

    return normalized
