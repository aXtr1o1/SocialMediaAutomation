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

export async function signInWithEmail(email: string, password: string) {
  const { error } = await supabase.auth.signInWithPassword({ email, password })

  if (error) {
    throw error
  }
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
