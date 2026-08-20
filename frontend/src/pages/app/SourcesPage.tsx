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
  const scope = (selection?.subdomainNames || []).filter(Boolean).join(', ')

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
      <div className="flex flex-col gap-xs">
        <h1 className="font-display-lg text-display-lg text-on-surface">Sources</h1>
        <p className="font-body-lg text-body-lg text-on-surface-variant">
          Related content found for your selected {domainName || 'chosen'} subdomains.
        </p>
      </div>

      <div className="flex items-center justify-end border-b border-surface-variant py-sm">
        <div className="font-label-md text-label-md text-on-surface-variant">
          {isRunning ? 'Finding sources...' : `Showing ${articles.length} results`}
        </div>
      </div>

      {error ? <p className="font-body-md text-body-md text-error">{error}</p> : null}

      {isRunning ? <SourcesLoadingCard scope={scope} progress={progress} /> : null}

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
