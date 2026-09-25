import type { BrandInfo } from '../types/api'

export default function Header({ brand }: { brand: BrandInfo | null }) {
  return (
    <header className="border-b border-slate-200 bg-white px-6 py-4">
      <div className="mx-auto flex max-w-5xl items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-slate-900">
            {brand?.brand_name ?? 'Uber_Support'} — AI Support Agent
          </h1>
          <p className="text-sm text-slate-500">{brand?.scope ?? 'Ride-hailing scope'}</p>
        </div>
        <div className="flex items-center gap-2 rounded-full bg-amber-50 px-3 py-1 text-xs font-medium text-amber-700 ring-1 ring-amber-200">
          <span className="h-2 w-2 rounded-full bg-amber-500" />
          DEMO MODE — no live LLM connected
        </div>
      </div>
    </header>
  )
}
