import { useEffect, useState, type ReactNode } from 'react'

import { usePostVersions } from '../../hooks/usePostVersions'
import { useRegeneratePost } from '../../hooks/useRegeneratePost'
import {
  applyFullPost,
  type GeneratedPost,
  type GenerationDraft,
} from '../../lib/generations'
import { BlueskyPreview } from './BlueskyPreview'
import { LinkedInPreview } from './LinkedInPreview'
import { RegeneratePanel } from './RegeneratePanel'
import { VersionHistory } from './VersionHistory'
import { MaterialIcon } from '../ui/MaterialIcon'

type PlatformReviewCardProps = {
  post: GeneratedPost
  draft?: GenerationDraft | null
  articleId?: string
  authorName: string
  authorSubtitle: string
  onPostChange: (post: GeneratedPost) => void
  header?: ReactNode
}

export function PlatformReviewCard({
  post,
  draft,
  articleId,
  authorName,
  authorSubtitle,
  onPostChange,
  header,
}: PlatformReviewCardProps) {
  const [workingPost, setWorkingPost] = useState(post)
  const {
    draftId,
    versions,
    current,
    currentId,
    appendVersion,
    selectVersion,
    deleteVersion,
    ingestServerVersion,
    syncFromDraft,
  } = usePostVersions(post.full_post, draft)

  useEffect(() => {
    if (!current) {
      return
    }
    const next = applyFullPost(post, current.full_post)
    setWorkingPost(next)
    onPostChange(next)
    // Sync preview when the selected version changes only.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [current?.id])

  const regenerate = useRegeneratePost({
    platform: workingPost.platform,
    fullPost: workingPost.full_post,
    articleId,
    draftId,
    onSuccess: (result, instruction) => {
      if (result.draft) {
        syncFromDraft(result.draft)
        return
      }

      if (result.version) {
        ingestServerVersion(
          {
            id: result.version.id,
            version: result.version.version,
            full_post: result.version.full_post || result.full_post,
            label: result.version.label || instruction || 'Section update',
            source: result.version.source || 'regenerate',
            createdAt: result.version.createdAt || new Date().toISOString(),
            meta: result.version.meta || {
              target_text: result.target_text,
              instruction,
              replacement_text: result.replacement_text,
            },
          },
          result.draft_id,
        )
        return
      }

      void appendVersion({
        full_post: result.full_post,
        label: instruction || 'Section update',
        source: 'regenerate',
        meta: {
          target_text: result.target_text,
          instruction,
          replacement_text: result.replacement_text,
        },
      })
    },
  })

  const title = workingPost.platform === 'linkedin' ? 'LinkedIn Preview' : 'Bluesky Preview'

  return (
    <div className="grid gap-lg lg:grid-cols-[240px_minmax(0,1fr)]">
      <VersionHistory
        versions={versions}
        currentId={currentId}
        onSelect={(id) => {
          void selectVersion(id)
        }}
        onDelete={(id) => {
          void deleteVersion(id)
        }}
      />

      <div className="rounded-2xl bg-surface-container-lowest p-lg shadow-sm">
        <div className="mb-lg flex items-center justify-between gap-4 border-b border-surface-variant pb-md">
          <div className="min-w-0">
            {header ?? <div className="font-label-md text-label-md text-on-surface">{title}</div>}
          </div>
          <div className="flex shrink-0 items-center gap-2 text-on-surface-variant">
            <MaterialIcon name="visibility" className="text-[18px]" />
            <span className="font-body-md text-body-md">Preview</span>
          </div>
        </div>

        <div className="grid gap-lg lg:grid-cols-[minmax(0,1.1fr)_minmax(280px,0.95fr)]">
          <div className="min-w-0">
            {workingPost.platform === 'linkedin' ? (
              <LinkedInPreview post={workingPost} authorName={authorName} authorSubtitle={authorSubtitle} />
            ) : (
              <BlueskyPreview post={workingPost} authorName={authorName} handle={authorSubtitle} />
            )}
          </div>

          <div className="min-w-0">
            <RegeneratePanel
              targetText={regenerate.targetText}
              instruction={regenerate.instruction}
              error={regenerate.error}
              isSubmitting={regenerate.isSubmitting}
              onTargetTextChange={regenerate.setTargetText}
              onInstructionChange={regenerate.setInstruction}
              onSubmit={() => {
                void regenerate.submit()
              }}
            />
          </div>
        </div>
      </div>
    </div>
  )
}
