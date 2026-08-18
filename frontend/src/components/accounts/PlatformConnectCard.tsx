import type { ReactNode } from 'react'
import type { ConnectPlatform } from '../../lib/platforms'
import { MaterialIcon } from '../ui/MaterialIcon'

type PlatformConnectCardProps = {
  platform: ConnectPlatform
  icon: ReactNode
  onConnect?: () => void
}

export function PlatformConnectCard({ platform, icon, onConnect }: PlatformConnectCardProps) {
  return (
    <div className="group relative flex h-full flex-col overflow-hidden rounded-xl border border-surface-variant bg-surface-container-lowest p-xl shadow-sm transition-shadow duration-300 hover:shadow-md">
      <div
        className={`pointer-events-none absolute -right-16 -top-16 h-48 w-48 rounded-full blur-3xl transition-colors duration-500 ${platform.glowClass}`}
      />
      <div className="mb-lg flex h-16 w-16 items-center justify-center rounded-lg bg-surface-container">
        <span className={platform.accentClass}>{icon}</span>
      </div>
      <h3 className="mb-sm font-headline-sm text-headline-sm text-on-surface">{platform.name}</h3>
      <p className="mb-xl flex-1 font-body-md text-body-md text-on-surface-variant">{platform.description}</p>
      <button
        type="button"
        onClick={onConnect}
        className={`flex w-full items-center justify-center gap-2 rounded-lg px-4 py-2 font-label-md text-label-md text-white shadow-sm transition-colors ${platform.buttonClass}`}
      >
        {platform.actionLabel}
        <MaterialIcon name="arrow_forward" className="text-[18px]" />
      </button>
    </div>
  )
}
