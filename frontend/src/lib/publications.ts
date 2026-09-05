import { apiFetch } from './api'

export type PublicationCreate = {
  draft_id: string
  connected_account_id: string
}

export type PublicationResponse = {
  id: string
  draft_id: string
  version_id: string
  status_id: string
  status_name: string
  user_id: string
  platform_id: string
  platform_name: string
  connected_account_id: string
  platform_post_id: string | null
  platform_response: string | null
  error_message: string | null
  retry_count: number
  created_at: string
  updated_at: string
  published_at: string | null
  full_message: string | null
}

export type PublicationEventResponse = {
  id: string
  publication_id: string
  event_type: string | null
  event_status: string | null
  created_at: string
  updated_at: string
  message: string | null
}

export type PublicationDetailResponse = PublicationResponse & {
  events: PublicationEventResponse[]
}

export type PublicationListResponse = {
  publications: PublicationResponse[]
}

export async function publishPost(
  publication: PublicationCreate,
): Promise<PublicationResponse> {
  return apiFetch<PublicationResponse>('/publications', {
    method: 'POST',
    body: JSON.stringify(publication),
  })
}

export async function publishMultiplePosts(
  publications: PublicationCreate[],
): Promise<PublicationListResponse> {
  return apiFetch<PublicationListResponse>('/publications/multiple', {
    method: 'POST',
    body: JSON.stringify(publications),
  })
}

export async function getPublication(): Promise<PublicationListResponse> {
  return apiFetch<PublicationListResponse>('/publications', {method: 'GET'})
}