import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  formatPublishedAt,
  splitContentParagraphs,
  type SourceArticle,
  type SourcesSelection,
} from '../../lib/sources'
import { paths } from '../../lib/paths'
import { MaterialIcon } from '../ui/MaterialIcon'

type SourceArticleCardProps = {
  article: SourceArticle
  sourcesSelection?: SourcesSelection
}

export function SourceArticleCard({ article, sourcesSelection }: SourceArticleCardProps) {
  const navigate = useNavigate()
  const [expanded, setExpanded] = useState(false)
  const publishedAt = formatPublishedAt(article.published_at)
  const paragraphs = splitContentParagraphs(article.content)
  const sourceUrl = article.source_url?.trim() || ''
  const sourceLabel = formatSourceLinkLabel(sourceUrl)

  return (
    <div className="flex flex-col overflow-hidden rounded-[14px] border border-surface-variant bg-surface-container-lowest shadow-sm transition-shadow hover:shadow-md">
      <div className="flex flex-col gap-md p-lg">
        <div className="flex items-start justify-between gap-md">
          <div className="flex min-w-0 flex-1 flex-col gap-sm">
            <div className="flex items-center gap-xs">
              <MaterialIcon name="article" className="text-[16px] text-on-surface-variant" />
              <span className="font-label-sm text-label-sm uppercase tracking-wider text-on-surface-variant">
                Source Material
              </span>
            </div>
            {sourceUrl ? (
              <h2 className="text-headline-sm text-[20px] font-semibold leading-[28px]">
                <a
                  href={sourceUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-on-surface transition-colors hover:text-primary hover:underline"
                >
                  {article.title}
                </a>
              </h2>
            ) : (
              <h2 className="text-headline-sm text-[20px] font-semibold leading-[28px] text-on-surface">
                {article.title}
              </h2>
            )}
            <div className="flex flex-wrap items-center gap-sm">
              {publishedAt ? (
                <div className="flex items-center gap-xs rounded-full bg-surface-container px-sm py-base font-label-md text-label-md text-on-surface-variant">
                  <MaterialIcon name="calendar_today" className="text-[16px]" />
                  {publishedAt}
                </div>
              ) : null}
              {article.author ? (
                <div className="flex items-center gap-xs rounded-full bg-surface-container px-sm py-base font-label-md text-label-md text-on-surface-variant">
                  <MaterialIcon name="person" className="text-[16px]" />
                  By {article.author}
                </div>
              ) : null}
              {article.subdomain_name ? (
                <div className="rounded-full border border-primary/25 bg-primary/10 px-sm py-base font-label-md text-label-md text-primary">
                  {article.subdomain_name}
                </div>
              ) : null}
            </div>
            {sourceUrl ? (
              <a
                href={sourceUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex max-w-full items-center gap-xs font-body-md text-body-md text-primary transition-colors hover:underline"
              >
                <MaterialIcon name="link" className="shrink-0 text-[16px]" />
                <span className="min-w-0 truncate">{sourceLabel}</span>
                <MaterialIcon name="open_in_new" className="shrink-0 text-[14px]" />
              </a>
            ) : null}
          </div>
          <button
            type="button"
            className="flex shrink-0 items-center gap-xs text-on-surface-variant transition-colors hover:text-on-surface"
            onClick={() => setExpanded((current) => !current)}
          >
            <span className="whitespace-nowrap font-label-md text-label-md">
              {expanded ? 'Hide content' : 'Show full content'}
            </span>
            <MaterialIcon
              name="expand_more"
              className={`transform transition-transform duration-200 ${expanded ? 'rotate-180' : ''}`}
            />
          </button>
        </div>

        {expanded ? (
          <div className="flex flex-col gap-md border-t border-surface-variant pt-md font-body-lg text-body-lg leading-relaxed text-on-surface-variant">
            {paragraphs.length ? (
              paragraphs.map((paragraph, index) => <p key={`${article.id}-${index}`}>{paragraph}</p>)
            ) : (
              <p>No article content is available.</p>
            )}
          </div>
        ) : null}
      </div>

      <div className="flex items-center justify-end border-t border-surface-variant px-lg py-md">
        <button
          type="button"
          className="inline-flex h-10 shrink-0 items-center gap-xs whitespace-nowrap rounded-lg bg-primary px-md font-label-md text-label-md text-on-primary shadow-sm transition-colors hover:bg-primary/90"
          onClick={() =>
            navigate(paths.generationsCompose, {
              state: { article, sourcesSelection },
            })
          }
        >
          <MaterialIcon name="auto_awesome" className="text-[18px]" />
          Generate post
        </button>
      </div>
    </div>
  )
}

function formatSourceLinkLabel(url: string) {
  if (!url) {
    return ''
  }
  try {
    const parsed = new URL(url)
    const path = parsed.pathname === '/' ? '' : parsed.pathname
    return `${parsed.hostname}${path}`
  } catch {
    return url
  }
}
