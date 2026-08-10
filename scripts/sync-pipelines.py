#!/usr/bin/env python3
"""Sync pipelines/ to Grafana Fleet Management without going through CI.

Local equivalent of the grafana/fleet-management-sync-action GitHub Action:
reads every YAML file under pipelines/ and posts them in one atomic
SyncPipelines call. Pipelines synced earlier under the same namespace but
missing from pipelines/ are deleted server-side.

Usage:
    GCLOUD_FM_URL=... GCLOUD_FM_INSTANCE_ID=... FM_API_TOKEN=... \
        ./scripts/sync-pipelines.py

FM_API_TOKEN needs the fleet-management:write scope (the collector token from
.env only has read access). Falls back to reading .env for GCLOUD_FM_URL and
GCLOUD_FM_INSTANCE_ID.
"""

import base64
import json
import os
import sys
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
NAMESPACE = os.environ.get("NAMESPACE", "otelcol-fleet-demo")


def load_dotenv(path: Path) -> dict:
    env = {}
    if path.exists():
        for line in path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                env[key.strip()] = value.strip().strip('"')
    return env


def main() -> int:
    dotenv = load_dotenv(ROOT / ".env")
    fm_url = os.environ.get("GCLOUD_FM_URL") or dotenv.get("GCLOUD_FM_URL")
    instance_id = os.environ.get("GCLOUD_FM_INSTANCE_ID") or dotenv.get("GCLOUD_FM_INSTANCE_ID")
    token = os.environ.get("FM_API_TOKEN")

    if not (fm_url and instance_id and token):
        print("error: GCLOUD_FM_URL, GCLOUD_FM_INSTANCE_ID and FM_API_TOKEN are required", file=sys.stderr)
        print("       (FM_API_TOKEN must have the fleet-management:write scope)", file=sys.stderr)
        return 1

    pipelines = []
    for path in sorted((ROOT / "pipelines").glob("**/*.yaml")):
        doc = yaml.safe_load(path.read_text())
        config_type = "CONFIG_TYPE_OTEL" if doc.get("config_type") == "otel" else "CONFIG_TYPE_ALLOY"
        pipelines.append(
            {
                "name": doc["name"],
                "contents": doc["contents"],
                "matchers": doc.get("matchers", []),
                "enabled": doc.get("enabled", True),
                "config_type": config_type,
            }
        )
        print(f"  {path.relative_to(ROOT)} -> {doc['name']} ({config_type}, enabled={doc.get('enabled', True)})")

    body = json.dumps(
        {
            "source": {"type": "SOURCE_TYPE_GIT", "namespace": NAMESPACE},
            "pipelines": pipelines,
        }
    ).encode()

    auth = base64.b64encode(f"{instance_id}:{token}".encode()).decode()
    request = urllib.request.Request(
        f"{fm_url.rstrip('/')}/pipeline.v1.PipelineService/SyncPipelines",
        data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Basic {auth}"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request) as response:
            response.read()
    except urllib.error.HTTPError as err:
        print(f"error: HTTP {err.code} from Fleet Management API:\n{err.read().decode()}", file=sys.stderr)
        return 1

    print(f"synced {len(pipelines)} pipeline(s) under namespace '{NAMESPACE}'")
    return 0


if __name__ == "__main__":
    sys.exit(main())
