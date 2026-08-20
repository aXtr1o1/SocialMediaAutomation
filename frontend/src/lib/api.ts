import { supabase } from './supabaseClient'

function getApiUrl() {
  const apiUrl = import.meta.env.VITE_API_URL?.replace(/\/$/, '')

  if (!apiUrl) {
    throw new Error('Missing VITE_API_URL in .env.local')
  }

  return apiUrl
}

function getErrorMessage(body: unknown, fallback: string) {
  if (body && typeof body === 'object' && 'detail' in body) {
    const detail = (body as { detail: unknown }).detail

    if (typeof detail === 'string' && detail.trim()) {
      return detail
    }
  }

  return fallback
}

async function getAccessToken(forceRefresh = false) {
  if (forceRefresh) {
    const { data, error } = await supabase.auth.refreshSession()
    if (error) {
      return null
    }
    return data.session?.access_token ?? null
  }

  const { data } = await supabase.auth.getSession()
  return data.session?.access_token ?? null
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  let token = await getAccessToken()

  if (!token) {
    throw new Error('You need to sign in again.')
  }

  const send = (accessToken: string) =>
    fetch(`${getApiUrl()}${path}`, {
      ...init,
      headers: {
        'Content-Type': 'application/json',
        ...init?.headers,
        Authorization: `Bearer ${accessToken}`,
      },
    })

  let response = await send(token)

  if (response.status === 401) {
    token = await getAccessToken(true)
    if (!token) {
      throw new Error('You need to sign in again.')
    }
    response = await send(token)
  }

  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error(getErrorMessage(body, 'Request failed'))
  }

  return response.json() as Promise<T>
}
