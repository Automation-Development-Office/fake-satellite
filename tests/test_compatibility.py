"""Tests for legacy Satellite API field compatibility."""

import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.compatibility import apply_read_aliases, normalize_write_payload


BASE_URL = "http://localhost:8080"


def test_normalize_write_aliases():
    assert normalize_write_payload(
        "organizations",
        {"select_all_types": ["Host"]},
    ) == {"ignore_types": ["Host"]}

    assert normalize_write_payload(
        "domains",
        {"name": "example.com", "fullname": "Example Domain"},
    )["description"] == "Example Domain"

    assert normalize_write_payload(
        "operatingsystems",
        {"name": "RHEL 9", "os_family": "Redhat"},
    )["family"] == "Redhat"

    assert normalize_write_payload(
        "activation_keys",
        {"name": "key", "environment_id": 2},
    )["lifecycle_environment_id"] == 2


def test_apply_read_aliases():
    record = apply_read_aliases(
        "organizations",
        {"name": "Default Organization", "ignore_types": ["Host"]},
    )
    assert record["select_all_types"] == ["Host"]

    record = apply_read_aliases(
        "operatingsystems",
        {"name": "RHEL 9", "family": "Redhat"},
    )
    assert record["os_family"] == "Redhat"


def test_live_api_aliases(base_url: str = BASE_URL):
    domain = requests.post(
        f"{base_url}/api/domains",
        json={"domain": {"name": "legacy.example.com", "fullname": "Legacy Domain"}},
        timeout=5,
    )
    assert domain.status_code == 201
    payload = domain.json()
    assert payload.get("fullname") == "Legacy Domain"
    assert payload.get("description") == "Legacy Domain"

    operating_system = requests.get(f"{base_url}/api/operatingsystems/1", timeout=5)
    assert operating_system.status_code == 200
    payload = operating_system.json()
    assert payload.get("family") == "Redhat"
    assert payload.get("os_family") == "Redhat"

    activation_key = requests.get(f"{base_url}/katello/api/activation_keys/1", timeout=5)
    assert activation_key.status_code == 200
    payload = activation_key.json()
    assert payload.get("lifecycle_environment_id") == payload.get("environment_id")


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Run compatibility tests")
    parser.add_argument("--url", default=BASE_URL)
    args = parser.parse_args()

    test_normalize_write_aliases()
    test_apply_read_aliases()
    try:
        test_live_api_aliases(args.url)
    except requests.exceptions.ConnectionError:
        print("Live API compatibility tests skipped (server not running)")
        sys.exit(0)

    print("compatibility tests passed")
