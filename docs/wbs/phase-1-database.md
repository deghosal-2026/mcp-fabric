# Phase 1: Database & Models

> **Tasks:** 82 · **Effort:** 60h (7.5 days)  
> **Dependencies:** Phase 0 complete

## 1.1 ORM Models (20 tasks)

### P1-01: MCPServer Model (#48)
**Effort:** 2h | **Deps:** P0-07, P0-11

**Checklist:**
- [ ] `__tablename__ = "mcp_servers"`
- [ ] id UUID PK, name VARCHAR(255) NOT NULL, endpoint VARCHAR(1024) NOT NULL
- [ ] owner_team, description nullable
- [ ] labels JSONB default []
- [ ] trust_level VARCHAR(50) default "unreviewed"
- [ ] health_status VARCHAR(50) default "unknown"
- [ ] last_health_check TIMESTAMPTZ nullable
- [ ] registered_at, updated_at TIMESTAMPTZ
- [ ] decommissioned_at, decommission_phase, version, team_namespace nullable
- [ ] Relationships: tools→ServerTool, tool_versions→ToolVersion, mappings→CapabilityMapping, trust→TrustAssignment
- [ ] Indexes: idx_servers_team, idx_servers_trust, idx_servers_health

**Success Criteria:** Table creates on SQLite + PostgreSQL. JSONB works on both. Cascade delete removes tools.

### P1-02: ServerTool Model (#50)
**Effort:** 1.5h | **Deps:** P1-01

**Checklist:**
- [ ] id UUID PK, server_id FK→mcp_servers CASCADE, tool_name VARCHAR(255)
- [ ] description TEXT, input_schema JSONB NOT NULL, output_schema JSONB
- [ ] UNIQUE(server_id, tool_name)
- [ ] Index: idx_tools_server
- [ ] Relationship: server→MCPServer

**Success Criteria:** Table creates. Unique constraint enforced. JSONB queries work.

### P1-03: ToolVersion Model (#54)
**Effort:** 1h | **Deps:** P1-01

**Checklist:**
- [ ] id UUID PK, server_id FK CASCADE, tool_name, input_schema, output_schema
- [ ] detected_at TIMESTAMPTZ, is_breaking BOOLEAN default False
- [ ] Index: idx_tool_versions_server(server_id, tool_name)
- [ ] Relationship: server→MCPServer

**Success Criteria:** Each inspect stores version record. is_breaking flag for schema changes.

### P1-04: Capability Model (#57)
**Effort:** 1.5h | **Deps:** P0-07

**Checklist:**
- [ ] id UUID PK, name VARCHAR(255) UNIQUE, domain VARCHAR(100)
- [ ] normalized_input_schema, normalized_output_schema JSONB
- [ ] description TEXT, status VARCHAR(50) default "active" (active/deprecated)
- [ ] deprecated_at TIMESTAMPTZ, grace_period_days INT default 14, migration_guidance TEXT
- [ ] created_at, created_by
- [ ] Relationships: mappings→CapabilityMapping, aliases→CapabilityAlias
- [ ] Indexes: idx_capabilities_domain, idx_capabilities_status, idx_capabilities_name

**Success Criteria:** Table creates. Status one-way transition (active→deprecated). Aliases resolve to parent.

### P1-05: CapabilityMapping Model (#60)
**Effort:** 1h | **Deps:** P1-01, P1-04

**Checklist:**
- [ ] id UUID PK, capability_id FK CASCADE, server_id FK CASCADE, tool_name
- [ ] input_mapping, output_mapping JSONB nullable
- [ ] is_primary BOOLEAN default True, routing_weight FLOAT default 1.0
- [ ] created_at
- [ ] Indexes: idx_mappings_capability, idx_mappings_server

**Success Criteria:** Maps tool to capability. Multiple servers can map same capability. Cascade delete works.

### P1-06: CapabilityAlias Model (#63)
**Effort:** 0.5h | **Deps:** P1-04

**Checklist:**
- [ ] id UUID PK, capability_id FK CASCADE, alias VARCHAR(255) UNIQUE
- [ ] created_at
- [ ] Indexes: idx_aliases_alias, idx_aliases_capability

**Success Criteria:** Alias resolves to parent capability. Unique enforced across all capabilities.

### P1-07: AgentClass Model (#66)
**Effort:** 1h | **Deps:** P0-07

**Checklist:**
- [ ] id UUID PK, name VARCHAR(255) UNIQUE, description TEXT, team_namespace
- [ ] created_at
- [ ] Relationships: trust_assignments, agent_identities, class_packs

**Success Criteria:** Name unique enforced. Relationships return correct collections.

### P1-08: TrustAssignment Model (#69)
**Effort:** 1h | **Deps:** P1-01, P1-07

