#!/usr/bin/env python3
"""Read-only SAE EDGE CORE repository enrollment policy validator."""
import json
import os
import re
import sys
from pathlib import Path

def validate(path: Path, repo: str | None = None) -> list[str]:
    errors = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return [f"cannot read manifest: {exc}"]
    if not isinstance(data, dict):
        return ["manifest must be an object"]
    if data.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    own = data.get("repository")
    if not isinstance(own, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", own):
        errors.append("repository must be owner/name")
    if repo and own != repo:
        errors.append(f"repository mismatch: expected {repo}")
    gateway = data.get("gateway")
    if not isinstance(gateway, dict):
        return errors + ["gateway object missing"]
    if gateway.get("mode") not in ("catalog-only", "staging", "production"):
        errors.append("gateway.mode invalid")
    enabled = gateway.get("enabled")
    if not isinstance(enabled, bool):
        errors.append("gateway.enabled must be boolean")
    if gateway.get("mode") == "catalog-only" and enabled is not False:
        errors.append("catalog-only must remain disabled")
    origin = gateway.get("origin")
    if gateway.get("mode") == "catalog-only" and origin is not None:
        errors.append("catalog-only must not define origin")
    if enabled:
        errors.append("enabled routing forbidden by automated enrollment: requires separate approval")
    if any(key in gateway for key in ("token", "api_key", "password", "secret", "authorization")):
        errors.append("credentials must never appear in manifest")
    if data.get("control_plane_url") != "https://sae-edge-core-30.pages.dev/":
        errors.append("control_plane_url must identify the information portal")
    return errors

if __name__ == "__main__":
    file = Path(sys.argv[1] if len(sys.argv) > 1 else ".sae/edge-core.json")
    repo = os.environ.get("GITHUB_REPOSITORY") or None
    problems = validate(file, repo)
    for problem in problems:
        print("ERROR:", problem, file=sys.stderr)
    if problems:
        sys.exit(1)
    print("SAE EDGE CORE enrollment policy: PASS (no gateway traffic activated)")
