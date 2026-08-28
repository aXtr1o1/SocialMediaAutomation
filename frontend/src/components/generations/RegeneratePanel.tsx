import { MaterialIcon } from '../ui/MaterialIcon'

type RegeneratePanelProps = {
  targetText: string
  instruction: string
  error: string
  isSubmitting: boolean
  onTargetTextChange: (value: string) => void
  onInstructionChange: (value: string) => void
  onSubmit: () => void
}

export function RegeneratePanel({
  targetText,
  instruction,
  error,
  isSubmitting,
  onTargetTextChange,
  onInstructionChange,
  onSubmit,
}: RegeneratePanelProps) {
  return (
    <div className="rounded-xl border border-surface-variant bg-surface-container-low p-md">
      <div className="mb-sm flex items-center gap-xs">
        <MaterialIcon name="auto_awesome" className="text-[18px] text-primary" />
        <h3 className="font-label-md text-label-md text-on-surface">Regenerate section</h3>
      </div>
      <p className="mb-md font-body-md text-body-md text-on-surface-variant">
        Paste only the part you want changed. The rest of the post stays the same.
      </p>

      <label className="mb-md flex flex-col gap-xs">
        <span className="font-label-sm text-label-sm text-on-surface-variant">Text to change</span>
        <textarea
          value={targetText}
          onChange={(event) => onTargetTextChange(event.target.value)}
          rows={4}
          placeholder="Copy and paste the exact lines from the preview…"
          className="w-full resize-y rounded-lg border border-surface-variant bg-surface-container-lowest px-md py-sm font-body-md text-body-md text-on-surface outline-none transition-colors focus:border-primary"
        />
      </label>

      <label className="mb-md flex flex-col gap-xs">
        <span className="font-label-sm text-label-sm text-on-surface-variant">What to change</span>
        <textarea
          value={instruction}
          onChange={(event) => onInstructionChange(event.target.value)}
          rows={3}
          placeholder="e.g. Make this shorter and more direct"
          className="w-full resize-y rounded-lg border border-surface-variant bg-surface-container-lowest px-md py-sm font-body-md text-body-md text-on-surface outline-none transition-colors focus:border-primary"
        />
      </label>

      {error ? <p className="mb-sm font-body-md text-body-md text-error">{error}</p> : null}

      <button
        type="button"
        onClick={onSubmit}
        disabled={isSubmitting}
        className="inline-flex h-10 items-center justify-center gap-2 rounded-lg bg-primary px-md font-label-md text-label-md text-on-primary transition-colors hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {isSubmitting ? (
          <>
            <MaterialIcon name="progress_activity" className="animate-spin text-[18px]" />
            Regenerating…
          </>
        ) : (
          <>
            <MaterialIcon name="refresh" className="text-[18px]" />
            Regenerate
          </>
        )}
      </button>
    </div>
  )
}
