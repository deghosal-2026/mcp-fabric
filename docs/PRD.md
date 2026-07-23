# MCP Fabric — Product Requirements Document

> **TLDR:** A fabric layer for MCP servers: discovery, schema normalization, trust policies, capability routing, and tool composition across many MCP backends.

---

## WHY — The Problem

### The Painful Truth

A pile of MCP servers is not a platform.

MCP solves one important problem: a standard interface for AI tools and data. It does not solve the next problem that appears immediately after success: tool ecosystem sprawl.

As soon as a team adds multiple MCP servers, several hard questions emerge:

- Which tools should be exposed to which agents?
- How should overlapping capabilities be described?
- What trust level should be assigned to each server?
- How should an agent choose between several tools that look similar?
- How should a platform team audit and govern usage across the whole tool ecosystem?

### Market Context

MCP is growing rapidly. The number of publicly available MCP servers, clients, and integrations is accelerating. Much of the community energy right now is focused on building individual servers — connecting one more tool, wrapping one more API.

That work is valuable, but it creates a second-order problem: the more successful MCP becomes, the more urgent the governance and discovery problem becomes.

MCP Fabric occupies the space directly above that growth curve. If MCP grows, the need for tool governance, routing, packaging, and discovery grows with it.

### User Problems

**Problem 1: Tool Discovery Is Unstructured**

Agents and developers see many tools but lack a coherent capability model. There is no way to ask "which server can help me understand this incident?" and get a ranked, policy-respected answer.

**Problem 2: Schema Drift and Naming Drift**

Different servers expose similar actions with different names, parameters, and result conventions. Two servers might both offer "search" but expect different inputs and return different shapes. Agents have no standard way to normalize across them.

**Problem 3: Trust and Permission Ambiguity**

There is often no clear answer to which tools are safe for which workflows. A code search tool and a deployment tool live side by side with the same implicit trust level. Platform teams lack controls to restrict powerful tools to specific agent classes.

**Problem 4: No Tool Ecosystem Governance**

Even if individual servers are well built, the platform has no single place to audit usage, resolve overlap, or curate bundles for different users. Compliance and oversight are manual or nonexistent.

---

## WHAT — MCP Fabric

### Vision

An organization has many MCP servers: code search, docs, incidents, PRs, cost analytics, deployment tools, knowledge retrieval, and internal governance systems. Instead of connecting clients to each one manually, the organization connects agents to MCP Fabric.

MCP Fabric provides:

- a registry of all servers and tools
- normalized capability metadata
- trust and permission levels
- routing from requested capability to best-fit tool
- curated capability packs for different agent classes
- full audit of routed calls and policy decisions

Agents stop thinking in terms of arbitrary server sprawl and instead receive a coherent capability layer.

### Who It's For

**Primary:** Platform teams and advanced agent builders managing multiple MCP servers.

**Secondary:**
- Developer experience teams building internal AI tooling platforms
- OSS builders creating reusable MCP ecosystems
- Teams standardizing how AI agents interact with internal tools and data

**Not For:**
- Users who only need one or two local tools
- Teams that do not yet have an MCP footprint

### Product Scope

**In Scope:**
- MCP server registry
- Capability normalization and cataloging
- Trust and permission layer
- Capability-based routing
- Audit logs and usage analytics
- Simple admin UI

**Out of Scope for Initial Versions:**
- Replacing MCP clients
- Rewriting third-party MCP servers
- Solving every auth model in v1
- Full enterprise directory integration

### Design Principles

- **Do not hide protocol reality unnecessarily** — transparency over magic
- **Normalize enough to help, not so much that semantics are lost** — capability modeling is a balance, not a brute-force problem
- **Make trust explicit and inspectable** — every routing decision should be explainable
- **Optimize for curated capability distribution, not raw tool count** — a small well-governed set beats a large ungoverned one

---

## Customer User Journeys

### Journey 1: Platform Engineer Registers a New MCP Server

**Persona:** Priya, platform engineer on a team managing 12 MCP servers for internal AI agents.

**Scenario:** The security team has built a new MCP server that exposes vulnerability scanning and dependency audit tools. Priya needs to add it to the platform so approved agents can use it — but not all agents should have access to vulnerability data.

