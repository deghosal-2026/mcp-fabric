import { QueryClient } from '@tanstack/react-query'
import { useAuthStore } from '../stores/authStore'
import type {
  MCPServer, ServerDetail, Capability, CapabilityMapping,
  AgentClass, AgentIdentity, TrustAssignment,
  ApprovalRequest, AuditEvent, CapabilityPack,
  AlertEvent, AdminUser, DashboardStats, PaginatedResponse,
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

  return res.json()
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
  return fetcher<{ token: string; user: import('../types').AuthUser }>(
    '/auth/mfa/verify',
    { method: 'POST', body: JSON.stringify({ token, code }) },
  )
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
  return fetcher<ApprovalRequest>(`/approvals/${id}/resolve`, {
    method: 'POST',
    body: JSON.stringify({ status, reason }),
  })
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

// Dashboard
export function fetchDashboard() {
  return fetcher<DashboardStats>('/admin/dashboard')
}

// Trust Posture — uses fetchServers directly; this function removed (dead code)
