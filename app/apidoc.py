"""
Generate an Apipie-compatible /apidoc/v2.json document.

Ansible's redhat.satellite collection uses apypie, which expects:

    apidoc["docs"]["resources"][<resource>]["methods"]

Each method must define routes, params, and examples so apypie can discover
and validate API calls.
"""

from __future__ import annotations

from typing import Any


FOREMAN_RESOURCES = (
    "organizations",
    "locations",
    "hostgroups",
    "hosts",
    "domains",
    "subnets",
    "computeresources",
    "architectures",
    "operatingsystems",
    "media",
    "ptables",
    "templates",
    "users",
    "roles",
    "permissions",
    "tasks",
)

KATELLO_RESOURCES = (
    "lifecycle_environments",
    "content_views",
    "content_view_versions",
    "activation_keys",
    "repositories",
    "products",
    "environments",
    "subscriptions",
    "content_view_filter_rules",
)

SINGULAR_NAMES = {
    "organizations": "organization",
    "locations": "location",
    "hostgroups": "hostgroup",
    "hosts": "host",
    "domains": "domain",
    "subnets": "subnet",
    "computeresources": "computeresource",
    "architectures": "architecture",
    "operatingsystems": "operatingsystem",
    "media": "medium",
    "ptables": "ptable",
    "templates": "template",
    "users": "user",
    "roles": "role",
    "permissions": "permission",
    "tasks": "task",
    "lifecycle_environments": "lifecycle_environment",
    "content_views": "content_view",
    "content_view_versions": "content_view_version",
    "activation_keys": "activation_key",
    "repositories": "repository",
    "products": "product",
    "environments": "environment",
    "subscriptions": "subscription",
    "content_view_filter_rules": "content_view_filter_rule",
}


def _param(
    name: str,
    *,
    expected_type: str = "string",
    required: bool = False,
    params: list[dict[str, Any]] | None = None,
    full_name: str | None = None,
    allow_nil: bool | None = None,
) -> dict[str, Any]:
    return {
        "name": name,
        "full_name": full_name or name,
        "description": "",
        "required": required,
        "allow_nil": allow_nil if allow_nil is not None else not required,
        "allow_blank": False,
        "validator": "",
        "expected_type": expected_type,
        "metadata": None,
        "show": True,
        "validations": [],
        "params": params or [],
    }


def _route(api_url: str, http_method: str, description: str = "") -> dict[str, str]:
    return {
        "api_url": api_url,
        "http_method": http_method,
        "short_description": description,
    }


def _method(
    name: str,
    api_url: str,
    http_method: str,
    params: list[dict[str, Any]] | None = None,
    description: str = "",
) -> dict[str, Any]:
    return {
        "name": name,
        "apis": [_route(api_url, http_method, description)],
        "params": params or [],
        "examples": [],
    }


def _index_params() -> list[dict[str, Any]]:
    return [
        _param("search"),
        _param("page", expected_type="numeric"),
        _param("per_page", expected_type="numeric"),
        _param("thin", expected_type="boolean"),
    ]


def _id_param() -> dict[str, Any]:
    return _param("id", expected_type="numeric", required=True)


def _resource_hash_param(resource: str) -> dict[str, Any]:
    singular = SINGULAR_NAMES[resource]
    fields = [_param("name", required=True)]

    if resource == "hosts":
        fields.extend(
            [
                _param("location_id", expected_type="numeric"),
                _param("organization_id", expected_type="numeric"),
            ]
        )

    return _param(
        singular,
        expected_type="hash",
        required=True,
        full_name=singular,
        params=fields,
    )