**Step by Step:**

1. Priya opens the MCP Fabric admin UI and navigates to the server registry.
2. She enters the server endpoint and metadata (name, owner team, description, version).
3. Fabric inspects the server's `/tools/list` endpoint and pulls in all exposed tool definitions and schemas.
4. The admin UI shows the imported tools with auto-detected input/output schemas and a suggested trust level.
5. Priya reviews the tool list: `scan_vulnerabilities`, `list_dependencies`, `check_deprecation`.
6. She sets `scan_vulnerabilities` to "restricted" (requires explicit approval) and the others to "trusted."
7. She tags the server with labels: `security`, `production`, `read-only`.
8. Fabric maps each tool into the capability catalog — `scan_vulnerabilities` maps to `vulnerability:scan`, `list_dependencies` maps to `dependency:list`.
9. Priya saves. The server is now live in the registry and available to agents matching the trust policy.

**Outcome:** A new MCP server is registered, its tools are inspected and classified, trust levels are assigned, and capabilities are normalized — all in a single UI session. Agents can discover and use the tools without Priya touching any client configuration.

---

### Journey 2: Agent Requests a Capability Through the Fabric

**Persona:** An automated incident response agent ("Igor") operating in a production environment with access to incident management, code search, deployment, and knowledge base MCP servers.

**Scenario:** A P1 incident is triggered. Igor needs to find recent code changes that could be related, check if there's a known runbook, and assess blast radius — all through different tools.

**Step by Step:**

1. Igor receives an alert and needs capability `code:blameless-diff` to find recent changes to the failing service.
2. Igor sends a capability request to MCP Fabric: `{ capability: "code:blameless-diff", params: { service: "payment-api", since: "2h" } }`.
3. Fabric's routing engine resolves the capability against the registry. Three MCP servers advertise related capabilities:
   - Code Search server — capability `code:blameless-diff`, trust level `trusted`
   - Git History server — capability `code:diff`, trust level `trusted`
   - Docs server — capability `code:blameless-diff`, trust level `restricted` (docs-only context)
4. The policy layer checks Igor's agent class (`incident-responder`) against each server's trust policy. All three are allowed, but the Docs server is lower confidence for this use case.
5. The routing engine selects the Code Search server (best capability match + trusted + lowest latency).
6. Fabric proxies the request, returns the normalized response, and logs the routing decision.
7. Igor proceeds with the incident response. Later, Igor also fetches the runbook via capability `knowledge:runbook-get` and assesses blast radius via `dependency:impact-analysis`.

**Outcome:** Igor gets the right tool for each task without knowing which server provides it. Fabric handled discovery, policy check, routing, and audit transparently. The incident response is faster and safer than if Igor had to query each server manually.

---

### Journey 3: Platform Team Curates a Capability Bundle for New Hires

**Persona:** Alex, developer experience lead, onboarding a new engineer to the platform team.

**Scenario:** New hires need access to a focused set of tools: docs search, code search, PR status, and onboarding guides. They should not have access to deployment, vulnerability scanning, or cost analytics tools until they're ramped.

**Step by Step:**

1. Alex opens the admin UI and navigates to "Capability Packs."
2. She creates a new pack called "New Hire — Platform Engineer."
3. She browses the capability catalog and selects:
   - `knowledge:doc-search` (trusted, read-only)
   - `code:search` (trusted, read-only)
   - `code:pr-status` (trusted, read-only)
   - `onboarding:guide-get` (trusted)
4. She saves the pack and assigns it to the agent identity class `agent:new-hire`.
5. When a new hire's agent connects to Fabric, it sees only the capabilities in this pack.
6. Alex can later promote the agent to the full `agent:platform-engineer` class, which unlocks deployment and vulnerability tools.
7. Fabric provides a usage report showing which capabilities the pack is using most and where new hires request capabilities that are not in their pack (signal for expansion).

**Outcome:** Alex can onboard new engineers with a curated, safe tool surface. No manual per-server configuration. No risk of exposing powerful tools too early. Usage data helps evolve the pack over time.

---

### Journey 4: Security Admin Reviews Trust Posture and Audit Logs

**Persona:** Jordan, security engineer responsible for AI tool governance across the organization.

