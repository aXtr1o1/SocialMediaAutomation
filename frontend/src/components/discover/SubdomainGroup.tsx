import { SubdomainChip } from './SubdomainChip'

type SubdomainGroupItem = {
  id: string
  label: string
}

type SubdomainGroupProps = {
  items: SubdomainGroupItem[]
  selectedIds: string[]
  onToggle: (id: string) => void
}

export function SubdomainGroup({ items, selectedIds, onToggle }: SubdomainGroupProps) {
  if (items.length === 0) {
    return (
      <p className="font-body-md text-body-md text-on-surface-variant">
        No subdomains in the database for this domain.
      </p>
    )
  }

  return (
    <div className="flex flex-wrap gap-2">
      {items.map((item) => (
        <SubdomainChip
          key={item.id}
          label={item.label}
          selected={selectedIds.includes(item.id)}
          onClick={() => onToggle(item.id)}
        />
      ))}
    </div>
  )
}
