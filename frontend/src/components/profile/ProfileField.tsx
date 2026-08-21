import { cn } from '../../lib/cn'

type ProfileFieldProps = {
  id: string
  label: string
  value: string
  onChange?: (value: string) => void
  readOnly?: boolean
  autoComplete?: string
  required?: boolean
}

export function ProfileField({
  id,
  label,
  value,
  onChange,
  readOnly = false,
  autoComplete,
  required = false,
}: ProfileFieldProps) {
  return (
    <div className="flex flex-col gap-2">
      <label
        htmlFor={id}
        className="font-label-sm text-label-sm uppercase tracking-widest text-on-surface-variant"
      >
        {label}
      </label>
      <input
        id={id}
        value={value}
        readOnly={readOnly}
        required={required}
        autoComplete={autoComplete}
        onChange={onChange ? (event) => onChange(event.target.value) : undefined}
        className={cn(
          'h-12 rounded-lg border border-surface-variant px-4 font-body-md text-body-md text-on-surface outline-none transition-shadow focus:border-transparent focus:ring-2 focus:ring-primary',
          readOnly && 'cursor-not-allowed bg-surface-container text-on-surface-variant',
          !readOnly && 'bg-surface-container-lowest',
        )}
      />
    </div>
  )
}
