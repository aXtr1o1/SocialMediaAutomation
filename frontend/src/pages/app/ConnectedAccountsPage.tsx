import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { AddAccountCard } from '../../components/accounts/AddAccountCard'
import { ConnectedAccountCard } from '../../components/accounts/ConnectedAccountCard'
import { useConnectedAccounts } from '../../hooks/useConnectedAccounts'
import {
  disconnectAccount,
  getAccountPlatformId,
  startAccountConnect,
} from '../../lib/accounts'
import { paths } from '../../lib/paths'

export function ConnectedAccountsPage() {
  const { accounts, isLoading, error, reload } = useConnectedAccounts()
  const [searchParams, setSearchParams] = useSearchParams()
  const [notice, setNotice] = useState('')
  const [oauthError, setOauthError] = useState('')
  const [busyAccountId, setBusyAccountId] = useState('')

  useEffect(() => {
    const connected = searchParams.get('connected')
    const callbackError = searchParams.get('error')

    if (!connected && !callbackError) {
      return
    }

    if (connected === 'linkedin') {
      setNotice('LinkedIn account connected.')
    } else if (connected === 'bluesky') {
      setNotice('Bluesky account connected.')
    } else if (connected) {
      setNotice('Account connected.')
    }

    if (callbackError) {
      setOauthError(callbackError)
    }

    setSearchParams({}, { replace: true })
  }, [searchParams, setSearchParams])

  useEffect(() => {
    if (!notice) {
      return
    }

    const timeoutId = window.setTimeout(() => {
      setNotice('')
    }, 2500)

    return () => window.clearTimeout(timeoutId)
  }, [notice])

  async function handleReconnect(accountId: string) {
    const account = accounts.find((item) => item.id === accountId)
    const platformId = account ? getAccountPlatformId(account) : null

    if (!platformId) {
      setOauthError('This account cannot be reconnected yet.')
      return
    }

    setOauthError('')
    setBusyAccountId(accountId)

    try {
      const { authorization_url } = await startAccountConnect(platformId)
      window.location.assign(authorization_url)
    } catch (caught) {
      setBusyAccountId('')
      setOauthError(caught instanceof Error ? caught.message : 'Could not reconnect account')
    }
  }

  async function handleDisconnect(accountId: string) {
    setOauthError('')
    setBusyAccountId(accountId)

    try {
      await disconnectAccount(accountId)
      await reload()
    } catch (caught) {
      setOauthError(caught instanceof Error ? caught.message : 'Could not disconnect account')
    } finally {
      setBusyAccountId('')
    }
  }

  return (
    <div className="flex w-full flex-col px-lg py-xl">
      <div className="mb-lg">
        <h1 className="mb-xs font-display-lg text-display-lg text-on-surface">Connected Accounts</h1>
        <p className="max-w-2xl font-body-md text-body-md text-on-surface-variant">
          Manage the social profiles linked to your SMAP workspace. Ensure connections remain active to avoid
          publishing interruptions.
        </p>
      </div>

      {notice ? <p className="mb-md font-body-md text-body-md text-primary">{notice}</p> : null}
      {oauthError ? <p className="mb-md font-body-md text-body-md text-error">{oauthError}</p> : null}
      {error ? <p className="mb-md font-body-md text-body-md text-error">{error}</p> : null}
      {isLoading ? <p className="mb-md font-body-md text-body-md text-on-surface-variant">Loading accounts...</p> : null}

      <div className="grid grid-cols-1 gap-md md:grid-cols-2 lg:grid-cols-3">
        {!isLoading
          ? accounts.map((account) => (
              <ConnectedAccountCard
                key={account.id}
                account={account}
                isBusy={busyAccountId === account.id}
                onReconnect={() => {
                  void handleReconnect(account.id)
                }}
                onDisconnect={() => {
                  void handleDisconnect(account.id)
                }}
              />
            ))
          : null}
        {!isLoading ? <AddAccountCard /> : null}
      </div>

      {!isLoading && accounts.length === 0 ? (
        <Link
          className="mt-lg font-body-md text-on-surface-variant underline transition-colors hover:text-on-surface"
          to={paths.discover}
        >
          Skip for now
        </Link>
      ) : null}
    </div>
  )
}
