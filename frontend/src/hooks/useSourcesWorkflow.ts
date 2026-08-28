import { useEffect, useState } from 'react'
import {
  clearLeaveCancel,
  getCachedWorkflow,
  runSourcesWorkflow,
  scheduleCancelOnLeave,
  type SourceArticle,
  type SourcesSelection,
  type WorkflowProgress,
} from '../lib/sources'

function isTerminal(status?: string) {
  return status === 'COMPLETED' || status === 'FAILED' || status === 'PARTIAL' || status === 'CANCELLED'
}

export function useSourcesWorkflow(selection: SourcesSelection | null) {
  const cached = selection ? getCachedWorkflow(selection.runId) : null
  const [articles, setArticles] = useState<SourceArticle[]>(cached?.articles ?? [])
  const [domainName, setDomainName] = useState(cached?.domain_name || selection?.domainName || '')
  const [isRunning, setIsRunning] = useState(Boolean(selection) && !isTerminal(cached?.job_status))
  const [progress, setProgress] = useState<WorkflowProgress | null>(cached?.progress ?? null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!selection) {
      setArticles([])
      setIsRunning(false)
      setProgress(null)
      return
    }

    const existing = getCachedWorkflow(selection.runId)
    if (existing && isTerminal(existing.job_status)) {
      setArticles(existing.articles)
      setDomainName(existing.domain_name || selection.domainName)
      setProgress(existing.progress ?? null)
      setError('')
      setIsRunning(false)
      return
    }

    let alive = true
    clearLeaveCancel(selection.runId)
    setIsRunning(true)
    setError('')
    setDomainName(selection.domainName)

    if (existing?.progress) {
      setProgress(existing.progress)
      if (existing.articles.length) {
        setArticles(existing.articles)
      }
    } else {
      setArticles([])
      setProgress({
        stage: 'crawling',
        message: 'Preparing your source search…',
        activity: 'Preparing your source search…',
        current_site: '',
        activity_log: ['Preparing your source search…'],
        crawled: 0,
        kpi_passed: 0,
        match_passed: 0,
        sources_done: 0,
        sources_total: 0,
        checked: 0,
      })
    }

    const request = runSourcesWorkflow(selection, (latest) => {
      if (!alive) {
        return
      }
      setDomainName(latest.domain_name || selection.domainName)
      if (latest.progress) {
        setProgress(latest.progress)
      }
      if (latest.articles.length) {
        setArticles(latest.articles)
      }
      if (isTerminal(latest.job_status)) {
        setIsRunning(false)
      }
    })

    void request
      .then((result) => {
        if (!alive) {
          return
        }
        setArticles(result.articles)
        setDomainName(result.domain_name || selection.domainName)
        if (result.progress) {
          setProgress(result.progress)
        }
        if (result.job_status === 'FAILED' && result.articles.length === 0) {
          setError('Could not find sources for this selection.')
        }
      })
      .catch((caught) => {
        if (!alive) {
          return
        }
        setError(caught instanceof Error ? caught.message : 'Could not process sources')
      })
      .finally(() => {
        if (alive) {
          setIsRunning(false)
        }
      })

    return () => {
      alive = false
      request.stop()
      scheduleCancelOnLeave(selection.runId)
    }
  }, [selection?.runId])

  return { articles, domainName, isRunning, progress, error }
}
