import { apiFetch } from './api'
import type { ConnectPlatform } from './platforms'

export type ConnectedAccount = {
  id: string
  account_name: string
  provider_handle: string | null
  is_enabled: boolean
  connected_at?: string | null
  last_synced_at?: string | null
  token_expiry?: string | null
  platform?: { platform_name: string } | null
}

export function listConnectedAccounts() {
  return apiFetch<ConnectedAccount[]>('/accounts')
}

export function startAccountConnect(platform: ConnectPlatform['id']) {
  return apiFetch<{ authorization_url: string }>(`/accounts/${platform}/connect`)
}

export function disconnectAccount(accountId: string) {
  return apiFetch<{ message: string }>(`/accounts/${accountId}`, {
    method: 'DELETE',
  })
}

export function getAccountPlatformId(account: ConnectedAccount): ConnectPlatform['id'] | null {
  const name = account.platform?.platform_name?.toLowerCase()

  if (name === 'linkedin' || name === 'bluesky') {
    return name
  }

  return null
}

export function getAccountPlatformName(account: ConnectedAccount) {
  const id = getAccountPlatformId(account)

  if (id === 'linkedin') {
    return 'LinkedIn'
  }

  if (id === 'bluesky') {
    return 'Bluesky'
  }

  return account.platform?.platform_name || 'Account'
}

export function getAccountTitle(account: ConnectedAccount) {
  const platformId = getAccountPlatformId(account)
  const handle = account.provider_handle?.trim()

  if (platformId === 'bluesky' && handle) {
    return handle.startsWith('@') ? handle : `@${handle}`
  }

  return account.account_name
}

export function getAccountSubtitle(account: ConnectedAccount) {
  const platformId = getAccountPlatformId(account)

  if (platformId === 'linkedin') {
    return 'LinkedIn Personal Profile'
  }

  if (platformId === 'bluesky') {
    return 'Bluesky Account'
  }

  return getAccountPlatformName(account)
}

export function isAccountExpired(account: ConnectedAccount) {
  if (!account.is_enabled) {
    return true
  }

  if (!account.token_expiry) {
    return false
  }

  const expiry = Date.parse(account.token_expiry)
  return Number.isFinite(expiry) && expiry < Date.now()
}

export function formatVerifiedAt(account: ConnectedAccount) {
  const timestamp = account.last_synced_at || account.connected_at

  if (!timestamp) {
    return 'Verified just now'
  }

  const then = Date.parse(timestamp)

  if (!Number.isFinite(then)) {
    return 'Verified just now'
  }

  const minutes = Math.max(0, Math.floor((Date.now() - then) / 60000))

  if (minutes < 1) {
    return 'Verified just now'
  }

  if (minutes < 60) {
    return `Verified ${minutes} minute${minutes === 1 ? '' : 's'} ago`
  }

  const hours = Math.floor(minutes / 60)

  if (hours < 24) {
    return `Verified ${hours} hour${hours === 1 ? '' : 's'} ago`
  }

  const days = Math.floor(hours / 24)
  return `Verified ${days} day${days === 1 ? '' : 's'} ago`
}
