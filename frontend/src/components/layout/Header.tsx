import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { signOut } from '../../lib/auth'
import { paths } from '../../lib/paths'
import { getUserAvatarUrl, getUserDisplayName, getUserInitials } from '../../lib/user'
import { MaterialIcon } from '../ui/MaterialIcon'
import { ThemeToggle } from '../ui/ThemeToggle'

export function Header() {
  const { session } = useAuth()
  const navigate = useNavigate()
  const [isMenuOpen, setIsMenuOpen] = useState(false)
  const [error, setError] = useState('')
  const menuRef = useRef<HTMLDivElement>(null)
  const user = session?.user
  const displayName = user ? getUserDisplayName(user) : 'User'
  const avatarUrl = user ? getUserAvatarUrl(user) : null
  const subtitle = user?.email ?? ''

  useEffect(() => {
    function handlePointerDown(event: MouseEvent) {
      if (!menuRef.current?.contains(event.target as Node)) {
        setIsMenuOpen(false)
      }
    }

    document.addEventListener('mousedown', handlePointerDown)
    return () => document.removeEventListener('mousedown', handlePointerDown)
  }, [])

  async function handleSignOut() {
    setError('')

    try {
      await signOut()
      navigate(paths.signIn, { replace: true })
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not sign out')
    }
  }

  return (
    <header className="fixed left-64 right-0 top-0 z-40 flex h-16 items-center justify-end gap-md border-b border-surface-variant bg-surface/80 px-lg backdrop-blur-xl">
      <ThemeToggle />
      <div className="relative pl-xs" ref={menuRef}>
        <button
          className="group flex cursor-pointer items-center gap-md"
          type="button"
          onClick={() => setIsMenuOpen((open) => !open)}
          aria-expanded={isMenuOpen}
          aria-haspopup="menu"
        >
          <div className="hidden flex-col items-end sm:flex">
            <span className="font-label-md text-label-md text-on-surface">{displayName}</span>
            <span className="font-label-sm text-label-sm text-on-surface-variant">{subtitle}</span>
          </div>
          {avatarUrl ? (
            <img
              alt=""
              className="h-8 w-8 rounded-full border border-surface-variant object-cover"
              src={avatarUrl}
            />
          ) : (
            <div className="flex h-8 w-8 items-center justify-center rounded-full border border-surface-variant bg-primary/10 text-label-sm font-semibold text-primary">
              {getUserInitials(displayName)}
            </div>
          )}
        </button>

        {isMenuOpen ? (
          <div
            className="absolute right-0 mt-2 w-48 rounded-lg border border-surface-variant bg-surface-container-lowest py-1 shadow-lg"
            role="menu"
          >
            <Link
              to={paths.profile}
              role="menuitem"
              className="flex w-full items-center gap-2 px-3 py-2 text-left font-body-md text-body-md text-on-surface hover:bg-surface-container"
              onClick={() => setIsMenuOpen(false)}
            >
              <MaterialIcon name="person" className="text-[18px]" />
              Profile
            </Link>
            <button
              className="flex w-full items-center gap-2 px-3 py-2 text-left font-body-md text-body-md text-on-surface hover:bg-surface-container"
              type="button"
              role="menuitem"
              onClick={handleSignOut}
            >
              <MaterialIcon name="logout" className="text-[18px]" />
              Sign out
            </button>
            {error ? <p className="px-3 py-1 text-[12px] text-error">{error}</p> : null}
          </div>
        ) : null}
      </div>
    </header>
  )
}
