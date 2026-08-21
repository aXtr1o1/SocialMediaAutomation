import { useEffect, useState } from 'react'
import { MaterialIcon } from '../ui/MaterialIcon'

export type SourcesLoadProgress = {
  stage: string
  message: string
  activity?: string
  current_site?: string
  activity_log?: string[]
  crawled: number
  kpi_passed: number
  match_passed: number
  sources_done: number
  sources_total: number
  checked?: number
  pages_seen?: number
}

function uiStage(stage: string) {
  if (stage === 'matching' || stage === 'completed') {
    return 'matching'
  }
  return 'finding'
}

function loadPercent(progress: SourcesLoadProgress | null) {
  if (!progress) {
    return 3
  }
  if (progress.stage === 'completed') {
    return 100
  }

  const sites = progress.sources_total
    ? Math.min(1, progress.sources_done / Math.max(1, progress.sources_total))
    : 0

  if (uiStage(progress.stage) === 'matching') {
    const total = progress.kpi_passed || 0
    const ratio = total > 0 ? Math.min(1, progress.match_passed / total) : 0
    return Math.min(99, 70 + Math.round(ratio * 29))
  }

  if (progress.stage === 'kpi') {
    const total = progress.crawled || 0
    const reviewed = total > 0 ? Math.min(1, (progress.checked ?? 0) / total) : 0
    return Math.min(70, 52 + Math.round(reviewed * 18))
  }

  const pageBoost = progress.pages_seen ? Math.min(8, Math.floor(progress.pages_seen / 5)) : 0
  const floor = progress.current_site ? 10 : 4
  return Math.min(52, Math.max(floor, Math.round(sites * 44) + pageBoost))
}

function softCap(progress: SourcesLoadProgress | null, base: number) {
  if (!progress || progress.stage === 'completed') {
    return base
  }
  if (uiStage(progress.stage) === 'matching') {
    return Math.min(99, base + 3)
  }
  if (progress.stage === 'kpi') {
    return Math.min(69, base + 4)
  }
  return Math.min(51, base + 5)
}

function MetricCard({
  label,
  value,
  hint,
}: {
  label: string
  value: string
  hint: string
}) {
  return (
    <div className="flex h-[92px] min-w-0 flex-col justify-between rounded-xl bg-surface-container-low px-md py-md">
      <p className="font-label-sm text-label-sm text-on-surface-variant">{label}</p>
      <p className="truncate font-headline-sm text-headline-sm text-on-surface tabular-nums">{value}</p>
      <p className="truncate font-label-sm text-label-sm text-on-surface-variant">{hint}</p>
    </div>
  )
}

type SourcesLoadingCardProps = {
  scope: string
  progress: SourcesLoadProgress | null
}

