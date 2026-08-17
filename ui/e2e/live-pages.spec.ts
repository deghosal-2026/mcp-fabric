import { test, expect } from '@playwright/test'

async function login(page: import('@playwright/test').Page) {
  await page.goto('/login')
  const textboxes = page.getByRole('textbox')
  await textboxes.nth(0).fill('admin')
  await textboxes.nth(1).fill('Admin123!')
  await page.getByRole('button', { name: 'Login' }).click()
  await expect(page).toHaveURL('/')
}

test('live approvals page handles empty data', async ({ page }) => {
  await login(page)
  await page.goto('/approvals')
  await expect(page.getByRole('heading', { name: 'Approvals' })).toBeVisible()
  await expect(page.getByText('Something went wrong')).toHaveCount(0)
  // Page should render with a Total: label regardless of data state
  await expect(page.getByText(/Total: \d+/)).toBeVisible()
})

test('live audit page handles empty data', async ({ page }) => {
  await login(page)
  await page.goto('/audit')
  await expect(page.getByRole('heading', { name: 'Audit Log' })).toBeVisible()
  await expect(page.getByText('Something went wrong')).toHaveCount(0)
  await expect(page.getByText(/Total: \d+/)).toBeVisible()
})
