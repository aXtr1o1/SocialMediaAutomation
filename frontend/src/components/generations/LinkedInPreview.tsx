import { formatHashtag, type GeneratedPost } from '../../lib/generations'
import { MaterialIcon } from '../ui/MaterialIcon'

type LinkedInPreviewProps = {
  post: GeneratedPost
  authorName: string
  authorSubtitle?: string
}

export function LinkedInPreview({ post, authorName, authorSubtitle }: LinkedInPreviewProps) {
  const paragraphs = [post.hook, ...post.body_paragraphs].filter(Boolean)
  const hashtags = post.hashtags.map(formatHashtag).filter(Boolean)

  return (
    <div className="mx-auto max-w-[552px] overflow-hidden rounded-xl bg-surface shadow-md">
      <div className="flex items-start gap-3 p-md">
        <div className="min-w-0 flex-1">
          <div className="flex items-center justify-between">
            <span className="truncate font-label-md text-label-md text-on-surface">{authorName}</span>
            <MaterialIcon name="more_horiz" className="text-[14px] text-on-surface-variant" />
          </div>
          {authorSubtitle ? (
            <div className="truncate text-[12px] text-on-surface-variant">{authorSubtitle}</div>
          ) : null}
          <div className="mt-0.5 flex items-center gap-1 text-[10px] text-on-surface-variant">
            <span>Just now</span>
            <span>•</span>
            <MaterialIcon name="public" className="text-[12px]" />
          </div>
        </div>
      </div>

      <div className="space-y-4 px-md pb-md font-body-md text-body-md text-on-surface">
        {paragraphs.length ? (
          paragraphs.map((paragraph, index) => <p key={`${index}-${paragraph.slice(0, 24)}`}>{paragraph}</p>)
        ) : (
          <p className="whitespace-pre-wrap">{post.full_post}</p>
        )}

        {post.key_points.length ? (
          <p>
            {post.key_points.map((point, index) => (
              <span key={point.slice(0, 32)}>
                {index + 1}️⃣ {point}
                {index < post.key_points.length - 1 ? <br /> : null}
              </span>
            ))}
          </p>
        ) : null}

        {post.closing_cta ? <p>{post.closing_cta}</p> : null}

        {hashtags.length ? <p className="font-medium text-primary">{hashtags.join(' ')}</p> : null}
      </div>

      <div className="flex items-center justify-between border-t border-surface-variant bg-surface-container-lowest px-md py-sm text-on-surface-variant">
        <div className="flex gap-4">
          <span className="flex items-center gap-1.5 rounded-md px-2 py-1 text-[12px] font-medium">
            <MaterialIcon name="thumb_up" className="text-[18px]" /> Like
          </span>
          <span className="flex items-center gap-1.5 rounded-md px-2 py-1 text-[12px] font-medium">
            <MaterialIcon name="chat_bubble" className="text-[18px]" /> Comment
          </span>
          <span className="flex items-center gap-1.5 rounded-md px-2 py-1 text-[12px] font-medium">
            <MaterialIcon name="sync" className="text-[18px]" /> Repost
          </span>
        </div>
        <span className="flex items-center gap-1.5 rounded-md px-2 py-1 text-[12px] font-medium">
          <MaterialIcon name="send" className="text-[18px]" /> Send
        </span>
      </div>
    </div>
  )
}
