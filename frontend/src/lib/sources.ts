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
  activity?: string
  current_site?: string
  activity_log?: string[]
  crawled: number
  kpi_passed: number
  match_passed: number
  sources_done: number
  sources_total: number
  checked?: number
  pages_seen?: number
}

export type WorkflowRunResponse = {
  workflow_run_id: string | null
  job_status: string
  domain_name: string
  articles: SourceArticle[]
  progress?: WorkflowProgress | null
}

type WorkflowControl = {
  stopPolling: boolean
  workflowRunId: string | null
}

const SOURCES_SELECTION_KEY = 'smap.sources.selection'
const workflowRuns = new Map<string, Promise<WorkflowRunResponse>>()
const workflowResults = new Map<string, WorkflowRunResponse>()
const workflowLatest = new Map<string, WorkflowRunResponse>()
const workflowListeners = new Map<string, Set<(result: WorkflowRunResponse) => void>>()
const workflowControls = new Map<string, WorkflowControl>()
const pendingLeaveCancels = new Map<string, number>()
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
  return workflowResults.get(runId) ?? workflowLatest.get(runId) ?? null
}

function isTerminalStatus(status: string) {
  return status === 'COMPLETED' || status === 'FAILED' || status === 'PARTIAL' || status === 'CANCELLED'
}

function getControl(runId: string) {
  let control = workflowControls.get(runId)
  if (!control) {
    control = { stopPolling: false, workflowRunId: null }
    workflowControls.set(runId, control)
  }
  return control
}

function notifyProgress(runId: string, result: WorkflowRunResponse) {
  workflowLatest.set(runId, result)
  if (result.workflow_run_id) {
    getControl(runId).workflowRunId = result.workflow_run_id
  }
  const listeners = workflowListeners.get(runId)
  if (!listeners?.size) {
    return
  }
  for (const listener of [...listeners]) {
    listener(result)
  }
}

function subscribeProgress(runId: string, onProgress: (result: WorkflowRunResponse) => void) {
  let listeners = workflowListeners.get(runId)
  if (!listeners) {
    listeners = new Set()
    workflowListeners.set(runId, listeners)
  }
  listeners.add(onProgress)

  const latest = workflowLatest.get(runId) ?? workflowResults.get(runId)
  if (latest) {
    onProgress(latest)
  }

  return () => {
    listeners?.delete(onProgress)
    if (listeners && listeners.size === 0) {
      workflowListeners.delete(runId)
    }
  }
}

export async function getWorkflowRun(workflowRunId: string) {
  return apiFetch<WorkflowRunResponse>(`/processing/run/${workflowRunId}`)
}

export async function cancelWorkflowRun(workflowRunId: string) {
  return apiFetch<WorkflowRunResponse>(`/processing/run/${workflowRunId}/cancel`, {
    method: 'POST',
  })
}

function ensureWorkflowRequest(selection: SourcesSelection) {
  const existing = workflowRuns.get(selection.runId)
  if (existing) {
    return existing
  }

  const control = getControl(selection.runId)
  control.stopPolling = false

  const request = apiFetch<WorkflowRunResponse>('/processing/run', {
    method: 'POST',
    body: JSON.stringify({
      domain_id: selection.domainId,
      subdomain_ids: selection.subdomainIds,
    }),
  })
    .then(async (started) => {
      notifyProgress(selection.runId, started)
      const workflowRunId = started.workflow_run_id
      control.workflowRunId = workflowRunId
      if (!workflowRunId || isTerminalStatus(started.job_status)) {
        workflowResults.set(selection.runId, started)
        return started
      }

      let misses = 0
      for (;;) {
        if (control.stopPolling) {
          const latest = workflowLatest.get(selection.runId) ?? started
          return {
            ...latest,
            job_status: isTerminalStatus(latest.job_status) ? latest.job_status : 'CANCELLED',
          }
        }
        await new Promise((resolve) => window.setTimeout(resolve, 750))
        if (control.stopPolling) {
          const latest = workflowLatest.get(selection.runId) ?? started
          return {
            ...latest,
            job_status: isTerminalStatus(latest.job_status) ? latest.job_status : 'CANCELLED',
          }
        }
        try {
          const latest = await getWorkflowRun(workflowRunId)
          misses = 0
          notifyProgress(selection.runId, latest)
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

export function runSourcesWorkflow(
  selection: SourcesSelection,
  onProgress?: (result: WorkflowRunResponse) => void,
) {
  rememberSourcesSelection(selection)
  clearLeaveCancel(selection.runId)
  const stop = onProgress ? subscribeProgress(selection.runId, onProgress) : () => undefined
  const request = ensureWorkflowRequest(selection)
  return Object.assign(request, { stop })
}

export function stopSourcesPolling(clientRunId: string) {
  getControl(clientRunId).stopPolling = true
}

export async function cancelSourcesWorkflow(clientRunId: string) {
  stopSourcesPolling(clientRunId)
  const control = getControl(clientRunId)
  const workflowRunId =
    control.workflowRunId ||
    workflowLatest.get(clientRunId)?.workflow_run_id ||
    workflowResults.get(clientRunId)?.workflow_run_id

  if (!workflowRunId) {
    workflowRuns.delete(clientRunId)
    return null
  }

  try {
    const cancelled = await cancelWorkflowRun(workflowRunId)
    notifyProgress(clientRunId, cancelled)
    workflowResults.set(clientRunId, cancelled)
    return cancelled
  } catch {
    const latest = workflowLatest.get(clientRunId)
    if (latest) {
      const stopped = { ...latest, job_status: 'CANCELLED' }
      notifyProgress(clientRunId, stopped)
      workflowResults.set(clientRunId, stopped)
      return stopped
    }
    return null
  } finally {
    workflowRuns.delete(clientRunId)
  }
}

export function clearLeaveCancel(clientRunId: string) {
  const timer = pendingLeaveCancels.get(clientRunId)
  if (timer) {
    window.clearTimeout(timer)
    pendingLeaveCancels.delete(clientRunId)
  }
}

/** Delay cancel so React Strict Mode remounts don't kill a fresh run. */
export function scheduleCancelOnLeave(clientRunId: string) {
  clearLeaveCancel(clientRunId)
  const timer = window.setTimeout(() => {
    pendingLeaveCancels.delete(clientRunId)
    void cancelSourcesWorkflow(clientRunId)
  }, 600)
  pendingLeaveCancels.set(clientRunId, timer)
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
