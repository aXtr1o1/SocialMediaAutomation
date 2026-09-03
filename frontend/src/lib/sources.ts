import { apiFetch } from './api'

export type SourcesSelection = {
  domainId: string
  subdomainIds: string[]
  domainName: string
  subdomainNames?: string[]
  runId: string

  /*
   * Persisted source-search state.
   *
   * This is important because the frontend's in-memory
   * Maps disappear after logout/login or a full reload.
   */
  searchStatus?:
    | 'IDLE'
    | 'RUNNING'
    | 'COMPLETED'
    | 'FAILED'
    | 'PARTIAL'
    | 'CANCELLED'

  /*
   * Real backend workflow ID.
   *
   * If this exists, we reconnect to that workflow instead
   * of creating a new /processing/run.
   */
  workflowRunId?: string | null
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

  /*
   * Resolves as soon as the backend gives us the
   * workflow_run_id.
   *
   * This prevents Stop from racing the initial POST.
   */
  startedPromise: Promise<string | null>
  resolveStarted: (
    workflowRunId: string | null,
  ) => void
}

const SOURCES_SELECTION_KEY =
  'smap.sources.selection'

const workflowRuns =
  new Map<
    string,
    Promise<WorkflowRunResponse>
  >()

const workflowResults =
  new Map<
    string,
    WorkflowRunResponse
  >()

const workflowLatest =
  new Map<
    string,
    WorkflowRunResponse
  >()

const workflowListeners =
  new Map<
    string,
    Set<
      (result: WorkflowRunResponse) => void
    >
  >()

const workflowControls =
  new Map<string, WorkflowControl>()

let rememberedSelection:
  SourcesSelection | null = null

/* -------------------------------------------------------------------------- */
/* Selection persistence                                                      */
/* -------------------------------------------------------------------------- */

export function isSourcesSelection(
  value: unknown,
): value is SourcesSelection {
  if (!value || typeof value !== 'object') {
    return false
  }

  const row = value as SourcesSelection

  return Boolean(
    row.domainId &&
      row.runId &&
      Array.isArray(row.subdomainIds) &&
      row.subdomainIds.length,
  )
}

export function rememberSourcesSelection(
  selection: SourcesSelection,
) {
  rememberedSelection = selection

  try {
    sessionStorage.setItem(
      SOURCES_SELECTION_KEY,
      JSON.stringify(selection),
    )
  } catch {
    // Ignore storage failures.
  }
}

export function getRememberedSourcesSelection() {
  if (rememberedSelection) {
    return rememberedSelection
  }

  try {
    const raw =
      sessionStorage.getItem(
        SOURCES_SELECTION_KEY,
      )

    const parsed = raw
      ? JSON.parse(raw)
      : null

    if (isSourcesSelection(parsed)) {
      rememberedSelection = parsed
      return parsed
    }
  } catch {
    // Ignore storage failures.
  }

  return null
}

/*
 * Creates a completely new source-search selection.
 *
 * Used ONLY when the user explicitly clicks
 * "Start Search Again".
 */
export function createNewSourcesSelection(
  selection: SourcesSelection,
): SourcesSelection {
  const nextSelection: SourcesSelection = {
    ...selection,

    runId: crypto.randomUUID(),

    searchStatus: 'IDLE',

    workflowRunId: null,
  }

  rememberSourcesSelection(
    nextSelection,
  )

  return nextSelection
}

/*
 * Update only the persisted source-search state.
 */
export function updateSourcesSelectionStatus(
  runId: string,
  status: SourcesSelection['searchStatus'],
  workflowRunId?: string | null,
) {
  const current =
    getRememberedSourcesSelection()

  if (
    !current ||
    current.runId !== runId
  ) {
    return
  }

  const updated: SourcesSelection = {
    ...current,

    searchStatus: status,

    ...(workflowRunId !== undefined
      ? {
          workflowRunId,
        }
      : {}),
  }

  rememberSourcesSelection(updated)
}

/* -------------------------------------------------------------------------- */
/* Cached workflow state                                                      */
/* -------------------------------------------------------------------------- */

export function getCachedWorkflow(
  runId: string,
) {
  return (
    workflowResults.get(runId) ??
    workflowLatest.get(runId) ??
    null
  )
}

function isTerminalStatus(
  status?: string,
) {
  return (
    status === 'COMPLETED' ||
    status === 'FAILED' ||
    status === 'PARTIAL' ||
    status === 'CANCELLED'
  )
}

