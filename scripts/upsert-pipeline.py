#!/usr/bin/env python3
"""Upsert or delete a single Fleet Management pipeline from a manifest file.

Break-glass companion to sync-pipelines.py: deploys one ad-hoc pipeline (e.g.
examples/canary-checkout-debug.yaml) without touching the GitOps-synced set,
and supports OTel-type pipelines (which `gcx fleet pipelines create` currently
does not — it only accepts Alloy contents).

Usage:
    FM_API_TOKEN=<write-token> ./scripts/upsert-pipeline.py examples/canary-checkout-debug.yaml
    FM_API_TOKEN=<write-token> ./scripts/upsert-pipeline.py --delete canary-checkout-debug

Reads GCLOUD_FM_URL and GCLOUD_FM_INSTANCE_ID from the environment or .env.
FM_API_TOKEN needs the fleet-management:write scope.
"""

import base64
import json
import os
import sys
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def load_dotenv(path: Path) -> dict:
    env = {}
    if path.exists():
        for line in path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                env[key.strip()] = value.strip().strip('"')
    return env


def call(fm_url: str, auth: str, method: str, payload: dict) -> dict:
    request = urllib.request.Request(
        f"{fm_url.rstrip('/')}/pipeline.v1.PipelineService/{method}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Basic {auth}"},
        method="POST",
    )
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read() or b"{}")


def main() -> int:
    args = sys.argv[1:]
    delete = "--delete" in args
    args = [a for a in args if a != "--delete"]
    if len(args) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    target = args[0]

    dotenv = load_dotenv(ROOT / ".env")
    fm_url = os.environ.get("GCLOUD_FM_URL") or dotenv.get("GCLOUD_FM_URL")
    instance_id = os.environ.get("GCLOUD_FM_INSTANCE_ID") or dotenv.get("GCLOUD_FM_INSTANCE_ID")
    token = os.environ.get("FM_API_TOKEN")
    if not (fm_url and instance_id and token):
        print("error: GCLOUD_FM_URL, GCLOUD_FM_INSTANCE_ID and FM_API_TOKEN are required", file=sys.stderr)
        return 1
    auth = base64.b64encode(f"{instance_id}:{token}".encode()).decode()

    try:
        if delete:
            listing = call(fm_url, auth, "ListPipelines", {})
            match = next((p for p in listing.get("pipelines", []) if p["name"] == target), None)
            if not match:
                print(f"error: no pipeline named '{target}' found", file=sys.stderr)
                return 1
            call(fm_url, auth, "DeletePipeline", {"id": match["id"]})
            print(f"deleted pipeline '{target}' (id={match['id']})")
        else:
            doc = yaml.safe_load(Path(target).read_text())
            config_type = "CONFIG_TYPE_OTEL" if doc.get("config_type") == "otel" else "CONFIG_TYPE_ALLOY"
            result = call(
                fm_url,
                auth,
                "UpsertPipeline",
                {
                    "pipeline": {
                        "name": doc["name"],
                        "contents": doc["contents"],
                        "matchers": doc.get("matchers", []),
                        "enabled": doc.get("enabled", True),
                        "config_type": config_type,
                    },
                    "validate_only": False,
                },
            )
            print(f"upserted pipeline '{doc['name']}' ({config_type}, id={result.get('id', '?')})")
    except urllib.error.HTTPError as err:
        print(f"error: HTTP {err.code} from Fleet Management API:\n{err.read().decode()}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