**Scenario:** A quarterly audit is due. Jordan needs to review which MCP servers are registered, what trust levels are assigned, whether any policy exceptions have been granted, and whether any unusual access patterns exist.

**Step by Step:**

1. Jordan opens the Fabric admin dashboard and goes to the "Trust Posture" view.
2. The dashboard shows all 15 registered servers, each with:
   - Trust level (trusted / restricted / approval-gated)
   - Owner team
   - Last health check status
   - Number of tools exposed
   - Recent policy changes
3. Jordan notices one server listed as "unreviewed" — a developer team registered it last week but no one assigned a trust level.
4. Jordan drills in, reviews the tool list, and marks it as "restricted" pending a full security review.
5. Jordan then opens the Audit Log and filters by "denied requests" over the last 30 days.
6. Several denied requests stand out: an agent tried to call `deployment:promote` from a `read-only` agent class.
7. Jordan reviews the denial reason: policy match — correct behavior. No exception needed.
8. Jordan also sees a trend: three different agents requested `database:query` in the last week, but no server offers that capability. This becomes a signal to the platform team.
9. Jordan exports the audit report as JSON for the compliance system.

**Outcome:** Jordan has full visibility into the MCP tool ecosystem. Servers without trust review are caught. Policy violations are auditable. Capability gaps are surfaced from real agent demand. The platform is governable.

---

### Journey 5: Agent Onboards and Gets Its Capability Surface

**Persona:** A new incident response agent ("Igor v2") being deployed for the first time into production.

**Scenario:** The team has built a new agent to handle deployment-health monitoring. It needs access to deployment status, service metrics, and incident tools — but not vulnerability or cost data. Before it can make any capability requests, it must connect to Fabric and get assigned an identity class.

**Step by Step:**

1. The agent starts up with a pre-shared identity token (API key or signed JWT embedded in its deployment config).
2. Agent calls Fabric's connect endpoint with its identity token and declared role: `{ intent: "deployment-health-monitor" }`.
3. Fabric validates the token against the identity store. The token maps to the pre-registered agent identity `agent:deploy-monitor`.
4. Fabric looks up the agent class `agent:deploy-monitor` and resolves its assigned capability pack.
5. Fabric returns the agent's capability surface — a curated list of capabilities it can request:
   - `deployment:status` (trusted)
   - `service:health-metrics` (trusted)
   - `incident:create` (trusted)
   - `incident:get` (trusted)
6. The agent parses its capability surface and is ready to operate within those boundaries.
7. On its first capability request — `deployment:status` — Fabric checks the agent class, confirms `trusted` policy, routes the call, and logs it.
8. On a later request for `vulnerability:scan` — Fabric denies it (not in the assigned capability pack) and logs the denial.

**Outcome:** The agent connected with zero manual server configuration. It received a capability surface scoped exactly to its role. No risky tools are accidentally exposed. The journey from deploy → connect → operate takes seconds and requires no platform engineer intervention beyond the initial agent class setup.

---

### Journey 6: Server Failure — Graceful Degradation and Transparent Fallback

**Persona:** Igor the incident response agent (from Journey 2), mid-incident at 2 AM.

**Scenario:** A production incident is in progress. Igor has been routing capability requests through Fabric for 20 minutes. The Code Search server suddenly becomes unresponsive — a network partition in the hosting cluster. Igor must not fail.

**Step by Step:**

1. Igor requests `code:blameless-diff` for the payment API to identify recent changes.
2. Fabric routes the request to the Code Search server — primary choice based on best capability match, trusted policy, and historical low latency.
3. The request times out after 5 seconds. Fabric retries once — same result.
4. Fabric marks Code Search as `degraded` in the registry, increments its failure counter, and timestamps the event.
5. Fabric checks its fallback chain for `code:blameless-diff`. The Git History server advertises `code:diff` — a partial match but sufficient for recent-change analysis.
6. Policy check: Git History is `trusted` for Igor's agent class `agent:incident-responder`.
7. Fabric routes the request to Git History. The response shape differs from Code Search (commit-level instead of line-level detail), but Fabric normalizes it to the standard `code:blameless-diff` output schema.
8. Fabric logs the full event: primary server failed, fallback server used, normalization applied, latency delta (+800ms).
9. Fabric triggers an alert: "Code Search server degraded — failover count 3 in last 5 minutes. Notify platform-oncall."
10. The platform on-call engineer receives the alert and begins investigating the Code Search outage.
11. Igor continues its incident response using Git History for code diffs. The user never sees the failure.

