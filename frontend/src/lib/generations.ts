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

export type ReviewState = {
  article: SourceArticle
  posts: GeneratedPost[]
  sourcesSelection?: SourcesSelection
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

export function generatePosts(articleId: string, platforms: GeneratePlatform[]) {
  return apiFetch<{ article_id: string; posts: GeneratedPost[] }>('/generations', {
    method: 'POST',
    body: JSON.stringify({
      article_id: articleId,
      platforms,
    }),
  })
}

export function formatHashtag(tag: string) {
  const value = tag.trim().replace(/^#/, '')
  return value ? `#${value}` : ''
}
