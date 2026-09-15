"""Katello-specific helpers for content view workflows."""

from __future__ import annotations

from typing import Any


def next_content_view_version(
    existing_versions: list[dict[str, Any]],
    major: int | None = None,
    minor: int | None = None,
) -> tuple[int, int, str]:
    if major is not None and minor is not None:
        return major, minor, f"{major}.{minor}"

    if not existing_versions:
        return 1, 0, "1.0"

    latest_major = 0
    latest_minor = -1
    for version in existing_versions:
        version_label = str(version.get("version", "0.0"))
        parts = version_label.split(".", 1)
        current_major = int(parts[0])
        current_minor = int(parts[1]) if len(parts) > 1 else 0
        if (current_major, current_minor) > (latest_major, latest_minor):
            latest_major = current_major
            latest_minor = current_minor

    return latest_major, latest_minor + 1, f"{latest_major}.{latest_minor + 1}"


def publish_response(content_view_version_id: int) -> dict[str, Any]:
    return {
        "id": content_view_version_id,
        "action": "Actions::Katello::ContentView::Publish",
        "state": "stopped",
        "result": "success",
        "input": {"content_view_version_id": content_view_version_id},
        "output": {"content_view_version_id": content_view_version_id},
    }
