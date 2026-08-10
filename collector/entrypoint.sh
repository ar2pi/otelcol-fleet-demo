#!/bin/sh
set -eu

: "${GCLOUD_FM_URL:?Set GCLOUD_FM_URL to your Fleet Management URL (Connections > Fleet Management > API tab)}"
: "${GCLOUD_FM_INSTANCE_ID:?Set GCLOUD_FM_INSTANCE_ID to the instance ID shown on the Fleet Management API tab}"
: "${GCLOUD_RW_API_KEY:?Set GCLOUD_RW_API_KEY to an access policy token with the set:otel-data-write scope}"
: "${FLEET_COLLECTOR_NAME:?Set FLEET_COLLECTOR_NAME}"
: "${FLEET_ENVIRONMENT:=dev}"
: "${FLEET_TEAM:=platform}"
export FLEET_ENVIRONMENT FLEET_TEAM

# OpAMP authenticates with HTTP basic auth: <instance-id>:<token>, base64-encoded
GCLOUD_BASIC_AUTH_BASE64=$(printf '%s' "${GCLOUD_FM_INSTANCE_ID}:${GCLOUD_RW_API_KEY}" | base64 | tr -d '\n')
export GCLOUD_BASIC_AUTH_BASE64

exec opampsupervisor --config=/etc/otelcol/supervisor.yaml
