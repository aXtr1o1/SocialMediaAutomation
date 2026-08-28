import { useEffect } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { SourceArticleCard } from '../../components/sources/SourceArticleCard'
import { SourcesLoadingCard } from '../../components/sources/SourcesLoadingCard'
import { useSourcesWorkflow } from '../../hooks/useSourcesWorkflow'
import { paths } from '../../lib/paths'
import {
  getRememberedSourcesSelection,
  isSourcesSelection,
  rememberSourcesSelection,
} from '../../lib/sources'

export function SourcesPage() {
  const location = useLocation()
  const locationSelection = isSourcesSelection(location.state) ? location.state : null
  const selection = locationSelection ?? getRememberedSourcesSelection()

  useEffect(() => {
    if (locationSelection) {
      rememberSourcesSelection(locationSelection)
    }
  }, [locationSelection])

  const { articles, domainName, isRunning, progress, error } = useSourcesWorkflow(selection)
  const selectedDomain = domainName || selection?.domainName || ''
  const selectedSubdomains = (selection?.subdomainNames || []).filter(Boolean)

  if (!selection) {
    return (
      <div className="mx-auto flex w-full max-w-5xl flex-col gap-lg p-lg lg:p-xl">
        <h1 className="font-display-lg text-display-lg text-on-surface">Sources</h1>
        <p className="font-body-lg text-body-lg text-on-surface-variant">
          Select a domain and subdomains in Discover first, then continue here.
        </p>
        <Link className="font-body-md text-primary underline" to={paths.discover}>
          Back to Discover
        </Link>
      </div>
    )
  }

  return (
    <div className="mx-auto flex min-h-[calc(100vh-64px)] w-full max-w-5xl flex-col gap-lg p-lg lg:p-xl">
      <div className="flex flex-col gap-md">
        <div className="flex flex-col gap-xs">
          <h1 className="font-display-lg text-display-lg text-on-surface">Sources</h1>
          <p className="font-body-lg text-body-lg text-on-surface-variant">
            Related content for your selected domain and subdomains.
          </p>
        </div>

        <div className="rounded-xl border border-surface-variant bg-surface-container-lowest px-md py-md">
          <p className="font-label-sm text-label-sm uppercase tracking-widest text-on-surface-variant">
            Selected topics
          </p>
          <div className="mt-sm flex flex-col gap-sm">
            <div>
              <p className="font-label-md text-label-md text-on-surface-variant">Domain</p>
              <p className="mt-0.5 font-headline-sm text-headline-sm text-on-surface">
                {selectedDomain || '—'}
              </p>
            </div>
            <div>
              <p className="font-label-md text-label-md text-on-surface-variant">Subdomains</p>
              {selectedSubdomains.length ? (
                <ul className="mt-2 flex flex-wrap gap-2">
                  {selectedSubdomains.map((name) => (
                    <li
                      key={name}
                      className="rounded-md border border-surface-variant bg-surface px-2.5 py-1 font-label-md text-label-md text-on-surface"
                    >
                      {name}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="mt-0.5 font-body-md text-body-md text-on-surface-variant">—</p>
              )}
            </div>
          </div>
        </div>
      </div>

      <div className="flex items-center justify-end border-b border-surface-variant py-sm">
        <div className="font-label-md text-label-md text-on-surface-variant">
          {isRunning ? 'Finding sources...' : `Showing ${articles.length} results`}
        </div>
      </div>

      {error ? <p className="font-body-md text-body-md text-error">{error}</p> : null}

      {isRunning ? (
        <SourcesLoadingCard
          domainName={selectedDomain}
          subdomainNames={selectedSubdomains}
          progress={progress}
        />
      ) : null}

      {!isRunning && !error && articles.length === 0 ? (
        <p className="font-body-md text-body-md text-on-surface-variant">
          No matching source material was found for this selection.
        </p>
      ) : null}

      <div className="flex flex-col gap-md">
        {articles.map((article) => (
          <SourceArticleCard key={article.id} article={article} sourcesSelection={selection} />
        ))}
      </div>
    </div>
  )
}
