import { useEffect, useState } from 'react'
import {
  cancelSourcesWorkflow,
  getCachedWorkflow,
  rememberSourcesSelection,
  runSourcesWorkflow,
  type SourceArticle,
  type SourcesSelection,
  type WorkflowProgress,
} from '../lib/sources'

function isTerminal(
  status?: string,
) {
  return (
    status === 'COMPLETED' ||
    status === 'FAILED' ||
    status === 'PARTIAL' ||
    status === 'CANCELLED'
  )
}

export function useSourcesWorkflow(
  selection: SourcesSelection | null,
) {
  const cached =
    selection
      ? getCachedWorkflow(
          selection.runId,
        )
      : null

  const persistedStatus =
    selection?.searchStatus

  const initialStatus =
    persistedStatus ||
    cached?.job_status ||
    ''

  const [articles, setArticles] =
    useState<SourceArticle[]>(
      cached?.articles ?? [],
    )

  const [domainName, setDomainName] =
    useState(
      cached?.domain_name ||
        selection?.domainName ||
        '',
    )

  const [isRunning, setIsRunning] =
    useState(
      Boolean(selection) &&
        initialStatus !==
          'CANCELLED' &&
        !isTerminal(
          initialStatus,
        ),
    )

  const [isCancelling, setIsCancelling] =
    useState(false)

  const [progress, setProgress] =
    useState<WorkflowProgress | null>(
      cached?.progress ?? null,
    )

  const [jobStatus, setJobStatus] =
    useState<string>(
      initialStatus,
    )

  const [error, setError] =
    useState('')

  useEffect(() => {
    if (!selection) {
      setArticles([])
      setIsRunning(false)
      setIsCancelling(false)
      setProgress(null)
      setJobStatus('')
      setError('')
      setDomainName('')
      return
    }

    /*
     * ------------------------------------------------------------
     * EXPLICITLY CANCELLED SEARCH
     * ------------------------------------------------------------
     *
     * This is the most important check.
     *
     * If the user stopped this search previously, including
     * before logging out, NEVER call /processing/run again.
     */
    if (
      selection.searchStatus ===
      'CANCELLED'
    ) {
      const existing =
        getCachedWorkflow(
          selection.runId,
        )

      if (existing) {
        setArticles(
          existing.articles,
        )

        setDomainName(
          existing.domain_name ||
            selection.domainName,
        )

        setProgress(
          existing.progress ??
            null,
        )
      } else {
        setArticles([])
        setDomainName(
          selection.domainName,
        )
      }

      setJobStatus(
        'CANCELLED',
      )

      setIsRunning(false)
      setIsCancelling(false)
      setError('')

      return
    }

    const existing =
      getCachedWorkflow(
        selection.runId,
      )

    /*
     * Existing terminal workflow.
     *
     * Never automatically create another one.
     */
    if (
      existing &&
      isTerminal(
        existing.job_status,
      )
    ) {
      setArticles(
        existing.articles,
      )

      setDomainName(
        existing.domain_name ||
          selection.domainName,
      )

      setProgress(
        existing.progress ??
          null,
      )

      setJobStatus(
        existing.job_status,
      )

      setError('')
      setIsRunning(false)
      setIsCancelling(false)

      return
    }

    let alive = true

    setIsCancelling(false)
    setError('')
    setDomainName(
      selection.domainName,
    )

    /*
     * If this selection has a persisted RUNNING state,
     * runSourcesWorkflow() will reconnect to the existing
     * backend workflow using workflowRunId.
     */
    setJobStatus(
      selection.searchStatus ||
        existing?.job_status ||
        'RUNNING',
    )

    setIsRunning(true)

    if (existing?.progress) {
      setProgress(
        existing.progress,
      )

      if (
        existing.articles.length
      ) {
        setArticles(
          existing.articles,
        )
      }
    } else {
      setArticles([])

      setProgress({
        stage: 'crawling',

        message:
          'Preparing your source search…',

        activity:
          'Preparing your source search…',

        current_site: '',

        activity_log: [
          'Preparing your source search…',
        ],

        crawled: 0,

        kpi_passed: 0,

        match_passed: 0,

        sources_done: 0,

        sources_total: 0,

        checked: 0,
      })
    }

    const request =
      runSourcesWorkflow(
        selection,
        (latest) => {
          if (!alive) {
            return
          }

          setDomainName(
            latest.domain_name ||
              selection.domainName,
          )

          setJobStatus(
            latest.job_status,
          )

          if (
            latest.progress
          ) {
            setProgress(
              latest.progress,
            )
          }

          if (
            latest.articles.length
          ) {
            setArticles(
              latest.articles,
            )
          }

          if (
            isTerminal(
              latest.job_status,
            )
          ) {
            setIsRunning(false)
          }
        },
      )

    void request
      .then(
        (result) => {
          if (!alive) {
            return
          }

          setArticles(
            result.articles,
          )

          setDomainName(
            result.domain_name ||
              selection.domainName,
          )

          setJobStatus(
            result.job_status,
          )

          if (
            result.progress
          ) {
            setProgress(
              result.progress,
            )
          }

          if (
            result.job_status ===
              'FAILED' &&
            result.articles.length === 0
          ) {
            setError(
              'Could not find sources for this selection.',
            )
          }

          if (
            result.job_status ===
              'CANCELLED'
          ) {
            setIsRunning(false)
          }
        },
      )
      .catch((caught) => {
        if (!alive) {
          return
        }

        setError(
          caught instanceof Error
            ? caught.message
            : 'Could not process sources',
        )

        setIsRunning(false)
      })
      .finally(() => {
        if (alive) {
          setIsRunning(false)
        }
      })

    return () => {
      alive = false

      /*
       * IMPORTANT:
       *
       * Navigating away only removes this page's
       * progress listener.
       *
       * It DOES NOT cancel the backend workflow.
       */
      request.stop()
    }
  }, [selection?.runId])

  async function stopWorkflow() {
    if (
      !selection ||
      isCancelling
    ) {
      return
    }

    setIsCancelling(true)
    setError('')

    /*
     * Immediately persist the user's explicit decision.
     *
     * This survives logout/login.
     */
    const stoppedSelection: SourcesSelection =
      {
        ...selection,

        searchStatus:
          'CANCELLED',

        workflowRunId:
          selection.workflowRunId ??
          null,
      }

    rememberSourcesSelection(
      stoppedSelection,
    )

    setJobStatus(
      'CANCELLED',
    )

    setIsRunning(false)

    try {
      const result =
        await cancelSourcesWorkflow(
          selection.runId,
        )

      if (result) {
        setArticles(
          result.articles,
        )

        setDomainName(
          result.domain_name ||
            selection.domainName,
        )

        setProgress(
          result.progress ??
            null,
        )

        setJobStatus(
          'CANCELLED',
        )

        /*
         * Persist the real backend workflow ID
         * returned by cancellation.
         */
        rememberSourcesSelection({
          ...stoppedSelection,

          searchStatus:
            'CANCELLED',

          workflowRunId:
            result.workflow_run_id ??
            stoppedSelection.workflowRunId ??
            null,
        })
      }
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : 'Could not stop source search',
      )

      /*
       * Even if the HTTP cancellation request fails,
       * the UI remains stopped because the user explicitly
       * requested Stop.
       */
      setJobStatus(
        'CANCELLED',
      )

      setIsRunning(false)

      rememberSourcesSelection({
        ...stoppedSelection,

        searchStatus:
          'CANCELLED',
      })
    } finally {
      setIsCancelling(false)
    }
  }

  return {
    articles,

    domainName,

    isRunning,

    isCancelling,

    progress,

    jobStatus,

    error,

    stopWorkflow,
  }
}