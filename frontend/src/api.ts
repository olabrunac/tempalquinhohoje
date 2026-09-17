export interface TodayOut {
  day: string
  has_palquinho: boolean | null
  note?: string | null
}

export interface DayOut {
  day: string
  has_palquinho: boolean
  note?: string | null
}

export interface VoteOut {
  id: number
  day: string
  name: string
  vote: boolean
  created_at: string
}

export interface SuggestionOut {
  day: string
  has_palquinho?: boolean | null
  votes: VoteOut[]
}

const BASE = import.meta.env.VITE_API_BASE ?? '/api/v1'

export class ApiError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(BASE + path, options)
  if (res.status === 204) return undefined as T
  const body = await res.json().catch(() => null)
  if (!res.ok) {
    const detail = body?.detail ?? res.statusText
    throw new ApiError(typeof detail === 'string' ? detail : res.statusText, res.status)
  }
  return body as T
}

function jsonHeaders(extra?: HeadersInit): HeadersInit {
  return { 'Content-Type': 'application/json', ...extra }
}

export const api = {
  getToday: () => request<TodayOut>('/today'),
  getDays: () => request<DayOut[]>('/days'),
  getVotes: (day: string) => request<VoteOut[]>(`/votes/${day}`),
  vote: (payload: { day: string; name: string; vote: boolean }) =>
    request<VoteOut>('/vote', {
      method: 'POST',
      headers: jsonHeaders(),
      body: JSON.stringify(payload),
    }),
  setDay: (day: string, has_palquinho: boolean, note: string | null, adminKey: string) =>
    request<DayOut>(`/admin/${day}`, {
      method: 'PUT',
      headers: jsonHeaders({ 'X-Admin-Key': adminKey }),
      body: JSON.stringify({ has_palquinho, note }),
    }),
  unsetDay: (day: string, adminKey: string) =>
    request<void>(`/admin/${day}`, {
      method: 'DELETE',
      headers: jsonHeaders({ 'X-Admin-Key': adminKey }),
    }),
  getSuggestions: (adminKey: string) =>
    request<SuggestionOut[]>('/admin/suggestions', {
      headers: jsonHeaders({ 'X-Admin-Key': adminKey }),
    }),
}