/* -------------------------------------------------------------------------- */
/* Workflow controls                                                          */
/* -------------------------------------------------------------------------- */

function createWorkflowControl(): WorkflowControl {
  let resolveStarted:
    | ((
        workflowRunId: string | null,
      ) => void)
    | null = null

  const startedPromise =
    new Promise<string | null>(
      (resolve) => {
        resolveStarted = resolve
      },
    )

  return {
    stopPolling: false,

    workflowRunId: null,

    startedPromise,

    resolveStarted: (
      workflowRunId,
    ) => {
      resolveStarted?.(
        workflowRunId,
      )

      resolveStarted = null
    },
  }
}

function getControl(
  runId: string,
) {
  let control =
    workflowControls.get(runId)

  if (!control) {
    control =
      createWorkflowControl()

    workflowControls.set(
      runId,
      control,
    )
  }

  return control
}

/* -------------------------------------------------------------------------- */
/* Progress listeners                                                         */
/* -------------------------------------------------------------------------- */

function notifyProgress(
  runId: string,
  result: WorkflowRunResponse,
) {
  workflowLatest.set(
    runId,
    result,
  )

  if (result.workflow_run_id) {
    getControl(
      runId,
    ).workflowRunId =
      result.workflow_run_id

    updateSourcesSelectionStatus(
      runId,
      result.job_status as SourcesSelection['searchStatus'],
      result.workflow_run_id,
    )
  } else {
    updateSourcesSelectionStatus(
      runId,
      result.job_status as SourcesSelection['searchStatus'],
    )
  }

  const listeners =
    workflowListeners.get(runId)

  if (!listeners?.size) {
    return
  }

  for (const listener of [
    ...listeners,
  ]) {
    listener(result)
  }
}

function subscribeProgress(
  runId: string,
  onProgress: (
    result: WorkflowRunResponse,
  ) => void,
) {
  let listeners =
    workflowListeners.get(runId)

  if (!listeners) {
    listeners =
      new Set()

    workflowListeners.set(
      runId,
      listeners,
    )
  }

  listeners.add(onProgress)

  const latest =
    workflowLatest.get(runId) ??
    workflowResults.get(runId)

  if (latest) {
    onProgress(latest)
  }

  return () => {
    listeners?.delete(
      onProgress,
    )

    if (
      listeners &&
      listeners.size === 0
    ) {
      workflowListeners.delete(
        runId,
      )
    }
  }
}

/* -------------------------------------------------------------------------- */
/* Backend API                                                                */
/* -------------------------------------------------------------------------- */

export async function getWorkflowRun(
  workflowRunId: string,
) {
  return apiFetch<WorkflowRunResponse>(
    `/processing/run/${workflowRunId}`,
  )
}

export async function cancelWorkflowRun(
  workflowRunId: string,
) {
  return apiFetch<WorkflowRunResponse>(
    `/processing/run/${workflowRunId}/cancel`,
    {
      method: 'POST',
    },
  )
}

/* -------------------------------------------------------------------------- */
/* Existing workflow polling                                                  */
/* -------------------------------------------------------------------------- */

function pollExistingWorkflow(
  selection: SourcesSelection,
  workflowRunId: string,
) {
  const control =
    getControl(selection.runId)

  control.workflowRunId =
    workflowRunId

  const request =
    (async (): Promise<WorkflowRunResponse> => {
      let misses = 0

      /*
       * Get the current state immediately.
       */
      try {
        const current =
          await getWorkflowRun(
            workflowRunId,
          )

        notifyProgress(
          selection.runId,
          current,
        )

        if (
          isTerminalStatus(
            current.job_status,
          )
        ) {
          workflowResults.set(
            selection.runId,
            current,
          )

          return current
        }
      } catch (error) {
        misses += 1

        if (misses >= 8) {
          throw error
        }
      }

      /*
       * Continue polling the EXISTING backend
       * workflow.
       */
      for (;;) {
        if (
          control.stopPolling
        ) {
          const latest =
            workflowLatest.get(
              selection.runId,
            )

          const stopped: WorkflowRunResponse =
            {
              ...(latest ?? {
                workflow_run_id:
                  workflowRunId,

                job_status:
                  'CANCELLED',

                domain_name:
                  selection.domainName,

                articles: [],

                progress: null,
              }),

              job_status:
                'CANCELLED',
            }

          workflowResults.set(
            selection.runId,
            stopped,
          )

          return stopped
        }

        await new Promise<void>(
          (resolve) =>
            window.setTimeout(
              resolve,
              750,
            ),
        )

        if (
          control.stopPolling
        ) {
          const latest =
            workflowLatest.get(
              selection.runId,
            )

          const stopped: WorkflowRunResponse =
            {
              ...(latest ?? {
                workflow_run_id:
                  workflowRunId,

                job_status:
                  'CANCELLED',

                domain_name:
                  selection.domainName,

                articles: [],

                progress: null,
              }),

              job_status:
                'CANCELLED',
            }

          workflowResults.set(
            selection.runId,
            stopped,
          )

          return stopped
        }

        try {
          const latest =
            await getWorkflowRun(
              workflowRunId,
            )

          misses = 0

          notifyProgress(
            selection.runId,
            latest,
          )

          if (
            isTerminalStatus(
              latest.job_status,
            )
          ) {
            workflowResults.set(
              selection.runId,
              latest,
            )

            return latest
          }
        } catch (error) {
          misses += 1

          if (misses >= 8) {
            throw error
          }
        }
      }
    })()

  workflowRuns.set(
    selection.runId,
    request,
  )

  return request
}

