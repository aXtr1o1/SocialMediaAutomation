import { useEffect, useState } from 'react'
import {
  getPublication,
  type PublicationResponse,
} from '../../lib/publications'
import { MaterialIcon } from '../../components/ui/MaterialIcon'
import { PublicationHistoryCard } from '../../components/publications/PublicationhistoryCard'


export function PublicationHistoryPage() {
  const [publications, setPublications] = useState<PublicationResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)


  useEffect(() => {
    const loadPublications = async () => {
      try {
        setLoading(true)
        setError(null)

        const response = await getPublication()

        setPublications(response.publications)
      } catch (caught) {
        setError(
          caught instanceof Error
            ? caught.message
            : 'Failed to load publication history',
        )
      } finally {
        setLoading(false)
      }
    }

    void loadPublications()
  }, [])

  const isLoading = loading

  if (isLoading) {
    return (
      <div className="flex w-full flex-col px-lg py-xl">
        <div className="mb-lg">
          <h1 className="font-display-lg text-display-lg text-on-surface">
            Publication History
          </h1>

          <p className="mt-xs font-body-md text-body-md text-on-surface-variant">
            View your published posts and their publication status.
          </p>
        </div>

        <div className="flex min-h-[40vh] w-full items-center justify-center">
          <div className="flex items-center gap-sm text-on-surface-variant">
            <MaterialIcon
              name="progress_activity"
              className="animate-spin text-[22px]"
            />

            <span className="font-body-md text-body-md">
              Loading publication history...
            </span>
          </div>
        </div>
      </div>
    )
  }

  if (error ) {
    const message = error

    return (
      <div className="flex w-full flex-col px-lg py-xl">
        <div className="mb-lg">
          <h1 className="font-display-lg text-display-lg text-on-surface">
            Publication History
          </h1>

          <p className="mt-xs font-body-md text-body-md text-on-surface-variant">
            View your published posts and their publication status.
          </p>
        </div>

        <div className="flex items-start gap-sm rounded-xl border border-error/30 bg-error-container/20 px-md py-sm">
          <MaterialIcon
            name="error_outline"
            className="mt-0.5 shrink-0 text-[18px] text-error"
          />

          <p className="font-body-sm text-body-sm text-on-surface-variant">
            {message}
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex w-full flex-col px-lg py-xl">
      {/* Header */}
      <div className="mb-lg">
        <h1 className="font-display-lg text-display-lg text-on-surface">
          Publication History
        </h1>

        <p className="mt-xs max-w-2xl font-body-md text-body-md text-on-surface-variant">
          View the posts you have published and the result of each publication.
        </p>
      </div>

      {/* Empty state */}
      {publications.length === 0 ? (
        <div className="flex min-h-[55vh] w-full flex-col items-center justify-center">
          <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-surface-container">
            <MaterialIcon
              name="history"
              className="text-[30px] text-primary"
            />
          </div>

          <h2 className="mt-lg font-headline-sm text-headline-sm text-on-surface">
            No publication history yet
          </h2>

          <p className="mt-xs max-w-md text-center font-body-md text-body-md text-on-surface-variant">
            Posts you successfully publish or fail to publish will appear here.
          </p>
        </div>
      ) : (
        <div className="flex flex-col gap-md">
          {publications.map((publication) => (
            <PublicationHistoryCard
              key={publication.id}
              publication={publication}
            />
          ))}
        </div>
      )}
    </div>
  )
}