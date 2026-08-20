import { BlueskyIcon } from '../../assets/icons/BlueskyIcon'
import { LinkedInIcon } from '../../assets/icons/LinkedInIcon'
import {
  formatVerifiedAt,
  getAccountPlatformId,
  getAccountSubtitle,
  getAccountTitle,
  isAccountExpired,
  type ConnectedAccount,
} from '../../lib/accounts'
import { MaterialIcon } from '../ui/MaterialIcon'

type ConnectedAccountCardProps = {
  account: ConnectedAccount
  isBusy?: boolean
  onReconnect?: () => void
  onDisconnect?: () => void
}

function PlatformIcon({ account }: { account: ConnectedAccount }) {
  const platformId = getAccountPlatformId(account)

  if (platformId === 'linkedin') {
    return (
      <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-[#0077b5] text-white shadow-sm">
        <LinkedInIcon className="h-6 w-6" />
      </div>
    )
  }

  if (platformId === 'bluesky') {
    return (
      <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-[#0085FF] text-white shadow-sm">
        <BlueskyIcon className="h-7 w-7" />
      </div>
    )
  }

  return (
    <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-surface-container-high text-primary">
      <MaterialIcon name="account_circle" className="text-[24px]" />
    </div>
  )
}

export function ConnectedAccountCard({
  account,
  isBusy = false,
  onReconnect,
  onDisconnect,
}: ConnectedAccountCardProps) {
  const expired = isAccountExpired(account)

  return (
    <div className="group relative flex flex-col overflow-hidden rounded-xl bg-surface-container p-md transition-transform hover:-translate-y-1 hover:shadow-md">
      <div
        className={`pointer-events-none absolute -right-12 -top-12 h-32 w-32 rounded-full blur-2xl transition-colors ${
          expired ? 'bg-error/10' : 'bg-primary/10 group-hover:bg-primary/20'
        }`}
      />

      <div className="relative z-10 mb-md flex items-start justify-between">
        <PlatformIcon account={account} />
        {expired ? (
          <div className="flex items-center gap-1 rounded-full bg-error-container px-3 py-1 font-label-sm text-label-sm text-on-error-container">
            <MaterialIcon name="error" className="text-[14px]" />
            Expired
          </div>
        ) : (
          <div className="flex items-center gap-1 rounded-full bg-primary-fixed/20 px-3 py-1 font-label-sm text-label-sm text-on-primary-fixed">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-primary" />
            Connected
          </div>
        )}
      </div>

      <div className="relative z-10 mb-lg">
        <h3 className="font-headline-sm text-headline-sm text-on-surface">{getAccountTitle(account)}</h3>
        <p className="font-body-md text-body-md text-on-surface-variant">{getAccountSubtitle(account)}</p>
        {expired ? (
          <div className="mt-xs flex items-center gap-2 text-error">
            <MaterialIcon name="warning" className="text-[14px]" />
            <span className="font-label-sm text-label-sm">Token expired. Reconnect required.</span>
          </div>
        ) : (
          <div className="mt-xs flex items-center gap-2 text-on-surface-variant/70">
            <MaterialIcon name="verified" className="text-[14px]" />
            <span className="font-label-sm text-label-sm">{formatVerifiedAt(account)}</span>
          </div>
        )}
      </div>

      <div className="relative z-10 mt-auto flex gap-2 pt-md">
        {expired ? (
          <button
            type="button"
            onClick={onReconnect}
            disabled={isBusy}
            className="flex-1 rounded-lg bg-primary py-2 font-label-md text-label-md text-on-primary shadow-sm transition-colors hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isBusy ? 'Reconnecting...' : 'Reconnect'}
          </button>
        ) : (
          <button
            type="button"
            onClick={onDisconnect}
            disabled={isBusy}
            className="flex-1 rounded-lg bg-surface py-2 font-label-md text-label-md text-error transition-colors hover:bg-error-container hover:text-on-error-container disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isBusy ? 'Disconnecting...' : 'Disconnect'}
          </button>
        )}
      </div>
    </div>
  )
}
