import { apiFetch } from './api'
import type { SourceArticle, SourcesSelection } from './sources'

export type GeneratePlatform = 'linkedin' | 'bluesky'
export type PlatformChoice = GeneratePlatform | 'both'

export type GeneratedPost = {
  platform: GeneratePlatform
  hook: string
  body_paragraphs: string[]
  key_points: string[]
  closing_cta: string
  hashtags: string[]
  article_summary: string
  related_insights: { title: string; url?: string | null }[]
  posts: { text: string; char_count: number }[]
  full_post: string
}

export type ComposeState = {
  article: SourceArticle
  sourcesSelection?: SourcesSelection
}

export type PostVersionSource = 'generate' | 'regenerate' | 'restore'

export type PostVersion = {
  id: string
  version: number
  full_post: string
  createdAt: string
  label: string
  source: PostVersionSource
  meta?: {
    target_text?: string | null
    instruction?: string | null
    replacement_text?: string | null
  }
}

export type GenerationDraft = {
  id: string
  article_id: string
  platform: GeneratePlatform
  current_version_id: string
  versions: PostVersion[]
}

export type ReviewState = {
  article: SourceArticle
  posts: GeneratedPost[]
  drafts?: GenerationDraft[]
  sourcesSelection?: SourcesSelection
}

export type RegenerateSnippetResponse = {
  platform: GeneratePlatform
  original_full_post: string
  target_text: string
  replacement_text: string
  full_post: string
  occurrences: number
  draft_id?: string | null
  version?: PostVersion | null
  draft?: GenerationDraft | null
}

type ApiVersion = {
  id: string
  version: number
  full_post: string
  label: string
  source: PostVersionSource
  created_at?: string
  meta?: PostVersion['meta']
}

type ApiDraft = {
  id: string
  article_id: string
  platform: GeneratePlatform
  current_version_id: string
  versions: ApiVersion[]
}

function mapVersion(row: ApiVersion): PostVersion {
  return {
    id: row.id,
    version: row.version,
    full_post: row.full_post,
    label: row.label,
    source: row.source,
    createdAt: row.created_at || new Date().toISOString(),
    meta: row.meta,
  }
}

export function mapDraft(row: ApiDraft): GenerationDraft {
  return {
    id: row.id,
    article_id: row.article_id,
    platform: row.platform,
    current_version_id: row.current_version_id,
    versions: (row.versions || []).map(mapVersion),
  }
}

export function isComposeState(value: unknown): value is ComposeState {
  if (!value || typeof value !== 'object') {
    return false
  }

  const article = (value as ComposeState).article
  return Boolean(article?.id && (article.article_id || article.content))
}

export function isReviewState(value: unknown): value is ReviewState {
  if (!isComposeState(value) || typeof value !== 'object') {
    return false
  }

  return Array.isArray((value as ReviewState).posts)
}

export function platformsFromChoice(choice: PlatformChoice): GeneratePlatform[] {
  return choice === 'both' ? ['linkedin', 'bluesky'] : [choice]
}

export async function generatePosts(articleId: string, platforms: GeneratePlatform[]) {
  const result = await apiFetch<{
    article_id: string
    posts: GeneratedPost[]
    drafts?: ApiDraft[]
  }>('/generations', {
    method: 'POST',
    body: JSON.stringify({
      article_id: articleId,
      platforms,
    }),
  })

  return {
    article_id: result.article_id,
    posts: result.posts,
    drafts: (result.drafts || []).map(mapDraft),
  }
}

export async function regenerateSnippet(input: {
  platform: GeneratePlatform
  full_post: string
  target_text: string
  instruction: string
  article_id?: string
  draft_id?: string
  label?: string
}) {
  const result = await apiFetch<{
    platform: GeneratePlatform
    original_full_post: string
    target_text: string
    replacement_text: string
    full_post: string
    occurrences: number
    draft_id?: string | null
    version?: ApiVersion | null
    draft?: ApiDraft | null
  }>('/generations/regenerate', {
    method: 'POST',
    body: JSON.stringify(input),
  })

  return {
    platform: result.platform,
    original_full_post: result.original_full_post,
    target_text: result.target_text,
    replacement_text: result.replacement_text,
    full_post: result.full_post,
    occurrences: result.occurrences,
    draft_id: result.draft_id,
    version: result.version ? mapVersion(result.version) : null,
    draft: result.draft ? mapDraft(result.draft) : null,
  } satisfies RegenerateSnippetResponse
}

export async function getGenerationDraft(draftId: string) {
  const draft = await apiFetch<ApiDraft>(`/generations/drafts/${draftId}`)
  return mapDraft(draft)
}

export async function addGenerationVersion(
  draftId: string,
  input: {
    full_post: string
    label: string
    source: PostVersionSource
    target_text?: string
    instruction?: string
    replacement_text?: string
  },
) {
  const draft = await apiFetch<ApiDraft>(`/generations/drafts/${draftId}/versions`, {
    method: 'POST',
    body: JSON.stringify(input),
  })
  return mapDraft(draft)
}

export async function setGenerationCurrentVersion(draftId: string, versionId: string) {
  const draft = await apiFetch<ApiDraft>(`/generations/drafts/${draftId}/current`, {
    method: 'POST',
    body: JSON.stringify({ version_id: versionId }),
  })
  return mapDraft(draft)
}

export async function deleteGenerationVersion(draftId: string, versionId: string) {
  const draft = await apiFetch<ApiDraft>(`/generations/drafts/${draftId}/versions/${versionId}`, {
    method: 'DELETE',
  })
  return mapDraft(draft)
}

/** After snippet regen, full_post is the source of truth for preview. */
export function applyFullPost(post: GeneratedPost, fullPost: string): GeneratedPost {
  if (post.platform === 'bluesky') {
    const text = fullPost.slice(0, 300)
    return {
      ...post,
      full_post: fullPost,
      posts: [{ text, char_count: text.length }],
      hook: '',
      body_paragraphs: [],
      key_points: [],
      closing_cta: '',
    }
  }

  return {
    ...post,
    full_post: fullPost,
    hook: '',
    body_paragraphs: [fullPost],
    key_points: [],
    closing_cta: '',
    hashtags: [],
  }
}

export function countOccurrences(haystack: string, needle: string) {
  return findFlexibleMatches(haystack, needle).length
}

/** Match pasted text even when spaces/newlines differ from the stored post. */
export function findFlexibleMatches(haystack: string, needle: string): { start: number; end: number }[] {
  const post = canonicalizeCopyText(haystack)
  const target = canonicalizeCopyText(needle).trim()
  if (!target) {
    return []
  }
  const parts = target.split(/\s+/).filter(Boolean)
  if (!parts.length) {
    return []
  }
  const pattern = parts.map(escapeRegExp).join('\\s+')
  const re = new RegExp(pattern, 'g')
  const matches: { start: number; end: number }[] = []
  let match: RegExpExecArray | null
  while ((match = re.exec(post)) !== null) {
    matches.push({ start: match.index, end: match.index + match[0].length })
    if (match[0].length === 0) {
      re.lastIndex += 1
    }
  }
  return matches
}

function canonicalizeCopyText(value: string) {
  return value
    .replace(/\r\n/g, '\n')
    .replace(/\r/g, '\n')
    .replace(/[\u00a0\u2000-\u200b\u202f\ufeff]/g, ' ')
}

function escapeRegExp(value: string) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

export function formatHashtag(tag: string) {
  const value = tag.trim().replace(/^#/, '')
  return value ? `#${value}` : ''
}
