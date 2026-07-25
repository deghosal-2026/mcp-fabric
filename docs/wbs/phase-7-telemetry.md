# Phase 7: Telemetry

> **Tasks:** 15 · **Effort:** 16h (2 days)  
> **Dependencies:** Phase 3, Phase 4

### P7-01: Prometheus Metrics Definitions (#302) — ✅ Done
- [x] 14 metric families in `api/telemetry/metrics.py`
- [x] Counters: requests, policy decisions, audit events, Celery tasks
- [x] Histograms: latency, routing overhead, policy eval, approval duration
- [x] Gauges: server health, tool count, pending approvals, DB/Redis connections
- [x] Info: fabric_info with version + environment

### P7-02: OpenTelemetry Setup (#303) — ✅ Done
- [x] TracerProvider with resource, OTLP exporter (configurable)
- [x] Lazy init via _get_tracer() — no import-time side effects
- [x] TracingMiddleware consumes tracer per request

### P7-03: Structlog Configuration (#304) — ✅ Done
- [x] JSON format in production, console (colored) in dev
- [x] Context binding: request_id, agent_id, agent_class from auth
- [x] Redaction processors for tokens, passwords, secrets
- [x] Log levels: INFO (requests), WARN (degraded), ERROR (failures)

### P7-04: Metrics Integration — Middleware (#305) — ✅ Done
- [x] TracingMiddleware increments fabric_requests_total on response
- [x] Records fabric_request_duration_seconds histogram
- [x] Labels: method, path, status, agent_class

### P7-05: Metrics Integration — Services (#306) — ✅ Done
- [x] RoutingService records fabric_routing_overhead_seconds
- [x] Other services pending (PolicyService, ApprovalService — Phase 3)

### P7-06: Metrics Integration — Celery (#82) — ✅ Done (stub)
- [x] fabric_celery_tasks_total metric defined
- [x] Full signal wiring deferred (needs running Celery worker)

### P7-07: Metrics Integration — DB/Redis (#84) — ✅ Done
- [x] SQLAlchemy event listeners: checkout → inc, checkin → dec
- [x] Updates fabric_db_connections + fabric_redis_connections

### P7-08: Health Metrics Endpoint (#86) — ✅ Done
- [x] GET /v1/metrics — Prometheus text format
- [x] No auth required (in HEALTH_PATHS)
- [x] content-type: text/plain

### P7-09: Grafana Dashboard JSON (#88) — ✅ Done
- [x] 10 panels in monitoring/grafana-dashboard.json
- [x] Request rate, latency p50/p95/p99, routing overhead, server health, approvals, policies, audit, DB, Redis, Celery

### P7-10: Prometheus Alertmanager Rules (#90) — ✅ Done
- [x] 7 alert rules in monitoring/alerts.yml
- [x] Error budget burn, high latency, low availability, unhealthy servers, denial rate, unreviewed server, API error rate

### P7-11: Trace Span Definitions (#92) — ✅ Done
- [x] Custom spans in TracingMiddleware (method + path)
- [x] Span attributes: http.method, http.url, http.status_code, http.request_id
- [x] Trace context propagated via _trace_headers() in MCPClient

### P7-12: Trace Context Propagation — ✅ Done
- [x] traceparent/tracestate injected into MCP server requests via httpx

### P7-13: Logging — Audit Event Correlation (#96) — ✅ Done
- [x] audit_event_id included in log entries when events are created
- [x] AuditService emits "audit:event_created" with event_id + type + actor

### P7-14: Logging — Sensitive Data Redaction (#98) — ✅ Done
- [x] structlog processor redacts: tokens, passwords, secrets, auth fields
- [x] Configurable via api/telemetry/redaction.py

### P7-15: Telemetry Integration Tests (#100) — ⏳ Deferred to v0.2.0
- Requires running services for end-to-end verification
