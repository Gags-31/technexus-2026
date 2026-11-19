export const API_BASE = '/api'

export class ApiError extends Error {
  status: number
  detail: string
  constructor(status: number, detail: string) {
    super(detail)
    this.status = status
    this.detail = detail
  }
}

export async function api<T = any>(path: string, init: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = { ...(init.headers as Record<string, string> || {}) }
  if (init.body && !(init.body instanceof FormData)) headers['Content-Type'] = 'application/json'
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
    credentials: 'include',
  })
  let data: any = null
  const text = await response.text()
  try { data = text ? JSON.parse(text) : null } catch { data = { detail: text } }
  if (!response.ok) {
    throw new ApiError(response.status, data?.detail || `Request failed (${response.status})`)
  }
  return data as T
}

export const get = <T = any>(path: string) => api<T>(path)
export const post = <T = any>(path: string, body?: any) =>
  api<T>(path, { method: 'POST', body: body === undefined ? undefined : JSON.stringify(body) })
export const put = <T = any>(path: string, body: any) =>
  api<T>(path, { method: 'PUT', body: JSON.stringify(body) })
export const patch = <T = any>(path: string, body: any) =>
  api<T>(path, { method: 'PATCH', body: JSON.stringify(body) })
export const del = <T = any>(path: string) => api<T>(path, { method: 'DELETE' })

export function downloadUrl(path: string) {
  return `${API_BASE}${path}`
}