**Outcome:** A server failure at 2 AM didn't block the incident response. Fabric handled fallback, normalization, and alerting transparently. The platform team was notified without the agent or its user needing to know the route changed. The pathway from failure → fallback → alert → investigation is fully captured in audit.

---

### Journey 7: Approval-Gated Capability — Human-in-the-Loop Review

**Persona:** CRBot, a code review agent that suggests fixes. Priya, the platform engineer responsible for deployment gates.

**Scenario:** CRBot has completed a code review and identified a safe configuration change to fix a feature flag misconfiguration. It wants to promote the change to staging. The deployment capability is `approval-gated` for CRBot's agent class — a human must approve before Fabric routes the call.

**Step by Step:**

1. CRBot finishes its review. It determines the fix is low-risk: a feature flag toggle in staging. It requests capability `deployment:promote` with parameters `{ service: "config-api", env: "staging", change: "toggle feature flag enable-new-checkout" }`.
2. Fabric checks the policy layer. `deployment:promote` is tagged `approval-gated` for agent class `agent:code-reviewer`.
3. Fabric does not route the request. Instead, it creates a pending approval record with full context:
   - Agent: CRBot (code-reviewer)
   - Capability: deployment:promote
   - Parameters: config-api, staging, feature flag toggle
   - Server: Deployment Server v2.1
   - Timestamp
4. Fabric sends a notification to the deployment approver group: "CRBot requests deployment:promote — review in admin UI."
5. Priya receives the notification. She opens the admin UI and reviews the request. She sees it's a low-risk staging toggle from a trusted reviewer agent.
6. Priya clicks "Approve." Fabric logs the approval decision and immediately routes the request to the Deployment Server.
7. The Deployment Server executes the promote action and returns the result. Fabric normalizes the response and passes it back to CRBot with the approval trail attached.
8. If Priya had clicked "Deny," Fabric would return a standardized denial to CRBot with the reason she provided, log the denial, and close the approval record.

**Outcome:** Sensitive capabilities are gated behind human approval without blocking agent workflows entirely. The approval flow is fast, auditable, and doesn't require the agent to know the mechanism — it just waits for a response. Every approval or denial is captured for compliance.

---

### Journey 8: OSS Contributor Self-Hosts and Tests End-to-End

**Persona:** Taylor, an open-source developer who builds MCP servers and wants to try MCP Fabric.

**Scenario:** Taylor found MCP Fabric on GitHub. She has two local MCP servers running: a filesystem server and a git server. She wants to see if Fabric makes them feel like a single coherent platform. She has 10 minutes to get a first impression.

**Step by Step:**

1. Taylor clones the repo and reads the README. One command: `docker-compose up`.
2. She runs it. Docker pulls images and within 60 seconds the admin UI is at `http://localhost:8000/admin`.
3. Taylor opens the admin UI. The server registry is empty — she's the first user of this instance.
4. She clicks "Register Server" and enters her filesystem server endpoint: `http://localhost:3001`. She adds metadata: "Local FS Server," owner "taylor-dev," labels `filesystem`, `local`.
5. Fabric inspects the server, pulls its tool list (`read_file`, `write_file`, `list_directory`, `search_files`), and displays them with auto-detected schemas.
6. Taylor repeats for her git server on `http://localhost:3002`. Fabric imports `git_diff`, `git_log`, `git_status`.
7. Taylor navigates to the Capability Catalog. She maps the imported tools to capabilities: filesystem tools → `fs:read`, `fs:write`, `fs:list`, `fs:search`; git tools → `code:diff`, `code:log`, `code:status`.
8. She creates an agent class `agent:developer` and assigns both servers as `trusted`.
9. Taylor opens a terminal and sends a test request via curl: `POST /capability/request { "capability": "code:diff", "params": { "repo": ".", "since": "1h" } }`. She includes the agent identity header.
10. Fabric routes to the git server, returns the diff normalized, and logs the call. The response is clean and consistent.
11. Taylor checks the Audit Log in the admin UI — her test call is there with routing detail, latency, and server chosen.
12. Total time from clone to first successful capability request: under 8 minutes.

