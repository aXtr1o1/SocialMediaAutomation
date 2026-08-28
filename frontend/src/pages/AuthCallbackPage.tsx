import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AuthCard } from '../components/layout/AuthCard'
import { AuthLayout } from '../components/layout/AuthLayout'
import { authClasses } from '../lib/authTheme'
import { POST_LOGIN_PATH } from '../lib/paths'
import { supabase } from '../lib/supabaseClient'

export function AuthCallbackPage() {
  const navigate = useNavigate()
  const [error, setError] = useState('')
  const didRun = useRef(false)

  useEffect(() => {
    if (didRun.current) {
      return
    }

    didRun.current = true

    async function completeSignIn() {
      const params = new URLSearchParams(window.location.search)
      const code = params.get('code')
      const authError = params.get('error_description') || params.get('error')

      if (authError) {
        setError(authError)
        return
      }

      if (code) {
        const { error: exchangeError } = await supabase.auth.exchangeCodeForSession(window.location.href)

        if (exchangeError) {
          const { data } = await supabase.auth.getSession()
          if (!data.session) {
            setError(exchangeError.message)
            return
          }
        }
      }

      navigate(POST_LOGIN_PATH, { replace: true })
    }

    completeSignIn()
  }, [navigate])

  return (
    <AuthLayout className={authClasses.page}>
      <AuthCard className={`w-full max-w-[400px] ${authClasses.card}`} contentClassName="gap-3 text-center">
        <h1 className={authClasses.title}>{error ? 'Sign-in failed' : 'Signing you in...'}</h1>
        <p className={authClasses.subtitle}>{error || 'Please wait while we finish signing you in.'}</p>
      </AuthCard>
    </AuthLayout>
  )
}
