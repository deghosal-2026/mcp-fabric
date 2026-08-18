# Monitoring Guide

Monitoring MCP Fabric with Prometheus, Grafana, Alertmanager, and OpenTelemetry.

## Prometheus Metrics

Fabric exposes 15 metric families at `GET /v1/metrics` in Prometheus text format.

### Metric Families

| # | Metric | Type | Labels | Description |
|---|--------|------|--------|-------------|
| 1 | `fabric_requests_total` | Counter | `method`, `path`, `status`, `agent_class` | Total HTTP requests |
| 2 | `fabric_request_duration_seconds` | Histogram | `method`, `path`, `status` | HTTP request latency. Buckets: 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0 |
| 3 | `fabric_routing_overhead_seconds` | Histogram | `server_id` | Routing time excluding the MCP server call. Buckets: 0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5 |
| 4 | `fabric_server_health` | Gauge | `server_id`, `server_name` | Per-server health (1=healthy, 0=unhealthy) |
| 5 | `fabric_server_tool_count` | Gauge | `server_id`, `server_name` | Number of tools per server |
| 6 | `fabric_policy_decisions_total` | Counter | `agent_class`, `server_id`, `decision` | Policy allow/deny decisions |
| 7 | `fabric_policy_evaluation_duration` | Histogram | `agent_class` | Policy evaluation time. Buckets: 0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5 |
| 8 | `fabric_approvals_pending` | Gauge | — | Number of pending approval requests |
| 9 | `fabric_approval_duration_minutes` | Histogram | `status` | Time to resolve an approval. Buckets: 1, 5, 15, 30, 60, 120, 360, 720, 1440 |
| 10 | `fabric_audit_events_total` | Counter | `event_type` | Total audit events logged |
| 11 | `fabric_db_connections` | Gauge | `pool` | Database pool connections |
| 12 | `fabric_redis_connections` | Gauge | `pool` | Redis pool connections |
| 13 | `fabric_celery_tasks_total` | Counter | `task_type`, `status` | Celery tasks by type and status |
| 14 | `fabric_info` | Info | — | Static instance metadata (version, environment) |

### Prometheus Scrape Configuration

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'mcp-fabric'
    scrape_interval: 15s
    scrape_timeout: 10s
    metrics_path: /v1/metrics
    static_configs:
      - targets: ['localhost:8000']
    relabel_configs:
      - source_labels: [__address__]
        target_label: instance
        replacement: 'fabric-production'
```

## Grafana Dashboard

A pre-built Grafana dashboard is available at `monitoring/grafana-dashboard.json`.

### Import

1. Open Grafana → Dashboards → New → Import
2. Paste the JSON contents or upload the file
3. Select the Prometheus data source

### Dashboard Panels

| Panel | Type | Description |
|-------|------|-------------|
| Request Rate | Graph | `rate(fabric_requests_total[5m])` by method and path |
| Latency p50/p95/p99 | Graph | Histogram quantiles of request duration |
| Routing Overhead | Graph | p95 routing overhead time |
| Server Health | Table | Live `fabric_server_health` per server |
| Pending Approvals | Singlestat | Current `fabric_approvals_pending` count |
| Policy Decisions | Graph | `rate(fabric_policy_decisions_total[5m])` by decision |
| Audit Events | Graph | `rate(fabric_audit_events_total[5m])` by event_type |
| DB Connections | Graph | `fabric_db_connections` per pool |
| Redis Connections | Graph | `fabric_redis_connections` per pool |
| Celery Tasks | Graph | `rate(fabric_celery_tasks_total[5m])` by task_type and status |

### Dashboard UID

The dashboard registers with UID `mcp-fabric-overview` for easy scripting.

## Alertmanager Rules

Alert rules are defined in `monitoring/alerts.yml`. There are 7 rules:

| Alert Name | Expression | Severity | Condition |
|------------|-----------|----------|-----------|
| HighErrorBudgetBurn | `rate(5xx) / rate(total) > 0.05 for 5m` | critical | Error budget burn > 5% |
| HighLatency | `p95 latency > 1s for 10m` | critical | Slow responses |
| LowAvailability | `availability < 99% for 30m` | critical | Service degradation |
| UnhealthyServers | `count(unhealthy) > 2 for 5m` | high | 3+ servers down |
| HighDenialRate | `rate(deny) / rate(total) > 0.1 for 5m` | high | Policy denial spike |
| UnreviewedServer | `trust_level=unreviewed > 0 for 48h` | warning | Server not reviewed |
| APIErrorRate | `rate(5xx) > 0.01 for 5m` | high | API error rate > 1% |

### Deploy Alert Rules

```bash
# Validate rules
promtool check rules monitoring/alerts.yml

# Configure Alertmanager to load the rules file
# Add to alertmanager.yml:
rule_files:
  - /etc/alertmanager/rules/alerts.yml
