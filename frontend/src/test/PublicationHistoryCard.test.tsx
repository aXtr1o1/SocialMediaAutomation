import { render, screen } from '@testing-library/react'
import '@testing-library/jest-dom'
import { describe, expect, it } from 'vitest'

import { PublicationHistoryCard } from '../components/publications/PublicationhistoryCard'
import type { PublicationResponse } from '../lib/publications'

function createPublication(
  overrides: Partial<PublicationResponse> = {},
): PublicationResponse {
  return {
    id: '1',
    draft_id: 'draft-1',
    version_id: 'version-1',
    status_id: 'status-1',
    status_name: 'completed',
    user_id: 'user-1',
    platform_id: 'platform-1',
    platform_name: 'linkedin',
    connected_account_id: 'account-1',
    platform_post_id: 'post-1',
    platform_response: 'success',
    error_message: null,
    retry_count: 0,
    created_at: '2026-09-03T10:00:00Z',
    updated_at: '2026-09-03T10:00:00Z',
    published_at: '2026-09-03T11:00:00Z',
    full_message: 'This is the first paragraph.\n\nThis is the second paragraph.',
    ...overrides,
  }
}

describe('PublicationHistoryCard', () => {
  it('shows the platform name', () => {
    render(
      <PublicationHistoryCard
        publication={createPublication({
          platform_name: 'linkedin',
        })}
      />,
    )

    expect(screen.getByText('linkedin')).toBeInTheDocument()
  })

  it('shows Completed for a successful publication', () => {
    render(
      <PublicationHistoryCard
        publication={createPublication({
          status_name: 'completed',
        })}
      />,
    )

    expect(screen.getByText('Completed')).toBeInTheDocument()
  })

  it('shows Failed for a failed publication', () => {
    render(
      <PublicationHistoryCard
        publication={createPublication({
          status_name: 'failed',
          error_message: 'Publishing failed',
        })}
      />,
    )

    expect(screen.getByText('Failed')).toBeInTheDocument()
  })

  it('shows the first paragraph of the post', () => {
    render(
      <PublicationHistoryCard
        publication={createPublication({
          full_message:
            'First paragraph.\n\nSecond paragraph.\n\nThird paragraph.',
        })}
      />,
    )

    expect(screen.getByText('First paragraph.')).toBeInTheDocument()
  })

  it('shows fallback text when post content is unavailable', () => {
    render(
      <PublicationHistoryCard
        publication={createPublication({
          full_message: null,
        })}
      />,
    )

    expect(
      screen.getByText('No post content available.'),
    ).toBeInTheDocument()
  })

  it('uses created_at when published_at is unavailable', () => {
    render(
      <PublicationHistoryCard
        publication={createPublication({
          published_at: null,
        })}
      />,
    )

    expect(screen.getByText(/Published/)).toBeInTheDocument()
  })

  it('renders Bluesky publications', () => {
    render(
      <PublicationHistoryCard
        publication={createPublication({
          platform_name: 'bluesky',
        })}
      />,
    )

    expect(screen.getByText('bluesky')).toBeInTheDocument()
  })
})