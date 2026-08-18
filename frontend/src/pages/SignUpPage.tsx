import type { FormEvent } from 'react'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { GoogleAuthButton } from '../components/ui/GoogleAuthButton'
import { AuthCard } from '../components/layout/AuthCard'
import { AuthLayout } from '../components/layout/AuthLayout'
import { Button } from '../components/ui/Button'
import { Divider } from '../components/ui/Divider'
import { Input } from '../components/ui/Input'
import { MaterialIcon } from '../components/ui/MaterialIcon'
import { PasswordStrength } from '../components/ui/PasswordStrength'
import { usePasswordVisibility } from '../hooks/usePasswordVisibility'
import { signUpWithEmail } from '../lib/auth'
import { authClasses } from '../lib/authTheme'
import { cn } from '../lib/cn'
import { POST_LOGIN_PATH, paths } from '../lib/paths'
import { isValidEmail } from '../lib/validation'

type SignUpForm = {
  firstName: string
  lastName: string
  username: string
  email: string
  password: string
  confirmPassword: string
}

const initialForm: SignUpForm = {
  firstName: '',
  lastName: '',
  username: '',
  email: '',
  password: '',
  confirmPassword: '',
}

export function SignUpPage() {
  const navigate = useNavigate()
  const [form, setForm] = useState<SignUpForm>(initialForm)
  const [emailError, setEmailError] = useState('')
  const [confirmError, setConfirmError] = useState('')
  const [formError, setFormError] = useState('')
  const [notice, setNotice] = useState('')
  const [isShaking, setIsShaking] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const passwordVisibility = usePasswordVisibility()
  const confirmPasswordVisibility = usePasswordVisibility()

  function updateField<Key extends keyof SignUpForm>(key: Key, value: SignUpForm[Key]) {
    setForm((current) => ({ ...current, [key]: value }))
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setFormError('')
    setNotice('')

    if (!isValidEmail(form.email)) {
      setEmailError('Valid email required')
      setIsShaking(true)
      window.setTimeout(() => setIsShaking(false), 400)
      return
    }

    if (form.password !== form.confirmPassword) {
      setConfirmError('Passwords do not match')
      return
    }

    setEmailError('')
    setConfirmError('')
    setIsSubmitting(true)

    try {
      const data = await signUpWithEmail({
        email: form.email,
        password: form.password,
        firstName: form.firstName,
        lastName: form.lastName,
        username: form.username,
      })

      if (data.session) {
        navigate(POST_LOGIN_PATH, { replace: true })
        return
      }

      setNotice('Check your email to confirm your account, then sign in.')
    } catch (caught) {
      setFormError(caught instanceof Error ? caught.message : 'Could not create account')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <AuthLayout className={authClasses.page}>
      <AuthCard className={`w-full max-w-[420px] ${authClasses.card}`} contentClassName="gap-[24px]">
        <div className="flex flex-col gap-1 text-center">
          <h1 className={authClasses.title}>Create your account</h1>
          <p className={authClasses.subtitle}>Join the leading platform for professionals.</p>
        </div>

        <GoogleAuthButton label="Sign up with Google" />

        <Divider label="OR" />

        <form className={cn('flex flex-col gap-[24px]', isShaking && 'animate-shake')} onSubmit={handleSubmit}>
          <div className="flex gap-3">
            <div className="flex-1">
              <Input
                id="firstName"
                label="First Name"
                name="firstName"
                placeholder="Jane"
                autoComplete="given-name"
                value={form.firstName}
                onChange={(event) => updateField('firstName', event.target.value)}
                required
              />
            </div>
            <div className="flex-1">
              <Input
                id="lastName"
                label="Last Name"
                name="lastName"
                placeholder="Doe"
                autoComplete="family-name"
                value={form.lastName}
                onChange={(event) => updateField('lastName', event.target.value)}
                required
              />
            </div>
          </div>

          <Input
            id="username"
            label="Username"
            name="username"
            placeholder="janedoe99"
            autoComplete="username"
            leftIcon="person"
            value={form.username}
            onChange={(event) => updateField('username', event.target.value)}
            required
          />

          <Input
            id="email"
            label="Email address"
            name="email"
            type="email"
            placeholder="jane@example.com"
            autoComplete="email"
            leftIcon="mail"
            error={emailError}
            showErrorIcon
            value={form.email}
            onChange={(event) => {
              updateField('email', event.target.value)
              if (emailError) setEmailError('')
            }}
          />

          <div>
            <Input
              id="password"
              label="Password"
              name="password"
              placeholder="••••••••"
              autoComplete="new-password"
              leftIcon="lock"
              type={passwordVisibility.inputType}
              value={form.password}
              onChange={(event) => updateField('password', event.target.value)}
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
              required
            />
            <PasswordStrength password={form.password} />
          </div>

          <Input
            id="confirm-password"
            label="Confirm Password"
            name="confirm-password"
            type={confirmPasswordVisibility.inputType}
            placeholder="••••••••"
            autoComplete="new-password"
            leftIcon="lock_reset"
            error={confirmError}
            value={form.confirmPassword}
            onChange={(event) => {
              updateField('confirmPassword', event.target.value)
              if (confirmError) setConfirmError('')
            }}
            rightSlot={
              <button
                className="absolute right-3 top-1/2 -translate-y-1/2 text-on-surface-variant transition-colors hover:text-on-surface focus:outline-none"
                type="button"
                onClick={confirmPasswordVisibility.toggle}
                aria-label={confirmPasswordVisibility.isVisible ? 'Hide confirm password' : 'Show confirm password'}
              >
                <MaterialIcon name={confirmPasswordVisibility.icon} className="text-[20px]" />
              </button>
            }
            required
          />

          <div className="flex flex-col gap-3">
            <Button className={`group relative overflow-hidden ${authClasses.primaryButton}`} type="submit" disabled={isSubmitting}>
              <span className="relative z-10 flex items-center gap-1">
                {isSubmitting ? (
                  <>
                    <MaterialIcon name="progress_activity" className="animate-spin text-[18px]" />
                    Creating...
                  </>
                ) : (
                  <>
                    Create Account
                    <MaterialIcon name="arrow_forward" className="text-[18px] transition-transform group-hover:translate-x-1" />
                  </>
                )}
              </span>
              <div className="absolute inset-0 translate-y-full bg-white/20 transition-transform duration-300 ease-out group-hover:translate-y-0" />
            </Button>
            {formError ? <p className="text-center text-[13px] text-error">{formError}</p> : null}
            {notice ? <p className="text-center text-[13px] text-primary">{notice}</p> : null}
            <p className="text-center text-[12px] text-on-surface-variant">
              By signing up, you agree to our{' '}
              <a className={`font-semibold ${authClasses.link}`} href="#">
                Terms of Service
              </a>{' '}
              and{' '}
              <a className={`font-semibold ${authClasses.link}`} href="#">
                Privacy Policy
              </a>
              .
            </p>
          </div>
        </form>

        <div className={authClasses.footer}>
          Already have an account?
          <Link className={`ml-1 font-bold underline ${authClasses.link}`} to={paths.signIn}>
            Sign in
          </Link>
        </div>
      </AuthCard>
    </AuthLayout>
  )
}
