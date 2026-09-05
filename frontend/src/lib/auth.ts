import { supabase } from './supabaseClient'
import { apiFetch } from './api'
import { paths } from './paths'

export async function signInWithGoogle() {
  const { error } = await supabase.auth.signInWithOAuth({
    provider: 'google',
    options: {
      redirectTo: `${window.location.origin}${paths.callback}`,
    },
  })

  if (error) {
    throw error
  }
}

function getApiUrl() {
  const apiUrl = import.meta.env.VITE_API_URL?.replace(/\/$/, '')

  if (!apiUrl) {
    throw new Error('Missing VITE_API_URL in .env.local')
  }

  return apiUrl
}

function getAuthErrorMessage(body: unknown, fallback: string) {
  if (body && typeof body === 'object' && 'detail' in body) {
    const detail = (body as { detail: unknown }).detail
    if (typeof detail === 'string' && detail.trim()) {
      return detail
    }
  }
  return fallback
}

function getLoginErrorMessage(body: unknown) {
  return getAuthErrorMessage(body, 'Invalid username/email or password')
}

export async function signInWithEmail(identifier: string, password: string) {
  const response = await fetch(`${getApiUrl()}/auth/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      identifier: identifier.trim(),
      password,
    }),
  })

  const body = await response.json().catch(() => ({}))

  if (!response.ok) {
    throw new Error(getLoginErrorMessage(body))
  }

  const accessToken =
    body && typeof body === 'object' && 'access_token' in body
      ? (body as { access_token: unknown }).access_token
      : null
  const refreshToken =
    body && typeof body === 'object' && 'refresh_token' in body
      ? (body as { refresh_token: unknown }).refresh_token
      : null

  if (typeof accessToken !== 'string' || typeof refreshToken !== 'string') {
    throw new Error('Login succeeded but session tokens were not returned.')
  }

  const { error } = await supabase.auth.setSession({
    access_token: accessToken,
    refresh_token: refreshToken,
  })

  if (error) {
    throw error
  }
}

export async function requestPasswordReset(identifier: string) {
  const response = await fetch(`${getApiUrl()}/auth/forgot-password`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ identifier: identifier.trim() }),
  })

  const body = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new Error(getAuthErrorMessage(body, 'Could not send reset code'))
  }

  const message =
    body && typeof body === 'object' && typeof (body as { message?: unknown }).message === 'string'
      ? (body as { message: string }).message
      : 'If an account exists, we sent a one-time code.'

  return { message }
}

export async function resetPasswordWithOtp(input: {
  identifier: string
  otp: string
  password: string
  confirmPassword: string
}) {
  const response = await fetch(`${getApiUrl()}/auth/reset-password`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      identifier: input.identifier.trim(),
      otp: input.otp.trim(),
      password: input.password,
      confirm_password: input.confirmPassword,
    }),
  })

  const body = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new Error(getAuthErrorMessage(body, 'Could not reset password'))
  }

  const message =
    body && typeof body === 'object' && typeof (body as { message?: unknown }).message === 'string'
      ? (body as { message: string }).message
      : 'Password updated. You can sign in with your new password.'

  return { message }
}

type SignUpWithEmailInput = {
  email: string
  password: string
  firstName: string
  lastName: string
  username: string
}

export async function signUpWithEmail({
  email,
  password,
  firstName,
  lastName,
  username,
}: SignUpWithEmailInput) {
  const { data, error } = await supabase.auth.signUp({
    email,
    password,
    options: {
      emailRedirectTo: `${window.location.origin}${paths.callback}`,
      data: {
        first_name: firstName,
        last_name: lastName,
        username,
        full_name: `${firstName} ${lastName}`.trim(),
      },
    },
  })

  if (error) {
    throw error
  }

  if (data.user && (data.user.identities?.length ?? 0) === 0) {
    throw new Error('An account with this email already exists. Sign in instead.')
  }

  return data
}

export async function ensurePublicUserProfile() {
  await apiFetch('/auth/me')
}

export async function signOut() {
  const { error } = await supabase.auth.signOut()

  if (error) {
    throw error
  }
}

type UpdateUserProfileInput = {
  firstName: string
  lastName: string
  username: string
}

export async function updateUserProfile({ firstName, lastName, username }: UpdateUserProfileInput) {
  const trimmedFirstName = firstName.trim()
  const trimmedLastName = lastName.trim()
  const trimmedUsername = username.trim()
  const fullName = `${trimmedFirstName} ${trimmedLastName}`.trim()

  const { data, error } = await supabase.auth.updateUser({
    data: {
      first_name: trimmedFirstName,
      last_name: trimmedLastName,
      username: trimmedUsername,
      full_name: fullName,
      name: fullName,
    },
  })

  if (error) {
    throw error
  }

  await apiFetch('/auth/me', {
    method: 'PATCH',
    body: JSON.stringify({
      first_name: trimmedFirstName,
      last_name: trimmedLastName,
      username: trimmedUsername,
    }),
  })

  return data.user
}

export async function changePassword(input: {
  currentPassword: string
  newPassword: string
  confirmPassword: string
  signOutAllDevices: boolean
}) {
  const result = await apiFetch<{
    message: string
    signed_out_all_devices: boolean
  }>('/auth/change-password', {
    method: 'POST',
    body: JSON.stringify({
      current_password: input.currentPassword,
      new_password: input.newPassword,
      confirm_password: input.confirmPassword,
      sign_out_all_devices: input.signOutAllDevices,
    }),
  })

  return result
}
