# Phase 7: Telemetry

> **Tasks:** 15 · **Effort:** 16h (2 days)  
> **Dependencies:** Phase 3, Phase 4

### P7-01: Prometheus Metrics Definitions (#302)
**Effort:** 2h | **Deps:** None
**Checklist:** `api/telemetry/metrics.py` — 15 metric definitions per spec Section 21.1: fabric_requests_total (Counter), fabric_request_duration_seconds (Histogram), fabric_routing_overhead_seconds (Histogram), fabric_server_health (Gauge), fabric_server_tool_count (Gauge), fabric_policy_decisions_total (Counter), fabric_policy_evaluation_duration (Histogram), fabric_approvals_pending (Gauge), fabric_approval_duration_minutes (Histogram), fabric_audit_events_total (Counter), fabric_db_connections (Gauge), fabric_redis_connections (Gauge), fabric_celery_tasks_total (Counter), fabric_info (Info). All with proper labels.
**Success Criteria:** /metrics endpoint returns all 15 families. Labels correct.

### P7-02: OpenTelemetry Setup (#303)
**Effort:** 2h | **Deps:** None
**Checklist:**
- [x] `api/telemetry/tracing.py` — TracerProvider with resource, OTLP exporter (configurable), ConsoleSpanExporter fallback
- [x] FastAPI auto-instrumentation via instrument_fastapi()
- [x] Module-level tracer instance consumed by TracingMiddleware
- [x] otel_endpoint config setting
**Success Criteria:** Traces exported to backend when configured. TracingMiddleware creates spans per request.

### P7-03: Structlog Configuration (#304)
**Effort:** 1.5h | **Deps:** None
**Checklist:** `api/telemetry/logging.py` — structlog config: JSON format in production, console (colored) in dev → context binding: request_id, agent_id, agent_class from middleware → log levels: DEBUG (SQL, bodies), INFO (method+path+status), WARN (degraded, fallback, rate limit), ERROR (failures). Redact: tokens, passwords, MCP response bodies, param values.
**Success Criteria:** Production logs valid JSON. Dev logs readable. No secrets logged.

### P7-04: Metrics Integration — Middleware (#305)
**Effort:** 1h | **Deps:** P7-01, P4-03
**Checklist:** Tracing middleware increments fabric_requests_total on response → records fabric_request_duration_seconds histogram → sets agent_class+capability+status labels.
**Success Criteria:** Every request increments counter. Histogram captures latency distribution.

### P7-05: Metrics Integration — Services (#306)
**Effort:** 1h | **Deps:** P7-01, Phase 3
**Checklist:** RoutingService records fabric_routing_overhead_seconds (routing time excluding server call) → PolicyService records fabric_policy_decisions_total + evaluation duration → ApprovalService updates fabric_approvals_pending gauge → AuditService increments fabric_audit_events_total → Server health updates fabric_server_health gauge.
**Success Criteria:** All metrics populated during normal operation. Gauges reflect current state.

### P7-06: Metrics Integration — Celery (#82)
**Effort:** 0.5h | **Deps:** P7-01, Phase 6
**Checklist:** Celery task signals: task_prerun → increment fabric_celery_tasks_total{status="started"}, task_success → increment {status="success"}, task_failure → increment {status="failure"}.
**Success Criteria:** Task execution visible in metrics.

### P7-07: Metrics Integration — DB/Redis (#84)
**Effort:** 0.5h | **Deps:** P7-01
**Checklist:** SQLAlchemy event listeners: checkout → increment gauge, checkin → decrement → Redis connection pool: similar → update fabric_db_connections + fabric_redis_connections.
**Success Criteria:** Connection pool metrics accurate.

### P7-08: Health Metrics Endpoint (#86)
**Effort:** 0.5h | **Deps:** P7-01
**Checklist:** `GET /v1/metrics` → returns Prometheus text format via prometheus_client.generate_latest() → no auth required → content-type: text/plain.
**Success Criteria:** `curl /v1/metrics` returns valid Prometheus format. Prometheus can scrape.

### P7-09: Grafana Dashboard JSON (#88)
**Effort:** 2h | **Deps:** P7-01 through P7-08
**Checklist:** `monitoring/grafana-dashboard.json` — 14 panels per spec Section 21.3: request rate, latency p50/p95/p99, routing overhead, by agent class, by capability, error rate, denial rate, fallback rate, server health grid, pending approvals, approval resolution time, OPA latency, DB connections, Celery tasks. Importable via Grafana UI.
**Success Criteria:** All panels render. Time range picker works. Datasource = Prometheus.

### P7-10: Prometheus Alertmanager Rules (#90)
**Effort:** 1.5h | **Deps:** P7-01
**Checklist:** `monitoring/alerts.yml` — 7 alert rules: error budget burn rate >5x (P0), p95 latency >1s for 10min (P1), availability <99% for 30min (P0), 3+ servers unhealthy (P1), denial rate >10% for any class (P1), unreviewed server >48h (P2), API error rate >1% for 5min (P1). Labels: severity, component.
**Success Criteria:** `promtool check rules` passes. Alerts fire in Prometheus at correct thresholds.

### P7-11: Trace Span Definitions (#92)
**Effort:** 1h | **Deps:** P7-02
**Checklist:** Define span names + attributes: capability_request (root, agent_id+capability+params_hash), resolve_capability (name+match_type), evaluate_policy (agent_class+server+decision), select_server (candidates_evaluated+selected+reason), call_mcp_server (server+tool+timeout), normalize_response (mapping_applied), write_audit_event (event_type+id). Events for key decisions.
**Success Criteria:** All spans visible in trace viewer. Meaningful attributes on each span.

### P7-12: fmtrace Context Propagation
**Effort:** 0.5h | **Deps:** P7-02
**Checklist:** Propagate trace context headers (traceparent, tracestate) to MCP server calls via httpx → MCP servers can link their spans to Fabric's trace.
**Success Criteria:** Trace shows end-to-end flow from agent → Fabric → MCP server.

### P7-13: Logging — Audit Event Correlation (#96)
**Effort:** 0.5h | **Deps:** P7-03
**Checklist:** Include audit_event_id in log entries → link logs to audit events for debugging → query: find all logs for a specific capability_request event.
**Success Criteria:** Log query by request_id returns all log entries for that request.

### P7-14: Logging — Sensitive Data Redaction (#98)
**Effort:** 1h | **Deps:** P7-03
**Checklist:** structlog processor that redacts: token values → "***", param values in capability requests → "***", MCP response bodies >1KB → "[truncated]", admin passwords → "[redacted]". Configurable redaction patterns.
**Success Criteria:** No secrets in logs. Redaction visible as "***" in log output.

### P7-15: Telemetry Integration Tests (#100)
**Effort:** 1h | **Deps:** P7-01 through P7-14
**Checklist:** Verify /metrics returns all families → make capability request → verify fabric_requests_total incremented → verify histogram has observation → verify trace exported → verify log contains request_id → verify no secrets in log output.
**Success Criteria:** Metrics + traces + logs all working. No sensitive data leaked.
