import { QueryClient } from '@tanstack/react-query'
import { useAuthStore } from '../stores/authStore'
import type {
  MCPServer, ServerDetail, Capability, CapabilityMapping,
  AgentClass, AgentIdentity, TrustAssignment,
  ApprovalRequest, AuditEvent, CapabilityPack,
  AlertEvent, AdminUser, DashboardStats, PaginatedResponse,
  PackSafetyMetrics, PackBreadthRow,
} from '../types'

const BASE = '/v1'

export async function fetcher<T>(path: string, options?: RequestInit): Promise<T> {
  const token = useAuthStore.getState().token
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    Accept: 'application/vnd.fabric.v1+json',
    ...(options?.headers as Record<string, string>),
  }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const res = await fetch(`${BASE}${path}`, { ...options, headers })

  if (res.status === 401 && !path.startsWith('/auth/')) {
    useAuthStore.getState().logout()
    window.location.href = '/login'
    throw new Error('Unauthorized')
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.message || `Request failed: ${res.status}`)
  }

  if (res.status === 204) {
    return undefined as unknown as T
  }

  return res.json()
}

async function authFetcher<T>(path: string, token: string, body: unknown): Promise<T> {
  return fetcher<T>(path, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(body),
  })
}

export function buildQuery(base: string, params?: Record<string, string | undefined>): string {
  const search = new URLSearchParams()
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined) search.set(key, value)
    }
  }
  const qs = search.toString()
  return qs ? `${base}?${qs}` : base
}

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 30_000,
      refetchOnWindowFocus: false,
    },
  },
})

// Auth
export function login(username: string, password: string) {
  return fetcher<{ token: string; user: import('../types').AuthUser; mfa_required: boolean }>(
    '/auth/login',
    { method: 'POST', body: JSON.stringify({ username, password }) },
  )
}

export function verifyMfa(token: string, code: string) {
  return authFetcher<{ token: string; user: import('../types').AuthUser }>('/auth/mfa/verify', token, {
    code,
  })
}

// Servers
export function fetchServers(params?: Record<string, string>) {
  return fetcher<PaginatedResponse<MCPServer>>(buildQuery('/servers', params))
}

export function fetchServer(id: string) {
  return fetcher<ServerDetail>(`/servers/${id}`)
}

export function registerServer(data: Partial<MCPServer>) {
  return fetcher<MCPServer>('/servers', { method: 'POST', body: JSON.stringify(data) })
}

export function inspectServer(id: string) {
  return fetcher<{ changes: unknown }>(`/servers/${id}/inspect`, { method: 'POST' })
}

export function decommissionServer(id: string, phase: string) {
  return fetcher<{ status: string }>(`/servers/${id}/decommission`, {
    method: 'POST',
    body: JSON.stringify({ phase }),
  })
}

// Capabilities
export function fetchCapabilities(params?: Record<string, string>) {
  return fetcher<PaginatedResponse<Capability>>(buildQuery('/capabilities', params))
}

export function createCapability(data: Partial<Capability>) {
  return fetcher<Capability>('/capabilities', { method: 'POST', body: JSON.stringify(data) })
}

export function deprecateCapability(id: string, graceDays: number) {
  return fetcher<Capability>(`/capabilities/${id}/deprecate`, {
    method: 'POST',
    body: JSON.stringify({ grace_days: graceDays }),
  })
}

export function fetchCapabilityMappings(id: string) {
  return fetcher<CapabilityMapping[]>(`/capabilities/${id}/mappings`)
}