export function SourcesLoadingCard({ scope, progress }: SourcesLoadingCardProps) {
  const stage = progress?.stage || 'crawling'
  const current = uiStage(stage)
  const basePercent = loadPercent(progress)
  const [displayPercent, setDisplayPercent] = useState(basePercent)

  const headline =
    progress?.activity ||
    progress?.message ||
    (progress?.current_site ? `Scanning ${progress.current_site}…` : 'Preparing your source search…')

  const activityLog = (progress?.activity_log || []).filter(Boolean).slice(0, 5)
  const sitesTotal = progress?.sources_total || 0
  const sitesDone = progress?.sources_done || 0
  const found = progress?.crawled || 0
  const matched = progress?.match_passed || 0
  const currentSite = progress?.current_site || ''

  useEffect(() => {
    setDisplayPercent((prev) => Math.max(prev, basePercent))
  }, [basePercent])

  useEffect(() => {
    const cap = softCap(progress, basePercent)
    const timer = window.setInterval(() => {
      setDisplayPercent((prev) => {
        if (progress?.stage === 'completed') {
          return 100
        }
        if (prev >= cap) {
          return prev
        }
        return Math.min(cap, Math.round((prev + 0.4) * 10) / 10)
      })
    }, 400)
    return () => window.clearInterval(timer)
  }, [basePercent, progress, progress?.stage])

  const shownPercent = Math.min(100, Math.round(displayPercent))
  const findingDone = current === 'matching' || stage === 'completed'
  const matchingActive = current === 'matching' && stage !== 'completed'

  return (
    <section className="overflow-hidden rounded-2xl border border-surface-variant bg-surface-container-lowest shadow-sm">
      <div className="border-b border-surface-variant bg-gradient-to-br from-primary/10 via-surface-container-lowest to-surface-container-low px-lg py-lg">
        <div className="flex min-w-0 items-start gap-md">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-primary text-on-primary shadow-sm">
            <MaterialIcon name="travel_explore" className="animate-pulse text-[24px]" />
          </div>
          <div className="min-w-0">
            <p className="font-label-sm text-label-sm text-primary">Live source search</p>
            <h2 className="mt-1 font-headline-sm text-headline-sm text-on-surface">
              {scope ? `Looking for ${scope}` : 'Looking for matching articles'}
            </h2>
            <p
              key={headline}
              className="mt-2 line-clamp-2 font-body-md text-body-md text-on-surface transition-opacity duration-300"
            >
              {headline}
            </p>
          </div>
        </div>

        <div className="mt-lg">
          <div className="mb-xs flex items-center justify-between gap-sm">
            <span className="font-label-md text-label-md text-on-surface">
              {current === 'matching' ? 'Matching articles to your topics' : 'Finding articles from mapped sites'}
            </span>
            <span className="font-label-md text-label-md text-primary tabular-nums">{shownPercent}%</span>
          </div>
          <div className="h-2.5 overflow-hidden rounded-full bg-surface-container-high">
            <div
              className="h-full rounded-full bg-primary transition-[width] duration-500 ease-out"
              style={{ width: `${shownPercent}%` }}
            >
              <div className="h-full w-full animate-smap-shimmer bg-gradient-to-r from-primary via-white/30 to-primary bg-[length:200%_100%]" />
            </div>
          </div>
        </div>

        <div className="mt-md grid grid-cols-2 gap-sm">
          <div
            className={`rounded-xl px-md py-sm ${
              !findingDone ? 'bg-primary text-on-primary' : 'bg-surface-container-lowest text-on-surface'
            }`}
          >
            <p className="font-label-sm text-label-sm opacity-80">Step 1</p>
            <p className="font-label-md text-label-md">{findingDone ? 'Articles found' : 'Finding articles'}</p>
          </div>
          <div
            className={`rounded-xl px-md py-sm ${
              matchingActive
                ? 'bg-primary text-on-primary'
                : findingDone
                  ? 'bg-surface-container-lowest text-on-surface'
                  : 'bg-surface-container-high/70 text-on-surface-variant'
            }`}
          >
            <p className="font-label-sm text-label-sm opacity-80">Step 2</p>
            <p className="font-label-md text-label-md">
              {stage === 'completed' ? 'Matching complete' : 'Matching to topics'}
            </p>
          </div>
        </div>
      </div>

      <div className="flex flex-col gap-md px-lg py-lg">
        <div className="grid grid-cols-3 gap-sm">
          <MetricCard
            label="Sites"
            value={sitesTotal > 0 ? `${sitesDone}/${sitesTotal}` : '—'}
            hint={sitesTotal > 0 ? (sitesDone >= sitesTotal ? 'All checked' : 'In progress') : 'Starting soon'}
          />
          <MetricCard label="Found" value={`${found}`} hint="Articles" />
          <MetricCard
            label="Matched"
            value={`${matched}`}
            hint={current === 'matching' ? 'Updating' : 'Next step'}
          />
        </div>

        <div className="min-h-[180px] rounded-xl border border-surface-variant bg-surface px-md py-md">
          <div className="mb-sm flex items-center justify-between gap-sm">
            <div className="flex items-center gap-xs">
              <span className="relative flex h-2.5 w-2.5">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary/40" />
                <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-primary" />
              </span>
              <span className="font-label-md text-label-md text-on-surface">Crawling progress</span>
            </div>
            {currentSite ? (
              <span className="max-w-[50%] truncate rounded-md bg-primary/10 px-2 py-0.5 font-label-sm text-label-sm text-primary">
                {currentSite}
              </span>
            ) : null}
          </div>
          <ul className="flex min-h-[108px] flex-col gap-sm">
            {(activityLog.length ? activityLog : [headline]).map((line, index) => (
              <li key={`${index}-${line}`} className="flex items-start gap-sm">
                <span
                  className={`mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full ${
                    index === 0 ? 'bg-primary' : 'bg-outline-variant'
                  }`}
                />
                <span
                  className={`min-w-0 flex-1 truncate font-body-md text-body-md leading-snug ${
                    index === 0 ? 'text-on-surface' : 'text-on-surface-variant'
                  }`}
                >
                  {line}
                </span>
              </li>
            ))}
          </ul>
          <p className="mt-md font-label-sm text-label-sm text-on-surface-variant">
            This usually takes a few minutes. Blocked sites are skipped automatically.
          </p>
        </div>
      </div>
    </section>
  )
}
