import type { AnalyzeResponse } from '../types/api'

const RISK_COLORS: Record<string, string> = {
  low: 'bg-emerald-100 text-emerald-800 ring-emerald-200',
  medium: 'bg-amber-100 text-amber-800 ring-amber-200',
  high: 'bg-red-100 text-red-800 ring-red-200',
  unknown: 'bg-slate-100 text-slate-800 ring-slate-200',
}

export default function DecisionBadge({ result }: { result: AnalyzeResponse }) {
  const isAuto = result.decision === 'AUTO_HANDLE'
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Decision</h3>
      <div className="mt-2 flex items-center gap-2">
        <span
          className={`rounded-full px-3 py-1 text-sm font-semibold ring-1 ${
            isAuto ? 'bg-emerald-600 text-white' : 'bg-red-600 text-white'
          }`}
        >
          {isAuto ? 'AUTO-HANDLE' : 'ESCALATE TO HUMAN'}
        </span>
        <span className={`rounded-full px-2 py-0.5 text-xs font-medium ring-1 ${RISK_COLORS[result.risk_level]}`}>
          risk: {result.risk_level}
        </span>
      </div>
      <p className="mt-2 text-sm text-slate-700">{result.decision_reason}</p>
    </div>
  )
}
