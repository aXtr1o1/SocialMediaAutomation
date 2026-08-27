import type { FormEvent } from 'react'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { AuthCard } from '../components/layout/AuthCard'
import { AuthLayout } from '../components/layout/AuthLayout'
import { Button } from '../components/ui/Button'
import { Input } from '../components/ui/Input'
import { MaterialIcon } from '../components/ui/MaterialIcon'
import { PasswordStrength } from '../components/ui/PasswordStrength'
import { usePasswordVisibility } from '../hooks/usePasswordVisibility'
import { requestPasswordReset, resetPasswordWithOtp } from '../lib/auth'
import { authClasses } from '../lib/authTheme'
import { paths } from '../lib/paths'

type Step = 'identify' | 'otp' | 'password'

export function ForgotPasswordPage() {
  const navigate = useNavigate()
  const [step, setStep] = useState<Step>('identify')
  const [identifier, setIdentifier] = useState('')
  const [otp, setOtp] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const passwordVisibility = usePasswordVisibility()
  const confirmVisibility = usePasswordVisibility()

  async function sendCode() {
    const value = identifier.trim()
    if (!value) {
      setError('Enter your username or email')
      return
    }

    setIsSubmitting(true)
    setError('')
    setNotice('')
    try {
      const result = await requestPasswordReset(value)
      setNotice(result.message)
      setStep('otp')
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not send reset code')
    } finally {
      setIsSubmitting(false)
    }
  }

  function goToPasswordStep() {
    const code = otp.trim()
    if (code.length < 4) {
      setError('Enter the one-time code from your email')
      return
    }
    setError('')
    setNotice('')
    setStep('password')
  }

  async function submitNewPassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (password.length < 8) {
      setError('Password must be at least 8 characters')
      return
    }
    if (password !== confirmPassword) {
      setError('Passwords do not match')
      return
    }

    setIsSubmitting(true)
    setError('')
    try {
      const result = await resetPasswordWithOtp({
        identifier,
        otp,
        password,
        confirmPassword,
      })
      navigate(paths.signIn, {
        replace: true,
        state: {
          email: identifier.includes('@') ? identifier.trim() : undefined,
          notice: result.message,
        },
      })
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not reset password')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <AuthLayout className={authClasses.page}>
      <AuthCard className={`w-full max-w-[400px] ${authClasses.card}`} contentClassName="gap-[24px]">
        <div className="flex flex-col gap-1 text-center">
          <h1 className={authClasses.title}>Reset password</h1>
          <p className={authClasses.subtitle}>
            {step === 'identify'
              ? 'Enter your username or email and we will send a one-time code.'
              : step === 'otp'
                ? 'Check your email for the one-time code.'
                : 'Choose a new password for your account.'}
          </p>
        </div>

        {step === 'identify' ? (
          <form
            className="flex flex-col gap-[24px]"
            onSubmit={(event) => {
              event.preventDefault()
              void sendCode()
            }}
          >
            <Input
              id="reset-identifier"
              label="Username or Email address"
              type="text"
              placeholder="username or name@company.com"
              autoComplete="username"
              value={identifier}
              onChange={(event) => setIdentifier(event.target.value)}
            />
            <Button className={authClasses.primaryButton} type="submit" disabled={isSubmitting}>
              {isSubmitting ? 'Sending…' : 'Send code'}
            </Button>
          </form>
        ) : null}

        {step === 'otp' ? (
          <form
            className="flex flex-col gap-[24px]"
            onSubmit={(event) => {
              event.preventDefault()
              goToPasswordStep()
            }}
          >
            <Input
              id="reset-otp"
              label="One-time code"
              type="text"
              inputMode="numeric"
              autoComplete="one-time-code"
              placeholder="Enter the code from email"
              value={otp}
              onChange={(event) => setOtp(event.target.value)}
            />
            <Button className={authClasses.primaryButton} type="submit" disabled={isSubmitting}>
              Continue
            </Button>
            <button
              type="button"
              className={`text-center text-[14px] font-medium ${authClasses.link}`}
              disabled={isSubmitting}
              onClick={() => {
                void sendCode()
              }}
            >
              Resend code
            </button>
            <button
              type="button"
              className="text-center text-[14px] text-on-surface-variant"
              onClick={() => {
                setStep('identify')
                setError('')
                setNotice('')
              }}
            >
              Use a different account
            </button>
          </form>
        ) : null}

        {step === 'password' ? (
          <form className="flex flex-col gap-[24px]" onSubmit={submitNewPassword}>
            <Input
              id="new-password"
              label="New password"
              type={passwordVisibility.inputType}
              autoComplete="new-password"
              placeholder="••••••••"
              className="pr-12"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              rightSlot={
                <button
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-on-surface-variant transition-colors hover:text-on-surface focus:outline-none"
                  type="button"
                  onClick={passwordVisibility.toggle}
                  aria-label={passwordVisibility.isVisible ? 'Hide password' : 'Show password'}
                >
                  <MaterialIcon name={passwordVisibility.icon} className="text-[20px]" />
                </button>
              }
            />
            <PasswordStrength password={password} />
            <Input
              id="confirm-new-password"
              label="Confirm password"
              type={confirmVisibility.inputType}
              autoComplete="new-password"
              placeholder="••••••••"
              className="pr-12"
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
              rightSlot={
                <button
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-on-surface-variant transition-colors hover:text-on-surface focus:outline-none"
                  type="button"
                  onClick={confirmVisibility.toggle}
                  aria-label={confirmVisibility.isVisible ? 'Hide password' : 'Show password'}
                >
                  <MaterialIcon name={confirmVisibility.icon} className="text-[20px]" />
                </button>
              }
            />
            <Button className={authClasses.primaryButton} type="submit" disabled={isSubmitting}>
              {isSubmitting ? 'Updating…' : 'Confirm'}
            </Button>
            <button
              type="button"
              className="text-center text-[14px] text-on-surface-variant"
              onClick={() => {
                setStep('otp')
                setError('')
              }}
            >
              Back to code
            </button>
          </form>
        ) : null}

        {notice ? <p className="-mt-2 text-center text-[13px] text-primary">{notice}</p> : null}
        {error ? <p className="-mt-2 text-center text-[13px] text-error">{error}</p> : null}

        <div className={`-mt-2 ${authClasses.footer}`}>
          Remembered it?{' '}
          <Link className={`font-bold underline ${authClasses.link}`} to={paths.signIn}>
            Sign in
          </Link>
        </div>
      </AuthCard>
    </AuthLayout>
  )
}
