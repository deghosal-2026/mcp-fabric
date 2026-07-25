import { test, expect } from '@playwright/test'

async function login(page: import('@playwright/test').Page) {
  await page.goto('/login')
  const textboxes = page.getByRole('textbox')
  await textboxes.nth(0).fill('admin')
  await textboxes.nth(1).fill('Admin123!')
  await page.getByRole('button', { name: 'Login' }).click()
  await expect(page).toHaveURL('/')
}

test('approvals review action does not 404', async ({ page }) => {
  await login(page)
  await page.goto('/approvals')

  await expect(page.getByRole('heading', { name: 'Approvals' })).toBeVisible()
  await page.getByRole('button', { name: 'Review' }).first().click()

  const responsePromise = page.waitForResponse(
    response => response.url().includes('/v1/approvals/') && response.request().method() === 'POST',
  )

  await page.getByRole('button', { name: 'Approve' }).click()
  const response = await responsePromise

  expect(response.status()).not.toBe(404)
})
