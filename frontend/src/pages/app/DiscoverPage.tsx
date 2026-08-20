import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { DomainCard } from '../../components/discover/DomainCard'
import { SubdomainGroup } from '../../components/discover/SubdomainGroup'
import { MaterialIcon } from '../../components/ui/MaterialIcon'
import { useDiscoverCatalog } from '../../hooks/useDiscoverCatalog'
import { paths } from '../../lib/paths'

export function DiscoverPage() {
  const navigate = useNavigate()
  const { domains, subdomains, isLoading, error } = useDiscoverCatalog()
  const [selectedDomainId, setSelectedDomainId] = useState('')
  const [selectedSubdomainIds, setSelectedSubdomainIds] = useState<string[]>([])

  useEffect(() => {
    if (!domains.length) {
      setSelectedDomainId('')
      return
    }

    const stillExists = domains.some((domain) => domain.id === selectedDomainId)
    if (!stillExists) {
      setSelectedDomainId(domains[0].id)
    }
  }, [domains, selectedDomainId])

  useEffect(() => {
    setSelectedSubdomainIds([])
  }, [selectedDomainId])

  const selectedDomain = useMemo(
    () => domains.find((domain) => domain.id === selectedDomainId) ?? null,
    [domains, selectedDomainId],
  )

  const visibleSubdomains = useMemo(
    () => subdomains.filter((subdomain) => subdomain.domainId === selectedDomainId),
    [subdomains, selectedDomainId],
  )

  function toggleSubdomain(id: string) {
    setSelectedSubdomainIds((current) =>
      current.includes(id) ? current.filter((item) => item !== id) : [...current, id],
    )
  }

  const isSingleDomain = domains.length === 1
  const canContinue = Boolean(selectedDomainId && selectedSubdomainIds.length)

  function continueToSources() {
    if (!canContinue) {
      return
    }

    navigate(paths.sources, {
      state: {
        domainId: selectedDomainId,
        subdomainIds: selectedSubdomainIds,
        domainName: selectedDomain?.name ?? '',
        subdomainNames: visibleSubdomains
          .filter((item) => selectedSubdomainIds.includes(item.id))
          .map((item) => item.name),
        runId: crypto.randomUUID(),
      },
    })
  }

  return (
    <div className="relative flex min-h-full w-full flex-col">
      <div className="pointer-events-none absolute inset-0 z-0 overflow-hidden">
        <div className="absolute right-0 top-0 h-[800px] w-[800px] translate-x-1/3 -translate-y-1/3 rounded-full bg-primary/5 opacity-50 blur-[120px] mix-blend-multiply" />
        <div className="absolute bottom-0 left-0 h-[600px] w-[600px] -translate-x-1/4 translate-y-1/4 rounded-full bg-[#5952af]/5 opacity-40 blur-[100px] mix-blend-multiply" />
      </div>

      <div className="relative z-10 mx-auto flex w-full max-w-7xl flex-1 flex-col px-lg py-xl">
        <div className="mb-xl flex flex-col">
          <h1 className="mb-xs font-display-lg text-display-lg tracking-tighter text-on-surface">
            Content Discover
          </h1>
          <p className="mb-lg max-w-2xl font-body-lg text-body-lg text-on-surface-variant">
            Configure your knowledge graph context for the AI engine.
          </p>
        </div>

        <div className="flex flex-1 flex-col gap-lg">
          <div className="flex flex-col gap-sm">
            <div className="mb-1 flex items-center gap-2">
              <span className="font-label-md text-label-md uppercase tracking-widest text-on-surface-variant">
                {isSingleDomain ? 'Domain' : 'Domains'}
              </span>
              {isSingleDomain ? (
                <div className="flex items-center gap-1 rounded-full bg-surface-container px-2 py-0.5">
                  <MaterialIcon name="lock" className="text-[12px] text-on-surface-variant" />
                  <span className="font-label-sm text-label-sm text-on-surface-variant">
                    Fixed for this workspace
                  </span>
                </div>
              ) : null}
            </div>

            {isLoading ? (
              <p className="font-body-md text-body-md text-on-surface-variant">Loading domains...</p>
            ) : null}

            {error ? <p className="font-body-md text-body-md text-error">{error}</p> : null}

            {!isLoading && !error && domains.length === 0 ? (
              <p className="font-body-md text-body-md text-on-surface-variant">
                No domains found in the database.
              </p>
            ) : null}

            <div className="flex flex-col gap-sm">
              {domains.map((domain) => (
                <DomainCard
                  key={domain.id}
                  domain={domain}
                  selected={domain.id === selectedDomainId}
                  locked={isSingleDomain}
                  onSelect={() => setSelectedDomainId(domain.id)}
                />
              ))}
            </div>
          </div>

          <div className="flex flex-col gap-lg rounded-[14px] border border-surface-variant bg-surface-container-lowest p-lg shadow-sm">
            <div className="flex items-center justify-between gap-md">
              <div className="flex items-center gap-2">
                <MaterialIcon name="filter_list" className="text-[20px] text-primary" />
                <h3 className="font-headline-sm text-headline-sm text-on-surface">Subdomains</h3>
              </div>
              <p className="font-body-md text-body-md text-on-surface-variant">
                {selectedDomain ? (
                  <>
                    Refine your scope within{' '}
                    <strong className="font-semibold text-primary">{selectedDomain.name}</strong>.
                  </>
                ) : (
                  'Select a domain to see its subdomains.'
                )}
              </p>
            </div>

            {isLoading ? (
              <p className="font-body-md text-body-md text-on-surface-variant">Loading subdomains...</p>
            ) : selectedDomain ? (
              <SubdomainGroup
                items={visibleSubdomains.map((item) => ({ id: item.id, label: item.name }))}
                selectedIds={selectedSubdomainIds}
                onToggle={toggleSubdomain}
              />
            ) : (
              <p className="font-body-md text-body-md text-on-surface-variant">
                No subdomains to show yet.
              </p>
            )}
          </div>
        </div>

        <div className="mt-xl flex items-center justify-end border-t border-surface-variant py-md">
          <button
            type="button"
            disabled={!canContinue}
            onClick={continueToSources}
            className="group relative flex h-9 items-center gap-2 overflow-hidden rounded bg-primary px-6 font-label-md text-label-md text-on-primary shadow-sm transition-all hover:bg-primary/90 hover:shadow-md disabled:pointer-events-none disabled:opacity-50"
          >
            <span className="relative z-10">Continue to Sources</span>
            <MaterialIcon
              name="arrow_forward"
              className="relative z-10 text-[18px] transition-transform group-hover:translate-x-1"
            />
            <div className="absolute inset-0 z-0 -translate-x-full bg-white/20 transition-transform duration-300 ease-out group-hover:translate-x-0" />
          </button>
        </div>
      </div>
    </div>
  )
}
