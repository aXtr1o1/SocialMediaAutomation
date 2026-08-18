import { cn } from '../../lib/cn'
import { MaterialIcon } from '../ui/MaterialIcon'

type SubdomainChipProps = {
  label: string
  selected?: boolean
  onClick?: () => void
}

export function SubdomainChip({ label, selected = false, onClick }: SubdomainChipProps) {
  return (
    <button
      type="button"
      aria-pressed={selected}
      onClick={onClick}
      className={cn(
        'flex items-center gap-1 rounded-full px-4 py-2 font-label-md text-label-md transition-colors',
        selected
          ? 'bg-primary text-white shadow-sm hover:bg-primary/90'
          : 'border border-surface-variant bg-surface-container-lowest text-on-surface hover:bg-surface-container-low',
      )}
    >
      {label}
      <MaterialIcon name={selected ? 'close' : 'add'} className={cn('text-[14px]', !selected && 'opacity-50')} />
    </button>
  )
}