**Outcome:** Taylor validated the full Fabric flow — registry, capability mapping, routing, audit — entirely locally with her own MCP servers. No cloud dependencies. No configuration files to hand-edit. She's now positioned to contribute, extend, or integrate Fabric with her own ecosystem. The OSS onboarding experience is measured in single-digit minutes.

---

### Journey 9: Capability Conflict Resolution — Two Servers Claim the Same Thing

**Persona:** Priya, platform engineer (from Journey 1), managing a growing server ecosystem.

**Scenario:** The platform now has 14 MCP servers. During registration of a new code intelligence server, Fabric detects that `code:search` is now claimed by two different servers. Priya must decide which server handles which kind of search request — or whether both can coexist with routing rules.

**Step by Step:**

1. Priya finishes registering the new Code Intelligence server (v0.9). Fabric inspects its tools and maps them to capabilities automatically.
2. During capability mapping, Fabric shows a conflict banner: "Capability `code:search` is claimed by 2 servers — review routing."
3. Priya opens the conflict resolution view. A side-by-side comparison appears:

   | | Code Search (v1.2) | Code Intelligence (v0.9) |
   |---|---|---|
   | Capability | code:search | code:search |
   | Input params | query, file_pattern, max_results | query, scope, include_tests |
   | Output | lines[] | results[] with relevance ranking |
   | Latency (avg) | 400ms | 200ms |
   | Trust level | trusted | trusted |

4. Priya notes that Code Intelligence is faster and returns ranked results, but doesn't support `file_pattern` filtering. Code Search is slower but supports file-pattern-based scoping.
5. Priya sets a routing rule:
   - **Primary:** Code Intelligence for general `code:search` (faster, ranked results).
   - **Fallback/Override:** Code Search when `params.file_pattern` is present in the request.
6. She saves the routing rule. Fabric now routes `code:search` requests based on parameter presence — no agent needs to know which server handles which request.
7. Fabric logs the conflict resolution: who resolved it, when, what rules were set. This is visible to Jordan in future audits.

**Outcome:** Two servers with overlapping capabilities coexist with clear, inspectable routing logic. Priya resolved the conflict in minutes without removing either server. Agents get the best tool for each specific request without knowing the behind-the-scenes server selection. The decision is auditable.

---

### Journey 10: Server Upgrade with Schema Diff — Breaking Change Review

**Persona:** Priya managing a version upgrade of a critical MCP server.

**Scenario:** The Code Search server team ships v2.0. The `search_code` tool now requires a new `context_lines` parameter, drops `file_pattern`, and returns structured results instead of raw text lines. Priya needs to update Fabric's registry without breaking agents that expect the old schema.

**Step by Step:**

1. Priya opens the Code Search server entry in the admin UI and clicks "Re-inspect."
2. Fabric re-fetches the tool list from the server's `/tools/list` endpoint.
3. Fabric compares the new tool definitions against the stored previous version and shows a schema diff:

   ```
   search_code:
     + context_lines (required, int) — new required parameter
     - file_pattern (was optional, string) — removed
     ~ output format: lines[] → results[] {line, score, snippet}
   
   search_symbols:
     + (new tool) — no previous version
   ```

4. Fabric flags the `search_code` changes as **potentially breaking** — removed parameter, changed output schema. It warns that agents expecting the old schema may get errors.
5. Priya reviews the diff. She updates the capability mapping for `code:search` to reflect the new `context_lines` parameter in the normalized input schema. She sets the parameter as required in the catalog so agents discover the change when they query capabilities.
6. She registers the new `search_symbols` tool and maps it to capability `code:symbol-search`.
7. She activates the updated server entry. Fabric now routes `code:search` with the v2 schema.
8. Priya also toggles a deprecation banner on the previous capability mapping: "Schema changed 2026-08-15 — see updated `code:search` input contract." Agents that list capabilities before making requests will see this.
9. Jordan (the security admin from Journey 4) will see the schema change recorded in the audit log — which server changed, what changed, when, and who approved it.

