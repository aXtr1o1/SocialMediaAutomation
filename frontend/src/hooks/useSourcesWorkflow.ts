import { useEffect, useState } from 'react'
import {
  getCachedWorkflow,
  runSourcesWorkflow,
  type SourceArticle,
  type SourcesSelection,
  type WorkflowProgress,
} from '../lib/sources'

export function useSourcesWorkflow(selection: SourcesSelection | null) {
  const cached = selection ? getCachedWorkflow(selection.runId) : null
  const [articles, setArticles] = useState<SourceArticle[]>(cached?.articles ?? [])
  const [domainName, setDomainName] = useState(cached?.domain_name || selection?.domainName || '')
  const [isRunning, setIsRunning] = useState(Boolean(selection) && !cached)
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
    if (existing) {
      setArticles(existing.articles)
      setDomainName(existing.domain_name || selection.domainName)
      setProgress(existing.progress ?? null)
      setError('')
      setIsRunning(false)
      return
    }

    let cancelled = false
    setIsRunning(true)
    setError('')
    setArticles([])
    setProgress(null)
    setDomainName(selection.domainName)

    void runSourcesWorkflow(selection, (latest) => {
      if (cancelled) {
        return
      }

      setDomainName(latest.domain_name || selection.domainName)
      setProgress(latest.progress ?? null)
      if (latest.articles.length) {
        setArticles(latest.articles)
      }
    })
      .then((result) => {
        if (cancelled) {
          return
        }

        setArticles(result.articles)
        setDomainName(result.domain_name || selection.domainName)
        setProgress(result.progress ?? null)
        if (result.job_status === 'FAILED' && result.articles.length === 0) {
          setError('Could not find sources for this selection.')
        }
      })
      .catch((caught) => {
        if (!cancelled) {
          setError(caught instanceof Error ? caught.message : 'Could not process sources')
        }
      })
      .finally(() => {
        if (!cancelled) {
          setIsRunning(false)
        }
      })

    return () => {
      cancelled = true
    }
  }, [selection?.runId])

  return { articles, domainName, isRunning, progress, error }
}
