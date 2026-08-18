import type { User } from '@supabase/supabase-js'

export function getUserDisplayName(user: User) {
  const metadata = user.user_metadata
  const fullName = metadata.full_name || metadata.name
  const firstLast = [metadata.first_name, metadata.last_name].filter(Boolean).join(' ')

  return fullName || firstLast || user.email?.split('@')[0] || 'User'
}

export function getUserAvatarUrl(user: User) {
  const metadata = user.user_metadata
  return metadata.avatar_url || metadata.picture || null
}

function asString(value: unknown) {
  return typeof value === 'string' && value.trim() ? value.trim() : ''
}

export function getUserProfileDetails(user: User) {
  const metadata = user.user_metadata ?? {}
  const fullName = asString(metadata.full_name) || asString(metadata.name)
  const nameParts = fullName.split(/\s+/).filter(Boolean)
  const email = user.email ?? ''

  return {
    firstName:
      asString(metadata.first_name) || asString(metadata.given_name) || nameParts[0] || '',
    lastName:
      asString(metadata.last_name) ||
      asString(metadata.family_name) ||
      nameParts.slice(1).join(' ') ||
      '',
    username:
      asString(metadata.username) ||
      asString(metadata.preferred_username) ||
      email.split('@')[0] ||
      '',
    email,
    displayName: getUserDisplayName(user),
    avatarUrl: getUserAvatarUrl(user),
  }
}

export function getUserInitials(name: string) {
  const parts = name.trim().split(/\s+/).filter(Boolean)

  if (parts.length === 0) {
    return 'U'
  }

  return parts
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? '')
    .join('')
}
