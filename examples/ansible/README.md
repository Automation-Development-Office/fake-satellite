# Ansible examples for fake-satellite

This directory contains a sample playbook that runs against a local fake-satellite container using the `redhat.satellite` collection.

## Prerequisites

1. fake-satellite running and reachable (default: `http://localhost:8080`)

   ```bash
   podman run -d --name fake-satellite -p 8080:8080 fake-satellite:latest
   ```

2. Ansible 2.14+ installed on the control node

3. `redhat.satellite` collection installed:

   ```bash
   ansible-galaxy collection install -r requirements.yml
   ```

## Run the playbook

From this directory:

```bash
ansible-playbook -i inventory.yml site.yml
```

Override connection settings without editing files:

```bash
ansible-playbook -i inventory.yml site.yml \
  -e fake_satellite_server_url=http://127.0.0.1:8080 \
  -e fake_satellite_organization=Engineering
```

## What the playbook does

1. Lists organizations via `organization_info`
2. Creates a domain named `lab.example.com`
3. Creates a content view named `RHEL8_Base` in the `Engineering` organization
4. Lists content views and prints their names

Connection settings live in `group_vars/all.yml`. The default organization matches seed data in `seed/satellite.yml`.

## Troubleshooting

If Ansible fails with an apidoc `TypeError`, rebuild the container and clear the apypie cache on the control node:

```bash
rm -rf ~/.cache/apypie/*
```

See the main [README.md](../../README.md#ansible-troubleshooting) for details.
