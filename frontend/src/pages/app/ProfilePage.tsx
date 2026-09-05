import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { ProfileField } from '../../components/profile/ProfileField'
import { MaterialIcon } from '../../components/ui/MaterialIcon'
import { PasswordStrength } from '../../components/ui/PasswordStrength'
import { useAuth } from '../../context/AuthContext'
import { usePasswordVisibility } from '../../hooks/usePasswordVisibility'
import { ApiError } from '../../lib/api'
import { changePassword, updateUserProfile } from '../../lib/auth'
import { removeProfileAvatar, uploadProfileAvatar } from '../../lib/avatar'
import { paths } from '../../lib/paths'
import { getUserInitials, getUserProfileDetails } from '../../lib/user'
import { supabase } from '../../lib/supabaseClient'

function PasswordToggle({
  isVisible,
  onToggle,
  label,
}: {
  isVisible: boolean
  onToggle: () => void
  label: string
}) {
  return (
    <button
      type="button"
      className="absolute right-3 top-1/2 -translate-y-1/2 text-on-surface-variant transition-colors hover:text-on-surface focus:outline-none"
      onClick={onToggle}
      aria-label={label}
    >
      <MaterialIcon
        name={isVisible ? 'visibility_off' : 'visibility'}
        className="text-[20px]"
      />
    </button>
  )
}

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

  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [isChangingPassword, setIsChangingPassword] = useState(false)
  const [passwordError, setPasswordError] = useState('')
  const [passwordNotice, setPasswordNotice] = useState('')

  const currentVisibility = usePasswordVisibility()
  const newVisibility = usePasswordVisibility()
  const confirmVisibility = usePasswordVisibility()

  const fileInputRef = useRef<HTMLInputElement>(null)

  const [isUploadingAvatar, setIsUploadingAvatar] = useState(false)
  const [avatarError, setAvatarError] = useState('')
  const [avatarNotice, setAvatarNotice] = useState('')
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)

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

  useEffect(() => {
    if (!passwordNotice) {
      return
    }

    const timeoutId = window.setTimeout(() => {
      setPasswordNotice('')
    }, 2500)

    return () => window.clearTimeout(timeoutId)
  }, [passwordNotice])

  useEffect(() => {
    if (!avatarNotice) {
      return
    }

    const timeoutId = window.setTimeout(() => {
      setAvatarNotice('')
    }, 2500)

    return () => window.clearTimeout(timeoutId)
  }, [avatarNotice])

  useEffect(() => {
    return () => {
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl)
      }
    }
  }, [previewUrl])

  if (!user || !profile) {
    return null
  }

  const displayAvatarUrl = previewUrl || profile.avatarUrl

  const isDirty =
    firstName.trim() !== profile.firstName ||
    lastName.trim() !== profile.lastName ||
    username.trim() !== profile.username

  async function handleAvatarSelected(file: File | null) {
    if (!file) {
      return
    }

    setAvatarError('')
    setAvatarNotice('')

    const nextPreview = URL.createObjectURL(file)

    setPreviewUrl((previous) => {
      if (previous) {
        URL.revokeObjectURL(previous)
      }

      return nextPreview
    })

    setIsUploadingAvatar(true)

    try {
      await uploadProfileAvatar(file)
      await refreshSession()

      setAvatarNotice('Profile photo updated.')
    } catch (caught) {
      setAvatarError(
        caught instanceof Error
          ? caught.message
          : 'Could not upload photo',
      )

      setPreviewUrl((previous) => {
        if (previous) {
          URL.revokeObjectURL(previous)
        }

        return null
      })
    } finally {
      setIsUploadingAvatar(false)

      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }

  async function handleRemoveAvatar() {
    setAvatarError('')
    setAvatarNotice('')
    setIsUploadingAvatar(true)

    try {
      await removeProfileAvatar()
      await refreshSession()

      setPreviewUrl((previous) => {
        if (previous) {
          URL.revokeObjectURL(previous)
        }

        return null
      })

      setAvatarNotice('Profile photo removed.')
    } catch (caught) {
      setAvatarError(
        caught instanceof Error
          ? caught.message
          : 'Could not remove photo',
      )
    } finally {
      setIsUploadingAvatar(false)
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    setError('')
    setNotice('')

    if (
      !firstName.trim() ||
      !lastName.trim() ||
      !username.trim()
    ) {
      setError(
        'First name, last name, and username are required.',
      )
      return
    }

    setIsSaving(true)

    try {
      await updateUserProfile({
        firstName,
        lastName,
        username,
      })

      await refreshSession()

      setNotice('Profile updated.')
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : 'Could not update profile',
      )
    } finally {
      setIsSaving(false)
    }
  }

  async function handlePasswordSubmit(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault()

    setPasswordError('')
    setPasswordNotice('')

    if (!currentPassword) {
      setPasswordError('Enter your current password.')
      return
    }

    if (newPassword.length < 8) {
      setPasswordError(
        'New password must be at least 8 characters.',
      )
      return
    }

    if (newPassword !== confirmPassword) {
      setPasswordError(
        'New password and confirm password do not match.',
      )
      return
    }

    if (newPassword === currentPassword) {
      setPasswordError(
        'New password must be different from the current password.',
      )
      return
    }

    /*
     * Ask whether the user wants to sign out all other
     * devices/browsers after changing the password.
     *
     * NOTE:
     * The backend currently uses Supabase global sign-out
     * when this is true. That also revokes the current session,
     * so the current browser will be redirected to sign-in.
     */
    const signOutAllDevices = window.confirm(
      'Do you want to sign out from all other devices and browsers after changing your password?',
    )

    setIsChangingPassword(true)

    try {
      const result = await changePassword({
        currentPassword,
        newPassword,
        confirmPassword,
        signOutAllDevices,
      })

      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')

      if (result.signed_out_all_devices) {
        /*
         * The backend has globally revoked the Supabase
         * sessions. Clear this browser's local session too.
         */
        await supabase.auth.signOut()

        window.location.href = paths.signIn
        return
      }

      setPasswordNotice(
        result.message || 'Password updated.',
      )
    } catch (caught) {
      if (caught instanceof ApiError) {
        setPasswordError(caught.message)
      } else {
        setPasswordError(
          caught instanceof Error
            ? caught.message
            : 'Could not update password',
        )
      }
    } finally {
      setIsChangingPassword(false)
    }
  }

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-xl px-lg py-xl">
      <div className="flex flex-col">
        <Link
          to={paths.discover}
          className="mb-md inline-flex items-center gap-1 font-label-md text-label-md text-on-surface-variant transition-colors hover:text-on-surface"
        >
          <MaterialIcon
            name="arrow_back"
            className="text-[18px]"
          />
          Back
        </Link>

        <h1 className="mb-xs font-display-lg text-display-lg text-on-surface">
          Profile
        </h1>

        <p className="max-w-2xl font-body-lg text-body-lg text-on-surface-variant">
          Your account details for this workspace.
        </p>
      </div>

      <form
        className="rounded-[14px] border border-surface-variant bg-surface-container-lowest p-lg shadow-sm"
        onSubmit={handleSubmit}
      >
        <div className="mb-lg flex items-center gap-md border-b border-surface-variant pb-lg">
          <div className="relative shrink-0">
            {displayAvatarUrl ? (
              <img
                alt=""
                className="h-16 w-16 rounded-full border border-surface-variant object-cover"
                src={displayAvatarUrl}
              />
            ) : (
              <div className="flex h-16 w-16 items-center justify-center rounded-full border border-surface-variant bg-primary/10 font-headline-sm text-headline-sm text-primary">
                {getUserInitials(
                  `${firstName} ${lastName}`.trim() ||
                    profile.displayName,
                )}
              </div>
            )}

            <button
              type="button"
              disabled={isUploadingAvatar}
              onClick={() =>
                fileInputRef.current?.click()
              }
              className="absolute -bottom-1 -right-1 flex h-8 w-8 items-center justify-center rounded-full border border-surface-variant bg-surface-container-lowest text-on-surface shadow-sm transition-colors hover:bg-surface-container disabled:cursor-not-allowed disabled:opacity-60"
              aria-label="Upload profile photo"
            >
              <MaterialIcon
                name={
                  isUploadingAvatar
                    ? 'progress_activity'
                    : 'photo_camera'
                }
                className={`text-[16px] ${
                  isUploadingAvatar
                    ? 'animate-spin'
                    : ''
                }`}
              />
            </button>

            <input
              ref={fileInputRef}
              type="file"
              accept="image/jpeg,image/png,image/webp,image/gif"
              className="hidden"
              onChange={(event) => {
                void handleAvatarSelected(
                  event.target.files?.[0] ?? null,
                )
              }}
            />
          </div>

          <div className="min-w-0 flex-1">
            <h2 className="font-headline-sm text-headline-sm text-on-surface">
              {`${firstName} ${lastName}`.trim() ||
                profile.displayName}
            </h2>

            <p className="font-body-md text-body-md text-on-surface-variant">
              {profile.email || '—'}
            </p>

            <div className="mt-2 flex flex-wrap items-center gap-3">
              <button
                type="button"
                disabled={isUploadingAvatar}
                onClick={() =>
                  fileInputRef.current?.click()
                }
                className="font-label-md text-label-md text-primary transition-colors hover:text-brand-hover disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isUploadingAvatar
                  ? 'Uploading…'
                  : 'Change photo'}
              </button>

              {displayAvatarUrl ? (
                <button
                  type="button"
                  disabled={isUploadingAvatar}
                  onClick={() => {
                    void handleRemoveAvatar()
                  }}
                  className="font-label-md text-label-md text-on-surface-variant transition-colors hover:text-error disabled:cursor-not-allowed disabled:opacity-60"
                >
                  Remove
                </button>
              ) : null}
            </div>

            {avatarError ? (
              <p className="mt-1 text-[13px] text-error">
                {avatarError}
              </p>
            ) : null}

            {avatarNotice ? (
              <p className="mt-1 text-[13px] text-primary">
                {avatarNotice}
              </p>
            ) : null}
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

          <ProfileField
            id="email"
            label="Email"
            value={profile.email}
            readOnly
          />
        </div>

        <div className="mt-xl flex flex-col items-end gap-sm border-t border-surface-variant pt-lg">
          {error ? (
            <p className="w-full text-right text-[13px] text-error">
              {error}
            </p>
          ) : null}

          {notice ? (
            <p className="w-full text-right text-[13px] text-primary">
              {notice}
            </p>
          ) : null}

          <button
            type="submit"
            disabled={isSaving || !isDirty}
            className="group relative flex h-9 items-center gap-2 overflow-hidden rounded bg-primary px-6 font-label-md text-label-md text-on-primary shadow-sm transition-all hover:bg-primary/90 hover:shadow-md disabled:cursor-not-allowed disabled:opacity-50"
          >
            <span className="relative z-10 flex items-center gap-2">
              {isSaving ? (
                <>
                  <MaterialIcon
                    name="progress_activity"
                    className="animate-spin text-[18px]"
                  />
                  Saving...
                </>
              ) : (
                'Save changes'
              )}
            </span>
          </button>
        </div>
      </form>

      <form
        className="rounded-[14px] border border-surface-variant bg-surface-container-lowest p-lg shadow-sm"
        onSubmit={handlePasswordSubmit}
      >
        <div className="mb-lg border-b border-surface-variant pb-md">
          <h2 className="font-headline-sm text-headline-sm text-on-surface">
            Change password
          </h2>

          <p className="mt-1 font-body-md text-body-md text-on-surface-variant">
            Update the password used to sign in with username or email.
          </p>
        </div>

        <div className="flex flex-col gap-lg">
          <ProfileField
            id="currentPassword"
            label="Current password"
            type={currentVisibility.inputType}
            value={currentPassword}
            autoComplete="current-password"
            onChange={setCurrentPassword}
            rightSlot={
              <PasswordToggle
                isVisible={currentVisibility.isVisible}
                onToggle={currentVisibility.toggle}
                label={
                  currentVisibility.isVisible
                    ? 'Hide password'
                    : 'Show password'
                }
              />
            }
          />

          <div className="flex flex-col gap-2">
            <ProfileField
              id="newPassword"
              label="New password"
              type={newVisibility.inputType}
              value={newPassword}
              autoComplete="new-password"
              onChange={setNewPassword}
              rightSlot={
                <PasswordToggle
                  isVisible={newVisibility.isVisible}
                  onToggle={newVisibility.toggle}
                  label={
                    newVisibility.isVisible
                      ? 'Hide password'
                      : 'Show password'
                  }
                />
              }
            />

            <PasswordStrength password={newPassword} />
          </div>

          <ProfileField
            id="confirmPassword"
            label="Confirm password"
            type={confirmVisibility.inputType}
            value={confirmPassword}
            autoComplete="new-password"
            onChange={setConfirmPassword}
            rightSlot={
              <PasswordToggle
                isVisible={confirmVisibility.isVisible}
                onToggle={confirmVisibility.toggle}
                label={
                  confirmVisibility.isVisible
                    ? 'Hide password'
                    : 'Show password'
                }
              />
            }
          />
        </div>

        <div className="mt-xl flex flex-col items-end gap-sm border-t border-surface-variant pt-lg">
          {passwordError ? (
            <p className="w-full text-right text-[13px] text-error">
              {passwordError}
            </p>
          ) : null}

          {passwordNotice ? (
            <p className="w-full text-right text-[13px] text-primary">
              {passwordNotice}
            </p>
          ) : null}

          <button
            type="submit"
            disabled={
              isChangingPassword ||
              !currentPassword ||
              !newPassword ||
              !confirmPassword
            }
            className="group relative flex h-9 items-center gap-2 overflow-hidden rounded bg-primary px-6 font-label-md text-label-md text-on-primary shadow-sm transition-all hover:bg-primary/90 hover:shadow-md disabled:cursor-not-allowed disabled:opacity-50"
          >
            <span className="relative z-10 flex items-center gap-2">
              {isChangingPassword ? (
                <>
                  <MaterialIcon
                    name="progress_activity"
                    className="animate-spin text-[18px]"
                  />
                  Updating...
                </>
              ) : (
                'Update password'
              )}
            </span>
          </button>
        </div>
      </form>
    </div>
  )
}