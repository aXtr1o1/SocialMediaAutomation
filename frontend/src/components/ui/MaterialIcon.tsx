type MaterialIconProps = {
  name: string
  className?: string
  filled?: boolean
}

export function MaterialIcon({ name, className, filled = false }: MaterialIconProps) {
  return (
    <span
      className={['material-symbols-outlined', className].filter(Boolean).join(' ')}
      style={
        filled
          ? { fontVariationSettings: "'FILL' 1, 'wght' 400, 'GRAD' 0, 'opsz' 24" }
          : undefined
      }
      aria-hidden
    >
      {name}
    </span>
  )
}
