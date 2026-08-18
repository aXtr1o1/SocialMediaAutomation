import { getDomainIcon, type DomainRow } from '../../lib/discover'
import { cn } from '../../lib/cn'
import { MaterialIcon } from '../ui/MaterialIcon'

type DomainCardProps = {
  domain: DomainRow
  selected?: boolean
  locked?: boolean
  onSelect?: () => void
}

export function DomainCard({ domain, selected = false, locked = false, onSelect }: DomainCardProps) {
  return (
    <button
      type="button"
      onClick={onSelect}
      disabled={locked}
      className={cn(
        'flex w-full items-center justify-between rounded-[14px] border-[1.5px] bg-surface-container-lowest p-6 text-left shadow-sm transition-colors',
        selected ? 'border-primary' : 'border-surface-variant hover:border-primary/50',
        locked && 'cursor-default',
      )}
    >
      <div className="flex items-center gap-md">
        <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
            <MaterialIcon name={getDomainIcon(domain.name)} className="text-[24px] text-primary" />
        </div>
        <div>
          <div className="mb-1 flex items-center gap-2">
            <h3 className="font-headline-sm text-headline-sm text-on-surface">{domain.name || 'Untitled domain'}</h3>
            {selected ? (
              <span className="rounded-md bg-primary/10 px-2 py-0.5 font-label-sm text-label-sm text-primary">
                Primary domain
              </span>
            ) : null}
          </div>
          {domain.description ? (
            <p className="font-body-md text-body-md text-on-surface-variant">{domain.description}</p>
          ) : null}
        </div>
      </div>
      {selected ? (
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary">
          <MaterialIcon name="check" filled className="text-[18px] text-white" />
        </div>
      ) : (
        <div className="h-8 w-8 shrink-0 rounded-full border border-surface-variant" />
      )}
    </button>
  )
}
