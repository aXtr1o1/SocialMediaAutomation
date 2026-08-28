import { useEffect, useState } from 'react'
import { fetchDiscoverCatalog, type DomainRow, type SubdomainRow } from '../lib/discover'

export function useDiscoverCatalog() {
  const [domains, setDomains] = useState<DomainRow[]>([])
  const [subdomains, setSubdomains] = useState<SubdomainRow[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let isActive = true

    async function load() {
      setIsLoading(true)
      setError('')

      try {
        const catalog = await fetchDiscoverCatalog()

        if (!isActive) {
          return
        }

        setDomains(catalog.domains)
        setSubdomains(catalog.subdomains)
      } catch (caught) {
        if (!isActive) {
          return
        }

        setError(caught instanceof Error ? caught.message : 'Could not load domains')
      } finally {
        if (isActive) {
          setIsLoading(false)
        }
      }
    }

    void load()

    return () => {
      isActive = false
    }
  }, [])

  return { domains, subdomains, isLoading, error }
}
