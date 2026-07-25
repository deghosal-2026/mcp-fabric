"""Prometheus metric definitions for MCP Fabric.

Naming convention:
    All metrics use the "fabric_" prefix followed by a descriptive name.
    Units are appended where applicable (e.g. _seconds, _minutes).
    Labels follow the pattern: lowercase_with_underscores.

Metric types used:
    - Counter: Cumulative count that only increases (requests, decisions, events).
    - Gauge: Snapshot value that goes up and down (connections, health, pending).
    - Histogram: Distribution of values across configurable buckets (latency, duration).
    - Info: Static key-value metadata about the instance.

Every metric includes a HELP string as the second argument, and most include
labelnames for dimensional slicing. The histogram buckets are tuned to the
expected value ranges for each use case.

Metric families (15 total):
    1.  fabric_requests_total              — Counter  — HTTP requests (method, path, status)
    2.  fabric_request_duration_seconds    — Histogram — HTTP latency
    3.  fabric_routing_overhead_seconds    — Histogram — routing time (excludes server call)
    4.  fabric_server_health               — Gauge    — per-server health (1/0)
    5.  fabric_server_tool_count           — Gauge    — number of tools per server
    6.  fabric_policy_decisions_total      — Counter  — policy allow/deny decisions
    7.  fabric_policy_evaluation_duration  — Histogram — policy evaluation time
    8.  fabric_approvals_pending           — Gauge    — pending approval count
    9.  fabric_approval_duration_minutes   — Histogram — approval resolution time
    10. fabric_audit_events_total          — Counter  — audit events by type
    11. fabric_db_connections              — Gauge    — database pool connections
    12. fabric_redis_connections           — Gauge    — Redis pool connections
    13. fabric_celery_tasks_total          — Counter  — Celery tasks by type/status
    14. fabric_info                        — Info     — static instance metadata
"""

from prometheus_client import Counter, Gauge, Histogram, Info

fabric_requests_total = Counter(
    "fabric_requests_total",
    "Total number of HTTP requests",
    labelnames=["method", "path", "status", "agent_class"],
)

fabric_request_duration_seconds = Histogram(
    "fabric_request_duration_seconds",
    "HTTP request latency in seconds",
    labelnames=["method", "path", "status"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

fabric_routing_overhead_seconds = Histogram(
    "fabric_routing_overhead_seconds",
    "Routing time excluding server call",
    labelnames=["server_id"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5),
)

fabric_server_health = Gauge(
    "fabric_server_health",
    "Server health status (1=healthy, 0=unhealthy)",
    labelnames=["server_id", "server_name"],
)

fabric_server_tool_count = Gauge(
    "fabric_server_tool_count",
    "Number of tools per server",
    labelnames=["server_id", "server_name"],
)

fabric_policy_decisions_total = Counter(
    "fabric_policy_decisions_total",
    "Total policy decisions",
    labelnames=["agent_class", "server_id", "decision"],
)

fabric_policy_evaluation_duration = Histogram(
    "fabric_policy_evaluation_duration",
    "Policy evaluation time in seconds",
    labelnames=["agent_class"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5),
)

fabric_approvals_pending = Gauge(
    "fabric_approvals_pending",
    "Number of pending approval requests",
)

fabric_approval_duration_minutes = Histogram(
    "fabric_approval_duration_minutes",
    "Time to resolve an approval in minutes",
    labelnames=["status"],
    buckets=(1, 5, 15, 30, 60, 120, 360, 720, 1440),
)

fabric_audit_events_total = Counter(
    "fabric_audit_events_total",
    "Total audit events logged",
    labelnames=["event_type"],
)

fabric_db_connections = Gauge(
    "fabric_db_connections",
    "Current database connection count",
    labelnames=["pool"],
)

fabric_redis_connections = Gauge(
    "fabric_redis_connections",
    "Current Redis connection count",
    labelnames=["pool"],
)

fabric_celery_tasks_total = Counter(
    "fabric_celery_tasks_total",
    "Total Celery tasks",
    labelnames=["task_type", "status"],
)

fabric_info = Info(
    "fabric_info",
    "Static metadata about this MCP Fabric instance",
)