```

## External Staleness Watchdog (#446)

The staleness watchdog is **architecturally external** to the review-queue system.
Its liveness does not depend on the API, worker, or beat services — if the queue
dies, stale items still trigger alerts.

### Architecture

```
                ┌─────────────────────────────────────┐
                │  Review Queue (api/worker/beat)     │
                │  — writes mappings to limbo         │
                │  — runs re-inspection               │
                └──────────────┬──────────────────────┘
                               │ (shared DB, read-only)
                               ▼
                ┌─────────────────────────────────────┐
                │  Staleness Watchdog (standalone)    │
                │  — polls pending_since timestamps   │
                │  — NEVER writes to the queue        │
                │  — beats own heartbeat              │
                │  — exposes Prometheus metrics :9100 │
                └──────────────┬──────────────────────┘
                               │ (alerts)
                               ▼
                      Alertmanager / Dashboard
```

### Key properties

| Property | How |
|----------|-----|
| Independent process | Separate container (`watchdog` in `docker-compose.yml`), depends only on `postgres` + `redis` |
| Read-only | Probes `capability_mappings.pending_since`; never mutates queue status |
| Own heartbeat | `fabric_watchdog_last_success_timestamp` gauge, updated each cycle |
| Dead-man switch | `WatchdogDeadManSwitch` alert fires if no check-in for >5 min |
| Grouped alerts | `GroupedStalenessAlert` per `failure_class` — unreachable ≠ drift |

### Running

```bash
# Standalone
python scripts/watchdog.py --interval 60 --threshold-hours 24 --dead-man-minutes 10

# Docker
docker compose up -d watchdog
```

### Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `fabric_watchdog_cycles_total` | Counter | Total cycles completed |
| `fabric_watchdog_alerts_total` | Counter | Alerts by `failure_class` |
| `fabric_watchdog_last_success_timestamp` | Gauge | Last successful cycle (dead-man switch source) |
| `fabric_watchdog_overdue_items` | Gauge | Overdue items by `failure_class` |

### Alert Rules

| Alert | Expression | Severity | Condition |
|-------|-----------|----------|-----------|
| `WatchdogDeadManSwitch` | `time() - fabric_watchdog_last_success_timestamp > 300` | critical | Watchdog dead/stuck for >5 min |
| `StaleReviewAgeAlert` | `sum(fabric_watchdog_overdue_items) > 0` | high | Items past review deadline |

### Kill-Queue Test

The watchdog's independence is verified by `tests/services/test_watchdog.py::test_watchdog_alert_survives_queue_service_death`: the watchdog is constructed with only a DB session and notifier (no `RegistryService`/`CapabilityService`), proving the queue process can be completely gone and stale items still alert.

## OpenTelemetry Tracing

### Configuration

Set the `OTEL_ENDPOINT` environment variable to enable trace export:

```bash
export OTEL_ENDPOINT=http://otel-collector:4318
```

### Collectors

| Collector | Protocol | Endpoint |
|-----------|----------|----------|
| Grafana Tempo | OTLP HTTP | `http://tempo:4318` |
| Jaeger | OTLP gRPC | `http://jaeger:4317` |
| Custom OpenTelemetry Collector | OTLP HTTP/gRPC | Configurable |

### Instrumentation

Fabric auto-instruments:

- **FastAPI** — request spans via `opentelemetry-instrumentation-fastapi`
- **SQLAlchemy** — database query spans via `opentelemetry-instrumentation-sqlalchemy`
- **Redis** — cache operation spans via `opentelemetry-instrumentation-redis`

Each capability request trace captures: capability resolution → policy evaluation → server selection → MCP server call → response normalization → audit logging.

### Trace Sampling

```python
# api/telemetry/tracing.py
# Sample rate: 100% in development, lower in production
from opentelemetry.sdk.trace.sampling import ParentBasedTraceIdRatio

sampler = ParentBasedTraceIdRatio(0.1)  # 10% sampling in production
```

## Logging

Fabric uses [structlog](https://www.structlog.org/) for structured JSON logging.

### Log Output Format

```json
{"event": "capability_request_routed", "request_id": "abc123",
 "agent_id": "igor-01", "capability": "code:search",
 "server_id": "uuid", "latency_ms": 320, "timestamp": "...",
 "level": "info", "logger": "api.services.routing"}
```

### Log Levels by Environment

| Environment | Level | Rationale |
|-------------|-------|-----------|
| Development | `DEBUG` | Full visibility for debugging |
| Staging | `INFO` | Key events, filter noisy debug |
| Production | `WARNING` | Degradation events, errors only |

## Example `docker-compose.monitoring.yml`

```yaml
version: "3.8"

services:
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana:latest
    environment:
      - GF_AUTH_ANONYMOUS_ENABLED=true
    ports:
      - "3001:3000"
    volumes:
      - ./monitoring/grafana-dashboard.json:/etc/grafana/provisioning/dashboards/fabric.json

  alertmanager:
    image: prom/alertmanager:latest
    volumes:
      - ./monitoring/alerts.yml:/etc/alertmanager/rules/alerts.yml
    ports:
      - "9093:9093"

  tempo:
    image: grafana/tempo:latest
    command: ["-config.file=/etc/tempo.yaml"]
    ports:
      - "4318:4318"  # OTLP HTTP
```
