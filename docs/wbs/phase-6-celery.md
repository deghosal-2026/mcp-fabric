# Phase 6: Celery Tasks

> **Tasks:** 18 · **Effort:** 16h (2 days)  
> **Dependencies:** Phase 3 (services), P0-08 (Celery config)

### P6-01: Celery App Initialization (#284)
**Effort:** 1h | **Deps:** P0-08
**Checklist:** `api/tasks.py` — create celery_app → configure task base class (auto-retry, acks_late) → import all task modules → verify worker starts.
**Success Criteria:** `celery -A api.tasks worker --loglevel=info` starts. Redis broker receives tasks.

### P6-02: health_check_server Task (#285)
**Effort:** 1.5h | **Deps:** P2-02, P3-06
**Checklist:** `@celery_app.task(bind=True, max_retries=2, default_retry_delay=10)` → calls mcp_client.list_tools() → updates Redis health state → on timeout: mark degraded, increment failure counter → on 3+ consecutive failures: mark unhealthy, fire alert.
**Success Criteria:** Healthy server → "healthy" in Redis. 3 failures → "unhealthy" + alert.

### P6-03: health_check_all_servers Task (#286)
**Effort:** 1h | **Deps:** P6-02
**Checklist:** Queries all non-decommissioned servers → dispatches health_check_server for each → asyncio.gather for parallel execution → max 10 concurrent.
**Success Criteria:** All servers health-checked within 30s interval.

### P6-04: notify_approval_request Task (#287)
**Effort:** 1.5h | **Deps:** P3-36
**Checklist:** `@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)` → loads approval from DB → for each channel in alert_rules: email (SMTP), Slack (webhook), generic webhook (POST) → logs delivery status.
**Success Criteria:** Email delivered. Slack notification sent. Webhook called. Retry on failure.

### P6-05: deliver_alert Task (#288)
**Effort:** 1.5h | **Deps:** P3-47
**Checklist:** Similar to notify_approval_request → delivers alert event via configured channels → logs delivery.
**Success Criteria:** Alerts reach configured channels. Failed delivery retries.

### P6-06: generate_audit_export Task (#289)
**Effort:** 2h | **Deps:** P3-34
**Checklist:** `@celery_app.task(bind=True, max_retries=1)` → queries audit_events matching export params → generates CSV or JSON file → stores locally (or S3) → updates background_tasks record with status=complete + download_url.
**Success Criteria:** Export file generated. Download URL accessible. Large exports (100k+ rows) stream, don't OOM.

### P6-07: cleanup_audit_logs Task (#290)
**Effort:** 1h | **Deps:** None
**Checklist:** `@celery_app.task` → DELETEs audit_events WHERE created_at < now() - settings.AUDIT_RETENTION_DAYS → batch delete 1000 rows at a time → logs count deleted.
**Success Criteria:** Old events removed. No table locks from large deletes. Daily schedule.

### P6-08: cleanup_expired_tokens Task (#291)
**Effort:** 0.5h | **Deps:** None
**Checklist:** UPDATE agent_identities SET status='expired' WHERE status='active' AND expires_at < now() → batch update → logs count.
**Success Criteria:** Expired tokens marked. Daily schedule.

### P6-09: cleanup_expired_approvals Task (#292)
**Effort:** 0.5h | **Deps:** None
**Checklist:** UPDATE approval_requests SET status='expired' WHERE status='pending' AND expires_at < now() → batch update → logs count.
**Success Criteria:** Expired approvals auto-denied. 5-min schedule.

### P6-10: cleanup_expired_sessions Task (#293)
**Effort:** 0.5h | **Deps:** None
**Checklist:** No-op — Redis TTL handles session expiry automatically. Task logs "0 sessions cleaned (Redis TTL handles this)" for audit trail.
**Success Criteria:** Task runs, confirms Redis TTL working, no false positives.

### P6-11: check_alert_thresholds Task (#294)
**Effort:** 2h | **Deps:** P3-47, P7-01
**Checklist:** `@celery_app.task` scheduled every 60s → loads all enabled alert_rules → for each: queries relevant metric (Redis counter, Prometheus, DB query) → compares against threshold → if crossed AND not already alerted (dedup via Redis key): fire alert.
**Success Criteria:** Threshold crossed → alert fires once. Threshold drops below → resets dedup key. 60s schedule.

### P6-12: deliver_webhook Task (#295)
**Effort:** 1.5h | **Deps:** None
**Checklist:** `@celery_app.task(bind=True, max_retries=3)` → POST event_payload to webhook URL → HMAC-SHA256 signature header → timeout 10s → retry: 1s, 5s, 25s → after 3 failures: mark webhook as degraded in DB.
**Success Criteria:** Webhook delivered with signature. Degraded after 3 failures. Reactivate possible.

### P6-13: run_scheduled_exports Task (#296)
**Effort:** 1h | **Deps:** None
**Checklist:** Queries recurring export configs (future feature, v0.2.0) → for each due: dispatches generate_audit_export. Currently no-op for v0.1.0.
**Success Criteria:** Task runs, logs "0 scheduled exports (v0.2.0 feature)".

### P6-14: health_check_self Task (#297)
**Effort:** 0.5h | **Deps:** None
**Checklist:** `@celery_app.task` → checks Celery worker health: broker connection, result backend, active task count → updates Prometheus gauge fabric_celery_health.
**Success Criteria:** Healthy worker → gauge=1. Broker down → gauge=0. Every 60s.

### P6-15: Celery Beat Schedule Verification (#298)
**Effort:** 0.5h | **Deps:** P6-01 through P6-14
**Checklist:** Verify all 7 scheduled tasks fire on time: health_check_all_servers (30s), check_alert_thresholds (60s), cleanup_expired_approvals (5min), cleanup_audit_logs (3am), cleanup_expired_tokens (2am), run_scheduled_exports (midnight), health_check_self (60s).
**Success Criteria:** Beat scheduler starts. All tasks appear in celery inspect scheduled.

### P6-16: Task Monitoring Dashboard (#299)
**Effort:** 1h | **Deps:** P6-01, P7-01
**Checklist:** Prometheus gauge fabric_celery_tasks_total by task_type + status → Grafana panel: tasks/sec, success rate, failure rate, avg duration → alerts: task failure rate > 10%.
**Success Criteria:** Tasks visible in Grafana. Failure rate alert works.

### P6-17: Task Idempotency Tests (#300)
**Effort:** 1h | **Deps:** P6-02 through P6-14
**Checklist:** Test each task: run twice → second run is safe (no duplicate alerts, no double-expiry, no double-export). health_check_server: running twice updates same Redis key. check_alert_thresholds: dedup prevents double-firing.
**Success Criteria:** All tasks idempotent. No side effects from retry/duplicate execution.

### P6-18: Celery Worker Docker Compose (#301)
**Effort:** 0.5h | **Deps:** P6-01, P0-06
**Checklist:** Verify worker + beat services in docker-compose.yml → worker connects to Redis broker → beat scheduler starts → tasks execute in worker.
**Success Criteria:** Both services healthy in docker-compose ps. Tasks process successfully.
