import { render, screen } from '@testing-library/react'
import '@testing-library/jest-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { PublicationHistoryPage } from '../pages/app/PublicationHistoryPage'
import { getPublication } from '../lib/publications'

vi.mock('../lib/publications', () => ({
  getPublication: vi.fn(),
}))

const mockedGetPublication = vi.mocked(getPublication)

describe('PublicationHistoryPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows loading state while publications are loading', () => {
    mockedGetPublication.mockImplementation(
      () => new Promise(() => {}),
    )

    render(<PublicationHistoryPage />)

    expect(
      screen.getByText('Loading publication history...'),
    ).toBeInTheDocument()
  })

  it('shows publication history after loading', async () => {
    mockedGetPublication.mockResolvedValue({
      publications: [
        {
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
          full_message: 'Test published post',
        },
      ],
    })

    render(<PublicationHistoryPage />)

    expect(
      await screen.findByText('Test published post'),
    ).toBeInTheDocument()

    expect(screen.getByText('Completed')).toBeInTheDocument()
  })

  it('shows empty state when there are no publications', async () => {
    mockedGetPublication.mockResolvedValue({
      publications: [],
    })

    render(<PublicationHistoryPage />)

    expect(
      await screen.findByText('No publication history yet'),
    ).toBeInTheDocument()
  })

  it('shows an error when loading publications fails', async () => {
    mockedGetPublication.mockRejectedValue(
      new Error('Failed to load publications'),
    )

    render(<PublicationHistoryPage />)

    expect(
      await screen.findByText('Failed to load publications'),
    ).toBeInTheDocument()
  })
})