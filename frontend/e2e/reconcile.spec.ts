import { test, expect } from '@playwright/test'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const NAOS_FIXTURE = path.join(__dirname, 'fixtures', 'naos-sample.xlsx')
const EXACT_FIXTURE = path.join(__dirname, 'fixtures', 'exact-sample.xlsx')

const MOCK_OK = {
  summary: [
    { fecha: '2024-01-15', saldo_naos: 1000, saldo_exact: 1000, diferencia: 0,   cuadra: true  },
    { fecha: '2024-01-16', saldo_naos:  250, saldo_exact:  300, diferencia: -50, cuadra: false },
  ],
  totalDates: 2,
  matchedDates: 1,
  diffDates: 1,
  totalDiff: -50,
  download_token: 'test-token-abc123',
}

async function uploadBothFiles(page: import('@playwright/test').Page) {
  const inputs = page.locator('input[type="file"]')
  await inputs.nth(0).setInputFiles(NAOS_FIXTURE)
  await inputs.nth(1).setInputFiles(EXACT_FIXTURE)
}

test.describe('Reconciliation flow', () => {
  test('shows processing state while request is in flight', async ({ page }) => {
    let unblock: () => void
    const blocker = new Promise<void>((resolve) => { unblock = resolve })

    await page.route('**/api/reconcile', async (route) => {
      await blocker
      await route.fulfill({ json: MOCK_OK, status: 200 })
    })

    await page.goto('/')
    await uploadBothFiles(page)
    await page.getByRole('button', { name: /Reconciliar/i }).click()

    await expect(page.getByRole('heading', { name: /Procesando/i })).toBeVisible()
    unblock!()
  })

  test('shows results after successful reconciliation', async ({ page }) => {
    await page.route('**/api/reconcile', (route) =>
      route.fulfill({ json: MOCK_OK, status: 200 })
    )

    await page.goto('/')
    await uploadBothFiles(page)
    await page.getByRole('button', { name: /Reconciliar/i }).click()

    await expect(page.getByRole('link', { name: /Descargar Informe Excel/i })).toBeVisible({ timeout: 10_000 })
  })

  test('metrics cards appear with correct counts', async ({ page }) => {
    await page.route('**/api/reconcile', (route) =>
      route.fulfill({ json: MOCK_OK, status: 200 })
    )

    await page.goto('/')
    await uploadBothFiles(page)
    await page.getByRole('button', { name: /Reconciliar/i }).click()

    await expect(page.getByText(/Total fechas/i)).toBeVisible({ timeout: 10_000 })
    await expect(page.getByText(/Fechas OK/i)).toBeVisible()
    await expect(page.locator('p', { hasText: /^Con diferencia$/i })).toBeVisible()
    await expect(page.getByText(/Diferencia total/i)).toBeVisible()
  })

  test('download link points to correct API URL', async ({ page }) => {
    await page.route('**/api/reconcile', (route) =>
      route.fulfill({ json: MOCK_OK, status: 200 })
    )

    await page.goto('/')
    await uploadBothFiles(page)
    await page.getByRole('button', { name: /Reconciliar/i }).click()

    const link = page.getByRole('link', { name: /Descargar Informe Excel/i })
    await expect(link).toBeVisible({ timeout: 10_000 })
    await expect(link).toHaveAttribute('href', `/api/download/${MOCK_OK.download_token}`)
    await expect(link).toHaveAttribute('download', 'reconciliacion_resultado.xlsx')
  })

  test('shows error panel on API 500', async ({ page }) => {
    await page.route('**/api/reconcile', (route) =>
      route.fulfill({ status: 500, json: { detail: 'Error en reconciliación: datos inválidos' } })
    )

    await page.goto('/')
    await uploadBothFiles(page)
    await page.getByRole('button', { name: /Reconciliar/i }).click()

    await expect(page.getByText(/Error en el procesamiento/i)).toBeVisible({ timeout: 10_000 })
    await expect(page.getByText(/datos inválidos/i)).toBeVisible()
  })

  test('shows error panel on network failure', async ({ page }) => {
    await page.route('**/api/reconcile', (route) => route.abort())

    await page.goto('/')
    await uploadBothFiles(page)
    await page.getByRole('button', { name: /Reconciliar/i }).click()

    await expect(page.getByText(/Error en el procesamiento/i)).toBeVisible({ timeout: 10_000 })
  })

  test('limpiar after results resets to idle state', async ({ page }) => {
    await page.route('**/api/reconcile', (route) =>
      route.fulfill({ json: MOCK_OK, status: 200 })
    )

    await page.goto('/')
    await uploadBothFiles(page)
    await page.getByRole('button', { name: /Reconciliar/i }).click()
    await expect(page.getByRole('link', { name: /Descargar Informe Excel/i })).toBeVisible({ timeout: 10_000 })

    await page.getByRole('button', { name: /Limpiar/i }).click()

    await expect(page.getByText('Listo para reconciliar')).toBeVisible()
    await expect(page.getByRole('link', { name: /Descargar/i })).not.toBeVisible()
  })
})