export function mapTool(capabilityId: string, data: Partial<CapabilityMapping>) {
  return fetcher<CapabilityMapping>(`/capabilities/${capabilityId}/mappings`, {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

// Resolve a single capability by ID to get its display name.
  // Used by ReviewsPage to show human-readable capability names in the review table.
export function fetchCapability(id: string) {
  return fetcher<import('../types').Capability>(`/capabilities/${id}`)
}

// Agent Classes
export function fetchAgentClasses() {
  return fetcher<AgentClass[]>('/agent-classes')
}

export function createAgentClass(data: Partial<AgentClass>) {
  return fetcher<AgentClass>('/agent-classes', { method: 'POST', body: JSON.stringify(data) })
}

export function fetchAgentIdentities(classId: string) {
  return fetcher<AgentIdentity[]>(`/agent-classes/${classId}/identities`)
}

export function createAgentIdentity(classId: string, name: string) {
  return fetcher<AgentIdentity & { token: string }>(`/agent-classes/${classId}/identities`, {
    method: 'POST',
    body: JSON.stringify({ name }),
  })
}

// Trust
export function setTrustAssignment(classId: string, serverId: string, trustLevel: string) {
  return fetcher<TrustAssignment>(`/agent-classes/${classId}/trust`, {
    method: 'POST',
    body: JSON.stringify({ server_id: serverId, trust_level: trustLevel }),
  })
}

// Approvals
export function fetchApprovals(params?: Record<string, string>) {
  return fetcher<PaginatedResponse<ApprovalRequest>>(buildQuery('/approvals', params))
}

export function resolveApproval(id: string, status: 'approved' | 'denied', reason?: string) {
  return fetcher<ApprovalRequest>(`/approvals/${id}/review`, {
    method: 'POST',
    body: JSON.stringify({ action: status, approver_id: useAuthStore.getState().user?.id, note: reason }),
  })
}

export function grantEnvelope(body: import('../types').ApprovalEnvelopeCreate) {
  return fetcher<import('../types').ApprovalEnvelope>(
    '/approvals/envelopes',
    { method: 'POST', body: JSON.stringify(body) },
  )
}

export function bulkApprove(body: import('../types').BulkApproveRequest) {
  return fetcher<import('../types').BulkApproveResponse>(
    '/approvals/bulk-approve',
    { method: 'POST', body: JSON.stringify(body) },
  )
}

// Audit
export function fetchAuditEvents(params?: Record<string, string>) {
  return fetcher<PaginatedResponse<AuditEvent>>(buildQuery('/audit', params))
}

export function exportAudit(params?: Record<string, string>) {
  return fetcher<{ export_id: string }>('/audit/export', { method: 'POST', body: JSON.stringify(params || {}) })
}

// Packs
export function fetchPacks() {
  return fetcher<CapabilityPack[]>('/packs')
}

export function createPack(data: Partial<CapabilityPack>) {
  return fetcher<CapabilityPack>('/packs', { method: 'POST', body: JSON.stringify(data) })
}

export function assignPackToClass(packId: string, classId: string) {
  return fetcher<void>(`/packs/${packId}/classes`, {
    method: 'POST',
    body: JSON.stringify({ agent_class_id: classId }),
  })
}

// Alerts
export function fetchAlerts(params?: Record<string, string>) {
  return fetcher<PaginatedResponse<AlertEvent>>(buildQuery('/alerts', params))
}

export function acknowledgeAlert(id: string) {
  return fetcher<AlertEvent>(`/alerts/${id}/acknowledge`, { method: 'POST' })
}

// Admin
export function fetchAdminUsers() {
  return fetcher<AdminUser[]>('/admin/users')
}

export function inviteUser(data: { username: string; email: string; role: string }) {
  return fetcher<AdminUser>('/admin/users/invite', { method: 'POST', body: JSON.stringify(data) })
}

export function deactivateUser(id: string) {
  return fetcher<AdminUser>(`/admin/users/${id}/deactivate`, { method: 'POST' })
}

// Policies
export function fetchPolicies() {
  return fetcher<{ id: string; version: string; deployed_at: string }[]>('/admin/policies')
}

export function deployPolicy(regoContent: string) {
  return fetcher<{ version: string }>('/admin/policies/bundle', {
    method: 'POST',
    body: JSON.stringify({ rego_content: regoContent }),
  })
}

export function fetchPackSecurityMetrics(packId: string) {
  return fetcher<PackSafetyMetrics>(`/packs/${packId}/security-metrics`)
}

export function fetchPackBreadth() {
  return fetcher<PackBreadthRow[]>('/admin/trust-posture/pack-breadth')
}

// Resource Dimensions (v0.2.0)
export function fetchResourceDimensions(capabilityId: string) {
  return fetcher<import('../types').ResourceDimension[]>(
    `/admin/capabilities/${capabilityId}/dimensions`
  )
}

export function createResourceDimension(capabilityId: string, data: { dimension_key: string; display_name?: string }) {
  return fetcher<import('../types').ResourceDimension>(
    `/admin/capabilities/${capabilityId}/dimensions`,
    { method: 'POST', body: JSON.stringify(data) }
  )
}

export function deleteResourceDimension(capabilityId: string, dimId: string) {
  return fetcher<void>(
    `/admin/capabilities/${capabilityId}/dimensions/${dimId}`,
    { method: 'DELETE' }
  )
}

export function setDimensionValueMap(
  capabilityId: string,
  dimId: string,
  data: { source: string; param_path?: string; constant_value?: string }
) {
  return fetcher<import('../types').DimensionValueMap>(
    `/admin/capabilities/${capabilityId}/dimensions/${dimId}/value-map`,
    { method: 'POST', body: JSON.stringify(data) }
  )
}

export function setIdentityResourceBindings(identityId: string, bindings: { dimension_key: string; allowed_value: string }[]) {
  return fetcher<import('../types').ResourceBinding[]>(
    `/admin/agents/${identityId}/resources`,
    { method: 'POST', body: JSON.stringify({ bindings }) }
  )
}

export function fetchIdentityResourceBindings(identityId: string) {
  return fetcher<import('../types').ResourceBinding[]>(
    `/admin/agents/${identityId}/resources`
  )
}

export function setPackResourceBindings(packId: string, bindings: { dimension_key: string; allowed_value: string }[]) {
  return fetcher<import('../types').ResourceBinding[]>(
    `/admin/packs/${packId}/resources`,
    { method: 'POST', body: JSON.stringify({ bindings }) }
  )
}

export function fetchPackResourceBindings(packId: string) {
  return fetcher<import('../types').ResourceBinding[]>(
    `/admin/packs/${packId}/resources`
  )
}

// Dashboard
export function fetchDashboard() {
  return fetcher<DashboardStats>('/admin/dashboard')
}

// Trust Posture — uses fetchServers directly; this function removed (dead code)

// Schema-Digest Reviews
// Fetch all capability mappings whose tool_schema_digest does not match the
// server's current tool schema — these require an admin review decision.
// Optional failure_class filter (#447) restricts to a single reason
// ('unreachable' | 'timeout' | 'drifted' | 'schema_mismatch').
export function fetchStaleMappings(failureClass?: string) {
  const qs = failureClass ? `?failure_class=${encodeURIComponent(failureClass)}` : ''
  return fetcher<CapabilityMapping[]>(`/admin/mappings/stale${qs}`)
}

// Live priority summary of the review queue (#447). Separates unreachable
// (hands-off) items from genuine schema changes.
export function fetchQueueSummary() {
  return fetcher<import('../types').ReviewQueueSummary>('/admin/mappings/summary')
}

// Bulk-retire review items without per-item review (#447). Target a whole
// failure_class ("unreachable") or an explicit list of mapping IDs.
export function bulkRetireMappings(body: import('../types').BulkRetireRequest) {
  return fetcher<import('../types').BulkRetireResponse>('/admin/mappings/retire', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

// Submit an admin review decision (approved / rejected) for a specific mapping.
// The backend records the decision in a MappingReview and updates the mapping's status.
// An optional reason can be provided, especially when rejecting.
export function reviewMapping(mappingId: string, decision: 'approved' | 'rejected', reason?: string) {
  return fetcher<import('../types').MappingReview>(`/admin/mappings/${mappingId}/review`, {
    method: 'POST',
    body: JSON.stringify({ decision, reason }),
  })
}
