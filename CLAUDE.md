# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Demo of Grafana Cloud Fleet Management for OpenTelemetry Collectors: a
docker-compose fleet of 3 collectors running under the OpAMP Supervisor, remote
configured via pipeline files in `pipelines/` that are synced to the Fleet
Management API by GitHub Actions (GitOps) or `scripts/sync-pipelines.py`.

## Commands

- `make up` / `make down` / `make logs` — run the collector fleet (requires a
  filled-in `.env`, see `.env.example`; needs real Grafana Cloud credentials)
- `FM_API_TOKEN=<token> make sync` — push `pipelines/` to Fleet Management
  locally; token needs `fleet-management:write` scope (distinct from the
  read-only collector token in `.env`)
- `make traces` — send test OTLP traces to the dev collector
- `make clean` — down + delete state volumes (collectors re-register as new)
- No tests or linters; `docker compose config -q` validates the compose file.

## Architecture constraints

- `pipelines/*.yaml` is the source of truth; the file format is dictated by
  `grafana/fleet-management-sync-action` (fields: `name`, `config_type: otel`,
  `enabled`, `matchers`, inline `contents`). The workflow and the local script
  must use the same namespace (`otelcol-fleet-demo`) — it scopes server-side
  deletion of removed pipelines.
- Fleet Management merges all pipelines matching a collector into ONE collector
  config. Keep OTel component names unique across pipeline files (use `/suffix`
  naming, e.g. `debug/prod`) or configs will collide after merge.
- Collector targeting is via `matchers` against attributes set in
  `collector/supervisor.yaml` (`fleet`, `environment`, `team`, fed from
  `FLEET_*` env vars in `docker-compose.yml`).
- Secrets never go in pipeline contents — reference them as `${env:VAR}`,
  resolved inside the collector container from `.env`.
- Version pinning is a single ARG (`OTEL_VERSION`) in `collector/Dockerfile`;
  supervisor and collector images must share the same version.
