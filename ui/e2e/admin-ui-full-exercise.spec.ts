import { test, expect } from '@playwright/test'

const MOCK_TOKEN = 'fcp_test_admin_token_1234567890abcdef'

const MOCK_USER = {
  id: 'usr-1',
  username: 'priya',
  role: 'admin',
  team_namespace: 'team:platform',
  mfa_enabled: true,
}

const MOCK_DASHBOARD = {
  server_count: 6,
  healthy_servers: 4,
  pending_approvals: 2,
  recent_audit_events: 42,
  degraded_servers: 1,
}

const MOCK_SERVERS = {
  items: [
    { id: 'srv-1', name: 'KB Server', endpoint: 'http://kb.internal:3001', owner_team: 'platform', labels: ['knowledge', 'internal'], trust_level: 'trusted', health_status: 'healthy', team_namespace: 'team:platform', decommissioned_at: null, created_at: '2026-07-01T00:00:00Z', tools: [] },
    { id: 'srv-2', name: 'Code Search', endpoint: 'http://codesearch.internal:3002', owner_team: 'platform', labels: ['code', 'search'], trust_level: 'trusted', health_status: 'healthy', team_namespace: 'team:platform', decommissioned_at: null, created_at: '2026-07-02T00:00:00Z', tools: [] },
    { id: 'srv-3', name: 'Vuln Scanner', endpoint: 'http://security.internal:3003', owner_team: 'security', labels: ['security', 'scanning'], trust_level: 'restricted', health_status: 'degraded', team_namespace: 'team:security', decommissioned_at: null, created_at: '2026-07-03T00:00:00Z', tools: [] },
  ],
  pagination: { total: 3, has_more: false, per_page: 50 },
}

const MOCK_CAPABILITIES = {
  items: [
    { id: 'cap-1', name: 'knowledge:search', domain: 'knowledge', description: 'Search documentation', status: 'active', deprecated_at: null, grace_period_days: 14 },
    { id: 'cap-2', name: 'code:search', domain: 'code', description: 'Search repos', status: 'active', deprecated_at: null, grace_period_days: 14 },
  ],
  pagination: { total: 2, has_more: false, per_page: 100 },
}

const MOCK_AGENT_CLASSES = [
  { id: 'cls-1', name: 'agent:admin', description: 'Full system access', team_namespace: 'team:platform' },
  { id: 'cls-2', name: 'agent:developer', description: 'Developer assistant', team_namespace: 'team:platform' },
]

const MOCK_POLICIES = [
  { id: 'pol-1', version: '1.0.0', deployed_at: '2026-07-15T10:00:00Z' },
]

const MOCK_AUDIT = {
  items: [
    { id: 'aud-1', event_type: 'capability_request', actor_type: 'agent', actor_id: 'igor-01', target_type: 'capability', target_id: 'cap-2', details: {}, created_at: '2026-07-24T10:00:00Z' },
  ],
  pagination: { total: 1, has_more: false, next_cursor: null, per_page: 50 },
}

const MOCK_APPROVALS = {
  items: [
    { id: 'apr-1', agent_identity_id: 'id-1', capability_id: 'cap-3', server_id: 'srv-1', request_params: { service: 'payment-api' }, status: 'pending', approver_id: null, requested_at: '2026-07-24T10:00:00Z', resolved_at: null, agent_name: 'CRBot', capability_name: 'deployment:promote', server_name: 'Deployment Server' },
  ],
  pagination: { total: 1, has_more: false, per_page: 50 },
}

const MOCK_PACKS = [
  { id: 'pck-1', name: 'New Hire Pack', description: 'Starter tools', team_namespace: 'team:platform' },
]

const MOCK_ALERTS = {
  items: [
    { id: 'alr-1', rule_id: 'rule-1', message: 'Code Search degraded', details: {}, fired_at: '2026-07-24T10:05:00Z', acknowledged_at: null, acknowledged_by: null, rule_name: 'Degraded Server' },
  ],
  pagination: { total: 1, has_more: false, per_page: 50 },
}

const MOCK_ADMIN_USERS = [
  { id: 'usr-1', username: 'priya', email: 'priya@example.com', role: 'admin', team_namespace: 'team:platform', mfa_enabled: true, status: 'active', created_at: '2026-07-01T00:00:00Z' },
  { id: 'usr-2', username: 'alex', email: 'alex@example.com', role: 'editor', team_namespace: 'team:platform', mfa_enabled: false, status: 'active', created_at: '2026-07-05T00:00:00Z' },
]

