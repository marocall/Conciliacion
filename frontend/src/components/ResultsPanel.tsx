import { useEffect, useRef, useState } from 'react'
import { AppState, ReconciliationResult } from '../hooks/useReconciliation'
import { SummaryTable } from './SummaryTable'

interface Props {
  state: AppState
  result: ReconciliationResult | null
  error: string | null
}

const PROCESSING_MESSAGES = [
  'Cargando apuntes NAOS…',
  'Leyendo fichero EXACT…',
  'Normalizando referencias…',
  'Cruzando por ref + importe + fecha…',
  'Pasada B: matching one-to-one…',
  'Calculando diferencias de saldo…',
  'Generando informe Excel…',
]

function useAnimatedCounter(target: number, duration = 1000) {
  const [value, setValue] = useState(0)
  useEffect(() => {
    if (target === 0) return
    const start = performance.now()
    const tick = (now: number) => {
      const t = Math.min((now - start) / duration, 1)
      setValue(Math.round(t * target))
      if (t < 1) requestAnimationFrame(tick)
    }
    requestAnimationFrame(tick)
  }, [target, duration])
  return value
}


function MetricCard({
  label,
  value,
  color,
  prefix = '',
  suffix = '',
}: {
  label: string
  value: number
  color: string
  prefix?: string
  suffix?: string
}) {
  const animated = useAnimatedCounter(Math.abs(Math.round(value)))
  return (
    <div
      className="rounded-2xl p-5 flex flex-col gap-2"
      style={{ background: '#1a1a26', border: '1px solid rgba(255,255,255,0.06)' }}
    >
      <p className="text-xs uppercase tracking-widest font-semibold" style={{ color: 'rgba(255,255,255,0.4)' }}>
        {label}
      </p>
      <p className="font-mono text-2xl font-bold leading-none" style={{ color }}>
        {prefix}
        {animated.toLocaleString('es-ES')}
        {suffix}
      </p>
    </div>
  )
}

export function ResultsPanel({ state, result, error }: Props) {
  const [msgIdx, setMsgIdx] = useState(0)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    if (state === 'processing') {
      setMsgIdx(0)
      intervalRef.current = setInterval(() => {
        setMsgIdx((i) => (i + 1) % PROCESSING_MESSAGES.length)
      }, 800)
    } else {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [state])

  if (state === 'idle') {
    return (
      <div
        className="rounded-2xl p-10 text-center"
        style={{ background: '#12121a', border: '1px solid rgba(255,255,255,0.06)' }}
      >
        <div
          className="w-16 h-16 rounded-2xl mx-auto mb-5 flex items-center justify-center"
          style={{ background: 'rgba(107,45,139,0.1)', border: '1px solid rgba(107,45,139,0.2)' }}
        >
          <svg className="w-8 h-8" style={{ color: '#6B2D8B' }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
            />
          </svg>
        </div>
        <h3 className="font-display text-xl text-white mb-2">Listo para reconciliar</h3>
        <p className="text-white/40 text-sm max-w-sm mx-auto leading-relaxed">
          Carga los archivos NAOS y EXACT, luego pulsa <strong className="text-white/60">Reconciliar</strong> para
          obtener el informe de diferencias.
        </p>
        <div className="mt-6 flex justify-center gap-6 text-xs text-white/30">
          <span>✦ Cruce por referencia</span>
          <span>✦ Cruce por descripción</span>
          <span>✦ Cruce one-to-one</span>
        </div>
      </div>
    )
  }

  if (state === 'processing') {
    return (
      <div
        className="rounded-2xl p-10 text-center"
        style={{ background: '#12121a', border: '1px solid rgba(255,255,255,0.06)' }}
      >
        <div className="relative w-16 h-16 mx-auto mb-6">
          <svg className="w-16 h-16 animate-spin-slow" viewBox="0 0 64 64" fill="none">
            <circle cx="32" cy="32" r="28" stroke="rgba(107,45,139,0.15)" strokeWidth="4" />
            <path
              d="M32 4 A28 28 0 0 1 60 32"
              stroke="#6B2D8B"
              strokeWidth="4"
              strokeLinecap="round"
            />
          </svg>
          <div
            className="absolute inset-0 flex items-center justify-center text-lg"
            style={{ color: '#6B2D8B' }}
          >
            ⚡
          </div>
        </div>
        <h3 className="font-display text-xl text-white mb-3">Procesando reconciliación</h3>
        <div
          className="inline-block px-5 py-2 rounded-full text-sm font-mono transition-all"
          style={{ background: 'rgba(107,45,139,0.1)', color: '#6B2D8B', border: '1px solid rgba(107,45,139,0.2)' }}
        >
          {PROCESSING_MESSAGES[msgIdx]}
        </div>
        <div className="mt-6 w-full max-w-xs mx-auto h-1 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.06)' }}>
          <div
            className="h-full rounded-full"
            style={{
              background: 'linear-gradient(90deg, #6B2D8B, #8B3DAB)',
              width: `${((msgIdx + 1) / PROCESSING_MESSAGES.length) * 100}%`,
              transition: 'width 0.8s ease',
            }}
          />
        </div>
      </div>
    )
  }

  if (state === 'error') {
    return (
      <div
        className="rounded-2xl p-8"
        style={{ background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.3)' }}
      >
        <div className="flex items-start gap-4">
          <div className="w-10 h-10 rounded-xl bg-red-500/20 flex items-center justify-center flex-shrink-0">
            <svg className="w-5 h-5 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div>
            <h3 className="text-red-400 font-semibold mb-1">Error en el procesamiento</h3>
            <p className="text-red-300/70 text-sm font-mono">{error}</p>
          </div>
        </div>
      </div>
    )
  }

  if (state === 'done' && result) {
    return (
      <div className="space-y-6 animate-fade-up">
        {/* Metrics */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <MetricCard label="Total fechas" value={result.totalDates} color="#f8fafc" />
          <MetricCard label="Fechas OK" value={result.matchedDates} color="#10b981" />
          <MetricCard label="Con diferencia" value={result.diffDates} color="#6B2D8B" />
          <MetricCard
            label="Diferencia total"
            value={result.totalDiff}
            color={Math.abs(result.totalDiff) < 0.02 ? '#10b981' : '#ef4444'}
            suffix=" €"
          />
        </div>

        {/* Download button */}
        <a
          href={result.downloadUrl}
          download="reconciliacion_resultado.xlsx"
          className="flex items-center justify-center gap-3 w-full py-4 rounded-2xl font-semibold text-base transition-all duration-300 hover:scale-[1.02]"
          style={{
            background: 'linear-gradient(135deg, #6B2D8B, #8B3DAB)',
            color: '#ffffff',
            boxShadow: '0 0 30px rgba(107,45,139,0.4)',
            animation: 'pulsePurple 2s ease-in-out infinite',
          }}
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
          </svg>
          Descargar Informe Excel
        </a>

        {/* Summary table */}
        <SummaryTable summary={result.summary} diffDates={result.diffDates} />
      </div>
    )
  }

  return null
}
