# Fake Satellite

A lightweight mock of the Red Hat Satellite / Foreman API for development and testing. Use it to exercise Ansible playbooks, automation jobs, or API clients without a real Satellite server.

The service exposes Foreman-style endpoints under `/api` and Katello-style endpoints under `/katello/api`, backed by SQLite and seeded from `seed/satellite.yml`.

## Quick start with a container

Build and run with Podman or Docker:

```bash
podman build -f Containerfile -t fake-satellite:latest .
podman run -d --name fake-satellite -p 8080:8080 fake-satellite:latest
```

Or with Docker:

```bash
docker build -f Containerfile -t fake-satellite:latest .
docker run -d --name fake-satellite -p 8080:8080 fake-satellite:latest
```

Verify the API is up:

```bash
curl http://localhost:8080/api/status
curl http://localhost:8080/katello/api/status
```

Expected response from `/api/status`:

```json
{
  "status": "ok",
  "version": "6.19.0-fake",
  "satellite": true,
  "katello": true
}
```

Stop and remove the container:

```bash
podman rm -f fake-satellite
```

## Pull a published image

Release builds are published to GitHub Container Registry:

```bash
podman pull ghcr.io/automation-development-office/fake-satellite:latest
podman run -d --name fake-satellite -p 8080:8080 ghcr.io/automation-development-office/fake-satellite:latest
```

## Run locally without a container

Requirements: Python 3.13+

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export FAKE_SATELLITE_DB=./data/satellite.db
export FAKE_SATELLITE_SEED=./seed/satellite.yml

uvicorn app.main:app --host 0.0.0.0 --port 8080
```

On first startup the app creates the SQLite database and loads seed data from `seed/satellite.yml`.

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `FAKE_SATELLITE_DB` | `/data/satellite.db` | Path to the SQLite database file |
| `FAKE_SATELLITE_SEED` | `/app/seed/satellite.yml` | YAML file used to populate initial data |

To persist data across container restarts, mount a volume:

```bash
podman run -d \
  --name fake-satellite \
  -p 8080:8080 \
  -v fake-satellite-data:/data \
  fake-satellite:latest
```

To use custom seed data:

```bash
podman run -d \
  --name fake-satellite \
  -p 8080:8080 \
  -v ./my-seed.yml:/app/seed/satellite.yml:ro \
  fake-satellite:latest
```

## Testing the API

Install test dependencies:

```bash
pip install requests apypie
```

Run the full endpoint test suite:

```bash
python tests/test_endpoints.py --url http://localhost:8080
```

Run a smaller curl-based smoke test:

```bash
./tests/quick_test.sh http://localhost:8080
```

See [tests/README.md](tests/README.md) for details on what the test suite covers.

## Using with Ansible

A full example playbook lives in [examples/ansible/](examples/ansible/). Install the collection and run it against a local container:

```bash
cd examples/ansible
ansible-galaxy collection install -r requirements.yml
ansible-playbook -i inventory.yml site.yml
```

Point the `redhat.satellite` collection at this service using `server_url` and any credentials your playbook expects. The fake API does not enforce authentication, but modules still require username/password parameters.

Example:

```yaml
- name: List organizations
  redhat.satellite.organization_info:
    server_url: "http://localhost:8080"
    username: "admin"
    password: "changeme"
```

Example playbook task to create a domain:

```yaml
- name: Create test domain
  redhat.satellite.domain:
    server_url: "http://localhost:8080"
    username: "admin"
    password: "changeme"
    name: "lab.example.com"
    state: present
```

The service serves Apipie-compatible documentation at `/apidoc/v2.json`, which Ansible uses through the `apypie` library to discover available API resources and actions.

### Ansible troubleshooting

If you see an error like:

```text
TypeError: list indices must be integers or slices, not str
```

when Ansible connects, the `redhat.satellite` modules are reading an outdated `/apidoc/v2.json` payload. That usually means one of two things:

1. **An old container image is still running** — rebuild and restart from current `main`:

   ```bash
   podman rm -f fake-satellite
   podman build -f Containerfile -t fake-satellite:latest .
   podman run -d --name fake-satellite -p 8080:8080 fake-satellite:latest
   ```

2. **A stale apypie cache on the Ansible control node** — apypie caches API docs locally and reuses them without re-fetching:

   ```bash
   rm -rf ~/.cache/apypie/*
   ```

Verify the running server returns the correct apidoc shape:

```bash
curl -s http://localhost:8080/apidoc/v2.json | python3 -c "
import json, sys
apidoc = json.load(sys.stdin)
docs = apidoc.get('docs')
assert isinstance(docs, dict), f'docs should be a dict, got {type(docs).__name__}'
assert 'resources' in docs, 'docs.resources is missing'
assert 'home' in docs['resources'], 'home resource is missing'
print('apidoc OK')
"
```

If that check passes but Ansible still fails, clear the apypie cache and rerun the playbook.

## API overview

| Endpoint | Description |
|----------|-------------|
| `GET /api/status` | Foreman/Satellite status |
| `GET /api/ping` | Simple health check |
| `GET /katello/api/status` | Katello status |
| `GET /apidoc/v2.json` | Apipie API documentation |
| `GET/POST/PUT/DELETE /api/<resource>` | Foreman resources |
| `GET/POST/PUT/DELETE /katello/api/<resource>` | Katello resources |

Supported resources include organizations, locations, hosts, hostgroups, domains, subnets, users, roles, repositories, products, content views, activation keys, and more. Seed data for each resource type is defined in `seed/satellite.yml`.

Common operations:

```bash
# List organizations
curl http://localhost:8080/api/organizations

# Get a host by ID
curl http://localhost:8080/api/hosts/1

# Create a domain
curl -X POST http://localhost:8080/api/domains \
  -H "Content-Type: application/json" \
  -d '{"domain":{"name":"lab.example.com","fullname":"lab.example.com"}}'

# Sync a repository
curl -X POST http://localhost:8080/katello/api/repositories/1/sync

# Publish and promote a content view
curl -X POST http://localhost:8080/katello/api/content_views/1/publish -H 'Content-Type: application/json' -d '{}'
curl -X POST http://localhost:8080/katello/api/content_view_versions/1/promote \
  -H 'Content-Type: application/json' \
  -d '{"environment_ids":[2],"force":false,"force_yum_metadata_regeneration":false}'
```

Search and pagination follow a subset of Foreman search syntax:

```bash
curl 'http://localhost:8080/api/hosts?search=name~"web"'
curl 'http://localhost:8080/api/organizations?page=1&per_page=10'
```

## Project layout

```
app/
  main.py       FastAPI application and API routes
  apidoc.py     Apipie-compatible /apidoc/v2.json generator
seed/
  satellite.yml Initial seed data
tests/
  test_endpoints.py  Python API test suite
  quick_test.sh    Curl-based smoke test
Containerfile     Container image definition
```

## CI and releases

- **CI** (`.github/workflows/ci.yml`): builds the container image, starts it, and runs `tests/test_endpoints.py` on pushes and pull requests to `main`.
- **Release** (`.github/workflows/release.yml`): runs tests, then builds and pushes the image to `ghcr.io/automation-development-office/fake-satellite` when a GitHub release is published.

## Limitations

This is a fake API, not a full Satellite implementation.

- No real authentication or authorization
- No background task engine beyond simple task records
- Unsupported endpoints return `501 Not Implemented`
- Apidoc covers the resources and actions needed for common Ansible module workflows, but not every real Satellite endpoint

Use it for development, integration testing, and Ansible module validation—not for production workloads.