**Outcome:** Server upgrades don't create silent breakage. Fabric diffs old and new schemas, flags breaking changes for human review, and lets the platform engineer activate with full context. Agents can self-discover schema changes through the capability catalog. The change is auditable.

---

## Feature Catalog

### 1. Registry

The single source of truth for every MCP server connected to the fabric.

| Feature | Description |
|---|---|
| Server registration | Add, update, remove MCP server endpoints with metadata |
| Auto-inspection | On registration, fetch `/tools/list` and import all tool definitions |
| Metadata store | Name, owner, version, description, labels, trust level, health status |
| Health checks | Periodic pings to registered servers (optional, configurable interval) |
| Status dashboard | See all servers, their tool counts, health, and last-updated |

### 2. Capability Catalog

Normalizes raw MCP tool definitions into a queryable, consistent capability model.

| Feature | Description |
|---|---|
| Tool ingestion | Parse tool definitions from registered MCP servers |
| Capability mapping | Map raw tools to normalized capability terms (e.g., `code:search`, `incident:get`) |
| Schema normalization | Store unified input/output schemas with original schemas preserved |
| Conflict detection | Flag tools from different servers that map to the same capability for review |
| Search and browse | Query the catalog by capability name, tool name, server, or label |

### 3. Routing Engine

Selects the right server and tool for each capability request.

| Feature | Description |
|---|---|
| Capability resolution | Match an incoming capability request to one or more candidate tools |
| Policy-aware selection | Filter candidates by agent class trust policy before ranking |
| Latency hints | Optionally prefer lower-latency servers when multiple match |
| Fallback chain | If the primary server fails, try the next best match |
| Response normalization | Return a consistent response shape regardless of which server handled the request |
| Explainability | Attach the routing decision reason to each response for audit and debugging |

### 4. Policy Layer

Controls which agents can access which tools under which conditions.

| Feature | Description |
|---|---|
| Trust levels | Assign `trusted`, `restricted`, or `approval-gated` to each server or individual tool |
| Agent class mapping | Define agent classes and map them to allowed trust levels |
| Policy rules | Simple Python rules for conditions, exceptions, and overrides |
| Approval workflows | Optional async approval flow for `approval-gated` capability requests |
| Policy audit trail | Log every policy match, denial, and exception |

### 5. Audit Pipeline

Captures every routed call, denial, fallback, and policy decision.

| Feature | Description |
|---|---|
| Request log | Every capability request: agent, capability, server chosen, latency, outcome |
| Denial log | Every denied request: agent, capability, policy rule that denied it |
| Policy change log | Every trust level change, agent class update, or rule modification |
| Export | JSON and CSV export for compliance and analysis |
| Retention | Configurable retention window with automatic archival |

### 6. Admin UI

A web interface for managing the fabric.

| Feature | Description |
|---|---|
| Server inventory | Table of all registered servers with health, trust level, tool count |
| Capability browser | Search and browse the capability catalog with drill-down into tools |
| Policy editor | Create and modify trust levels, agent classes, and policy rules |
| Bundle curator | Create capability packs by selecting capabilities and assigning agent classes |
| Audit viewer | Filterable log viewer for requests, denials, and policy changes |
| Trust posture | At-a-glance view of unreviewed servers, policy exceptions, and risk signals |

### 7. Alerting

Proactive notifications for events that require platform team attention.

| Feature | Description |
|---|---|
| Health degradation alerts | Notify when a server fails N consecutive health checks or failover count spikes |
| Unreviewed server alert | Notify when a server remains unreviewed beyond a configurable threshold (default 48 hours) |
| Denial rate spike alert | Notify when an agent class experiences a sudden increase in denied capability requests |
| Schema change notification | Notify admins when a server's tool schema changes after re-inspection |
| Notification channels | Email, webhook, Slack — configurable per alert type |
| Alert history | Browse and filter past alerts alongside audit logs |

These alerts surface naturally in existing journeys — Jordan (Journey 4) gets proactive alerts instead of purely manual review, and the platform team is notified automatically during server failures (Journey 6).

---

## Success Metrics

