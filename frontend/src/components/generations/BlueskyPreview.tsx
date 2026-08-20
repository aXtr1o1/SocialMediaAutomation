import type { GeneratedPost } from '../../lib/generations'
import { BlueskyIcon } from '../../assets/icons/BlueskyIcon'

type BlueskyPreviewProps = {
  post: GeneratedPost
  authorName: string
  handle?: string
}

export function BlueskyPreview({ post, authorName, handle }: BlueskyPreviewProps) {
  const skeets = post.posts.length ? post.posts : [{ text: post.full_post, char_count: post.full_post.length }]

  return (
    <div className="mx-auto flex max-w-[552px] flex-col gap-sm">
      {skeets.map((skeet, index) => (
        <div
          key={`${skeet.text.slice(0, 24)}-${index}`}
          className="rounded-xl border border-surface-variant bg-surface p-md shadow-sm"
        >
          <div className="mb-sm flex items-center gap-sm">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-[#0085FF]/10 text-[#0085FF]">
              <BlueskyIcon className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <p className="truncate font-label-md text-label-md text-on-surface">{authorName}</p>
              <p className="truncate text-[12px] text-on-surface-variant">{handle || 'Just now'}</p>
            </div>
          </div>
          <p className="whitespace-pre-wrap font-body-md text-body-md text-on-surface">{skeet.text}</p>
          <p className="mt-sm text-[11px] text-on-surface-variant">{skeet.char_count}/300</p>
        </div>
      ))}
    </div>
  )
}
