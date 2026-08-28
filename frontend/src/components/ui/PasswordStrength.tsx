import { usePasswordStrength } from '../../hooks/usePasswordStrength'
import { cn } from '../../lib/cn'

type PasswordStrengthProps = {
  password: string
}

const bars = [0, 1, 2, 3] as const

export function PasswordStrength({ password }: PasswordStrengthProps) {
  const { level, label, textClass, barClass } = usePasswordStrength(password)

  return (
    <div className="mt-1 flex flex-col gap-1">
      <div className="flex h-1 w-full gap-1 overflow-hidden rounded-full">
        {bars.map((index) => (
          <div
            key={index}
            className={cn(
              'flex-1 transition-colors duration-300',
              level > index ? barClass : 'bg-surface-container-highest',
            )}
          />
        ))}
      </div>
      <span className={cn('font-label-sm text-label-sm font-semibold', textClass)}>{label}</span>
    </div>
  )
}
