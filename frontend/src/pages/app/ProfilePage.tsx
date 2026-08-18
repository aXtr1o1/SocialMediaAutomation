import { useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { ProfileField } from '../../components/profile/ProfileField'
import { MaterialIcon } from '../../components/ui/MaterialIcon'
import { useAuth } from '../../context/AuthContext'
import { updateUserProfile } from '../../lib/auth'
import { paths } from '../../lib/paths'
import { getUserInitials, getUserProfileDetails } from '../../lib/user'

export function ProfilePage() {
  const { session, refreshSession } = useAuth()
  const user = session?.user
  const profile = user ? getUserProfileDetails(user) : null
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [username, setUsername] = useState('')
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  useEffect(() => {
    if (!profile) {
      return
    }

    setFirstName(profile.firstName)
    setLastName(profile.lastName)
    setUsername(profile.username)
  }, [profile?.firstName, profile?.lastName, profile?.username])

  useEffect(() => {
    if (!notice) {
      return
    }

    const timeoutId = window.setTimeout(() => {
      setNotice('')
    }, 2500)

    return () => window.clearTimeout(timeoutId)
  }, [notice])

  if (!user || !profile) {
    return null
  }

  const isDirty =
    firstName.trim() !== profile.firstName ||
    lastName.trim() !== profile.lastName ||
    username.trim() !== profile.username

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setNotice('')

    if (!firstName.trim() || !lastName.trim() || !username.trim()) {
      setError('First name, last name, and username are required.')
      return
    }

    setIsSaving(true)

    try {
      await updateUserProfile({ firstName, lastName, username })
      await refreshSession()
      setNotice('Profile updated.')
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Could not update profile')
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col px-lg py-xl">
      <div className="mb-xl flex flex-col">
        <Link
          to={paths.discover}
          className="mb-md inline-flex items-center gap-1 font-label-md text-label-md text-on-surface-variant transition-colors hover:text-on-surface"
        >
          <MaterialIcon name="arrow_back" className="text-[18px]" />
          Back
        </Link>
        <h1 className="mb-xs font-display-lg text-display-lg text-on-surface">Profile</h1>
        <p className="max-w-2xl font-body-lg text-body-lg text-on-surface-variant">
          Your account details for this workspace.
        </p>
      </div>

      <form
        className="rounded-[14px] border border-surface-variant bg-surface-container-lowest p-lg shadow-sm"
        onSubmit={handleSubmit}
      >
        <div className="mb-lg flex items-center gap-md border-b border-surface-variant pb-lg">
          {profile.avatarUrl ? (
            <img
              alt=""
              className="h-16 w-16 rounded-full border border-surface-variant object-cover"
              src={profile.avatarUrl}
            />
          ) : (
            <div className="flex h-16 w-16 items-center justify-center rounded-full border border-surface-variant bg-primary/10 font-headline-sm text-headline-sm text-primary">
              {getUserInitials(`${firstName} ${lastName}`.trim() || profile.displayName)}
            </div>
          )}
          <div>
            <h2 className="font-headline-sm text-headline-sm text-on-surface">
              {`${firstName} ${lastName}`.trim() || profile.displayName}
            </h2>
            <p className="font-body-md text-body-md text-on-surface-variant">{profile.email || '—'}</p>
          </div>
        </div>

        <div className="flex flex-col gap-lg">
          <div className="flex flex-col gap-lg sm:flex-row">
            <div className="flex-1">
              <ProfileField
                id="firstName"
                label="First name"
                value={firstName}
                autoComplete="given-name"
                required
                onChange={setFirstName}
              />
            </div>
            <div className="flex-1">
              <ProfileField
                id="lastName"
                label="Last name"
                value={lastName}
                autoComplete="family-name"
                required
                onChange={setLastName}
              />
            </div>
          </div>

          <ProfileField
            id="username"
            label="Username"
            value={username}
            autoComplete="username"
            required
            onChange={setUsername}
          />

          <ProfileField id="email" label="Email" value={profile.email} readOnly />
        </div>

        <div className="mt-xl flex flex-col items-end gap-sm border-t border-surface-variant pt-lg">
          {error ? <p className="w-full text-right text-[13px] text-error">{error}</p> : null}
          {notice ? <p className="w-full text-right text-[13px] text-primary">{notice}</p> : null}
          <button
            type="submit"
            disabled={isSaving || !isDirty}
            className="group relative flex h-9 items-center gap-2 overflow-hidden rounded bg-primary px-6 font-label-md text-label-md text-on-primary shadow-sm transition-all hover:bg-primary/90 hover:shadow-md disabled:cursor-not-allowed disabled:opacity-50"
          >
            <span className="relative z-10 flex items-center gap-2">
              {isSaving ? (
                <>
                  <MaterialIcon name="progress_activity" className="animate-spin text-[18px]" />
                  Saving...
                </>
              ) : (
                'Save changes'
              )}
            </span>
          </button>
        </div>
      </form>
    </div>
  )
}
