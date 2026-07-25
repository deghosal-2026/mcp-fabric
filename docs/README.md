# MCP Fabric Documentation

Welcome to the MCP Fabric documentation.

## Overview

- [Architecture Overview](ARCHITECTURE.md) — Component architecture, request lifecycle, state management, scaling boundaries
- [Product Requirements Document](PRD.md) — Problem statement, user journeys, feature catalog, success metrics
- [Technical Specification](spec.md) — API contract, database schema, OPA integration, Celery tasks, test strategy
- [Design Document](DESIGN.md) — Auth design, state machines, sequence diagrams, caching strategy, concurrency model

## User Guides

- [Admin UI Walkthrough](user-guide.md) — Screenshot-guided tour of the admin dashboard

## Operation Guides

- [Development Guide](guides/development.md) — Local setup, running tests, database migrations, Docker Compose
- [Deployment Guide](guides/deployment.md) — Production deployment, health checks, backup/restore, blue-green upgrades
- [Configuration Reference](guides/configuration.md) — All environment variables, feature flags, example `.env`
- [Monitoring Guide](guides/monitoring.md) — Prometheus metrics, Grafana dashboard, Alertmanager rules, OpenTelemetry
- [Security Guide](guides/security.md) — Authentication, RBAC, token lifecycle, CORS, threat mitigations
- [Troubleshooting Guide](guides/troubleshooting.md) — Common issues, diagnostic steps, solutions

## Other

- [Changelog](CHANGELOG.md) — Release history
- [Contributing](../CONTRIBUTING.md) — How to contribute to MCP Fabric
- [Security Policy](../SECURITY.md) — Vulnerability reporting

## Quick Links

| Resource | Location |
|----------|----------|
| Issue tracker | https://github.com/deghosal-2026/mcp-fabric/issues |
| Source code | https://github.com/deghosal-2026/mcp-fabric |
| API docs (dev) | http://localhost:8000/docs |
| UI (dev) | http://localhost:3000 |
