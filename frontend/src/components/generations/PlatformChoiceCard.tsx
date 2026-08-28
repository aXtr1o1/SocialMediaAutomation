import type { ReactNode } from 'react'
import { cn } from '../../lib/cn'

type PlatformChoiceCardProps = {
  label: string
  selected?: boolean
  disabled?: boolean
  onSelect?: () => void
  children: ReactNode
}

export function PlatformChoiceCard({
  label,
  selected = false,
  disabled = false,
  onSelect,
  children,
}: PlatformChoiceCardProps) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onSelect}
      className={cn(
        'group flex flex-col items-center justify-center rounded-lg border p-md transition-all focus:outline-none focus:ring-2 focus:ring-primary/20',
        disabled ? 'cursor-not-allowed' : 'cursor-pointer',
        selected
          ? 'border-primary bg-primary/5'
          : 'border-surface-variant bg-surface-container-lowest',
        !disabled && !selected && 'hover:bg-surface-container-low',
      )}
    >
      {children}
      <span
        className={cn(
          'font-label-md text-label-md transition-colors',
          selected ? 'text-primary' : 'text-on-surface group-hover:text-primary',
        )}
      >
        {label}
      </span>
    </button>
  )
}
