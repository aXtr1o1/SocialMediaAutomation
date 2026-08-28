type PlaceholderPageProps = {
  title: string
  description: string
}

export function PlaceholderPage({ title, description }: PlaceholderPageProps) {
  return (
    <div className="w-full px-lg py-xl">
      <h1 className="mb-xs font-display-lg text-display-lg text-on-surface">{title}</h1>
      <p className="max-w-2xl font-body-md text-body-md text-on-surface-variant">{description}</p>
    </div>
  )
}
