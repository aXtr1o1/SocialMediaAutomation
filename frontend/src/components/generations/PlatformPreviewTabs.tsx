import type { GeneratePlatform } from '../../lib/generations'

type PlatformPreviewTabsProps = {
  active: GeneratePlatform
  platforms: GeneratePlatform[]
  onChange: (platform: GeneratePlatform) => void
}

const LABELS: Record<GeneratePlatform, string> = {
  linkedin: 'LinkedIn Preview',
  bluesky: 'Bluesky Preview',
}

export function PlatformPreviewTabs({ active, platforms, onChange }: PlatformPreviewTabsProps) {
  return (
    <div role="tablist" aria-label="Platform preview" className="flex flex-wrap items-center gap-1">
      {platforms.map((platform) => {
        const selected = platform === active
        return (
          <button
            key={platform}
            type="button"
            role="tab"
            aria-selected={selected}
            onClick={() => onChange(platform)}
            className={`rounded-lg px-md py-sm font-label-md text-label-md transition-colors ${
              selected
                ? 'bg-primary/10 text-primary'
                : 'text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface'
            }`}
          >
            {LABELS[platform]}
          </button>
        )
      })}
    </div>
  )
}
