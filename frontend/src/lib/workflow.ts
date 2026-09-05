import { apiFetch } from './api'

import type {
  GeneratedPost,
  GenerationDraft,
} from './generations'

import type {
  SourceArticle,
} from './sources'

export type WorkflowSession = {
  user_id: string

  active_workflow_id: string | null

  active_project_id: string | null

  current_workflow: string | null

  current_step: string | null

  selected_source_posts: SourceArticle[]

  /**
   * The article that generated content is currently
   * associated with.
   *
   * This is deliberately separate from
   * selected_source_posts because starting another
   * source search must not destroy the generated
   * article context.
   */
  generated_article: SourceArticle | null

  /**
   * Backend generation job currently running.
   *
   * Used to resume polling after navigation/reload.
   */
  active_generation_id: string | null

  generated_content: GeneratedPost[]

  generation_drafts: GenerationDraft[]

  target_platforms: string[]

  filters: Record<
    string,
    unknown
  >

  draft_changes: Record<
    string,
    unknown
  >

  generation_status: string

  last_activity_at: string
}

export async function getWorkflowSession() {
  return apiFetch<WorkflowSession>(
    '/workflow/session',
  )
}

export async function updateWorkflowSession(
  input: Partial<WorkflowSession>,
) {
  return apiFetch<WorkflowSession>(
    '/workflow/session',
    {
      method: 'PATCH',
      body: JSON.stringify(input),
    },
  )
}

export async function updateWorkflowStep(
  currentStep: string,
  currentWorkflow =
    'content_generation',
) {
  return apiFetch<WorkflowSession>(
    '/workflow/session/step',
    {
      method: 'POST',
      body: JSON.stringify({
        current_step:
          currentStep,
        current_workflow:
          currentWorkflow,
      }),
    },
  )
}

export async function clearWorkflowSession() {
  return apiFetch<{
    message: string
  }>(
    '/workflow/session',
    {
      method: 'DELETE',
    },
  )
}