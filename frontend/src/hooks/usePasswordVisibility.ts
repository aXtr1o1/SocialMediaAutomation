import { useState } from 'react'

export function usePasswordVisibility() {
  const [isVisible, setIsVisible] = useState(false)

  function toggle() {
    setIsVisible((current) => !current)
  }

  return {
    isVisible,
    inputType: isVisible ? 'text' : 'password',
    icon: isVisible ? 'visibility' : 'visibility_off',
    toggle,
  }
}
