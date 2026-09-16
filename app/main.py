import json
import logging
import os
import re
import sqlite3
from pathlib import Path
from typing import Any

import yaml
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.apidoc import apidoc_checksum, build_apidoc
from app.compatibility import apply_read_aliases, normalize_write_payload
from app.katello import next_content_view_version, promote_response, publish_response
from app.registration import generate_registration_command
from app.resource_defaults import enrich_resource


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DB_PATH = os.getenv(
    "FAKE_SATELLITE_DB",
    "/data/satellite.db",
)

SEED_PATH = os.getenv(
    "FAKE_SATELLITE_SEED",
    "/app/seed/satellite.yml",
)


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

logger = logging.getLogger("fake-satellite")


# ---------------------------------------------------------------------------
# FastAPI
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Fake Red Hat Satellite",
    version="0.1.0",
)


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

RESOURCE_TABLES = {
    # Foreman - Infrastructure
    "organizations": "organizations",
    "locations": "locations",
    "hostgroups": "hostgroups",
    "hosts": "hosts",
    "domains": "domains",
    "subnets": "subnets",
    "computeresources": "computeresources",
    "architectures": "architectures",
    "operatingsystems": "operatingsystems",
    "media": "media",
    "ptables": "ptables",
    "templates": "templates",
    "users": "users",
    "roles": "roles",
    "permissions": "permissions",
    # Katello - Content Management
    "lifecycle_environments": "lifecycle_environments",
    "content_views": "content_views",
    "content_view_versions": "content_view_versions",
    "activation_keys": "activation_keys",
    "repositories": "repositories",
    "products": "products",
    "environments": "environments",
    # Tasks
    "tasks": "tasks",
}

ORG_SCOPED_RESOURCES = {
    "lifecycle_environments",
    "content_views",
    "content_view_versions",
    "products",
    "repositories",
    "activation_keys",
    "environments",
}


def get_connection():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def storage_name(resource: str, payload: dict) -> str:
    name = payload.get("name")
    organization_id = payload.get("organization_id")
    if resource in ORG_SCOPED_RESOURCES and organization_id is not None:
        return f"{organization_id}::{name}"
    return name


