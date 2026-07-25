import { test, expect } from '@playwright/test'

async function login(page: import('@playwright/test').Page) {
  await page.goto('/login')
  const textboxes = page.getByRole('textbox')
  await textboxes.nth(0).fill('admin')
  await textboxes.nth(1).fill('Admin123!')
  await page.getByRole('button', { name: 'Login' }).click()
  await expect(page).toHaveURL('/')
}

test('exercise live seeded admin UI on docker', async ({ page }) => {
  await login(page)

  await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Recent Servers' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Pending Approvals' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Recent Audit Events' })).toBeVisible()

  await page.goto('/servers')
  await expect(page.getByRole('heading', { name: 'Servers' })).toBeVisible()
  await expect(page.getByText('demo:server-01')).toBeVisible()
  await page.getByRole('button', { name: /register server/i }).click()
  await expect(page.getByText('Register MCP Server')).toBeVisible()
  await page.getByRole('button', { name: 'Cancel' }).click()

  await page.goto('/capabilities')
  await expect(page.getByRole('heading', { name: 'Capability Catalog' })).toBeVisible()
  await expect(page.getByRole('cell', { name: 'demo:knowledge:search' })).toBeVisible()
  await page.getByRole('button', { name: /create capability/i }).click()
  await expect(page.getByRole('button', { name: 'Create Capability' })).toBeVisible()
  await page.getByRole('button', { name: 'Cancel', disabled: false }).first().click()
  await expect(page.getByRole('heading', { name: 'Capability Catalog' })).toBeVisible()

  await page.goto('/agent-classes')
  await expect(page.getByRole('heading', { name: 'Agent Classes' })).toBeVisible()

  await page.goto('/policies')
  await expect(page.getByRole('heading', { name: 'Policy Editor' })).toBeVisible()
  await page.getByRole('button', { name: /new policy/i }).click()
  await expect(page.getByText('Edit Rego Policy')).toBeVisible()
  await page.getByRole('button', { name: 'Cancel' }).click()

  await page.goto('/audit')
  await expect(page.getByRole('heading', { name: 'Audit Log' })).toBeVisible()
  await expect(page.getByText('server_registered')).toBeVisible()

  await page.goto('/approvals')
  await expect(page.getByRole('heading', { name: 'Approvals' })).toBeVisible()
  await expect(page.getByText('Total: 8')).toBeVisible()
  await page.getByRole('button', { name: 'Review' }).first().click()
  await expect(page.getByText('Review Approval Request')).toBeVisible()
  await page.getByRole('button', { name: 'Close' }).click()

  await page.goto('/packs')
  await expect(page.getByRole('heading', { name: 'Capability Packs' })).toBeVisible()

  await page.goto('/alerts')
  await expect(page.getByRole('heading', { name: 'Alerts' })).toBeVisible()

  await page.goto('/admin/users')
  await expect(page.getByRole('heading', { name: 'Admin Users' })).toBeVisible()
  await expect(page.getByText('admin@mcp-fabric.local')).toBeVisible()
  await page.getByRole('button', { name: /invite user/i }).click()
  await expect(page.getByRole('heading', { name: 'Invite User' })).toBeVisible()
  await page.getByRole('button', { name: 'Cancel' }).click()

  await page.goto('/trust')
  await expect(page.getByRole('heading', { name: 'Trust Posture' })).toBeVisible()

  await page.getByRole('button', { name: /logout/i }).click()
  await expect(page).toHaveURL(/\/login/)
})
