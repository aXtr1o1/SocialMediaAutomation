import { useTheme } from '../../context/ThemeContext'
import { MaterialIcon } from './MaterialIcon'

export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme()
  const isDark = resolvedTheme === 'dark'

  return (
    <button
      type="button"
      className="p-2 text-on-surface-variant transition-colors hover:text-on-surface"
      aria-label={isDark ? 'Switch to light theme' : 'Switch to dark theme'}
      aria-pressed={isDark}
      onClick={() => setTheme(isDark ? 'light' : 'dark')}
    >
      <MaterialIcon name={isDark ? 'light_mode' : 'dark_mode'} className="text-[22px]" />
    </button>
  )
}
