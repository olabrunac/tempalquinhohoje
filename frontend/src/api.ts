// Um evento do dia: a nota e o link do anúncio daquele evento (link é opcional).
export interface EventItem {
  id: number
  position: number
  note: string
  instagram?: string | null
}

// O que o admin digita: sem id, porque ainda não foi salvo.
export interface EventDraft {
  note: string
  instagram?: string | null
}

export interface TodayOut {
  day: string
  has_palquinho: boolean | null
  // Dia sem palquinho que é outro evento (aparece laranja, não vermelho).
  // Precisa ser explícito: às vezes a nota do dia não é evento.
  is_other_event: boolean
  events: EventItem[]
}

export interface DayOut {
  day: string
  has_palquinho: boolean
  is_other_event: boolean
  events: EventItem[]
}

export interface SuggestionOut {
  id: number
  day: string
  organizer: string
  instagram?: string | null
  status: 'pending' | 'solved'
  action?: 'confirm' | 'dismiss' | null
  solved_at?: string | null
  created_at: string
  has_palquinho?: boolean | null
}

export interface SuggestionIn {
  day: string
  organizer: string
  instagram?: string | null
}

export interface DashboardOut {
  days: DayOut[]
  pending: SuggestionOut[]
  archive: SuggestionOut[]
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
  suggest: (payload: SuggestionIn) =>
    request<SuggestionOut>('/suggestions', {
      method: 'POST',
      headers: jsonHeaders(),
      body: JSON.stringify(payload),
    }),
  setDay: (
    day: string,
    has_palquinho: boolean,
    is_other_event: boolean,
    events: EventDraft[],
    adminKey: string
  ) =>
    request<DayOut>(`/admin/${day}`, {
      method: 'PUT',
      headers: jsonHeaders({ 'X-Admin-Key': adminKey }),
      body: JSON.stringify({
        has_palquinho,
        is_other_event,
        // nota vazia não vai pro banco (o backend também ignora, mas cortar aqui
        // evita mandar lixo e tomar 422 no limite de tamanho)
        events: events
          .map((e) => ({ note: e.note.trim(), instagram: (e.instagram ?? '').trim() || null }))
          .filter((e) => e.note.length > 0),
      }),
    }),
  unsetDay: (day: string, adminKey: string) =>
    request<void>(`/admin/${day}`, {
      method: 'DELETE',
      headers: jsonHeaders({ 'X-Admin-Key': adminKey }),
    }),
  getSuggestions: (adminKey: string, status?: 'pending' | 'solved') =>
    request<SuggestionOut[]>(`/admin/suggestions${status ? `?status=${status}` : ''}`, {
      headers: jsonHeaders({ 'X-Admin-Key': adminKey }),
    }),
  getDashboard: (adminKey: string) =>
    request<DashboardOut>('/admin/dashboard', {
      headers: jsonHeaders({ 'X-Admin-Key': adminKey }),
    }),
  confirmSuggestion: (
    id: number,
    has_palquinho: boolean,
    organizer: string,
    instagram: string | null,
    adminKey: string
  ) =>
    request<DayOut>(`/admin/suggestions/${id}/confirm`, {
      method: 'POST',
      headers: jsonHeaders({ 'X-Admin-Key': adminKey }),
      // Confirmar já marca o dia e cria o primeiro evento com o pedido de quem sugeriu
      // (nota = quem organiza). Aí é só ajustar o texto e salvar pelo painel.
      body: JSON.stringify({
        has_palquinho,
        events: [{ note: organizer, instagram: instagram?.trim() || null }],
      }),
    }),
  dismissSuggestion: (id: number, adminKey: string) =>
    request<void>(`/admin/suggestions/${id}`, {
      method: 'DELETE',
      headers: jsonHeaders({ 'X-Admin-Key': adminKey }),
    }),
}