import { apiFetch } from './api'

export type SourcesSelection = {
  domainId: string
  subdomainIds: string[]
  domainName: string
  subdomainNames?: string[]
  runId: string
}

export type SourceArticle = {
  id: string
  article_id: string
  title: string
  author: string | null
  published_at: string | null
  subdomain_name: string | null
  content: string
  source_url: string | null
}

export type WorkflowProgress = {
  stage: string
  message: string
  crawled: number
  kpi_passed: number
  match_passed: number
  sources_done: number
  sources_total: number
}

export type WorkflowRunResponse = {
  workflow_run_id: string | null
  job_status: string
  domain_name: string
  articles: SourceArticle[]
  progress?: WorkflowProgress | null
}

const SOURCES_SELECTION_KEY = 'smap.sources.selection'
const workflowRuns = new Map<string, Promise<WorkflowRunResponse>>()
const workflowResults = new Map<string, WorkflowRunResponse>()
let rememberedSelection: SourcesSelection | null = null

export function isSourcesSelection(value: unknown): value is SourcesSelection {
  if (!value || typeof value !== 'object') {
    return false
  }

  const row = value as SourcesSelection
  return Boolean(row.domainId && row.runId && Array.isArray(row.subdomainIds) && row.subdomainIds.length)
}

export function rememberSourcesSelection(selection: SourcesSelection) {
  rememberedSelection = selection

  try {
    sessionStorage.setItem(SOURCES_SELECTION_KEY, JSON.stringify(selection))
  } catch {
    // Ignore storage failures (private mode, blocked cookies).
  }
}

export function getRememberedSourcesSelection() {
  if (rememberedSelection) {
    return rememberedSelection
  }

  try {
    const raw = sessionStorage.getItem(SOURCES_SELECTION_KEY)
    const parsed = raw ? JSON.parse(raw) : null

    if (isSourcesSelection(parsed)) {
      rememberedSelection = parsed
      return parsed
    }
  } catch {
    // Ignore storage failures.
  }

  return null
}

export function getCachedWorkflow(runId: string) {
  return workflowResults.get(runId) ?? null
}

function isTerminalStatus(status: string) {
  return status === 'COMPLETED' || status === 'FAILED' || status === 'PARTIAL'
}

export async function getWorkflowRun(workflowRunId: string) {
  return apiFetch<WorkflowRunResponse>(`/processing/run/${workflowRunId}`)
}

export function runSourcesWorkflow(
  selection: SourcesSelection,
  onProgress?: (result: WorkflowRunResponse) => void,
) {
  rememberSourcesSelection(selection)

  const existing = workflowRuns.get(selection.runId)
  if (existing) {
    return existing
  }

  const request = apiFetch<WorkflowRunResponse>('/processing/run', {
    method: 'POST',
    body: JSON.stringify({
      domain_id: selection.domainId,
      subdomain_ids: selection.subdomainIds,
    }),
  })
    .then(async (started) => {
      onProgress?.(started)
      const workflowRunId = started.workflow_run_id
      if (!workflowRunId || isTerminalStatus(started.job_status)) {
        workflowResults.set(selection.runId, started)
        return started
      }

      let misses = 0
      for (;;) {
        await new Promise((resolve) => window.setTimeout(resolve, 1500))
        try {
          const latest = await getWorkflowRun(workflowRunId)
          misses = 0
          onProgress?.(latest)
          if (isTerminalStatus(latest.job_status)) {
            workflowResults.set(selection.runId, latest)
            return latest
          }
        } catch (error) {
          misses += 1
          if (misses >= 8) {
            throw error
          }
        }
      }
    })
    .catch((error) => {
      workflowRuns.delete(selection.runId)
      throw error
    })

  workflowRuns.set(selection.runId, request)
  return request
}

export function formatPublishedAt(value?: string | null) {
  if (!value) {
    return null
  }

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return null
  }

  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

export function splitContentParagraphs(content: string) {
  const blocks = content
    .split(/\n+/)
    .map((block) => block.trim())
    .filter(Boolean)

  return blocks.length ? blocks : []
}
