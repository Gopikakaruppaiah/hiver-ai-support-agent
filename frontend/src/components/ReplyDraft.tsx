import { useEffect, useState } from 'react'
import type { AnalyzeResponse } from '../types/api'

export default function ReplyDraft({ result }: { result: AnalyzeResponse }) {
  const [draft, setDraft] = useState(result.generated_reply)
  const [status, setStatus] = useState<'idle' | 'approved' | 'escalated'>('idle')

  useEffect(() => {
    setDraft(result.generated_reply)
    setStatus('idle')
  }, [result])

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">AI Draft</h3>
      <textarea
        className="mt-2 w-full resize-none rounded-lg border border-slate-300 p-3 text-sm text-slate-900 focus:border-slate-500 focus:outline-none"
        rows={4}
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
      />
      <p className="mt-2 text-xs text-slate-500">{result.grounding_note}</p>
      <div className="mt-3 flex gap-2">
        <button
          className="rounded-lg bg-emerald-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-emerald-700"
          onClick={() => setStatus('approved')}
        >
          Approve &amp; Send
        </button>
        <button
          className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
          onClick={() => setStatus('idle')}
        >
          Edit
        </button>
        <button
          className="rounded-lg border border-red-300 px-3 py-1.5 text-sm font-medium text-red-700 hover:bg-red-50"
          onClick={() => setStatus('escalated')}
        >
          Escalate
        </button>
      </div>
      {status === 'approved' && (
        <p className="mt-2 text-xs text-emerald-600">Marked approved (UI state only — no send integration wired in this build).</p>
      )}
      {status === 'escalated' && (
        <p className="mt-2 text-xs text-red-600">Marked escalated by reviewer (UI state only).</p>
      )}
    </div>
  )
}