def _crud_methods(resource: str, base_path: str) -> list[dict[str, Any]]:
    singular = SINGULAR_NAMES[resource]
    methods = [
        _method(
            "index",
            base_path,
            "GET",
            _index_params(),
            f"List all {resource}",
        ),
        _method(
            "show",
            f"{base_path}/:id",
            "GET",
            [_id_param()],
            f"Show a {singular}",
        ),
        _method(
            "create",
            base_path,
            "POST",
            [_resource_hash_param(resource)],
            f"Create a {singular}",
        ),
        _method(
            "update",
            f"{base_path}/:id",
            "PUT",
            [_id_param(), _resource_hash_param(resource)],
            f"Update a {singular}",
        ),
        _method(
            "destroy",
            f"{base_path}/:id",
            "DELETE",
            [_id_param()],
            f"Delete a {singular}",
        ),
    ]

    if resource == "hosts":
        update = next(method for method in methods if method["name"] == "update")
        update["params"].extend(
            [
                _param("location_id", expected_type="numeric"),
                _param("organization_id", expected_type="numeric"),
            ]
        )

    if resource == "content_views":
        methods.append(
            _method(
                "publish",
                f"{base_path}/:id/publish",
                "POST",
                [
                    _id_param(),
                    _param("description"),
                    _param("force_yum_metadata_regeneration", expected_type="boolean"),
                    _param("major", expected_type="numeric"),
                    _param("minor", expected_type="numeric"),
                ],
                "Publish a content view",
            )
        )

    if resource == "content_view_versions":
        methods.append(
            _method(
                "promote",
                f"{base_path}/:id/promote",
                "POST",
                [
                    _id_param(),
                    _param("environment_ids", expected_type="array"),
                    _param("force", expected_type="boolean"),
                    _param("force_yum_metadata_regeneration", expected_type="boolean"),
                ],
                "Promote a content view version",
            )
        )

    if resource == "repositories":
        methods.append(
            _method(
                "sync",
                f"{base_path}/:id/sync",
                "POST",
                [_id_param()],
                "Sync a repository",
            )
        )

    if resource == "products":
        methods.append(
            _method(
                "sync",
                f"{base_path}/:id/sync",
                "POST",
                [_id_param()],
                "Sync a product",
            )
        )

    if resource == "content_view_filter_rules":
        create = next(method for method in methods if method["name"] == "create")
        update = next(method for method in methods if method["name"] == "update")
        for param_name in ("uuid", "errata_ids", "date_type", "module_stream_ids"):
            create["params"].append(_param(param_name))

    if resource == "organizations":
        for action_name in ("create", "update"):
            action = next(method for method in methods if method["name"] == action_name)
            action["params"].append(_param("ignore_types", expected_type="array"))
            action["params"].append(_param("select_all_types", expected_type="array"))

    if resource == "locations":
        for action_name in ("create", "update"):
            action = next(method for method in methods if method["name"] == action_name)
            action["params"].append(_param("ignore_types", expected_type="array"))
            action["params"].append(_param("select_all_types", expected_type="array"))

    if resource == "domains":
        for action_name in ("create", "update"):
            action = next(method for method in methods if method["name"] == action_name)
            domain_param = next(
                param for param in action["params"]
                if param["name"] == SINGULAR_NAMES[resource]
            )
            domain_param["params"].append(_param("fullname"))
            domain_param["params"].append(_param("description"))

    if resource == "operatingsystems":
        for action_name in ("create", "update"):
            action = next(method for method in methods if method["name"] == action_name)
            os_param = next(
                param for param in action["params"]
                if param["name"] == SINGULAR_NAMES[resource]
            )
            os_param["params"].append(_param("family"))
            os_param["params"].append(_param("os_family"))

    if resource == "activation_keys":
        for action_name in ("create", "update"):
            action = next(method for method in methods if method["name"] == action_name)
            action["params"].append(_param("environment_id", expected_type="numeric"))
            action["params"].append(_param("lifecycle_environment_id", expected_type="numeric"))

    return methods


def _resource_path(resource: str) -> str:
    if resource in KATELLO_RESOURCES:
        return f"/katello/api/{resource}"
    return f"/api/{resource}"


def build_apidoc() -> dict[str, Any]:
    resources: dict[str, dict[str, Any]] = {
        "home": {
            "methods": [
                _method(
                    "status",
                    "/api/status",
                    "GET",
                    description="Get API status",
                ),
            ],
        },
    }

    for resource in FOREMAN_RESOURCES + KATELLO_RESOURCES:
        resources[resource] = {
            "methods": _crud_methods(resource, _resource_path(resource)),
        }

    return {
        "docs": {
            "name": "Fake Red Hat Satellite",
            "info": "Apipie-compatible API documentation for fake-satellite",
            "resources": resources,
        },
    }
