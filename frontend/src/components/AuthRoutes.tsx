import { Navigate } from 'react-router-dom'
import type { ReactNode } from 'react'
import { useAuth } from '../context/AuthContext'
import { authClasses } from '../lib/authTheme'
import { POST_LOGIN_PATH, paths } from '../lib/paths'
import { AuthLayout } from './layout/AuthLayout'

type GuardProps = {
  children: ReactNode
}

function AuthLoading() {
  return <AuthLayout className={authClasses.page} />
}

export function ProtectedRoute({ children }: GuardProps) {
  const { session, isReady } = useAuth()

  if (!isReady) {
    return <AuthLoading />
  }

  if (!session) {
    return <Navigate to={paths.signIn} replace />
  }

  return children
}

export function GuestRoute({ children }: GuardProps) {
  const { session, isReady } = useAuth()

  if (!isReady) {
    return <AuthLoading />
  }

  if (session) {
    return <Navigate to={POST_LOGIN_PATH} replace />
  }

  return children
}
