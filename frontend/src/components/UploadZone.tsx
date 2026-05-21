import React, { useCallback, useState } from 'react'

interface Props {
  label: string
  system: 'NAOS' | 'EXACT'
  file: File | null
  onFile: (f: File) => void
}

export function UploadZone({ label, system, file, onFile }: Props) {
  const [dragging, setDragging] = useState(false)

  const accent = system === 'NAOS' ? '#6B2D8B' : '#3b82f6'
  const accentLight = system === 'NAOS' ? 'rgba(107,45,139,0.15)' : 'rgba(59,130,246,0.15)'
  const accentGlow = system === 'NAOS' ? 'rgba(107,45,139,0.3)' : 'rgba(59,130,246,0.3)'

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setDragging(false)
      const f = e.dataTransfer.files[0]
      if (f) onFile(f)
    },
    [onFile],
  )

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]
    if (f) onFile(f)
  }

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  return (
    <div
      className="relative rounded-2xl overflow-hidden transition-all duration-300"
      style={{
        background: dragging ? accentLight : '#12121a',
        border: `1.5px ${dragging ? 'solid' : 'dashed'} ${dragging ? accent : 'rgba(255,255,255,0.12)'}`,
        boxShadow: dragging ? `0 0 24px ${accentGlow}` : 'none',
      }}
      onDragOver={(e) => {
        e.preventDefault()
        setDragging(true)
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
    >
      <input
        type="file"
        accept=".xlsx,.xls"
        className="absolute inset-0 opacity-0 cursor-pointer z-10"
        onChange={handleChange}
      />

      <div className="p-7">
        {/* System badge */}
        <div className="flex items-center gap-3 mb-5">
          <div
            className="w-10 h-10 rounded-xl flex items-center justify-center text-sm font-bold"
            style={{ background: accentLight, color: accent, border: `1px solid ${accent}` }}
          >
            {system === 'NAOS' ? 'N' : 'E'}
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-widest" style={{ color: accent }}>
              {system}
            </p>
            <p className="text-white font-semibold text-sm">{label}</p>
          </div>
        </div>

        {file ? (
          <div
            className="rounded-xl p-4 flex items-center gap-4"
            style={{ background: 'rgba(16,185,129,0.1)', border: '1px solid rgba(16,185,129,0.3)' }}
          >
            <div className="w-9 h-9 rounded-lg bg-emerald-500/20 flex items-center justify-center flex-shrink-0">
              <svg className="w-5 h-5 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <div className="min-w-0">
              <p className="text-emerald-300 text-sm font-medium truncate">{file.name}</p>
              <p className="text-emerald-500 text-xs mt-0.5">{formatSize(file.size)}</p>
            </div>
          </div>
        ) : (
          <div className="text-center py-6">
            <div
              className="w-14 h-14 rounded-2xl mx-auto mb-4 flex items-center justify-center"
              style={{ background: accentLight }}
            >
              <svg
                className="w-7 h-7"
                style={{ color: accent }}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                />
              </svg>
            </div>
            <p className="text-white/80 text-sm mb-1">Arrastra el archivo aquí</p>
            <p className="text-white/40 text-xs">o haz clic para seleccionar</p>
            <div
              className="inline-block mt-3 px-3 py-1 rounded-full text-xs font-mono"
              style={{ background: 'rgba(255,255,255,0.05)', color: 'rgba(255,255,255,0.4)' }}
            >
              .xlsx · .xls
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
