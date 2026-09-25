import type { AnalyzeResponse, BrandInfo } from '../types/api'

// API_BASE is empty by default -- requests go to relative paths ('/api/...'),
// which the Vite dev server proxies to the backend (see vite.config.ts).
// Override via VITE_API_BASE_URL in frontend/.env if serving the frontend
// separately from the backend (e.g. `npm run preview` without the dev proxy).
const API_BASE: string = import.meta.env.VITE_API_BASE_URL || ''

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!res.ok) {
    const body = await res.text()
    throw new Error(`Request to ${path} failed (${res.status}): ${body}`)
  }
  return res.json() as Promise<T>
}

export function analyzeMessage(message: string): Promise<AnalyzeResponse> {
  return request<AnalyzeResponse>('/api/analyze', {
    method: 'POST',
    body: JSON.stringify({ message }),
  })
}

export function getBrand(): Promise<BrandInfo> {
  return request<BrandInfo>('/api/brand')
}
