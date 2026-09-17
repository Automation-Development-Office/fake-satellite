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


def _optional_host_json_fields(params: dict[str, Any]) -> str:
    fields: list[str] = []
    for key in ("organization_id", "location_id"):
        value = params.get(key)
        if value not in (None, ""):
            fields.append(f'\\"{key}\\": {int(value)}')
    return ", ".join(fields)


def generate_registration_script(base_url: str, params: dict[str, Any]) -> str:
    """Return a shell script for the /register endpoint (piped to bash)."""
    api_url = f"{base_url.rstrip('/')}/api/hosts"
    extra_fields = _optional_host_json_fields(params)
    extra = f", {extra_fields}" if extra_fields else ""
    payload = '{\\"host\\":{\\"name\\":\\"${HOSTNAME}\\"' + extra + "}}"

    lines = [
        "#!/bin/bash",
        "set -euo pipefail",
        'HOSTNAME="${HOSTNAME:-$(hostname -f 2>/dev/null || hostname)}"',
        f"HTTP_CODE=$(curl -sS -o /dev/null -w '%{{http_code}}' -X POST '{api_url}' \\",
        "  -H 'Content-Type: application/json' \\",
        f'  -d "{payload}")',
        'if [ "$HTTP_CODE" = "201" ] || [ "$HTTP_CODE" = "422" ]; then',
        '  echo "The system has been registered."',
        "  exit 0",
        "fi",
        'echo "Registration failed with HTTP $HTTP_CODE" >&2',
        "exit 1",
    ]
    return "\n".join(lines) + "\n"


def generate_unregister_script(base_url: str, params: dict[str, Any]) -> str:
    """Return a shell script for the /unregister endpoint (piped to bash)."""
    api_url = f"{base_url.rstrip('/')}/api/hosts/unregister"

    return (
        "#!/bin/bash\n"
        "set -euo pipefail\n"
        'HOSTNAME="${HOSTNAME:-$(hostname -f 2>/dev/null || hostname)}"\n'
        f"curl -sS -X POST '{api_url}' \\\n"
        "  -H 'Content-Type: application/json' \\\n"
        '  -d "{\\"name\\":\\"${HOSTNAME}\\"}"\n'
        'echo "System has been unregistered."\n'
        'echo "All local data removed."\n'
    )
