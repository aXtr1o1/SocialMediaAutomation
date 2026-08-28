import type { InputHTMLAttributes, ReactNode } from 'react'
import { cn } from '../../lib/cn'

type ProfileFieldProps = {
  id: string
  label: string
  value: string
  onChange?: (value: string) => void
  readOnly?: boolean
  autoComplete?: string
  required?: boolean
  type?: InputHTMLAttributes<HTMLInputElement>['type']
  className?: string
  rightSlot?: ReactNode
}

export function ProfileField({
  id,
  label,
  value,
  onChange,
  readOnly = false,
  autoComplete,
  required = false,
  type = 'text',
  className,
  rightSlot,
}: ProfileFieldProps) {
  return (
    <div className="flex flex-col gap-2">
      <label
        htmlFor={id}
        className="font-label-sm text-label-sm uppercase tracking-widest text-on-surface-variant"
      >
        {label}
      </label>
      <div className="relative">
        <input
          id={id}
          type={type}
          value={value}
          readOnly={readOnly}
          required={required}
          autoComplete={autoComplete}
          onChange={onChange ? (event) => onChange(event.target.value) : undefined}
          className={cn(
            'h-12 w-full rounded-lg border border-surface-variant px-4 font-body-md text-body-md text-on-surface outline-none transition-shadow focus:border-transparent focus:ring-2 focus:ring-primary',
            readOnly && 'cursor-not-allowed bg-surface-container text-on-surface-variant',
            !readOnly && 'bg-surface-container-lowest',
            rightSlot ? 'pr-12' : undefined,
            className,
          )}
        />
        {rightSlot}
      </div>
    </div>
  )
}
