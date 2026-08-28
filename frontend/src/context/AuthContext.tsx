import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import type { Session, User } from '@supabase/supabase-js'
import { supabase } from '../lib/supabaseClient'
import { ensurePublicUserProfile } from '../lib/auth'

type AuthContextValue = {
  session: Session | null
  isReady: boolean
  refreshSession: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null)
  const [isReady, setIsReady] = useState(false)

  const applyUser = useCallback((user: User | null) => {
    setSession((current) => {
      if (!current || !user) {
        return current
      }

      return { ...current, user }
    })
  }, [])

  const refreshSession = useCallback(async () => {
    const { data, error } = await supabase.auth.getUser()

    if (error) {
      throw error
    }

    applyUser(data.user)
  }, [applyUser])

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session)
      setIsReady(true)
      if (data.session) {
        void ensurePublicUserProfile()
      }
    })

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      setSession(nextSession)
      if (nextSession) {
        void ensurePublicUserProfile()
      }
    })

    return () => {
      subscription.unsubscribe()
    }
  }, [])

  const value = useMemo(() => ({ session, isReady, refreshSession }), [session, isReady, refreshSession])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)

  if (!context) {
    throw new Error('useAuth must be used inside AuthProvider')
  }

  return context
}
