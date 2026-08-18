import { getPasswordStrength, type PasswordStrength } from '../lib/validation'

const strengthStyles: Record<
  PasswordStrength,
  { label: string; textClass: string; barClass: string }
> = {
  0: {
    label: 'Password strength',
    textClass: 'text-on-surface-variant',
    barClass: 'bg-surface-container-highest',
  },
  1: {
    label: 'Weak',
    textClass: 'text-error',
    barClass: 'bg-error',
  },
  2: {
    label: 'Fair',
    textClass: 'text-tertiary',
    barClass: 'bg-tertiary',
  },
  3: {
    label: 'Good',
    textClass: 'text-primary',
    barClass: 'bg-primary',
  },
  4: {
    label: 'Strong',
    textClass: 'text-[#34A853]',
    barClass: 'bg-[#34A853]',
  },
}

export function usePasswordStrength(password: string) {
  const level = getPasswordStrength(password)

  return {
    level,
    ...strengthStyles[level],
  }
}
