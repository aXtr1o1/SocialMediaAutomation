import { Link, useLocation, useNavigate } from 'react-router-dom'
import { BlueskyPreview } from '../../components/generations/BlueskyPreview'
import { LinkedInPreview } from '../../components/generations/LinkedInPreview'
import { MaterialIcon } from '../../components/ui/MaterialIcon'
import { useAuth } from '../../context/AuthContext'
import { isReviewState } from '../../lib/generations'
import { paths } from '../../lib/paths'
import { getRememberedSourcesSelection } from '../../lib/sources'
import { getUserDisplayName } from '../../lib/user'

export function ReviewGenerationsPage() {
  const location = useLocation()
  const navigate = useNavigate()
  const { session } = useAuth()
  const review = isReviewState(location.state) ? location.state : null
  const authorName = session?.user ? getUserDisplayName(session.user) : 'You'
  const authorSubtitle = session?.user?.email ?? ''

  function goBackToSources() {
    navigate(paths.sources, {
      state: review?.sourcesSelection ?? getRememberedSourcesSelection() ?? undefined,
    })
  }

  if (!review) {
    return (
      <div className="mx-auto flex w-full max-w-5xl flex-col gap-lg p-lg lg:p-xl">
        <h1 className="font-headline-md text-headline-md text-on-surface">Review Generations</h1>
        <p className="font-body-md text-body-md text-on-surface-variant">
          Generate a post from a source article to review it here.
        </p>
        <Link className="font-body-md text-primary underline" to={paths.discover}>
          Back to Discover
        </Link>
      </div>
    )
  }

  const linkedInPost = review.posts.find((item) => item.platform === 'linkedin')
  const blueskyPost = review.posts.find((item) => item.platform === 'bluesky')

  return (
    <div className="relative flex w-full flex-col pb-24">
      <div className="flex flex-col items-start justify-between gap-md px-xl py-lg md:flex-row md:items-center">
        <div className="flex flex-col gap-xs">
          <button
            type="button"
            onClick={goBackToSources}
            className="mb-xs inline-flex items-center gap-xs text-on-surface-variant transition-colors hover:text-on-surface"
          >
            <MaterialIcon name="arrow_back" className="text-[18px]" />
            <span className="font-label-md text-label-md">Back</span>
          </button>
          <h1 className="font-headline-md text-headline-md text-on-surface">Review Generations</h1>
          <p className="max-w-2xl font-body-md text-body-md text-on-surface-variant">
            Review and refine the generated content before publishing.
          </p>
        </div>
      </div>

      <div className="flex flex-col gap-xl px-xl pb-xl">
        {linkedInPost ? (
          <div className="rounded-2xl bg-surface-container-lowest p-lg shadow-sm">
            <div className="mb-lg flex items-center justify-between gap-4 border-b border-surface-variant pb-md">
              <div className="font-label-md text-label-md text-on-surface">LinkedIn Preview</div>
              <div className="flex items-center gap-2 text-on-surface-variant">
                <MaterialIcon name="visibility" className="text-[18px]" />
                <span className="font-body-md text-body-md">Preview</span>
              </div>
            </div>
            <LinkedInPreview
              post={linkedInPost}
              authorName={authorName}
              authorSubtitle={authorSubtitle}
            />
          </div>
        ) : null}

        {blueskyPost ? (
          <div className="rounded-2xl bg-surface-container-lowest p-lg shadow-sm">
            <div className="mb-lg flex items-center justify-between gap-4 border-b border-surface-variant pb-md">
              <div className="font-label-md text-label-md text-on-surface">Bluesky Preview</div>
              <div className="flex items-center gap-2 text-on-surface-variant">
                <MaterialIcon name="visibility" className="text-[18px]" />
                <span className="font-body-md text-body-md">Preview</span>
              </div>
            </div>
            <BlueskyPreview post={blueskyPost} authorName={authorName} handle={authorSubtitle} />
          </div>
        ) : null}
      </div>

      <div className="fixed bottom-0 left-64 right-0 z-40 flex items-center justify-end border-t border-surface-variant bg-surface/80 p-4 backdrop-blur-xl">
        <button
          type="button"
          className="flex h-12 items-center justify-center rounded-full bg-primary px-xl font-semibold text-on-primary shadow-md shadow-primary/20 transition-colors hover:bg-primary/90"
        >
          <span className="font-label-md text-label-md">Approve & Continue</span>
          <MaterialIcon name="arrow_forward" className="ml-2 text-[20px]" />
        </button>
      </div>
    </div>
  )
}
