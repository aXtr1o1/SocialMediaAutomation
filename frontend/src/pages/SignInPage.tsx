import type { FormEvent } from 'react'
import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { GoogleAuthButton } from '../components/ui/GoogleAuthButton'
import { AuthCard } from '../components/layout/AuthCard'
import { AuthLayout } from '../components/layout/AuthLayout'
import { Button } from '../components/ui/Button'
import { Divider } from '../components/ui/Divider'
import { Input } from '../components/ui/Input'
import { MaterialIcon } from '../components/ui/MaterialIcon'
import { usePasswordVisibility } from '../hooks/usePasswordVisibility'
import { signInWithEmail } from '../lib/auth'
import { authClasses } from '../lib/authTheme'
import { POST_LOGIN_PATH, paths } from '../lib/paths'

type SignInLocationState = {
  email?: string
  notice?: string
}

export function SignInPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const locationState = (location.state as SignInLocationState | null) ?? {}
  const [identifier, setIdentifier] = useState(locationState.email ?? '')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [notice] = useState(locationState.notice ?? '')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const passwordVisibility = usePasswordVisibility()

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setIsSubmitting(true)

    try {
      await signInWithEmail(identifier, password)
      navigate(POST_LOGIN_PATH, { replace: true })
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not sign in')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <AuthLayout className={authClasses.page}>
      <AuthCard className={`w-full max-w-[400px] ${authClasses.card}`} contentClassName="gap-[24px]">
        <div className="flex flex-col gap-1 text-center">
          <h1 className={authClasses.title}>Welcome back</h1>
          <p className={authClasses.subtitle}>Sign in to your account to continue</p>
        </div>

        <GoogleAuthButton label="Continue with Google" />

        <Divider label="OR" />

        <form className="flex flex-col gap-[24px]" onSubmit={handleSubmit}>
          <Input
            id="identifier"
            label="Username or Email address"
            type="text"
            placeholder="username or name@company.com"
            autoComplete="username"
            value={identifier}
            onChange={(event) => setIdentifier(event.target.value)}
          />

          <Input
            id="password"
            label="Password"
            type={passwordVisibility.inputType}
            placeholder="••••••••"
            autoComplete="current-password"
            className="pr-12"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            labelExtra={
              <a className={`text-[14px] ${authClasses.link}`} href="#">
                Forgot password?
              </a>
            }
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

          <Button className={authClasses.primaryButton} type="submit" disabled={isSubmitting}>
            {isSubmitting ? 'Signing in...' : 'Sign In'}
          </Button>
          {notice ? <p className="-mt-3 text-center text-[13px] text-primary">{notice}</p> : null}
          {error ? <p className="-mt-3 text-center text-[13px] text-error">{error}</p> : null}
        </form>

        <div className={`-mt-2 ${authClasses.footer}`}>
          Don&apos;t have an account?{' '}
          <Link className={`font-bold underline ${authClasses.link}`} to={paths.signUp}>
            Sign up
          </Link>
        </div>
      </AuthCard>
    </AuthLayout>
  )
}
