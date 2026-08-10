ARG OTEL_VERSION=0.158.0

FROM otel/opentelemetry-collector-contrib:${OTEL_VERSION} AS collector

# The supervisor image is alpine-based, runs as user 10001 (opampsupervisor)
FROM otel/opentelemetry-collector-opampsupervisor:${OTEL_VERSION}

USER root
COPY --from=collector /otelcol-contrib /usr/local/bin/otelcol-contrib
RUN mkdir -p /var/lib/otelcol/supervisor \
    && chown -R 10001:10001 /var/lib/otelcol/supervisor
COPY supervisor.yaml /etc/otelcol/supervisor.yaml
COPY --chmod=755 entrypoint.sh /usr/local/bin/entrypoint.sh

USER opampsupervisor
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
