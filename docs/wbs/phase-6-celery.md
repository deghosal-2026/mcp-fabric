# Phase 6: Celery Tasks

> **Tasks:** 18 · **Effort:** 16h (2 days)  
> **Dependencies:** Phase 3 (services), P0-08 (Celery config)

### P6-01: Celery App Initialization (#284) — ✅ Done
- [x] Celery app with broker/backend config
- [x] Task serialization (JSON), acks_late, worker config
- [x] `celery -A api.tasks worker` starts

### P6-02: health_check_server Task (#285) — ✅ Done
- [x] Calls MCPClient.list_tools() → healthy/unhealthy result
- [x] Retries on failure (max_retries=2, delay=10s)
- [x] api/tasks.py

### P6-03: health_check_all_servers Task (#286) — ✅ Done
- [x] Queries all non-decommissioned servers
- [x] Runs health_check for each, returns results
- [x] api/tasks.py

### P6-04: notify_approval_request Task (#287) — ✅ Done
- [x] Logs approval notification via configured channels
- [x] api/tasks.py

### P6-05: deliver_alert Task (#288) — ✅ Done
- [x] Logs alert delivery
- [x] api/tasks.py

### P6-06: generate_audit_export Task (#289) — ✅ Done (stub)
- [x] Stub logging (v0.1.0, full implementation in v0.2.0)
- [x] api/tasks.py

### P6-07: cleanup_audit_logs Task (#290) — ✅ Done
- [x] DELETE audit_events WHERE created_at < now() - retention_days
- [x] Daily schedule, logs count deleted
- [x] api/tasks.py

### P6-08: cleanup_expired_tokens Task (#291) — ✅ Done
- [x] UPDATE agent_identities SET status='expired' WHERE expired
- [x] api/tasks.py

### P6-09: cleanup_expired_approvals Task (#292) — ✅ Done
- [x] UPDATE approval_requests SET status='expired' WHERE expired
- [x] api/tasks.py

### P6-10: cleanup_expired_sessions Task (#293) — ✅ Done
- [x] No-op (Redis TTL handles session expiry)
- [x] api/tasks.py

### P6-11: check_alert_thresholds Task (#294) — ✅ Done (stub)
- [x] Stub for v0.1.0 (no alert rules configured yet)
- [x] api/tasks.py

### P6-12: deliver_webhook Task (#295) — ✅ Done
- [x] POST event_payload to webhook URL with retry
- [x] On failure: retry 3 times
- [x] api/tasks.py

### P6-13: run_scheduled_exports Task (#296) — ✅ Done (no-op)
- [x] No-op for v0.1.0 (v0.2.0 feature)
- [x] api/tasks.py

### P6-14: health_check_self Task (#297) — ✅ Done
- [x] Checks Celery worker health
- [x] api/tasks.py

### P6-15: Celery Beat Schedule Verification (#298) — ✅ Done
- [x] Beat schedule configured in settings (30s/60s/5min/3am/2am/midnight)

### P6-16: Task Monitoring Dashboard (#299) — ✅ Done
- [x] Prometheus metric fabric_celery_tasks_total defined
- [x] Grafana panel included in monitoring/grafana-dashboard.json

### P6-17: Task Idempotency Tests (#300) — ⏳ Deferred to v0.2.0
- Requires running Celery worker + test infrastructure

### P6-18: Celery Worker Docker Compose (#301) — ✅ Done
- [x] Worker + beat services in docker-compose.yml
- [x] Worker connects to Redis broker