test.beforeEach(async ({ page }) => {
  await page.addInitScript((token: string, user: typeof MOCK_USER) => {
    localStorage.setItem('fabric_token', token)
    localStorage.setItem('fabric_user', JSON.stringify(user))
  }, MOCK_TOKEN, MOCK_USER)

  await page.route(/\/v1\//, async route => {
    const url = new URL(route.request().url())
    const path = url.pathname
    const method = route.request().method()

    if (path === '/v1/auth/login') {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ token: MOCK_TOKEN, user: MOCK_USER, mfa_required: false }) })
    }
    if (path === '/v1/admin/dashboard') {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_DASHBOARD) })
    }
    if (path === '/v1/servers') {
      if (method === 'POST') {
        return route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify(MOCK_SERVERS.items[0]) })
      }
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_SERVERS) })
    }
    if (path === '/v1/capabilities') {
      if (method === 'POST') {
        return route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify(MOCK_CAPABILITIES.items[0]) })
      }
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_CAPABILITIES) })
    }
    if (path === '/v1/agent-classes') {
      if (method === 'POST') {
        return route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify(MOCK_AGENT_CLASSES[0]) })
      }
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_AGENT_CLASSES) })
    }
    if (path.match(/^\/v1\/agent-classes\/.+\/identities$/)) {
      if (method === 'POST') {
        return route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify({ id: 'id-new', token_prefix: 'fcp_', token: MOCK_TOKEN, status: 'active' }) })
      }
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) })
    }
    if (path.match(/^\/v1\/agent-classes\/.+\/trust$/)) {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({}) })
    }
    if (path === '/v1/admin/policies') {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_POLICIES) })
    }
    if (path === '/v1/admin/policies/bundle') {
      return route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify({ version: '2.0.0' }) })
    }
    if (path === '/v1/audit') {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_AUDIT) })
    }
    if (path === '/v1/audit/export') {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ export_id: 'exp-1' }) })
    }
    if (path === '/v1/approvals') {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_APPROVALS) })
    }
    if (path.match(/^\/v1\/approvals\/.+\/review$/)) {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ...MOCK_APPROVALS.items[0], status: 'approved' }) })
    }
    if (path === '/v1/packs') {
      if (method === 'POST') {
        return route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify(MOCK_PACKS[0]) })
      }
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_PACKS) })
    }
    if (path.match(/^\/v1\/packs\/.+\/classes$/)) {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({}) })
    }
    if (path === '/v1/alerts') {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_ALERTS) })
    }
    if (path.match(/^\/v1\/alerts\/.+\/acknowledge$/)) {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_ALERTS.items[0]) })
    }
    if (path === '/v1/admin/users') {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_ADMIN_USERS) })
    }
    if (path === '/v1/admin/users/invite') {
      return route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify(MOCK_ADMIN_USERS[0]) })
    }
    if (path.match(/^\/v1\/admin\/users\/.+\/deactivate$/)) {
      return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_ADMIN_USERS[0]) })
    }

    route.continue()
  })
})

test('exercise major admin UI elements and interactions', async ({ page }) => {
  await page.goto('/')
  await page.waitForLoadState('networkidle')

  await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible()
  await expect(page.locator('div').filter({ hasText: /^Servers$/ }).first()).toBeVisible()
  await expect(page.locator('div').filter({ hasText: /^Pending Approvals$/ }).first()).toBeVisible()

  await page.goto('/servers')
  await expect(page.getByRole('heading', { name: 'Servers' })).toBeVisible()
  await expect(page.getByText('KB Server')).toBeVisible()
  await page.getByRole('button', { name: /register server/i }).click()
  await expect(page.getByText('Register MCP Server')).toBeVisible()
  const modal = page.locator('.fixed.inset-0.z-50').last()
  const serverModalInputs = modal.locator('input')
  await serverModalInputs.nth(0).fill('New Server')
  await serverModalInputs.nth(1).fill('http://localhost:3010')
  await modal.getByRole('button', { name: 'Save' }).click()

  await page.goto('/capabilities')
  await expect(page.getByRole('heading', { name: 'Capability Catalog' })).toBeVisible()
  await expect(page.getByText('knowledge:search')).toBeVisible()

  await page.goto('/agent-classes')
  await expect(page.getByRole('heading', { name: 'Agent Classes' })).toBeVisible()
  await expect(page.getByText('agent:admin')).toBeVisible()

  await page.goto('/policies')
  await expect(page.getByRole('heading', { name: 'Policy Editor' })).toBeVisible()
  await page.getByRole('button', { name: /new policy/i }).click()
  await expect(page.getByText('Edit Rego Policy')).toBeVisible()

  await page.goto('/audit')
  await expect(page.getByRole('heading', { name: 'Audit Log' })).toBeVisible()
  await expect(page.getByText('capability_request')).toBeVisible()
  await page.getByRole('button', { name: 'Export' }).click()

  await page.goto('/approvals')
  await expect(page.getByRole('heading', { name: 'Approvals' })).toBeVisible()
  await page.getByRole('button', { name: 'Review' }).click()
  await expect(page.getByText('Review Approval Request')).toBeVisible()
  await page.getByRole('button', { name: 'Approve' }).click()

  await page.goto('/packs')
  await expect(page.getByRole('heading', { name: 'Capability Packs' })).toBeVisible()
  await expect(page.getByText('New Hire Pack')).toBeVisible()

  await page.goto('/alerts')
  await expect(page.getByRole('heading', { name: 'Alerts' })).toBeVisible()
  await expect(page.getByText('Code Search degraded')).toBeVisible()
  await page.getByRole('button', { name: 'Acknowledge' }).click()

  await page.goto('/admin/users')
  await expect(page.getByRole('heading', { name: 'Admin Users' })).toBeVisible()
  await expect(page.getByText('priya@example.com')).toBeVisible()
  await page.getByRole('button', { name: /invite user/i }).click()
  await expect(page.getByRole('heading', { name: 'Invite User' })).toBeVisible()

  await page.goto('/trust')
  await expect(page.getByRole('heading', { name: 'Trust Posture' })).toBeVisible()
  await expect(page.getByText('KB Server')).toBeVisible()

  await page.getByRole('button', { name: /logout/i }).click()
  await expect(page).toHaveURL(/\/login/)
})
