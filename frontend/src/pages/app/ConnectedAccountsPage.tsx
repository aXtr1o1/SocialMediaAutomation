import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { AddAccountCard } from '../../components/accounts/AddAccountCard'
import { AlreadyConnectedModal } from '../../components/accounts/AlreadyConnectedModal'
import { ConnectedAccountCard } from '../../components/accounts/ConnectedAccountCard'
import { DeleteAccountModal } from '../../components/accounts/DeleteAccountModal'
import { useConnectedAccounts } from '../../hooks/useConnectedAccounts'
import { ApiError } from '../../lib/api'
import {
  activateAccount,
  deleteAccount,
  disconnectAccount,
  getAccountPlatformId,
  getConflictAccount,
  startAccountConnect,
  type ConnectedAccount,
} from '../../lib/accounts'
import { paths } from '../../lib/paths'

export function ConnectedAccountsPage() {
  const { accounts, isLoading, error, reload } = useConnectedAccounts()
  const [searchParams, setSearchParams] = useSearchParams()
  const [notice, setNotice] = useState('')
  const [oauthError, setOauthError] = useState('')
  const [busyAccountId, setBusyAccountId] = useState('')
  const [conflictAccount, setConflictAccount] = useState<ConnectedAccount | null>(null)
  const [pendingConflictPlatform, setPendingConflictPlatform] = useState<string | null>(null)
  const [accountToDelete, setAccountToDelete] = useState<ConnectedAccount | null>(null)
  const [isDeleting, setIsDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState('')

  useEffect(() => {
    const connected = searchParams.get('connected')
    const saved = searchParams.get('saved')
    const conflict = searchParams.get('conflict') === '1'
    const callbackError = searchParams.get('error')

    if (!connected && !saved && !callbackError && !conflict) {
      return
    }

    if (connected === 'linkedin') {
      setNotice('LinkedIn account connected.')
    } else if (connected === 'bluesky') {
      setNotice('Bluesky account connected.')
    } else if (connected) {
      setNotice('Account connected.')
    } else if (saved === 'linkedin') {
      setNotice('LinkedIn account saved as disconnected.')
    } else if (saved === 'bluesky') {
      setNotice('Bluesky account saved as disconnected.')
    } else if (saved) {
      setNotice('Account saved as disconnected.')
    }

    if (callbackError) {
      setOauthError(callbackError)
    }

    if (conflict) {
      setPendingConflictPlatform(saved || connected || 'any')
    }

    setSearchParams({}, { replace: true })
  }, [searchParams, setSearchParams])

  useEffect(() => {
    if (!pendingConflictPlatform || isLoading) {
      return
    }

    const matching = accounts.find((account) => {
      const platformId = getAccountPlatformId(account)
      return (
        account.is_enabled &&
        (pendingConflictPlatform === 'any' || platformId === pendingConflictPlatform)
      )
    })

    if (matching) {
      setConflictAccount(matching)
    }

    setPendingConflictPlatform(null)
  }, [accounts, isLoading, pendingConflictPlatform])

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
      const { authorization_url } = await startAccountConnect(platformId, 'reconnect')
      window.location.assign(authorization_url)
    } catch (caught) {
      setBusyAccountId('')
      setOauthError(caught instanceof Error ? caught.message : 'Could not reconnect account')
    }
  }

  async function handleConnect(accountId: string) {
    setOauthError('')
    setBusyAccountId(accountId)

    try {
      await activateAccount(accountId)
      await reload()
    } catch (caught) {
      const conflicting = getConflictAccount(caught)
      if (conflicting) {
        setConflictAccount(conflicting)
      } else if (caught instanceof ApiError && caught.status === 400) {
        void handleReconnect(accountId)
        return
      } else {
        setOauthError(caught instanceof Error ? caught.message : 'Could not connect account')
      }
    } finally {
      setBusyAccountId('')
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

  async function handleConfirmDelete() {
    if (!accountToDelete) {
      return
    }

    setDeleteError('')
    setIsDeleting(true)

    try {
      await deleteAccount(accountToDelete.id)
      setAccountToDelete(null)
      await reload()
    } catch (caught) {
      setDeleteError(caught instanceof Error ? caught.message : 'Could not delete account')
    } finally {
      setIsDeleting(false)
    }
  }

  return (
    <div className="flex w-full flex-col px-lg py-xl">
      <div className="mb-lg">
        <h1 className="mb-xs font-display-lg text-display-lg text-on-surface">Connected Accounts</h1>
        <p className="max-w-2xl font-body-md text-body-md text-on-surface-variant">
          Manage the social profiles linked to your Social Media Automation Platform workspace.
        </p>
      </div>

      {notice ? <p className="mb-md font-body-md text-body-md text-primary">{notice}</p> : null}
      {oauthError ? <p className="mb-md font-body-md text-body-md text-error">{oauthError}</p> : null}
      {error ? <p className="mb-md font-body-md text-body-md text-error">{error}</p> : null}
      {isLoading ? <p className="mb-md font-body-md text-body-md text-on-surface-variant">Loading accounts...</p> : null}

      {/* Cards Section */}
      {!isLoading && accounts.length === 0 ? (
        <div className="flex min-h-[55vh] w-full flex-col items-center justify-center">
          <div className="w-full max-w-md">
            <AddAccountCard />
          </div>
          <Link
            className="mt-lg font-body-md text-on-surface-variant underline transition-colors hover:text-on-surface"
            to={paths.discover}
          >
            Skip for now
          </Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-md md:grid-cols-2 lg:grid-cols-3">
          {!isLoading
            ? accounts.map((account) => (
                <ConnectedAccountCard
                  key={account.id}
                  account={account}
                  isBusy={busyAccountId === account.id}
                  onConnect={() => {
                    void handleConnect(account.id)
                  }}
                  onReconnect={() => {
                    void handleReconnect(account.id)
                  }}
                  onDisconnect={() => {
                    void handleDisconnect(account.id)
                  }}
                  onDelete={() => {
                    setDeleteError('')
                    setAccountToDelete(account)
                  }}
                />
              ))
            : null}
          {!isLoading ? <AddAccountCard /> : null}
        </div>
      )}

      {conflictAccount ? (
        <AlreadyConnectedModal
          account={conflictAccount}
          onClose={() => {
            setConflictAccount(null)
          }}
        />
      ) : null}

      {accountToDelete ? (
        <DeleteAccountModal
          account={accountToDelete}
          isDeleting={isDeleting}
          error={deleteError}
          onCancel={() => {
            if (!isDeleting) {
              setAccountToDelete(null)
              setDeleteError('')
            }
          }}
          onConfirm={() => {
            void handleConfirmDelete()
          }}
        />
      ) : null}
    </div>
  )
}
