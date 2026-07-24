# Monitoring

Grafana dashboard and Prometheus alert rules for MCP Fabric.

## Grafana Dashboard

File: `grafana-dashboard.json` — 10 panels covering:

- Request rate (fabric_requests_total)
- Latency p50/p95/p99 (fabric_request_duration_seconds)
- Routing overhead (fabric_routing_overhead_seconds)
- Server health (fabric_server_health)
- Pending approvals (fabric_approvals_pending)
- Policy decisions (fabric_policy_decisions_total)
- Audit events (fabric_audit_events_total)
- DB connections (fabric_db_connections)
- Redis connections (fabric_redis_connections)
- Celery tasks (fabric_celery_tasks_total)

### Import

1. Open Grafana → Dashboards → New → Import
2. Paste the JSON contents or upload the file
3. Select the Prometheus data source

## Alert Rules

File: `alerts.yml` — 7 alert rules for Prometheus Alertmanager:

- High error budget burn rate
- High request latency (p99 > 1s)
- Low service availability
- Unhealthy MCP servers
- High denial rate
- Unreviewed servers
- High API error rate

### Deploy

```bash
# Assumes promtool is installed
promtool check rules monitoring/alerts.yml
```

Configure Alertmanager to load this rules file via its config.

## Metrics

All metrics are exposed at `GET /v1/metrics` in Prometheus text format. Key labels:

- `method`, `path`, `status`, `agent_class` — HTTP request metrics
- `server_id`, `server_name` — per-server health and tool count
- `event_type` — audit event counter
- `task_type`, `status` — Celery task counter