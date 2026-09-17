export interface TodayOut {
  day: string
  has_palquinho: boolean | null
  note?: string | null
  instagram?: string | null
}

export interface DayOut {
  day: string
  has_palquinho: boolean
  note?: string | null
  instagram?: string | null
}

export interface SuggestionOut {
  id: number
  day: string
  organizer: string
  instagram?: string | null
  status: string
  created_at: string
  has_palquinho?: boolean | null
}

export interface SuggestionIn {
  day: string
  organizer: string
  instagram?: string | null
}

export interface VisitDayOut {
  day: string
  count: number
}

export interface VisitsAdminOut {
  total: number
  today: number
  days: VisitDayOut[]
}

export const ADMIN_KEY = 'tph_admin_key'

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
  suggest: (payload: SuggestionIn) =>
    request<SuggestionOut>('/suggestions', {
      method: 'POST',
      headers: jsonHeaders(),
      body: JSON.stringify(payload),
    }),
  setDay: (day: string, has_palquinho: boolean, note: string | null, instagram: string | null, adminKey: string) =>
    request<DayOut>(`/admin/${day}`, {
      method: 'PUT',
      headers: jsonHeaders({ 'X-Admin-Key': adminKey }),
      body: JSON.stringify({ has_palquinho, note, instagram }),
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
  registerVisit: () =>
    request<{ ok: boolean }>('/visits', {
      method: 'POST',
      headers: jsonHeaders(),
    }),
  getVisits: (adminKey: string) =>
    request<VisitsAdminOut>('/admin/visits', {
      headers: jsonHeaders({ 'X-Admin-Key': adminKey }),
    }),
  confirmSuggestion: (id: number, has_palquinho: boolean, instagram: string | null, adminKey: string) =>
    request<DayOut>(`/admin/suggestions/${id}/confirm`, {
      method: 'POST',
      headers: jsonHeaders({ 'X-Admin-Key': adminKey }),
      body: JSON.stringify({ has_palquinho, instagram }),
    }),
  dismissSuggestion: (id: number, adminKey: string) =>
    request<void>(`/admin/suggestions/${id}`, {
      method: 'DELETE',
      headers: jsonHeaders({ 'X-Admin-Key': adminKey }),
    }),
}