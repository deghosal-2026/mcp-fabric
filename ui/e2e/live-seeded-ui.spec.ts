import { test, expect } from '@playwright/test'

async function login(page: import('@playwright/test').Page) {
  await page.goto('/login')
  const textboxes = page.getByRole('textbox')
  await textboxes.nth(0).fill('admin')
  await textboxes.nth(1).fill('Admin123!')
  await page.getByRole('button', { name: 'Login' }).click()
  await expect(page).toHaveURL('/')
}

test('seeded demo data is visible across key UI pages', async ({ page }) => {
  await login(page)

  await expect(page.getByText('Servers 12')).toBeVisible()
  await expect(page.getByText('Pending Approvals 3')).toBeVisible()
  await expect(page.getByText('demo:server-07')).toBeVisible()

  await page.goto('/approvals')
  await expect(page.getByRole('heading', { name: 'Approvals' })).toBeVisible()
  await expect(page.getByText('Total: 8')).toBeVisible()

  await page.goto('/audit')
  await expect(page.getByRole('heading', { name: 'Audit Log' })).toBeVisible()
  await expect(page.getByText('Total: 12')).toBeVisible()

  await page.goto('/servers')
  await expect(page.getByRole('heading', { name: 'Servers' })).toBeVisible()
  await expect(page.getByText('demo:server-01')).toBeVisible()
  await expect(page.getByText('demo:server-03')).toBeVisible()
})
