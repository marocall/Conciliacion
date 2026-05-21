import { test, expect } from '@playwright/test'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const NAOS_FIXTURE = path.join(__dirname, 'fixtures', 'naos-sample.xlsx')
const EXACT_FIXTURE = path.join(__dirname, 'fixtures', 'exact-sample.xlsx')

test.describe('Upload zones', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
  })

  test('both upload zones are rendered', async ({ page }) => {
    await expect(page.getByText('NAOS', { exact: true })).toBeVisible()
    await expect(page.getByText('EXACT', { exact: true })).toBeVisible()
  })

  test('upload zones show drop prompt by default', async ({ page }) => {
    const dropTexts = page.getByText('Arrastra el archivo aquí')
    await expect(dropTexts.first()).toBeVisible()
  })

  test('reconcile button is disabled without files', async ({ page }) => {
    await expect(page.getByRole('button', { name: /Reconciliar/i })).toBeDisabled()
  })

  test('limpiar button is hidden when no files loaded', async ({ page }) => {
    await expect(page.getByRole('button', { name: /Limpiar/i })).not.toBeVisible()
  })

  test('shows file name after NAOS upload', async ({ page }) => {
    await page.locator('input[type="file"]').nth(0).setInputFiles(NAOS_FIXTURE)
    await expect(page.getByText('naos-sample.xlsx')).toBeVisible()
  })

  test('shows file name after EXACT upload', async ({ page }) => {
    await page.locator('input[type="file"]').nth(1).setInputFiles(EXACT_FIXTURE)
    await expect(page.getByText('exact-sample.xlsx')).toBeVisible()
  })

  test('reconcile button enables after both files uploaded', async ({ page }) => {
    const inputs = page.locator('input[type="file"]')
    await inputs.nth(0).setInputFiles(NAOS_FIXTURE)
    await inputs.nth(1).setInputFiles(EXACT_FIXTURE)
    await expect(page.getByRole('button', { name: /Reconciliar/i })).toBeEnabled()
  })

  test('limpiar button appears once a file is loaded', async ({ page }) => {
    await page.locator('input[type="file"]').nth(0).setInputFiles(NAOS_FIXTURE)
    await expect(page.getByRole('button', { name: /Limpiar/i })).toBeVisible()
  })

  test('limpiar resets the uploaded file', async ({ page }) => {
    await page.locator('input[type="file"]').nth(0).setInputFiles(NAOS_FIXTURE)
    await expect(page.getByText('naos-sample.xlsx')).toBeVisible()
    await page.getByRole('button', { name: /Limpiar/i }).click()
    await expect(page.getByText('naos-sample.xlsx')).not.toBeVisible()
  })
})