def init_db():
    conn = get_connection()

    for table in RESOURCE_TABLES.values():
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {table} (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                data TEXT NOT NULL
            )
            """
        )

    conn.commit()
    conn.close()


def load_seed():
    if not os.path.exists(SEED_PATH):
        logger.info("No seed file found: %s", SEED_PATH)
        return

    conn = get_connection()

    with open(SEED_PATH, "r", encoding="utf-8") as f:
        seed = yaml.safe_load(f) or {}

    for resource, records in seed.items():
        if resource not in RESOURCE_TABLES:
            continue

        table = RESOURCE_TABLES[resource]

        for record in records or []:
            record = dict(record)

            record_id = record.pop("id", None)
            name = record.get("name")

            if not name:
                continue

            record_key = storage_name(resource, {"name": name, **record})
            exists = conn.execute(
                f"SELECT id FROM {table} WHERE name = ?",
                (record_key,),
            ).fetchone()

            if exists:
                continue

            conn.execute(
                f"""
                INSERT INTO {table} (id, name, data)
                VALUES (?, ?, ?)
                """,
                (
                    record_id,
                    record_key,
                    json.dumps(record),
                ),
            )

    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def row_to_dict(row, resource: str | None = None):
    if row is None:
        return None

    data = json.loads(row["data"])

    result = {
        "id": row["id"],
        **data,
    }

    # Foreman commonly exposes title as well as name.
    if "title" not in result:
        result["title"] = result.get("name")

    if resource is not None:
        result = enrich_resource(resource, result)
        result = apply_read_aliases(resource, result)

    return result


def next_id(conn, table):
    row = conn.execute(
        f"SELECT COALESCE(MAX(id), 0) + 1 AS id FROM {table}"
    ).fetchone()

    return row["id"]



def parse_search(search: str | None):
    """
    Small subset of Foreman search syntax.

    Examples:

        name="foo"
        name = "foo"
        name~"foo"
        name="foo" AND organization_id="1"
    """

    if not search:
        return []

    # Handle URL-decoded search strings such as:
    # name="ADO"
    # name='ADO'
    # name=ADO

    matches = re.findall(
        r'(\w+)\s*(=|~)\s*(?:"([^"]*)"|\'([^\']*)\'|([^\s]+))',
        search,
    )

    results = []

    for field, operator, double_quoted, single_quoted, unquoted in matches:
        value = (
            double_quoted
            or single_quoted
            or unquoted
        )

        results.append(
            (field, operator, value)
        )

    return results

def singular_resource_name(resource):
    """
    Convert our internal plural resource name into the
    singular names used by the Satellite API.
    """

    names = {
        "organizations": "organization",
        "locations": "location",
        "hostgroups": "hostgroup",
        "hosts": "host",
        "lifecycle_environments": "lifecycle_environment",
        "content_views": "content_view",
        "content_view_versions": "content_view_version",
        "activation_keys": "activation_key",
    }

    return names.get(resource, resource.rstrip("s"))


def matches_filters(resource_dict: dict, filters: dict) -> bool:
    for key, value in filters.items():
        if value in (None, ""):
            continue

        if key == "environment_id":
            environments = resource_dict.get("environments", [])
            env_ids = {
                env["id"] if isinstance(env, dict) else env
                for env in environments
            }
            if int(value) not in env_ids:
                return False
            continue

        actual = resource_dict.get(key)
        if actual is None:
            return False
        if str(actual) != str(value):
            return False

    return True


def query_params_to_filters(query_params) -> dict:
    reserved = {"search", "page", "per_page", "thin"}
    return {
        key: value
        for key, value in query_params.items()
        if key not in reserved
    }

def matches_search(resource: dict, search: str | None):
    conditions = parse_search(search)

    if not conditions:
        return True

    for field, operator, expected in conditions:
        actual = resource.get(field)

        if actual is None:
            return False

        actual = str(actual)
        expected = str(expected).strip()

        if operator == "=":
            if actual.lower() != expected.lower():
                return False

        elif operator == "~":
            if expected.lower() not in actual.lower():
                return False

    return True


def list_resources(resource, search=None, page=1, per_page=20, filters=None):
    table = RESOURCE_TABLES[resource]

    conn = get_connection()

    rows = conn.execute(
        f"SELECT * FROM {table} ORDER BY id"
    ).fetchall()

    conn.close()

    results = []
    for row in rows:
        record = row_to_dict(row, resource)
        if not matches_search(record, search):
            continue
        if filters and not matches_filters(record, filters):
            continue
        results.append(record)

    total = len(results)

    start = (page - 1) * per_page
    end = start + per_page

    results = results[start:end]

    return {
        "total": total,
        "subtotal": len(results),
        "page": page,
        "per_page": per_page,
        "results": results,
    }


def get_resource(resource, resource_id):
    table = RESOURCE_TABLES[resource]

    conn = get_connection()

    row = conn.execute(
        f"SELECT * FROM {table} WHERE id = ?",
        (resource_id,),
    ).fetchone()

    conn.close()

    if not row:
        raise HTTPException(
            status_code=404,
            detail=f"{resource} {resource_id} not found",
        )

    return row_to_dict(row, resource)


def create_resource(resource, payload):
    table = RESOURCE_TABLES[resource]

    conn = get_connection()

    name = payload.get("name")

    if not name:
        raise HTTPException(
            status_code=400,
            detail="name is required",
        )

    record_key = storage_name(resource, {"name": name, **payload})
    existing = conn.execute(
        f"SELECT * FROM {table} WHERE name = ?",
        (record_key,),
    ).fetchone()

    if existing:
        conn.close()

        raise HTTPException(
            status_code=422,
            detail=f"{resource} with name '{name}' already exists",
        )

    record_id = payload.pop("id", None)

    if record_id is None:
        record_id = next_id(conn, table)

    conn.execute(
        f"""
        INSERT INTO {table} (id, name, data)
        VALUES (?, ?, ?)
        """,
        (
            record_id,
            record_key,
            json.dumps(payload),
        ),
    )

    conn.commit()

    row = conn.execute(
        f"SELECT * FROM {table} WHERE id = ?",
        (record_id,),
    ).fetchone()

    conn.close()

    return row_to_dict(row, resource)


def update_resource(resource, resource_id, payload):
    table = RESOURCE_TABLES[resource]

    conn = get_connection()

    existing = conn.execute(
        f"SELECT * FROM {table} WHERE id = ?",
        (resource_id,),
    ).fetchone()

    if not existing:
        conn.close()

        raise HTTPException(
            status_code=404,
            detail=f"{resource} {resource_id} not found",
        )

    current = row_to_dict(existing, resource)
    current.update(payload)

    name = current.get("name")

    data = dict(current)
    data.pop("id", None)
    data.pop("title", None)

    record_key = storage_name(resource, {"name": name, **data})
    conn.execute(
        f"""
        UPDATE {table}
        SET name = ?, data = ?
        WHERE id = ?
        """,
        (
            record_key,
            json.dumps(data),
            resource_id,
        ),
    )

    conn.commit()

    row = conn.execute(
        f"SELECT * FROM {table} WHERE id = ?",
        (resource_id,),
    ).fetchone()

    conn.close()

    return row_to_dict(row, resource)


def delete_resource(resource, resource_id):
    table = RESOURCE_TABLES[resource]

    conn = get_connection()

    existing = conn.execute(
        f"SELECT * FROM {table} WHERE id = ?",
        (resource_id,),
    ).fetchone()

    if not existing:
        conn.close()

        raise HTTPException(
            status_code=404,
            detail=f"{resource} {resource_id} not found",
        )

    conn.execute(
        f"DELETE FROM {table} WHERE id = ?",
        (resource_id,),
    )

    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Request logging
# ---------------------------------------------------------------------------

@app.middleware("http")
async def log_requests(request: Request, call_next):
    body = await request.body()

    logger.info(
        "%s %s%s",
        request.method,
        request.url.path,
        f"?{request.url.query}" if request.url.query else "",
    )

    if body:
        try:
            logger.info(
                "Request body: %s",
                body.decode("utf-8"),
            )
        except UnicodeDecodeError:
            pass

    response = await call_next(request)

    if request.url.path.startswith(("/api/", "/katello/api/")):
        response.headers["apipie-checksum"] = apidoc_checksum()

    logger.info(
        "Response: %s",
        response.status_code,
    )

    return response


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

@app.on_event("startup")
def startup():
    init_db()
    load_seed()


# ---------------------------------------------------------------------------
# Satellite status
# ---------------------------------------------------------------------------

@app.get("/api/status")
def api_status():
    return {
        "status": "ok",
        "version": "6.19.0-fake",
        "satellite": True,
        "katello": True,
    }


@app.get("/api/ping")
def api_ping():
    return {
        "status": "ok",
    }


# ---------------------------------------------------------------------------
# Generic resource endpoints
# ---------------------------------------------------------------------------

class ResourcePayload(BaseModel):
    name: str
    data: dict[str, Any] = {}


def make_routes(prefix, resource):
    route = f"{prefix}/{resource}"

    @app.get(route)
    def list_endpoint(
        request: Request,
        search: str | None = None,
        page: int = 1,
        per_page: int = 20,
    ):
        return list_resources(
            resource,
            search,
            page,
            per_page,
            query_params_to_filters(request.query_params),
        )

    @app.get(f"{route}/{{resource_id}}")
    def get_endpoint(resource_id: int):
        return get_resource(
            resource,
            resource_id,
        )

    @app.post(route, status_code=201)
    async def create_endpoint(request: Request):
        body = await request.json()

        singular = singular_resource_name(resource)

        # Satellite normally wraps the object:
        #
        # {
        #   "organization": {
        #       "name": "ADO"
        #   }
        # }

        if singular in body:
            payload = body[singular]

        elif resource in body:
            payload = body[resource]

        else:
            payload = body

        return create_resource(
            resource,
            normalize_write_payload(resource, dict(payload)),
        )


    @app.put(f"{route}/{{resource_id}}")
    async def update_endpoint(
        resource_id: int,
        request: Request,
    ):
        body = await request.json()

        singular = singular_resource_name(resource)

        if singular in body:
            payload = body[singular]

        elif resource in body:
            payload = body[resource]

        else:
            payload = body

        return update_resource(
            resource,
            resource_id,
            normalize_write_payload(resource, dict(payload)),
        )

    @app.delete(f"{route}/{{resource_id}}")
    def delete_endpoint(resource_id: int):
        delete_resource(
            resource,
            resource_id,
        )

        return JSONResponse(
            status_code=200,
            content={},
        )


# Foreman - Core resources
make_routes("/api", "organizations")
make_routes("/api", "locations")
make_routes("/api", "hostgroups")
make_routes("/api", "hosts")

# Foreman - Infrastructure
make_routes("/api", "domains")
make_routes("/api", "subnets")
make_routes("/api", "computeresources")
make_routes("/api", "architectures")
make_routes("/api", "operatingsystems")
make_routes("/api", "media")
make_routes("/api", "ptables")
make_routes("/api", "templates")

# Foreman - Users & Permissions
make_routes("/api", "users")
make_routes("/api", "roles")
make_routes("/api", "permissions")

# Katello - Content Management
make_routes(
    "/katello/api",
    "lifecycle_environments",
)

make_routes(
    "/katello/api",
    "content_views",
)

make_routes(
    "/katello/api",
    "content_view_versions",
)

make_routes(
    "/katello/api",
    "activation_keys",
)

make_routes(
    "/katello/api",
    "repositories",
)

make_routes(
    "/katello/api",
    "products",
)

make_routes(
    "/katello/api",
    "environments",
)

# Tasks
make_routes("/api", "tasks")


# ---------------------------------------------------------------------------
# Special Katello aliases
# ---------------------------------------------------------------------------

@app.get("/katello/api/status")
def katello_status():
    return {
        "status": "ok",
    }


# ---------------------------------------------------------------------------
# Association endpoints
# ---------------------------------------------------------------------------

@app.post("/api/hostgroups/{hostgroup_id}/hosts/{host_id}")
def add_host_to_hostgroup(hostgroup_id: int, host_id: int):
    """Add a host to a hostgroup."""
    try:
        hostgroup = get_resource("hostgroups", hostgroup_id)
        host = get_resource("hosts", host_id)
    except HTTPException:
        raise
    
    conn = get_connection()
    hostgroups = hostgroup.get("hostgroups", [])
    if host_id not in hostgroups:
        hostgroups.append(host_id)
        update_resource("hostgroups", hostgroup_id, {"hostgroups": hostgroups})
    conn.close()
    
    return {"status": "ok"}


@app.delete("/api/hostgroups/{hostgroup_id}/hosts/{host_id}")
def remove_host_from_hostgroup(hostgroup_id: int, host_id: int):
    """Remove a host from a hostgroup."""
    try:
        hostgroup = get_resource("hostgroups", hostgroup_id)
    except HTTPException:
        raise
    
    hostgroups = hostgroup.get("hostgroups", [])
    if host_id in hostgroups:
        hostgroups.remove(host_id)
        update_resource("hostgroups", hostgroup_id, {"hostgroups": hostgroups})
    
    return JSONResponse(status_code=200, content={})


@app.post("/api/organizations/{org_id}/hosts/{host_id}")
def add_host_to_organization(org_id: int, host_id: int):
    """Assign a host to an organization."""
    try:
        org = get_resource("organizations", org_id)
        host = get_resource("hosts", host_id)
    except HTTPException:
        raise
    
    # Update host with organization_id
    update_resource("hosts", host_id, {"organization_id": org_id})
    
    return {"status": "ok"}


@app.post("/api/locations/{location_id}/hosts/{host_id}")
def add_host_to_location(location_id: int, host_id: int):
    """Assign a host to a location."""
    try:
        location = get_resource("locations", location_id)
        host = get_resource("hosts", host_id)
    except HTTPException:
        raise
    
    # Update host with location_id
    update_resource("hosts", host_id, {"location_id": location_id})
    
    return {"status": "ok"}


async def _json_body(request: Request) -> dict:
    try:
        body = await request.json()
    except json.JSONDecodeError:
        body = {}
    return body if isinstance(body, dict) else {}


# ---------------------------------------------------------------------------
# Registration command endpoint
# ---------------------------------------------------------------------------

@app.post("/api/registration_commands")
async def create_registration_command(request: Request):
    """Generate a fake host registration command for Ansible testing."""
    body = await _json_body(request)
    base_url = f"{request.url.scheme}://{request.headers.get('host', request.url.netloc)}"
    return generate_registration_command(base_url, body)


@app.get("/register")
def registration_endpoint():
    """Minimal registration endpoint referenced by generated commands."""

    return {
        "status": "ok",
        "message": "fake-satellite registration endpoint",
    }


# ---------------------------------------------------------------------------
# Content view publish / promote endpoints
# ---------------------------------------------------------------------------


@app.post("/katello/api/content_views/{content_view_id}/publish")
async def publish_content_view(content_view_id: int, request: Request):
    """Publish a content view and create a new content view version."""
    body = await _json_body(request)

    content_view = get_resource("content_views", content_view_id)
    existing_versions = list_resources(
        "content_view_versions",
        filters={"content_view_id": content_view_id},
    )["results"]

    major = body.get("major")
    minor = body.get("minor")
    major, minor, version = next_content_view_version(
        existing_versions,
        major,
        minor,
    )

    content_view_version = create_resource(
        "content_view_versions",
        {
            "name": f"{content_view['name']} {version}",
            "content_view_id": content_view_id,
            "organization_id": content_view.get("organization_id"),
            "version": version,
            "major": major,
            "minor": minor,
            "description": body.get("description", ""),
            "environments": [],
        },
    )

    return publish_response(content_view_version["id"])


@app.post("/katello/api/content_view_versions/{version_id}/promote")
async def promote_content_view_version(version_id: int, request: Request):
    """Promote a content view version to lifecycle environments."""
    body = await _json_body(request)

    content_view_version = get_resource("content_view_versions", version_id)
    environment_ids = body.get("environment_ids", [])
    environments = list(content_view_version.get("environments", []))
    existing_ids = {
        env["id"] if isinstance(env, dict) else env
        for env in environments
    }

    for environment_id in environment_ids:
        environment_id = int(environment_id)
        if environment_id in existing_ids:
            continue
        environment = get_resource("lifecycle_environments", environment_id)
        environments.append(
            {
                "id": environment["id"],
                "name": environment["name"],
            }
        )
        existing_ids.add(environment_id)

    updated_version = update_resource(
        "content_view_versions",
        version_id,
        {"environments": environments},
    )

    return promote_response(updated_version)


# ---------------------------------------------------------------------------
# Repository sync endpoint
# ---------------------------------------------------------------------------

@app.post("/katello/api/repositories/{repo_id}/sync")
def sync_repository(repo_id: int):
    """Trigger a repository sync operation."""
    try:
        repo = get_resource("repositories", repo_id)
    except HTTPException:
        raise
    
    # Create a task for the sync
    task = create_resource(
        "tasks",
        {
            "name": f"Sync repository {repo.get('name')}",
            "action": "Repository::Sync",
            "status": "running",
            "repository_id": repo_id,
        },
    )
    
    return {
        "status": "ok",
        "task_id": task.get("id"),
    }


# ---------------------------------------------------------------------------
# Product sync endpoint
# ---------------------------------------------------------------------------

@app.post("/katello/api/products/{product_id}/sync")
def sync_product(product_id: int):
    """Trigger a product sync operation."""
    try:
        product = get_resource("products", product_id)
    except HTTPException:
        raise
    
    # Create a task for the sync
    task = create_resource(
        "tasks",
        {
            "name": f"Sync product {product.get('name')}",
            "action": "Product::Sync",
            "status": "running",
            "product_id": product_id,
        },
    )
    
    return {
        "status": "ok",
        "task_id": task.get("id"),
    }


# ---------------------------------------------------------------------------
# API documentation
# ---------------------------------------------------------------------------

@app.get("/apidoc/v2.json")
def api_documentation():
    """
    Apipie-compatible API documentation consumed by Ansible's apypie client.
    """

    return build_apidoc()


# ---------------------------------------------------------------------------
# Catch unsupported Satellite API requests
# ---------------------------------------------------------------------------

@app.api_route(
    "/api/{path:path}",
    methods=[
        "GET",
        "POST",
        "PUT",
        "PATCH",
        "DELETE",
    ],
)
async def unsupported_api(request: Request, path: str):
    logger.warning(
        "Unsupported API endpoint: %s %s",
        request.method,
        request.url.path,
    )

    return JSONResponse(
        status_code=501,
        content={
            "error": "Fake Satellite endpoint not implemented",
            "method": request.method,
            "path": request.url.path,
            "query": str(request.url.query),
        },
    )


@app.api_route(
    "/katello/api/{path:path}",
    methods=[
        "GET",
        "POST",
        "PUT",
        "PATCH",
        "DELETE",
    ],
)
async def unsupported_katello_api(
    request: Request,
    path: str,
):
    logger.warning(
        "Unsupported Katello API endpoint: %s %s",
        request.method,
        request.url.path,
    )

    return JSONResponse(
        status_code=501,
        content={
            "error": "Fake Katello endpoint not implemented",
            "method": request.method,
            "path": request.url.path,
            "query": str(request.url.query),
        },
    )
