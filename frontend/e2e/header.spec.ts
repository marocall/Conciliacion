import { test, expect } from '@playwright/test'

test.describe('Header branding', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
  })

  test('logo image is visible', async ({ page }) => {
    const logo = page.locator('header img[alt="BPCE Equipment Solutions"]')
    await expect(logo).toBeVisible()
  })

  test('brand name is BPCE Equipment Solutions', async ({ page }) => {
    await expect(page.locator('header h1')).toHaveText('BPCE Equipment Solutions')
  })

  test('subtitle is Reconciliación Contable Inteligente', async ({ page }) => {
    await expect(page.locator('header p')).toContainText('Reconciliación Contable Inteligente')
  })

  test('NAOS ↔ EXACT pill is present', async ({ page }) => {
    await expect(page.locator('header')).toContainText('NAOS ↔ EXACT')
  })

  test('no old RECON brand name appears', async ({ page }) => {
    const header = page.locator('header')
    await expect(header.getByText('RECON', { exact: true })).not.toBeVisible()
  })
})
