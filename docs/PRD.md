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
