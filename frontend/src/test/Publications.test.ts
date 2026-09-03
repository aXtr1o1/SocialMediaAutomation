import { describe, expect, it, vi, beforeEach } from 'vitest'

import {
  publishPost,
  publishMultiplePosts,
  getPublication,
} from '../lib/publications'

import { apiFetch } from '../lib/api'

vi.mock('../lib/api', () => ({
  apiFetch: vi.fn(),
}))

const mockedApiFetch = vi.mocked(apiFetch)

describe('publication API functions', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('publishes a post', async () => {
    const publication = {
      draft_id: 'draft-1',
      connected_account_id: 'account-1',
    }

    const response = {
      id: 'publication-1',
      status_name: 'completed',
    }

    mockedApiFetch.mockResolvedValue(response as never)

    const result = await publishPost(publication)

    expect(result).toBe(response)

    expect(mockedApiFetch).toHaveBeenCalledWith(
      '/publications',
      {
        method: 'POST',
        body: JSON.stringify(publication),
      },
    )
  })

  it('publishes multiple posts', async () => {
    const publications = [
      {
        draft_id: 'draft-1',
        connected_account_id: 'account-1',
      },
      {
        draft_id: 'draft-2',
        connected_account_id: 'account-2',
      },
    ]

    const response = {
      publications: [],
    }

    mockedApiFetch.mockResolvedValue(response as never)

    const result = await publishMultiplePosts(publications)

    expect(result).toBe(response)

    expect(mockedApiFetch).toHaveBeenCalledWith(
      '/publications/multiple',
      {
        method: 'POST',
        body: JSON.stringify(publications),
      },
    )
  })

  it('gets publication history', async () => {
    const response = {
      publications: [],
    }

    mockedApiFetch.mockResolvedValue(response as never)

    const result = await getPublication()

    expect(result).toBe(response)

    expect(mockedApiFetch).toHaveBeenCalledWith(
      '/publications',
      {
        method: 'GET',
      },
    )
  })
})