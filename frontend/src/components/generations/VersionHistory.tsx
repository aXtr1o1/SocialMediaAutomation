import type { PostVersion } from '../../lib/generations'
import { MaterialIcon } from '../ui/MaterialIcon'

type VersionHistoryProps = {
  versions: PostVersion[]
  currentId: string
  onSelect: (id: string) => void
  onDelete: (id: string) => void
}

function formatTime(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return ''
  }
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

function sourceLabel(source: PostVersion['source']) {
  if (source === 'generate') {
    return 'Original'
  }
  if (source === 'restore') {
    return 'Restored'
  }
  return 'Edited'
}

export function VersionHistory({
  versions,
  currentId,
  onSelect,
  onDelete,
}: VersionHistoryProps) {
  const ordered = [...versions].reverse()
  const canDelete = versions.length > 1

  return (
    <aside className="flex h-full min-h-[420px] w-full flex-col rounded-xl border border-surface-variant bg-surface">
      <div className="border-b border-surface-variant px-md py-sm">
        <div className="flex items-center gap-xs">
          <MaterialIcon name="history" className="text-[18px] text-primary" />
          <h3 className="font-label-md text-label-md text-on-surface">Version history</h3>
        </div>
        <p className="mt-1 font-label-sm text-label-sm text-on-surface-variant">
          Select a version to preview. At least one version is always kept.
        </p>
      </div>

      <ul role="listbox" aria-label="Post versions" className="flex flex-1 flex-col overflow-y-auto px-sm py-sm">
        {ordered.map((item, index) => {
          const active = item.id === currentId
          const isLast = index === ordered.length - 1
          return (
            <li key={item.id} className="relative flex gap-sm px-sm py-sm">
              <div className="flex w-4 shrink-0 flex-col items-center">
                <span
                  className={`mt-1.5 h-2.5 w-2.5 rounded-full ${
                    active ? 'bg-primary ring-4 ring-primary/15' : 'bg-outline-variant'
                  }`}
                />
                {!isLast ? <span className="mt-1 w-px flex-1 bg-surface-variant" /> : null}
              </div>

              <div
                className={`min-w-0 flex-1 rounded-lg border px-sm py-sm transition-colors ${
                  active
                    ? 'border-primary bg-primary/5'
                    : 'border-transparent hover:border-surface-variant hover:bg-surface-container-low'
                }`}
              >
                <button
                  type="button"
                  role="option"
                  aria-selected={active}
                  onClick={() => onSelect(item.id)}
                  className="w-full text-left"
                >
                  <div className="flex items-center justify-between gap-xs">
                    <span className="font-label-md text-label-md text-on-surface">v{item.version}</span>
                    {active ? (
                      <span className="rounded bg-primary/10 px-1.5 py-0.5 font-label-sm text-label-sm text-primary">
                        Current
                      </span>
                    ) : (
                      <span className="font-label-sm text-label-sm text-on-surface-variant">
                        {sourceLabel(item.source)}
                      </span>
                    )}
                  </div>
                  <p className="mt-1 line-clamp-2 font-body-md text-body-md text-on-surface">{item.label}</p>
                  <p className="mt-1 font-label-sm text-label-sm text-on-surface-variant">
                    {formatTime(item.createdAt)}
                  </p>
                </button>

                {canDelete ? (
                  <div className="mt-2 flex flex-wrap items-center gap-1">
                    <button
                      type="button"
                      onClick={() => onDelete(item.id)}
                      className="inline-flex items-center gap-1 rounded-md px-2 py-1 font-label-sm text-label-sm text-error transition-colors hover:bg-error-container/40"
                    >
                      <MaterialIcon name="delete" className="text-[14px]" />
                      Delete
                    </button>
                  </div>
                ) : null}
              </div>
            </li>
          )
        })}
      </ul>
    </aside>
  )
}
