import { test, expect } from '@playwright/test'
import path from 'path'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const D = path.resolve(__dirname, '../../docs/ui-test/findings/screenshots')

async function login(page: import('@playwright/test').Page) {
  await page.goto('/login')
  const textboxes = page.getByRole('textbox')
  await textboxes.nth(0).fill('admin')
  await textboxes.nth(1).fill('Admin123!')
  await page.getByRole('button', { name: 'Login' }).click()
  await expect(page).toHaveURL('/')
}

test('full UI exercise — every page, every action, approve/deny', async ({ page }) => {
  await login(page)

  // ── Dashboard ──────────────────────────────────────────────────
  await page.getByRole('link', { name: /Dashboard/ }).click()
  await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible()
  await page.screenshot({ path: path.join(D, 'ex-01-dashboard.png'), fullPage: true })

  // ── Servers ────────────────────────────────────────────────────
  await page.getByRole('link', { name: /Servers/ }).click()
  await expect(page.getByRole('heading', { name: 'Servers' })).toBeVisible()
  await page.getByRole('button', { name: /register server/i }).click()
  await page.waitForTimeout(300)
  await page.screenshot({ path: path.join(D, 'ex-02-servers-register.png'), fullPage: true })
  await page.getByRole('button', { name: 'Cancel' }).click()

  // ── Capabilities ───────────────────────────────────────────────
  await page.getByRole('link', { name: /Capabilities/ }).click()
  await expect(page.getByRole('heading', { name: 'Capability Catalog' })).toBeVisible()
  await page.getByRole('button', { name: /create capability/i }).click()
  await page.waitForTimeout(300)
  await page.screenshot({ path: path.join(D, 'ex-03-capabilities-modal.png'), fullPage: true })
  await page.getByRole('button', { name: 'Cancel' }).click()

  // ── Agent Classes ──────────────────────────────────────────────
  await page.getByRole('link', { name: /Agent Classes/ }).click()
  await expect(page.getByRole('heading', { name: 'Agent Classes' })).toBeVisible()
  await page.getByRole('button', { name: /create agent class/i }).click()
  await page.waitForTimeout(300)
  await page.screenshot({ path: path.join(D, 'ex-04-agent-classes.png'), fullPage: true })
  await page.getByRole('button', { name: 'Cancel' }).click()

  // ── Policies ───────────────────────────────────────────────────
  await page.getByRole('link', { name: /Policies/ }).click()
  await expect(page.getByRole('heading', { name: 'Policy Editor' })).toBeVisible()
  await page.getByRole('button', { name: /new policy/i }).click()
  await page.waitForTimeout(300)
  await page.screenshot({ path: path.join(D, 'ex-05-policies-editor.png'), fullPage: true })
  await page.getByRole('button', { name: 'Cancel' }).click()

  // ── Audit Log ──────────────────────────────────────────────────
  await page.getByRole('link', { name: /Audit Log/ }).click()
  await expect(page.getByRole('heading', { name: 'Audit Log' })).toBeVisible()
  await page.getByRole('button', { name: 'Export' }).click()
  await page.waitForTimeout(300)
  await page.screenshot({ path: path.join(D, 'ex-06-audit.png'), fullPage: true })

  // ── Approvals ──────────────────────────────────────────────────
  await page.getByRole('link', { name: /Approvals/ }).click()
  await expect(page.getByRole('heading', { name: 'Approvals' })).toBeVisible()
  await page.screenshot({ path: path.join(D, 'ex-07-approvals-list.png'), fullPage: true })

  const reviewBtns = page.getByRole('button', { name: 'Review' })
  if (await reviewBtns.count() > 0) {
    await reviewBtns.first().click()
    await page.waitForTimeout(300)
    await page.screenshot({ path: path.join(D, 'ex-07b-approvals-review.png'), fullPage: true })
    await page.getByRole('button', { name: 'Approve' }).click()
    await page.waitForTimeout(500)
  }

  const reviewBtns2 = page.getByRole('button', { name: 'Review' })
  if (await reviewBtns2.count() > 0) {
    await reviewBtns2.first().click()
    await page.waitForTimeout(300)
    await page.getByRole('button', { name: 'Deny' }).click()
    await page.waitForTimeout(500)
  }
  await page.screenshot({ path: path.join(D, 'ex-07c-approvals-after.png'), fullPage: true })

  // ── Capability Packs ───────────────────────────────────────────
  await page.getByRole('link', { name: /Capability Packs/ }).click()
  await expect(page.getByRole('heading', { name: 'Capability Packs' })).toBeVisible()
  await page.getByRole('button', { name: /create pack/i }).click()
  await page.waitForTimeout(300)
  await page.screenshot({ path: path.join(D, 'ex-08-packs-modal.png'), fullPage: true })
  await page.getByRole('button', { name: 'Cancel' }).click()

  // ── Alerts ─────────────────────────────────────────────────────
  await page.getByRole('link', { name: /Alerts/ }).click()
  await expect(page.getByRole('heading', { name: 'Alerts' })).toBeVisible()
  await page.screenshot({ path: path.join(D, 'ex-09-alerts.png'), fullPage: true })

  // ── Admin Users ────────────────────────────────────────────────
  await page.getByRole('link', { name: /Admin Users/ }).click()
  await expect(page.getByRole('heading', { name: 'Admin Users' })).toBeVisible()
  await page.getByRole('button', { name: /invite user/i }).click()
  await page.waitForTimeout(300)
  await page.screenshot({ path: path.join(D, 'ex-10-admin-invite.png'), fullPage: true })
  await page.getByRole('button', { name: 'Cancel' }).click()

  // ── Trust Posture ──────────────────────────────────────────────
  await page.getByRole('link', { name: /Trust Posture/ }).click()
  await expect(page.getByRole('heading', { name: 'Trust Posture' })).toBeVisible()
  await page.screenshot({ path: path.join(D, 'ex-11-trust-posture.png'), fullPage: true })

  // ── Logout ─────────────────────────────────────────────────────
  await page.getByRole('button', { name: /logout/i }).click()
  await expect(page).toHaveURL(/\/login/)
})
