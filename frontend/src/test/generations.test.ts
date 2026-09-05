import { afterEach, describe, expect, it, vi } from 'vitest'

const { apiFetch } = vi.hoisted(() => ({
  apiFetch: vi.fn(),
}))

vi.mock('../lib/api', () => ({
  apiFetch,
}))

import {
  cancelGeneration,
  generatePosts,
  saveGenerationDraft,
} from '../lib/generations'

afterEach(() => {
  apiFetch.mockReset()
  vi.restoreAllMocks()
})

describe('generation job functions', () => {
  it('creates a job, polls until completion, and reports progress', async () => {
    vi.stubGlobal('window', {
      setTimeout: (fn: () => void) => {
        fn()
      },
    })

    apiFetch
      .mockResolvedValueOnce({
        generation_id: 'g1',
        article_id: 'a1',
        status: 'QUEUED',
        posts: [],
        drafts: [],
      })
      .mockResolvedValueOnce({
        generation_id: 'g1',
        article_id: 'a1',
        status: 'COMPLETED',
        posts: [
          {
            platform: 'linkedin',
            full_post: 'x',
          },
        ],
        drafts: [],
      })

    const progress: string[] = []

    const result = await generatePosts(
      'a1',
      ['linkedin'],
      (job) => progress.push(job.status),
    )

    expect(progress).toEqual(['QUEUED', 'COMPLETED'])
    expect(result.generation_id).toBe('g1')
    expect(apiFetch).toHaveBeenCalledTimes(2)
  })

  it('throws when the job fails', async () => {
    vi.stubGlobal('window', {
      setTimeout: (fn: () => void) => {
        fn()
      },
    })

    apiFetch
      .mockResolvedValueOnce({
        generation_id: 'g1',
        article_id: 'a1',
        status: 'QUEUED',
        posts: [],
        drafts: [],
      })
      .mockResolvedValueOnce({
        generation_id: 'g1',
        article_id: 'a1',
        status: 'FAILED',
        posts: [],
        drafts: [],
        error: 'boom',
      })

    await expect(
      generatePosts('a1', ['linkedin']),
    ).rejects.toThrow('boom')
  })

  it('throws the dedicated stopped message for cancelled jobs', async () => {
    vi.stubGlobal('window', {
      setTimeout: (fn: () => void) => {
        fn()
      },
    })

    apiFetch
      .mockResolvedValueOnce({
        generation_id: 'g1',
        article_id: 'a1',
        status: 'QUEUED',
        posts: [],
        drafts: [],
      })
      .mockResolvedValueOnce({
        generation_id: 'g1',
        article_id: 'a1',
        status: 'CANCELLED',
        posts: [],
        drafts: [],
      })

    await expect(
      generatePosts('a1', ['linkedin']),
    ).rejects.toThrow('Generation was stopped.')
  })

  it('cancels a generation job', async () => {
    apiFetch.mockResolvedValue({
      generation_id: 'g1',
      article_id: 'a1',
      status: 'CANCELLED',
      posts: [],
      drafts: [],
    })

    await cancelGeneration('g1')

    expect(apiFetch).toHaveBeenCalledWith(
      '/generations/jobs/g1/cancel',
      {
        method: 'POST',
      },
    )
  })

  it('saves a restored draft', async () => {
    apiFetch.mockResolvedValue({
      id: 'd1',
      versions: [],
      current_version_id: null,
      article_id: 'a1',
    })

    await saveGenerationDraft('d1', 'edited post')

    expect(apiFetch).toHaveBeenCalledWith(
      '/generations/drafts/d1/save',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          full_post: 'edited post',
          label: 'User Draft',
          source: 'restore',
        }),
      }),
    )
  })
})