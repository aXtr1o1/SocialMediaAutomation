import { MaterialIcon } from '../ui/MaterialIcon'

export type SourcesLoadProgress = {
  stage: string
  message: string
  crawled: number
  kpi_passed: number
  match_passed: number
  sources_done: number
  sources_total: number
}

const STEPS = [
  { id: 'crawling', label: 'Crawling mapped sites' },
  { id: 'kpi', label: 'Checking article quality' },
  { id: 'matching', label: 'Matching to your subdomains' },
] as const

function stepState(stage: string, id: string) {
  const order = ['crawling', 'kpi', 'matching', 'completed']
  const current = order.indexOf(stage)
  const index = order.indexOf(id)
  if (stage === 'completed' || (current >= 0 && index >= 0 && index < current)) {
    return 'done'
  }
  if (id === stage || (stage === 'completed' && id === 'matching')) {
    return 'active'
  }
  return 'pending'
}

type SourcesLoadingCardProps = {
  scope: string
  progress: SourcesLoadProgress | null
}

export function SourcesLoadingCard({ scope, progress }: SourcesLoadingCardProps) {
  const stage = progress?.stage || 'crawling'
  const message = progress?.message || 'Starting crawl, KPI checks, and matching...'

  return (
    <div className="flex flex-col gap-lg rounded-[14px] border border-surface-variant bg-surface-container-lowest p-lg shadow-sm">
      <div className="flex items-start gap-md">
        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
          <MaterialIcon name="progress_activity" className="animate-spin text-[28px]" />
        </div>
        <div className="flex min-w-0 flex-col gap-xs">
          <h2 className="font-headline-sm text-headline-sm text-on-surface">
            Finding sources{scope ? ` for ${scope}` : ''}
          </h2>
          <p className="font-body-md text-body-md text-on-surface-variant">{message}</p>
          <p className="font-body-md text-body-md text-on-surface-variant">
            This can take a few minutes. Blocked sites are skipped.
          </p>
        </div>
      </div>

      <ol className="flex flex-col gap-sm">
        {STEPS.map((step) => {
          const state = stepState(stage, step.id)
          return (
            <li key={step.id} className="flex items-center gap-sm font-label-md text-label-md">
              {state === 'done' ? (
                <MaterialIcon name="check_circle" className="text-[20px] text-primary" filled />
              ) : state === 'active' ? (
                <MaterialIcon name="radio_button_checked" className="text-[20px] text-primary" />
              ) : (
                <MaterialIcon name="radio_button_unchecked" className="text-[20px] text-on-surface-variant" />
              )}
              <span className={state === 'pending' ? 'text-on-surface-variant' : 'text-on-surface'}>
                {step.label}
              </span>
            </li>
          )
        })}
      </ol>

      {progress && (progress.sources_total > 0 || progress.crawled > 0) ? (
        <p className="font-label-md text-label-md text-on-surface-variant">
          Sites {progress.sources_done}/{progress.sources_total || 0}
          {' · '}Crawled {progress.crawled}
          {' · '}KPI passed {progress.kpi_passed}
          {' · '}Matched {progress.match_passed}
        </p>
      ) : null}
    </div>
  )
}
