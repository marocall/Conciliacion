import { DateSummary } from '../hooks/useReconciliation'

interface Props {
  summary: DateSummary[]
  diffDates: number
}

function fmt(n: number) {
  return n.toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function fmtDate(s: string) {
  try {
    const [y, m, d] = s.split('-')
    return `${d}/${m}/${y}`
  } catch {
    return s
  }
}

export function SummaryTable({ summary, diffDates }: Props) {
  return (
    <div>
      <div className="flex items-center gap-3 mb-4">
        <h3 className="text-white/80 text-sm font-semibold uppercase tracking-wider">
          Resumen por fecha
        </h3>
        {diffDates > 0 && (
          <span
            className="px-2.5 py-0.5 rounded-full text-xs font-bold font-mono"
            style={{ background: 'rgba(107,45,139,0.2)', color: '#6B2D8B', border: '1px solid rgba(107,45,139,0.4)' }}
          >
            {diffDates} con diferencia
          </span>
        )}
      </div>

      <div className="rounded-xl overflow-hidden" style={{ border: '1px solid rgba(255,255,255,0.06)' }}>
        {/* Header */}
        <div
          className="grid grid-cols-5 text-xs font-semibold uppercase tracking-wider"
          style={{ background: 'rgba(68,114,196,0.3)', color: 'rgba(255,255,255,0.6)' }}
        >
          {['Fecha', 'SALDO NAOS', 'SALDO EXACT', 'DIFERENCIA', 'Estado'].map((h) => (
            <div key={h} className="px-4 py-3 text-right first:text-left">
              {h}
            </div>
          ))}
        </div>

        {/* Rows */}
        <div className="divide-y divide-white/[0.04] max-h-72 overflow-y-auto">
          {summary.map((row, i) => (
            <div
              key={i}
              className="grid grid-cols-5 text-xs font-mono transition-colors hover:bg-white/[0.03]"
              style={{ background: i % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.015)' }}
            >
              <div className="px-4 py-2.5 text-white/70">{fmtDate(row.fecha)}</div>
              <div className="px-4 py-2.5 text-right text-white/80">{fmt(row.saldo_naos)}</div>
              <div className="px-4 py-2.5 text-right text-white/80">{fmt(row.saldo_exact)}</div>
              <div
                className="px-4 py-2.5 text-right font-semibold"
                style={{ color: row.cuadra ? '#10b981' : '#ef4444' }}
              >
                {fmt(row.diferencia)}
              </div>
              <div className="px-4 py-2.5 text-right">
                {row.cuadra ? (
                  <span className="text-emerald-400">✓</span>
                ) : (
                  <span className="text-red-400">✗</span>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