**Checklist:**
- [ ] id UUID PK, agent_class_id FK CASCADE, server_id FK CASCADE
- [ ] trust_level VARCHAR(50) NOT NULL (trusted/restricted/approval-gated)
- [ ] tool_scope JSONB nullable (null=all, list=specific)
- [ ] UNIQUE(agent_class_id, server_id)
- [ ] Index: idx_trust_class

**Success Criteria:** One trust per class-server pair. tool_scope null allows all tools.

### P1-09: AgentIdentity Model (#71)
**Effort:** 1.5h | **Deps:** P1-07

**Checklist:**
- [ ] id UUID PK, name UNIQUE, agent_class_id FK
- [ ] token_hash VARCHAR(512) NOT NULL (bcrypt), token_prefix VARCHAR(10)
- [ ] status VARCHAR(50) default "active" (active/rotating/revoked/expired)
- [ ] rate_limit_per_min INT default 100
- [ ] expires_at, grace_period_end, rotated_from_id (self-referential FK)
- [ ] created_at, revoked_at
- [ ] Indexes: idx_identities_class, idx_identities_status, idx_identities_token

**Success Criteria:** token_hash is bcrypt, never plaintext. Self-referential FK works. Status state machine enforced.

### P1-10: CapabilityPack Model (#74)
**Effort:** 1h | **Deps:** P0-07

**Checklist:**
- [ ] id UUID PK, name UNIQUE, description TEXT, team_namespace
- [ ] created_at
- [ ] Relationships: pack_assignments, class_packs

**Success Criteria:** Name unique enforced. pack.capabilities returns through pack_assignments.

### P1-11: PackAssignment Model (#77)
**Effort:** 0.5h | **Deps:** P1-04, P1-10

**Checklist:**
- [ ] id UUID PK, pack_id FK CASCADE, capability_id FK CASCADE
- [ ] UNIQUE(pack_id, capability_id)

**Success Criteria:** No duplicate capability in a pack. Cascade delete on both sides.

### P1-12: AgentClassPack Model (#80)
**Effort:** 0.5h | **Deps:** P1-07, P1-10

**Checklist:**
- [ ] id UUID PK, agent_class_id FK CASCADE, pack_id FK CASCADE
- [ ] UNIQUE(agent_class_id, pack_id)

**Success Criteria:** No duplicate pack assignment to a class.

### P1-13: AuditEvent Model (#173)
**Effort:** 1h | **Deps:** P0-07

**Checklist:**
- [ ] id UUID PK, event_type VARCHAR(100), actor_type, actor_id, target_type, target_id
- [ ] details JSONB NOT NULL, created_at TIMESTAMPTZ
- [ ] Indexes: idx_audit_type, idx_audit_actor, idx_audit_time DESC, idx_audit_type_time

**Success Criteria:** Append-only enforced at service layer. Composite indexes optimize common queries.

### P1-14: ApprovalRequest Model (#174)
**Effort:** 1h | **Deps:** P1-04, P1-09, P1-20 (AdminUser)

**Checklist:**
- [ ] id UUID PK, agent_identity_id FK, capability_id FK, server_id FK
- [ ] request_params JSONB, status (pending/approved/denied/expired)
- [ ] approver_id FK→admin_users nullable, approver_note TEXT
- [ ] requested_at, resolved_at, expires_at
- [ ] Indexes: idx_approvals_status, idx_approvals_agent

**Success Criteria:** Status transitions enforced. expires_at defaults to now+1h.

### P1-15: AlertRule Model (#175)
**Effort:** 0.5h | **Deps:** P0-07

**Checklist:**
- [ ] id UUID PK, name, alert_type, condition JSONB, channels JSONB, enabled BOOLEAN

**Success Criteria:** condition stores metric+threshold+window. channels stores delivery targets.

### P1-16: AlertEvent Model (#176)
**Effort:** 0.5h | **Deps:** P1-15, P1-20

**Checklist:**
- [ ] id UUID PK, rule_id FK, message TEXT, details JSONB
- [ ] fired_at, acknowledged_at, acknowledged_by FK→admin_users
- [ ] Indexes: idx_alerts_fired DESC, idx_alerts_rule

**Success Criteria:** Acknowledge sets timestamp+user. History queryable by rule.

### P1-17: RoutingRule Model (#177)
**Effort:** 0.5h | **Deps:** P1-01, P1-04

**Checklist:**
- [ ] id UUID PK, capability_id FK CASCADE, server_id FK CASCADE
- [ ] priority INT default 0, condition JSONB nullable
- [ ] created_at, created_by
- [ ] Index: idx_routing_rules_cap

**Success Criteria:** Rules ordered by priority. condition null = always applies.

