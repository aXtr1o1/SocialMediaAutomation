export type PasswordStrength = 0 | 1 | 2 | 3 | 4

export function isValidEmail(value: string) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim())
}

export function getPasswordStrength(password: string): PasswordStrength {
  let strength = 0

  if (password.length > 0) strength += 1
  if (password.length > 7) strength += 1
  if (/[A-Z]/.test(password) && /[a-z]/.test(password)) strength += 1
  if (/[0-9!@#$%^&*)(+=._-]/.test(password)) strength += 1

  return strength as PasswordStrength
}
