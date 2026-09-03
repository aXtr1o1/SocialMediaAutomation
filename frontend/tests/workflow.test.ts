import { describe, expect, it, vi } from 'vitest'

const { apiFetch } = vi.hoisted(() => ({ apiFetch: vi.fn() }))
vi.mock('../src/lib/api', () => ({ apiFetch }))

import { clearWorkflowSession, getWorkflowSession, updateWorkflowSession, updateWorkflowStep } from '../src/lib/workflow'

describe('workflow session functions', () => {
  it('gets the workflow session', async () => {
    apiFetch.mockResolvedValue({ user_id: 'u1' })
    await getWorkflowSession()
    expect(apiFetch).toHaveBeenCalledWith('/workflow/session')
  })

  it('updates workflow session', async () => {
    apiFetch.mockResolvedValue({ user_id: 'u1', current_step: 'generate' })
    await updateWorkflowSession({ current_step: 'generate' })
    expect(apiFetch).toHaveBeenCalledWith('/workflow/session', expect.objectContaining({ method: 'PATCH' }))
  })

  it('updates workflow step and workflow name', async () => {
    apiFetch.mockResolvedValue({ user_id: 'u1', current_step: 'review' })
    await updateWorkflowStep('review', 'content_generation')
    expect(apiFetch).toHaveBeenCalledWith('/workflow/session/step', expect.objectContaining({
      method: 'POST',
      body: JSON.stringify({ current_step: 'review', current_workflow: 'content_generation' }),
    }))
  })

  it('clears workflow session', async () => {
    apiFetch.mockResolvedValue({ message: 'Workflow session cleared' })
    await clearWorkflowSession()
    expect(apiFetch).toHaveBeenCalledWith('/workflow/session', { method: 'DELETE' })
  })
})
