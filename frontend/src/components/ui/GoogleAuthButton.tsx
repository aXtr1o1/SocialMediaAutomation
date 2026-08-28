import { useState } from 'react'
import { GoogleIcon } from '../../assets/icons/GoogleIcon'
import { signInWithGoogle } from '../../lib/auth'
import { authClasses } from '../../lib/authTheme'
import { Button } from './Button'

type GoogleAuthButtonProps = {
  label: string
}

export function GoogleAuthButton({ label }: GoogleAuthButtonProps) {
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')

  async function handleGoogleSignIn() {
    setError('')
    setIsLoading(true)

    try {
      await signInWithGoogle()
    } catch (caught) {
      setIsLoading(false)
      setError(caught instanceof Error ? caught.message : 'Google sign-in failed')
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <Button
        variant="google"
        className={authClasses.googleButton}
        onClick={handleGoogleSignIn}
        disabled={isLoading}
      >
        <GoogleIcon />
        {isLoading ? 'Redirecting...' : label}
      </Button>
      {error ? <p className="text-center text-[13px] text-error">{error}</p> : null}
    </div>
  )
}