### P1-18: OPAPolicyVersion Model (#178)
**Effort:** 0.5h | **Deps:** P1-20

**Checklist:**
- [ ] id UUID PK, version VARCHAR(50), bundle_hash VARCHAR(64), deployed_at, deployed_by, rego_content TEXT

**Success Criteria:** Each deploy creates version record. bundle_hash enables duplicate detection.

### P1-19: AdminUser Model (#179)
**Effort:** 1h | **Deps:** P0-07

**Checklist:**
- [ ] id UUID PK, username UNIQUE, email UNIQUE, password_hash VARCHAR(512)
- [ ] role (admin/editor/viewer), team_namespace
- [ ] mfa_enabled BOOLEAN, mfa_secret encrypted
- [ ] status (active/invited/deactivated), last_login_at, created_at
- [ ] password_history JSONB, failed_attempts INT, locked_until

**Success Criteria:** bcrypt password. Fernet-encrypted MFA secret. Password history prevents reuse.

### P1-20: BackgroundTask Model (#180)
**Effort:** 0.5h | **Deps:** P0-07

**Checklist:**
- [ ] id UUID PK, celery_task_id, task_type, status, params JSONB, result JSONB, error TEXT, created_at, completed_at
- [ ] Index: idx_bgtasks_status, idx_bgtasks_celery

**Success Criteria:** Tracks Celery task execution. Queryable by task_id.

## 1.2 Pydantic Schema Models (30 tasks)

### P1-21: ServerCreate Schema (#181)
**Effort:** 0.5h | **Deps:** None
**Checklist:** name (1-255), endpoint (http/https pattern), owner_team, description optional, labels list[str] default [], team_namespace optional. Custom validator for endpoint reachability check pattern.
**Success Criteria:** Valid input passes. Invalid endpoint pattern → 422. Empty name → 422.

### P1-22: ServerResponse Schema (#182)
**Effort:** 0.5h | **Deps:** P1-21
**Checklist:** All MCPServer fields + tools list[ToolResponse] + created_at + decommissioned_at nullable. model_config from_attributes=True for ORM conversion.
**Success Criteria:** Serializes from MCPServer ORM object correctly.

### P1-23: ToolResponse Schema (#183)
**Effort:** 0.5h | **Deps:** None
**Checklist:** id UUID, tool_name, description optional, input_schema dict, output_schema optional dict.
**Success Criteria:** Serializes from ServerTool ORM object.

### P1-24: ToolChange Schema (#184)
**Effort:** 0.5h | **Deps:** None
**Checklist:** tool_name, changes dict (added_params, removed_params, changed_output), is_breaking bool.
**Success Criteria:** Used in ServerInspectResponse for diff display.

### P1-25: ServerInspectResponse Schema (#185)
**Effort:** 0.5h | **Deps:** P1-22, P1-24
**Checklist:** Extends ServerResponse with tools_added list[ToolResponse], tools_removed list[ToolResponse], tools_changed list[ToolChange].
**Success Criteria:** Full diff visible in single response.

### P1-26: PaginationMeta Schema (#186)
**Effort:** 0.5h | **Deps:** None
**Checklist:** next_cursor optional str, has_more bool, per_page int, total int. Used in all list endpoint responses.
**Success Criteria:** Wraps cursor and offset pagination uniformly.

### P1-27: PaginatedServers Schema (#187)
**Effort:** 0.5h | **Deps:** P1-22, P1-26
**Checklist:** servers list[ServerResponse], pagination PaginationMeta.
**Success Criteria:** GET /servers returns this structure.

### P1-28: CapabilityCreate Schema (#188)
**Effort:** 0.5h | **Deps:** None
**Checklist:** name (pattern: ^[a-z]+:[a-z][a-z-]*$), domain optional, normalized_input_schema optional dict, normalized_output_schema optional dict, description optional. Custom validator for name convention.
**Success Criteria:** Valid pattern passes. Invalid pattern → 422 with format hint.

### P1-29: CapabilityResponse Schema (#189)
**Effort:** 0.5h | **Deps:** P1-28
**Checklist:** All Capability fields + mappings_count int + aliases list[str].
**Success Criteria:** Serializes from Capability ORM.

### P1-30: CapabilityMapping Schema (#190)
**Effort:** 0.5h | **Deps:** None
**Checklist:** server_id, tool_name, input_mapping optional dict, output_mapping optional dict, is_primary bool.
**Success Criteria:** Validates server_id + tool_name exist.

