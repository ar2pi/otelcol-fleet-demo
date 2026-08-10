.PHONY: up down logs sync traces clean

## Build images and start the collector fleet
up:
	docker compose up -d --build

## Stop the fleet (keeps supervisor state volumes / collector identities)
down:
	docker compose down

## Follow collector logs — watch remote configs arrive and debug exporter output
logs:
	docker compose logs -f

## Push pipelines/ to Fleet Management from this machine (bypasses CI).
## Requires FM_API_TOKEN with fleet-management:write scope.
sync:
	./scripts/sync-pipelines.py

## Send 10s of test traces to the dev collector's OTLP endpoint
traces:
	docker compose --profile loadgen run --rm telemetrygen

## Stop everything and delete state volumes (collectors re-register as new)
clean:
	docker compose down -v
