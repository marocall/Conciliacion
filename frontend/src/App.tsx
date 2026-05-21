import React, { useState } from 'react'
import { ResultsPanel } from './components/ResultsPanel'
import { UploadZone } from './components/UploadZone'
import { useReconciliation } from './hooks/useReconciliation'

export default function App() {
  const [naosFile, setNaosFile] = useState<File | null>(null)
  const [exactFile, setExactFile] = useState<File | null>(null)
  const { state, result, error, reconcile, reset } = useReconciliation()

  const canReconcile = naosFile !== null && exactFile !== null && state !== 'processing'

  async function handleReconcile() {
    if (!naosFile || !exactFile) return
    await reconcile(naosFile, exactFile)
  }

  function handleReset() {
    setNaosFile(null)
    setExactFile(null)
    reset()
  }

  return (
    <div className="min-h-screen" style={{ background: '#0a0a0f' }}>
      {/* Header */}
      <header
        className="border-b"
        style={{ borderColor: 'rgba(255,255,255,0.06)', background: 'rgba(18,18,26,0.9)', backdropFilter: 'blur(12px)', position: 'sticky', top: 0, zIndex: 50 }}
      >
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <img
              src="/logo.png"
              alt="BPCE Equipment Solutions"
              className="h-9 w-auto object-contain"
            />
            <div>
              <h1
                className="text-xl font-bold leading-none tracking-tight"
                style={{ fontFamily: 'Playfair Display, serif', color: '#f8fafc' }}
              >
                BPCE Equipment Solutions
              </h1>
              <p className="text-xs mt-0.5" style={{ color: 'rgba(255,255,255,0.35)', letterSpacing: '0.05em' }}>
                Reconciliación Contable Inteligente
              </p>
            </div>
          </div>

          <div
            className="text-xs font-mono px-3 py-1.5 rounded-full"
            style={{ background: 'rgba(255,255,255,0.04)', color: 'rgba(255,255,255,0.35)', border: '1px solid rgba(255,255,255,0.08)' }}
          >
            NAOS ↔ EXACT · Motor de cruce automatizado
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-10">
        {/* Title section */}
        <div className="text-center mb-12" style={{ animation: 'fadeUp 0.5s ease-out forwards' }}>
          <h2
            className="text-4xl md:text-5xl font-bold mb-3 leading-tight"
            style={{ fontFamily: 'Playfair Display, serif', color: '#f8fafc' }}
          >
            Reconciliación{' '}
            <span style={{ color: '#6B2D8B' }}>Automatizada</span>
          </h2>
          <p className="text-white/40 text-base max-w-xl mx-auto">
            Carga los ficheros de NAOS y EXACT para detectar diferencias y generar el informe ejecutivo.
          </p>
        </div>

        {/* Upload grid */}
        <div
          className="grid grid-cols-1 md:grid-cols-2 gap-5 mb-6"
          style={{ animation: 'fadeUp 0.5s 0.1s ease-out forwards', opacity: 0 }}
        >
          <UploadZone
            label="Archivo de exportación NAOS"
            system="NAOS"
            file={naosFile}
            onFile={setNaosFile}
          />
          <UploadZone
            label="Archivo de exportación EXACT"
            system="EXACT"
            file={exactFile}
            onFile={setExactFile}
          />
        </div>

        {/* Action buttons */}
        <div
          className="flex gap-3 mb-8"
          style={{ animation: 'fadeUp 0.5s 0.2s ease-out forwards', opacity: 0 }}
        >
          <button
            onClick={handleReconcile}
            disabled={!canReconcile}
            className="flex-1 py-4 rounded-2xl font-semibold text-base transition-all duration-300 disabled:opacity-40 disabled:cursor-not-allowed"
            style={
              canReconcile
                ? {
                    background: 'linear-gradient(135deg, #6B2D8B, #8B3DAB)',
                    color: '#ffffff',
                    boxShadow: '0 0 24px rgba(107,45,139,0.4)',
                  }
                : { background: 'rgba(255,255,255,0.06)', color: 'rgba(255,255,255,0.3)' }
            }
          >
            {state === 'processing' ? (
              <span className="flex items-center justify-center gap-2">
                <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Procesando…
              </span>
            ) : (
              '⚡ Reconciliar'
            )}
          </button>

          {(naosFile || exactFile || state !== 'idle') && (
            <button
              onClick={handleReset}
              className="px-6 py-4 rounded-2xl font-semibold text-sm transition-all duration-200 hover:bg-white/10"
              style={{ background: 'rgba(255,255,255,0.06)', color: 'rgba(255,255,255,0.5)', border: '1px solid rgba(255,255,255,0.08)' }}
            >
              Limpiar
            </button>
          )}
        </div>

        {/* Results */}
        <div style={{ animation: 'fadeUp 0.5s 0.3s ease-out forwards', opacity: 0 }}>
          <ResultsPanel state={state} result={result} error={error} />
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t mt-20 py-6 text-center" style={{ borderColor: 'rgba(255,255,255,0.04)' }}>
        <p className="text-xs font-mono" style={{ color: 'rgba(255,255,255,0.2)' }}>
          BPCE Equipment Solutions · Motor de reconciliación NAOS ↔ EXACT · v1.0.0
        </p>
      </footer>
    </div>
  )
}
