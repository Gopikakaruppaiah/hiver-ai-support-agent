import { useEffect, useState } from 'react'
import Header from '../components/Header'
import MessageInput from '../components/MessageInput'
import IntentCard from '../components/IntentCard'
import EvidenceList from '../components/EvidenceList'
import ReplyDraft from '../components/ReplyDraft'
import DecisionBadge from '../components/DecisionBadge'
import { analyzeMessage, getBrand } from '../services/api'
import type { AnalyzeResponse, BrandInfo } from '../types/api'

export default function SupportConsole() {
  const [brand, setBrand] = useState<BrandInfo | null>(null)
  const [result, setResult] = useState<AnalyzeResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getBrand().then(setBrand).catch(() => setBrand(null))
  }, [])

  async function handleAnalyze(message: string) {
    setLoading(true)
    setError(null)
    try {
      const res = await analyzeMessage(message)
      setResult(res)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Analysis failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <Header brand={brand} />
      <main className="mx-auto max-w-5xl space-y-4 px-6 py-6">
        <MessageInput onAnalyze={handleAnalyze} loading={loading} />

        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {result && (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <IntentCard result={result} />
            <DecisionBadge result={result} />
            <div className="md:col-span-2">
              <EvidenceList evidence={result.historical_evidence} />
            </div>
            <div className="md:col-span-2">
              <ReplyDraft result={result} />
            </div>
          </div>
        )}

        {!result && !loading && (
          <div className="rounded-xl border border-dashed border-slate-300 p-8 text-center text-sm text-slate-400">
            Enter a customer message above and click Analyze to see intent, historical
            evidence, a grounded draft reply, and the auto-handle/escalate decision.
          </div>
        )}
      </main>
    </div>
  )
}
