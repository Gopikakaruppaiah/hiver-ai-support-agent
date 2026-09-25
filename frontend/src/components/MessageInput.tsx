import { useState } from 'react'

const SAMPLE_MESSAGES: { label: string; text: string }[] = [
  { label: 'Fare/billing', text: 'I was charged twice for my ride yesterday, please refund the extra charge' },
  { label: 'Cancellation', text: 'My driver cancelled on me after I waited 25 minutes, this is the third time' },
  { label: 'Lost item', text: 'I left my phone in the car after my last trip, how do I get it back' },
  { label: 'Driver safety', text: 'the driver was driving so unsafely I was terrified, nearly hit a pedestrian' },
  { label: 'Account issue', text: 'my account got hacked and someone is using it without my permission' },
]

export default function MessageInput({
  onAnalyze,
  loading,
}: {
  onAnalyze: (message: string) => void
  loading: boolean
}) {
  const [text, setText] = useState('')

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <label className="mb-2 block text-sm font-medium text-slate-700">
        Customer message
      </label>
      <textarea
        className="w-full resize-none rounded-lg border border-slate-300 p-3 text-sm text-slate-900 focus:border-slate-500 focus:outline-none"
        rows={3}
        placeholder="e.g. I was charged twice for my ride, please refund me"
        value={text}
        onChange={(e) => setText(e.target.value)}
      />
      <div className="mt-2 flex flex-wrap gap-2">
        <span className="text-xs text-slate-400 self-center">Try:</span>
        {SAMPLE_MESSAGES.map((s) => (
          <button
            key={s.label}
            className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs text-slate-600 hover:bg-slate-100"
            onClick={() => setText(s.text)}
            type="button"
          >
            {s.label}
          </button>
        ))}
      </div>
      <div className="mt-3 flex justify-end">
        <button
          className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
          disabled={!text.trim() || loading}
          onClick={() => onAnalyze(text.trim())}
        >
          {loading ? 'Analyzing…' : 'Analyze Message'}
        </button>
      </div>
    </div>
  )
}