/* -------------------------------------------------------------------------- */
/* Start a brand-new workflow                                                  */
/* -------------------------------------------------------------------------- */

function ensureWorkflowRequest(
  selection: SourcesSelection,
) {
  const existing =
    workflowRuns.get(
      selection.runId,
    )

  if (existing) {
    return existing
  }

  /*
   * If we already have a backend workflow ID,
   * NEVER create another workflow.
   *
   * This is what makes logout/login safe.
   */
  if (
    selection.workflowRunId &&
    selection.searchStatus !==
      'CANCELLED'
  ) {
    const control =
      getControl(
        selection.runId,
      )

    control.stopPolling = false

    return pollExistingWorkflow(
      selection,
      selection.workflowRunId,
    )
  }

  const control =
    getControl(selection.runId)

  control.stopPolling = false

  /*
   * Create the backend workflow.
   */
  const request =
    apiFetch<WorkflowRunResponse>(
      '/processing/run',
      {
        method: 'POST',

        body: JSON.stringify({
          domain_id:
            selection.domainId,

          subdomain_ids:
            selection.subdomainIds,
        }),
      },
    )
      .then(
        async (started) => {
          const workflowRunId =
            started.workflow_run_id

          control.workflowRunId =
            workflowRunId

          /*
           * Persist the real backend ID
           * immediately.
           */
          updateSourcesSelectionStatus(
            selection.runId,
            started.job_status as SourcesSelection['searchStatus'],
            workflowRunId,
          )

          /*
           * Resolve the Stop race.
           */
          control.resolveStarted(
            workflowRunId,
          )

          notifyProgress(
            selection.runId,
            started,
          )

          if (
            !workflowRunId ||
            isTerminalStatus(
              started.job_status,
            )
          ) {
            workflowResults.set(
              selection.runId,
              started,
            )

            return started
          }

          let misses = 0

          for (;;) {
            if (
              control.stopPolling
            ) {
              const latest =
                workflowLatest.get(
                  selection.runId,
                ) ?? started

              const stopped: WorkflowRunResponse =
                {
                  ...latest,

                  job_status:
                    'CANCELLED',
                }

              workflowResults.set(
                selection.runId,
                stopped,
              )

              updateSourcesSelectionStatus(
                selection.runId,
                'CANCELLED',
                workflowRunId,
              )

              return stopped
            }

            await new Promise<void>(
              (resolve) =>
                window.setTimeout(
                  resolve,
                  750,
                ),
            )

            if (
              control.stopPolling
            ) {
              const latest =
                workflowLatest.get(
                  selection.runId,
                ) ?? started

              const stopped: WorkflowRunResponse =
                {
                  ...latest,

                  job_status:
                    'CANCELLED',
                }

              workflowResults.set(
                selection.runId,
                stopped,
              )

              updateSourcesSelectionStatus(
                selection.runId,
                'CANCELLED',
                workflowRunId,
              )

              return stopped
            }

            try {
              const latest =
                await getWorkflowRun(
                  workflowRunId,
                )

              misses = 0

              notifyProgress(
                selection.runId,
                latest,
              )

              if (
                isTerminalStatus(
                  latest.job_status,
                )
              ) {
                workflowResults.set(
                  selection.runId,
                  latest,
                )

                return latest
              }
            } catch (error) {
              misses += 1

              if (misses >= 8) {
                throw error
              }
            }
          }
        },
      )
      .catch((error) => {
        control.resolveStarted(
          control.workflowRunId,
        )

        workflowRuns.delete(
          selection.runId,
        )

        throw error
      })

  workflowRuns.set(
    selection.runId,
    request,
  )

  return request
}

