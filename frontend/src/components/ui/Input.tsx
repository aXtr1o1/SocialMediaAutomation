import type { InputHTMLAttributes, ReactNode } from 'react'
import { cn } from '../../lib/cn'
import { MaterialIcon } from './MaterialIcon'

type InputProps = InputHTMLAttributes<HTMLInputElement> & {
  id: string
  label: string
  error?: string
  leftIcon?: string
  rightSlot?: ReactNode
  labelExtra?: ReactNode
  showErrorIcon?: boolean
}

export function Input({
  id,
  label,
  error,
  leftIcon,
  rightSlot,
  labelExtra,
  showErrorIcon = false,
  className,
  ...props
}: InputProps) {
  const hasError = Boolean(error)

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <label
          className={cn('text-[14px] font-medium text-on-surface', error && 'flex w-full justify-between')}
          htmlFor={id}
        >
          {label}
          {error ? <span className="text-[12px] font-semibold text-error">{error}</span> : null}
        </label>
        {labelExtra}
      </div>

      <div className="relative">
        {leftIcon ? (
          <MaterialIcon
            name={leftIcon}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-[20px] text-on-surface-variant"
          />
        ) : null}

        <input
          id={id}
          className={cn(
            'h-[48px] w-full rounded-lg border border-outline-variant bg-surface-container-lowest px-4 text-[14px] text-on-surface placeholder:text-on-surface-variant/70 transition-shadow focus:border-transparent focus:outline-none focus:ring-2 focus:ring-primary',
            leftIcon && 'pl-10',
            (Boolean(rightSlot) || (showErrorIcon && hasError)) && 'pr-10',
            hasError && 'border-error text-error focus:ring-error/20',
            className,
          )}
          aria-invalid={hasError}
          {...props}
        />

        {showErrorIcon && hasError ? (
          <MaterialIcon
            name="error"
            className="absolute right-3 top-1/2 -translate-y-1/2 text-[20px] text-error"
          />
        ) : null}

        {rightSlot}
      </div>
    </div>
  )
}
