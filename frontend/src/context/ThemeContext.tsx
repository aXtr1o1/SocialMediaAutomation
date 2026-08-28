import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import {
  applyTheme,
  getStoredTheme,
  getSystemTheme,
  persistTheme,
  resolveTheme,
  type ResolvedTheme,
  type Theme,
} from '../lib/theme'

type ThemeContextValue = {
  theme: Theme
  resolvedTheme: ResolvedTheme
  setTheme: (theme: Theme) => void
}

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined)

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<Theme>(() =>
    typeof window === 'undefined' ? 'system' : getStoredTheme(),
  )
  const [resolvedTheme, setResolvedTheme] = useState<ResolvedTheme>(() =>
    typeof window === 'undefined' ? 'light' : resolveTheme(getStoredTheme()),
  )

  const setTheme = useCallback((next: Theme) => {
    persistTheme(next)
    setThemeState(next)
    const resolved = resolveTheme(next)
    setResolvedTheme(resolved)
    applyTheme(next)
  }, [])

  useEffect(() => {
    applyTheme(theme)
    setResolvedTheme(resolveTheme(theme))
  }, [theme])

  useEffect(() => {
    if (theme !== 'system') {
      return
    }

    const media = window.matchMedia('(prefers-color-scheme: dark)')

    function onChange() {
      applyTheme('system')
      setResolvedTheme(getSystemTheme())
    }

    media.addEventListener('change', onChange)
    return () => media.removeEventListener('change', onChange)
  }, [theme])

  const value = useMemo(
    () => ({ theme, resolvedTheme, setTheme }),
    [theme, resolvedTheme, setTheme],
  )

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}

export function useTheme() {
  const context = useContext(ThemeContext)

  if (!context) {
    throw new Error('useTheme must be used inside ThemeProvider')
  }

  return context
}
