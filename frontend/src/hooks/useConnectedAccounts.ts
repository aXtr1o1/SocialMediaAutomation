import { useCallback, useEffect, useState } from 'react'
import { listConnectedAccounts, type ConnectedAccount } from '../lib/accounts'

export function useConnectedAccounts() {
  const [accounts, setAccounts] = useState<ConnectedAccount[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')

  const reload = useCallback(async () => {
    setIsLoading(true)
    setError('')

    try {
      setAccounts(await listConnectedAccounts())
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not load accounts')
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    void reload()
  }, [reload])

  return { accounts, isLoading, error, reload }
}
