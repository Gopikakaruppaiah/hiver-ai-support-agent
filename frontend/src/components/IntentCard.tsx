import type { AnalyzeResponse } from '../types/api'

export default function IntentCard({ result }: { result: AnalyzeResponse }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Intent</h3>
      <div className="mt-1 flex items-baseline gap-3">
        <span className="text-xl font-semibold text-slate-900">
          {result.predicted_intent.replace(/_/g, ' ')}
        </span>
        <span className="text-sm text-slate-500">
          {(result.intent_confidence * 100).toFixed(0)}% confidence
        </span>
      </div>
      <p className="mt-2 text-sm text-slate-600">{result.intent_reason}</p>
      {result.intent_alternatives.length > 0 && (
        <p className="mt-1 text-xs text-slate-400">
          Alternatives:{' '}
          {result.intent_alternatives
            .map((a) => `${a.intent.replace(/_/g, ' ')} (${(a.confidence * 100).toFixed(0)}%)`)
            .join(', ')}
        </p>
      )}
      <p className="mt-2 rounded bg-amber-50 px-2 py-1 text-xs text-amber-700 ring-1 ring-amber-100">
        {result.intent_caveat}
      </p>
    </div>
  )
}
