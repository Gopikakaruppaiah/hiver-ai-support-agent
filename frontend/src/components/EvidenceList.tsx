import type { EvidenceCase } from '../types/api'

export default function EvidenceList({ evidence }: { evidence: EvidenceCase[] }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
        Historical Evidence
      </h3>
      {evidence.length === 0 && (
        <p className="mt-2 text-sm text-slate-500">No historical evidence retrieved.</p>
      )}
      <div className="mt-2 space-y-3">
        {evidence.map((e) => (
          <div key={e.example_id} className="rounded-lg border border-slate-100 bg-slate-50 p-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono text-slate-400">{e.example_id}</span>
              <span className="rounded-full bg-slate-200 px-2 py-0.5 text-xs font-medium text-slate-700">
                similarity {e.similarity.toFixed(2)}
              </span>
            </div>
            <p className="mt-1 text-sm text-slate-800">
              <span className="font-medium">Customer:</span> {e.customer_text}
            </p>
            <p className="mt-1 text-sm text-slate-600">
              <span className="font-medium">Agent resolution:</span> {e.brand_text}
            </p>
          </div>
        ))}
      </div>
    </div>
  )
}
