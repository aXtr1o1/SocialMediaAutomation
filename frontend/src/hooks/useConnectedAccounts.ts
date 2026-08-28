import { useCallback, useEffect, useRef, useState } from 'react'
import { listConnectedAccounts, type ConnectedAccount } from '../lib/accounts'

export function useConnectedAccounts() {
  const [accounts, setAccounts] = useState<ConnectedAccount[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')
  const requestIdRef = useRef(0)

  const reload = useCallback(async () => {
    const requestId = requestIdRef.current + 1
    requestIdRef.current = requestId

    setIsLoading(true)
    setError('')

    try {
      const nextAccounts = await listConnectedAccounts()

      if (requestId !== requestIdRef.current) {
        return
      }

      setAccounts(nextAccounts)
    } catch (caught) {
      if (requestId !== requestIdRef.current) {
        return
      }

      setError(caught instanceof Error ? caught.message : 'Could not load accounts')
    } finally {
      if (requestId === requestIdRef.current) {
        setIsLoading(false)
      }
    }
  }, [])

  useEffect(() => {
    void reload()
  }, [reload])

  return { accounts, isLoading, error, reload }
}
