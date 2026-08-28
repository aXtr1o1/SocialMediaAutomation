type BlueskyIconProps = {
  className?: string
}

export function BlueskyIcon({ className = 'h-8 w-8' }: BlueskyIconProps) {
  return (
    <svg className={className} fill="currentColor" viewBox="0 0 24 24" aria-hidden>
      <path d="M12 10.8c-1.087-2.114-4.046-6.053-6.798-7.995C2.566 1.05 0 2.226 0 5.485V7.4c0 1.959 1.487 3.596 3.42 3.844L6.92 11.7l-3.376.815c-3.155.762-3.642 4.148-1.052 5.626 4.093 2.336 8.528-1.579 9.508-3.03.98 1.45 5.415 5.366 9.508 3.03 2.59-1.478 2.103-4.864-1.052-5.626l-3.376-.815 3.501-.456c1.933-.248 3.42-1.885 3.42-3.844V5.485c0-3.259-2.566-4.434-5.202-2.68C16.046 4.747 13.087 8.687 12 10.8z" />
    </svg>
  )
}
