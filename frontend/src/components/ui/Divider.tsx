type DividerProps = {
  label: string
}

export function Divider({ label }: DividerProps) {
  return (
    <div className="flex items-center">
      <div className="h-px flex-grow bg-outline-variant" />
      <span className="px-4 text-[12px] uppercase tracking-widest text-on-surface-variant">{label}</span>
      <div className="h-px flex-grow bg-outline-variant" />
    </div>
  )
}