### P1-31- to P1-50: Remaining Schemas
_AgentIdentityCreate, AgentIdentityResponse, AgentConnectResponse, CapabilitySurfaceItem, LoginRequest, TokenResponse, MFASetupResponse, MFAVerifyRequest, MFARecoveryRequest, PasswordResetRequest, SetupCompleteRequest, AuditEventResponse, AuditExportRequest, PackCreate, PackResponse, PackAssignmentRequest, TrustAssignmentCreate, FabricError, PolicyDecision, WebhookRegistrationRequest_

Each follows the same pattern: fields from spec Section 32, Field validators, examples, from_attributes for ORM.

## 1.3 Migrations (4 tasks)

### P1-51: Initial Migration (#211)
**Effort:** 2h | **Deps:** P1-01 through P1-20
**Checklist:** `alembic revision --autogenerate -m "initial schema"`. Verify all 20 tables + indexes present. Test upgrade+downgrade on SQLite and PostgreSQL.
**Success Criteria:** All tables create and drop cleanly. Migration file committed.

### P1-52: Migration Validation — SQLite (#212)
**Effort:** 1h | **Deps:** P1-51
**Checklist:** `alembic upgrade head` on :memory: SQLite → verify all tables via `SELECT name FROM sqlite_master WHERE type='table'`. `alembic downgrade -1` → verify all tables removed. Check JSON columns store dicts (SQLite stores as TEXT, SQLAlchemy serializes).
**Success Criteria:** 20 tables created, 0 errors, round-trip clean.

### P1-53: Migration Validation — PostgreSQL (#213)
**Effort:** 1h | **Deps:** P1-51
**Checklist:** `alembic upgrade head` on PostgreSQL → verify via `\dt`. Check JSONB columns via `SELECT pg_typeof(labels) FROM mcp_servers` → jsonb. `alembic downgrade -1` → verify clean.
**Success Criteria:** 20 tables created, JSONB confirmed, round-trip clean.

### P1-54: Auto-Generation Test (#214)
**Effort:** 1h | **Deps:** P1-52, P1-53
**Checklist:** Add a test field to MCPServer model → `alembic revision --autogenerate -m "test"` → verify migration detects new column → `alembic upgrade head` → new column exists → `alembic downgrade -1` → column removed → discard test migration.
**Success Criteria:** Auto-generation detects model changes correctly.

## 1.4 Data Seeding (3 tasks)

### P1-55: Default Agent Classes Seeder (#215)
**Effort:** 1h | **Deps:** P1-07
**Checklist:** Seed 6 default agent classes on first run: agent:admin, agent:incident-responder, agent:deploy-monitor, agent:code-reviewer, agent:developer, agent:new-hire. Check if classes already exist before seeding.
**Success Criteria:** Fresh DB has 6 classes. Re-run is idempotent.

### P1-56: Default Alert Rules Seeder (#216)
**Effort:** 1h | **Deps:** P1-15
**Checklist:** Seed 5 default alert rules: server_degradation (3+ unhealthy in 5min), unreviewed_server (>0 for >48h), denial_spike (>10% for any class), schema_change_detected (any), fabric_error_rate (>1% for 5min). With default channels=["email"].
**Success Criteria:** Fresh DB has 5 rules. Re-run idempotent.

### P1-57: First Admin User Bootstrap (#217)
**Effort:** 1h | **Deps:** P1-19
**Checklist:** On first startup with 0 admin users + FABRIC_ADMIN_EMAIL + FABRIC_ADMIN_PASSWORD env vars set: create admin user with admin role, active status, no team namespace. If vars not set and 0 users: log warning, allow first login to auto-create admin.
**Success Criteria:** Fresh DB boots with admin user. Re-run idempotent.

## 1.5 Model Validation (3 tasks)

### P1-58: JSONB Compatibility Tests (#218)
**Effort:** 1h | **Deps:** P1-51
**Checklist:** Write test that creates MCPServer with labels=["code","production"], queries WHERE labels @> '["code"]' on PostgreSQL, verifies equivalent query works on SQLite. Test JSONB read/write for input_schema on ServerTool.
**Success Criteria:** JSON operations identical on both databases. No database-specific code paths.

### P1-59: Relationship Eager/Lazy Loading Tests (#219)
**Effort:** 1h | **Deps:** P1-01 through P1-20
**Checklist:** Test selectinload for server.tools, server.trust_assignments. Test joinedload for capability.mappings. Verify N+1 queries avoided with proper loading strategy.
**Success Criteria:** Relationship access doesn't trigger unexpected queries. Eager loading works where configured.

### P1-60: Cascade Delete Tests (#220)
**Effort:** 1h | **Deps:** P1-01 through P1-20
**Checklist:** Delete server → verify ServerTool + ToolVersion deleted. Delete capability → verify CapabilityMapping + CapabilityAlias deleted. Delete pack → verify PackAssignment + AgentClassPack deleted.
**Success Criteria:** All cascades work. No orphaned rows.
