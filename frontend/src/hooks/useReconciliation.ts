import { useState } from 'react'

export interface DateSummary {
  fecha: string
  saldo_naos: number
  saldo_exact: number
  diferencia: number
  cuadra: boolean
}

export interface ReconciliationResult {
  summary: DateSummary[]
  totalDates: number
  matchedDates: number
  diffDates: number
  totalDiff: number
  downloadUrl: string
}

export type AppState = 'idle' | 'processing' | 'done' | 'error'

export function useReconciliation() {
  const [state, setState] = useState<AppState>('idle')
  const [result, setResult] = useState<ReconciliationResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function reconcile(naosFile: File, exactFile: File) {
    setState('processing')
    setError(null)
    setResult(null)

    try {
      const form = new FormData()
      form.append('naos_file', naosFile)
      form.append('exact_file', exactFile)

      const res = await fetch('/api/reconcile', {
        method: 'POST',
        body: form,
      })

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Error desconocido' }))
        throw new Error(err.detail || `HTTP ${res.status}`)
      }

      const data = await res.json()
      const downloadUrl = `/api/download/${data.download_token}`

      setResult({
        summary: data.summary,
        totalDates: data.totalDates,
        matchedDates: data.matchedDates,
        diffDates: data.diffDates,
        totalDiff: data.totalDiff,
        downloadUrl,
      })
      setState('done')
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Error inesperado')
      setState('error')
    }
  }

  function reset() {
    setState('idle')
    setResult(null)
    setError(null)
  }

  return { state, result, error, reconcile, reset }
}
