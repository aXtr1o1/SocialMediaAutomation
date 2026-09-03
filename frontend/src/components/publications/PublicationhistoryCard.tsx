import type { PublicationResponse } from '../../lib/publications'
import { BlueskyIcon } from '../../assets/icons/BlueskyIcon'
import { LinkedInIcon } from '../../assets/icons/LinkedInIcon'
import { MaterialIcon } from '../../components/ui/MaterialIcon'

function getPostHook(fullMessage: string | null) {
  if (!fullMessage) {
    return 'No post content available.'
  }

  const hook = fullMessage
    .split(/\n\s*\n/)
    .map((part) => part.trim())
    .find(Boolean)

  return hook || fullMessage
}

function PlatformIcon({
  platformName,
}: {
  platformName: string
}) {
  if (platformName.toLowerCase() === 'linkedin') {
    return (
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[#0077b5] text-white">
        <LinkedInIcon className="h-6 w-6" />
      </div>
    )
  }

  if (platformName.toLowerCase() === 'bluesky') {
    return (
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[#0085FF] text-white">
        <BlueskyIcon className="h-7 w-7" />
      </div>
    )
  }

  return (
    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-surface-container-high text-primary">
      <MaterialIcon name="public" className="text-[22px]" />
    </div>
  )
}

function StatusBadge({
  status,
}: {
  status: string
}) {
  const isCompleted = status === 'completed'

  return (
    <span
      className={
        isCompleted
          ? 'inline-flex items-center gap-xs rounded-full bg-primary-fixed/20 px-3 py-1 font-label-sm text-label-sm text-on-primary-fixed'
          : 'inline-flex items-center gap-xs rounded-full bg-error-container/30 px-3 py-1 font-label-sm text-label-sm text-error'
      }
    >
      <MaterialIcon
        name={isCompleted ? 'check_circle' : 'cancel'}
        className="text-[16px]"
      />

      {isCompleted ? 'Completed' : 'Failed'}
    </span>
  )
}

type PublicationHistoryCardProps = {
  publication: PublicationResponse
}

export function PublicationHistoryCard({
  publication,
}: PublicationHistoryCardProps) {
  const date = new Date(
    publication.published_at ?? publication.created_at,
  )

  return (
    <article className="group relative overflow-hidden rounded-2xl bg-surface-container-lowest p-lg shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-md">
      <div
        className={
          publication.status_name === 'completed'
            ? 'absolute -right-12 -top-12 h-32 w-32 rounded-full bg-primary/5 blur-2xl'
            : 'absolute -right-12 -top-12 h-32 w-32 rounded-full bg-error/5 blur-2xl'
        }
      />

      <div className="relative flex flex-col gap-lg">
        {/* Header */}
        <div className="flex items-start justify-between gap-md">
          <div className="flex min-w-0 items-center gap-md">
            <PlatformIcon platformName={publication.platform_name} />

            <div className="min-w-0">
              <h2 className="font-headline-sm text-headline-sm text-on-surface">
                {publication.platform_name}
              </h2>

              <p className="font-body-sm text-body-sm text-on-surface-variant">
                Published{' '}
                {date.toLocaleString(undefined, {
                  dateStyle: 'medium',
                  timeStyle: 'short',
                })}
              </p>
            </div>
          </div>

          <StatusBadge status={publication.status_name} />
        </div>

        {/* Post */}
        <div className="rounded-xl bg-surface-container p-md">
          <div className="mb-xs flex items-center gap-xs">
            <MaterialIcon
              name="article"
              className="text-[18px] text-on-surface-variant"
            />

            <span className="font-label-sm text-label-sm text-on-surface-variant">
              Post
            </span>
          </div>

          <p className="line-clamp-3 whitespace-pre-line font-body-md text-body-md text-on-surface">
            {getPostHook(publication.full_message)}
          </p>
        </div>
      </div>
    </article>
  )
}