| Metric | Target | How to Measure |
|---|---|---|
| Agent tool selection consistency | Agents choose the same best tool for the same capability request >95% of the time | Audit log analysis |
| Audit coverage | 100% of routed calls and denials captured in audit pipeline | Pipeline health check |
| Time to register new server | < 5 minutes from endpoint URL to production availability | UX benchmark |
| Trust review lag | No server remains unreviewed for > 48 hours | Registry status tracking |
| Capability pack adoption | 80%+ of agents use curated packs rather than raw server access | Agent class distribution |
| External engagement | 3+ external contributors or adopters within 6 months of v0.1.0 | GitHub issues, PRs, discussions |
| Routing accuracy | Correct server selected for capability request >90% of evaluation cases | Manual eval against test scenarios |

---

## PR/FAQ

**FOR IMMEDIATE RELEASE**

### MCP Fabric Launches to Turn a Pile of MCP Servers Into a Real Agentic Platform

**SEATTLE, WA** — Debashish Ghosal today announced MCP Fabric, an open-source tool mesh for MCP ecosystems. MCP Fabric provides discovery, schema normalization, trust policies, and capability routing so teams can run many MCP servers as a coherent agentic platform rather than a loose collection of connectors.

"MCP is becoming the interface standard for agent tools, but standards don't remove platform problems," said Ghosal. "Once teams have many servers, they need discovery, curation, and trust controls. MCP Fabric is that missing layer."

Available at [github.com/deghosal-2026/mcp-fabric](https://github.com/deghosal-2026/mcp-fabric).

### FAQ

**Q: Isn't MCP already enough?**

A: MCP standardizes the interface. MCP Fabric manages the ecosystem that grows on top of it.

**Q: Who benefits most?**

A: Platform teams, AI infrastructure teams, and advanced builders working with many MCP servers.

**Q: Can this be built locally?**

A: Yes. The reference architecture is deliberately local-first and OSS-only.

**Q: How is this different from a simple proxy?**

A: A proxy relays calls. MCP Fabric models capabilities, enforces policy, resolves ambiguity, and provides audit. The hard part is not forwarding requests — it is choosing the right tool under the right policy and explaining why.

**Q: What makes the MVP good enough?**

A: If an agent connected through the fabric has a cleaner, safer, more understandable tool experience than the same agent connected directly to raw server sprawl, the MVP is meaningful.

---

## Future Considerations

Scenarios and features explicitly deferred from v0.1.0 — important, but not in the initial build scope.

### Multi-Environment Separation (dev / staging / prod)

A production incident response agent should not see dev servers, and a dev agent should never route through production servers. Currently, Fabric trusts the platform engineer to label servers correctly. A first-class environment tag with enforced isolation (servers tagged `env:prod` are invisible to agents tagged `env:dev` and vice versa) is a natural v0.2.0 addition.

### Rate Limiting and Quota

There is no mechanism today to prevent an agent from flooding the fabric with capability requests. Rate limiting per agent class, per capability, and per server — with configurable quotas and burst allowances — belongs in the routing engine as a policy extension.

### API and CLI Access for CI/CD

All journeys are UI-driven. Platform teams running automated tests or CI pipelines need programmatic access: register servers, update policies, and query audit logs via API or CLI. The admin API exists internally — exposing it with stable endpoints and authentication is a v0.2.0+ item.

### PII and Sensitive Data Controls in Audit Logs

Tool responses may contain sensitive data (code, configuration, customer identifiers). The audit pipeline today logs routed calls with full response payloads. A configurable redaction or sampling policy for audit log content — or the ability to log only metadata (capability, server, latency) without the response body — should be added before production deployment.

### Horizontal Scaling of Fabric Itself

Fabric is a central routing layer. As server count and request volume grow, Fabric itself becomes a bottleneck. The current architecture assumes a single Fabric instance. Multi-instance Fabric with shared registry state, leader election for health checks, and distributed routing is a future scaling concern.

### API Versioning for the Fabric Protocol

The capability request format, agent identity format, and normalized response schema will evolve. A versioned Fabric API (`/v1/capability/request` vs `/v2/`) lets clients and agents adopt changes without breakage. This should be designed before the first external integration lands.

### Multi-Organization / Federation

Two organizations each running their own Fabric instance may want to share select capabilities (e.g., a partner team's docs search server). Cross-fabric federation — capability sharing, trust delegation, and audit across Fabric instances — is a long-term platform vision.
