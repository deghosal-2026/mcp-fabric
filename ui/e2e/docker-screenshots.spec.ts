import { test, expect } from '@playwright/test'
import path from 'path'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const D = path.resolve(__dirname, '../../docs/ui-test/findings/screenshots')

test.setTimeout(120_000)

async function login(page: import('@playwright/test').Page) {
  await page.goto('/login')
  const textboxes = page.getByRole('textbox')
  await textboxes.nth(0).fill('admin')
  await textboxes.nth(1).fill('Admin123!')
  await page.getByRole('button', { name: 'Login' }).click()
  await expect(page).toHaveURL('/')
}

test('docker screenshots — all major pages', async ({ page }) => {
  await login(page)
  await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible()
  await page.screenshot({ path: path.join(D, 'docker-02-dashboard.png'), fullPage: true })

  await page.goto('/servers')
  await expect(page.getByRole('heading', { name: 'Servers' })).toBeVisible()
  await page.screenshot({ path: path.join(D, 'docker-03-servers.png'), fullPage: true })

  await page.goto('/capabilities')
  await expect(page.getByRole('heading', { name: 'Capability Catalog' })).toBeVisible()
  await page.screenshot({ path: path.join(D, 'docker-05-capabilities.png'), fullPage: true })

  await page.goto('/agent-classes')
  await expect(page.getByRole('heading', { name: 'Agent Classes' })).toBeVisible()
  await page.screenshot({ path: path.join(D, 'docker-07-agent-classes.png'), fullPage: true })

  await page.goto('/policies')
  await expect(page.getByRole('heading', { name: 'Policy Editor' })).toBeVisible()
  await page.screenshot({ path: path.join(D, 'docker-08-policies.png'), fullPage: true })

  await page.goto('/audit')
  await expect(page.getByRole('heading', { name: 'Audit Log' })).toBeVisible()
  await page.screenshot({ path: path.join(D, 'docker-10-audit.png'), fullPage: true })

  await page.goto('/approvals')
  await expect(page.getByRole('heading', { name: 'Approvals' })).toBeVisible()
  await page.screenshot({ path: path.join(D, 'docker-11-approvals.png'), fullPage: true })

  await page.goto('/packs')
  await expect(page.getByRole('heading', { name: 'Capability Packs' })).toBeVisible()
  await page.screenshot({ path: path.join(D, 'docker-13-packs.png'), fullPage: true })

  await page.getByRole('button', { name: /bindings/i }).first().click()
  await page.waitForTimeout(1500)
  await page.screenshot({ path: path.join(D, 'docker-13a-packs-bindings.png'), fullPage: true })
  await page.goto('/alerts')
  await page.waitForTimeout(1000)
  await expect(page.getByRole('heading', { name: 'Alerts' })).toBeVisible()
  await page.screenshot({ path: path.join(D, 'docker-14-alerts.png'), fullPage: true })

  await page.goto('/admin/users')
  await expect(page.getByRole('heading', { name: 'Admin Users' })).toBeVisible()
  await page.screenshot({ path: path.join(D, 'docker-15-admin-users.png'), fullPage: true })

  await page.goto('/trust')
  await expect(page.getByRole('heading', { name: 'Trust Posture' })).toBeVisible()
  await page.screenshot({ path: path.join(D, 'docker-17-trust-posture.png'), fullPage: true })

  // Schema Reviews: capture the stale-mapping review page for documentation
  await page.goto('/reviews')
  await expect(page.getByText(/Pending Schema Reviews/i)).toBeVisible()
  await page.screenshot({ path: path.join(D, 'docker-18-reviews.png'), fullPage: true })
})
