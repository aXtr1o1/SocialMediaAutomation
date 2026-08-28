import { useState } from 'react'
import { Link } from 'react-router-dom'
import { BlueskyIcon } from '../../assets/icons/BlueskyIcon'
import { LinkedInIcon } from '../../assets/icons/LinkedInIcon'
import { PlatformConnectCard } from '../../components/accounts/PlatformConnectCard'
import { MaterialIcon } from '../../components/ui/MaterialIcon'
import { startAccountConnect } from '../../lib/accounts'
import { CONNECT_PLATFORMS, type ConnectPlatform } from '../../lib/platforms'
import { paths } from '../../lib/paths'

const platformIcons = {
  linkedin: <LinkedInIcon className="h-8 w-8" />,
  bluesky: <BlueskyIcon className="h-8 w-8" />,
}

export function ConnectAccountPage() {
  const [connectingPlatform, setConnectingPlatform] = useState<ConnectPlatform['id'] | null>(null)
  const [error, setError] = useState('')

  async function handleConnect(platformId: ConnectPlatform['id']) {
    setError('')
    setConnectingPlatform(platformId)

    try {
      const { authorization_url } = await startAccountConnect(platformId)
      window.location.assign(authorization_url)
    } catch (caught) {
      setConnectingPlatform(null)
      setError(caught instanceof Error ? caught.message : 'Could not start account connection')
    }
  }

  return (
    <div className="mx-auto flex h-full w-full max-w-[1440px] flex-col px-lg py-xl">
      <div className="mb-xl flex-shrink-0">
        <h1 className="mb-xs font-headline-md text-headline-md text-on-surface">Connect a Social Account</h1>
        <p className="font-body-md text-body-md text-on-surface-variant">
          Choose a platform to link to your SMAP workspace.
        </p>
      </div>

      <div className="flex flex-1 flex-col items-center justify-center">
        {error ? <p className="mb-lg max-w-4xl text-center font-body-md text-body-md text-error">{error}</p> : null}

        <div className="mb-xl grid w-full max-w-4xl grid-cols-1 gap-lg md:grid-cols-2">
          {CONNECT_PLATFORMS.map((platform) => (
            <PlatformConnectCard
              key={platform.id}
              platform={platform}
              icon={platformIcons[platform.id]}
              isConnecting={connectingPlatform === platform.id}
              disabled={connectingPlatform !== null}
              onConnect={() => {
                void handleConnect(platform.id)
              }}
            />
          ))}
        </div>

        <Link
          to={paths.connectedAccounts}
          className="group inline-flex items-center gap-2 font-label-md text-label-md text-on-surface-variant transition-colors hover:text-primary"
        >
          <MaterialIcon name="arrow_back" className="text-[18px] transition-transform group-hover:-translate-x-1" />
          Back to Connected Accounts
        </Link>
      </div>
    </div>
  )
}
