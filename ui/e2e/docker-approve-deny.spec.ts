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

test('approve and deny workflow', async ({ page }) => {
  await login(page)
  await page.goto('/approvals')
  await page.waitForTimeout(5000)

  const reviewCount = await page.getByRole('button', { name: 'Review' }).count()
  if (reviewCount === 0) {
    // No pending - still take screenshot for visual check
    await page.screenshot({ path: path.join(D, 'ctrl-approvals-done.png'), fullPage: true })
    test.skip(true, 'No pending approvals to review')
    return
  }

  // Approve first pending
  await page.getByRole('button', { name: 'Review' }).first().click()
  await page.waitForTimeout(5000)
  await page.screenshot({ path: path.join(D, 'ctrl-review-panel.png'), fullPage: true })
  await page.getByRole('button', { name: 'Approve' }).click()
  await page.waitForTimeout(5000)

  // Deny next pending (if exists)
  // Reload to close any open modal/panel and get fresh data
  await page.reload()
  await page.waitForTimeout(3000)
  const remaining = page.getByRole('button', { name: 'Review' })
  if (await remaining.count() > 0) {
    await remaining.first().click()
    await page.waitForTimeout(5000)
    await page.getByRole('button', { name: 'Deny' }).click()
    await page.waitForTimeout(5000)
  }

  await page.screenshot({ path: path.join(D, 'ctrl-approvals-done.png'), fullPage: true })
})
