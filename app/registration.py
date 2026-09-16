"""Helpers for Foreman registration command generation."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlencode


def _registration_params(body: dict[str, Any]) -> dict[str, Any]:
    params = body.get("registration_command")
    if isinstance(params, dict):
        merged = dict(params)
        for key in ("organization_id", "location_id"):
            if key in body and key not in merged:
                merged[key] = body[key]
        return merged
    return dict(body)


def generate_registration_command(base_url: str, body: dict[str, Any]) -> dict[str, str]:
    params = _registration_params(body)
    query = urlencode(
        {key: value for key, value in params.items() if value is not None},
        doseq=True,
    )
    register_url = f"{base_url.rstrip('/')}/register"
    if query:
        register_url = f"{register_url}?{query}"

    insecure = params.get("insecure", False)
    curl_flags = "-ksS" if insecure else "-sS"
    command = f"curl {curl_flags} '{register_url}' | bash"
    return {"registration_command": command}


def generate_registration_script(params: dict[str, Any]) -> str:
    """Return a shell script for the /register endpoint (piped to bash)."""
    org_id = params.get("organization_id", "")
    location_id = params.get("location_id", "")
    activation_keys = params.get("activation_keys", "")
    return (
        "#!/bin/bash\n"
        "set -euo pipefail\n"
        "echo \"fake-satellite: host registration complete\"\n"
        f"echo \"  organization_id={org_id}\"\n"
        f"echo \"  location_id={location_id}\"\n"
        f"echo \"  activation_keys={activation_keys}\"\n"
    )
