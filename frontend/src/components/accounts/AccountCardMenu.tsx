import { useEffect, useRef, useState } from 'react'
import { MaterialIcon } from '../ui/MaterialIcon'

type AccountCardMenuProps = {
  disabled?: boolean
  onDelete: () => void
}

export function AccountCardMenu({ disabled = false, onDelete }: AccountCardMenuProps) {
  const [open, setOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) {
      return
    }

    function handlePointerDown(event: MouseEvent) {
      if (!menuRef.current?.contains(event.target as Node)) {
        setOpen(false)
      }
    }

    function handleEscape(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setOpen(false)
      }
    }

    document.addEventListener('mousedown', handlePointerDown)
    document.addEventListener('keydown', handleEscape)

    return () => {
      document.removeEventListener('mousedown', handlePointerDown)
      document.removeEventListener('keydown', handleEscape)
    }
  }, [open])

  return (
    <div className="relative" ref={menuRef}>
      <button
        type="button"
        disabled={disabled}
        aria-label="Account actions"
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => {
          setOpen((current) => !current)
        }}
        className="flex h-8 w-8 items-center justify-center rounded-full text-on-surface-variant transition-colors hover:bg-surface-container-high hover:text-on-surface disabled:cursor-not-allowed disabled:opacity-60"
      >
        <MaterialIcon name="more_vert" className="text-[20px]" />
      </button>

      {open ? (
        <div
          role="menu"
          className="absolute right-0 top-[calc(100%+6px)] z-30 min-w-[148px] overflow-hidden rounded-lg border border-outline-variant/40 bg-surface-container-lowest py-1 shadow-lg"
        >
          <button
            type="button"
            role="menuitem"
            className="flex w-full items-center gap-2 px-md py-sm text-left font-label-md text-label-md text-error transition-colors hover:bg-error-container/40"
            onClick={() => {
              setOpen(false)
              onDelete()
            }}
          >
            <MaterialIcon name="delete" className="text-[18px]" />
            Delete
          </button>
        </div>
      ) : null}
    </div>
  )
}