/* -------------------------------------------------------------------------- */
/* Public workflow functions                                                   */
/* -------------------------------------------------------------------------- */

export function runSourcesWorkflow(
  selection: SourcesSelection,
  onProgress?: (
    result: WorkflowRunResponse,
  ) => void,
) {
  rememberSourcesSelection(
    selection,
  )

  /*
   * Navigation does NOT cancel the workflow.
   */
  const stop = onProgress
    ? subscribeProgress(
        selection.runId,
        onProgress,
      )
    : () => undefined

  const request =
    ensureWorkflowRequest(
      selection,
    )

  return Object.assign(
    request,
    { stop },
  )
}

export function stopSourcesPolling(
  clientRunId: string,
) {
  getControl(
    clientRunId,
  ).stopPolling = true
}

export async function cancelSourcesWorkflow(
  clientRunId: string,
) {
  const control =
    getControl(clientRunId)

  /*
   * Stop the local polling immediately.
   */
  control.stopPolling = true

  /*
   * Persist cancellation immediately.
   *
   * This is what survives logout/login.
   */
  updateSourcesSelectionStatus(
    clientRunId,
    'CANCELLED',
    control.workflowRunId,
  )

  /*
   * If the backend hasn't returned the ID yet,
   * wait for it.
   */
  let workflowRunId =
    control.workflowRunId

  if (!workflowRunId) {
    workflowRunId =
      await control.startedPromise
  }

  workflowRunId =
    workflowRunId ||
    workflowLatest.get(
      clientRunId,
    )?.workflow_run_id ||
    workflowResults.get(
      clientRunId,
    )?.workflow_run_id ||
    getRememberedSourcesSelection()
      ?.workflowRunId ||
    null

  /*
   * No backend ID means there is nothing to
   * cancel remotely, but the selection is still
   * permanently marked CANCELLED.
   */
  if (!workflowRunId) {
    const latest =
      workflowLatest.get(
        clientRunId,
      )

    if (latest) {
      const stopped: WorkflowRunResponse =
        {
          ...latest,
          job_status:
            'CANCELLED',
        }

      workflowResults.set(
        clientRunId,
        stopped,
      )

      notifyProgress(
        clientRunId,
        stopped,
      )

      workflowRuns.delete(
        clientRunId,
      )

      return stopped
    }

    workflowRuns.delete(
      clientRunId,
    )

    return null
  }

  try {
    const cancelled =
      await cancelWorkflowRun(
        workflowRunId,
      )

    const result: WorkflowRunResponse =
      {
        ...cancelled,

        workflow_run_id:
          workflowRunId,

        job_status:
          'CANCELLED',
      }

    notifyProgress(
      clientRunId,
      result,
    )

    workflowResults.set(
      clientRunId,
      result,
    )

    updateSourcesSelectionStatus(
      clientRunId,
      'CANCELLED',
      workflowRunId,
    )

    return result
  } catch {
    const latest =
      workflowLatest.get(
        clientRunId,
      )

    const stopped: WorkflowRunResponse =
      {
        ...(latest ?? {
          workflow_run_id:
            workflowRunId,

          job_status:
            'CANCELLED',

          domain_name: '',

          articles: [],

          progress: null,
        }),

        workflow_run_id:
          workflowRunId,

        job_status:
          'CANCELLED',
      }

    notifyProgress(
      clientRunId,
      stopped,
    )

    workflowResults.set(
      clientRunId,
      stopped,
    )

    updateSourcesSelectionStatus(
      clientRunId,
      'CANCELLED',
      workflowRunId,
    )

    return stopped
  } finally {
    workflowRuns.delete(
      clientRunId,
    )
  }
}

/* -------------------------------------------------------------------------- */
/* Source article formatting helpers                                           */
/* -------------------------------------------------------------------------- */

export function formatPublishedAt(
  value?: string | null,
) {
  if (!value) {
    return ''
  }

  try {
    return new Intl.DateTimeFormat(
      undefined,
      {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      },
    ).format(new Date(value))
  } catch {
    return value
  }
}

export function splitContentParagraphs(
  content: string,
) {
  if (!content) {
    return []
  }

  return content
    .split(/\n\s*\n/)
    .map(
      (paragraph) =>
        paragraph.trim(),
    )
    .filter(Boolean)
}