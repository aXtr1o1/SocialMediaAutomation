import { useMemo, useState } from 'react'

import {
  addGenerationVersion,
  deleteGenerationVersion,
  setGenerationCurrentVersion,
  type GenerationDraft,
  type PostVersion,
  type PostVersionSource,
} from '../lib/generations'

function createLocalVersion(input: {
  version: number
  full_post: string
  label: string
  source: PostVersionSource
  meta?: PostVersion['meta']
}): PostVersion {
  return {
    id: crypto.randomUUID(),
    version: input.version,
    full_post: input.full_post,
    createdAt: new Date().toISOString(),
    label: input.label,
    source: input.source,
    meta: input.meta,
  }
}

function applyDraft(draft: GenerationDraft) {
  return {
    versions: draft.versions,
    currentId: draft.current_version_id || draft.versions[draft.versions.length - 1]?.id || '',
  }
}

export function usePostVersions(initialFullPost: string, draft?: GenerationDraft | null) {
  const seeded = draft ? applyDraft(draft) : null
  const [draftId, setDraftId] = useState(draft?.id ?? null)
  const [versions, setVersions] = useState<PostVersion[]>(
    () =>
      seeded?.versions ?? [
        createLocalVersion({
          version: 1,
          full_post: initialFullPost,
          label: 'Original',
          source: 'generate',
        }),
      ],
  )
  const [currentId, setCurrentId] = useState(
    () => seeded?.currentId ?? versions[0]?.id ?? '',
  )
  const [isSyncing, setIsSyncing] = useState(false)

  const current = useMemo(
    () => versions.find((item) => item.id === currentId) ?? versions[0] ?? null,
    [versions, currentId],
  )

  function replaceFromDraft(next: GenerationDraft) {
    setDraftId(next.id)
    setVersions(next.versions)
    setCurrentId(next.current_version_id || next.versions[next.versions.length - 1]?.id || '')
  }

  async function appendVersion(input: {
    full_post: string
    label: string
    source: PostVersionSource
    meta?: PostVersion['meta']
  }) {
    if (draftId) {
      setIsSyncing(true)
      try {
        const next = await addGenerationVersion(draftId, {
          full_post: input.full_post,
          label: input.label,
          source: input.source,
          target_text: input.meta?.target_text || undefined,
          instruction: input.meta?.instruction || undefined,
          replacement_text: input.meta?.replacement_text || undefined,
        })
        replaceFromDraft(next)
        return next.versions[next.versions.length - 1] ?? null
      } finally {
        setIsSyncing(false)
      }
    }

    const local = createLocalVersion({
      version: versions.length + 1,
      full_post: input.full_post,
      label: input.label,
      source: input.source,
      meta: input.meta,
    })
    setVersions((prev) => [...prev, local])
    setCurrentId(local.id)
    return local
  }

  async function selectVersion(id: string) {
    if (!versions.some((item) => item.id === id)) {
      return
    }
    setCurrentId(id)
    if (!draftId) {
      return
    }
    setIsSyncing(true)
    try {
      const next = await setGenerationCurrentVersion(draftId, id)
      replaceFromDraft(next)
    } finally {
      setIsSyncing(false)
    }
  }

  async function deleteVersion(id: string) {
    if (versions.length <= 1) {
      return false
    }

    if (draftId) {
      setIsSyncing(true)
      try {
        const next = await deleteGenerationVersion(draftId, id)
        replaceFromDraft(next)
        return true
      } finally {
        setIsSyncing(false)
      }
    }

    const index = versions.findIndex((item) => item.id === id)
    if (index < 0) {
      return false
    }
    const remaining = versions.filter((item) => item.id !== id)
    setVersions(remaining)
    if (currentId === id) {
      const fallback = remaining[Math.min(index, remaining.length - 1)] ?? remaining[0]
      setCurrentId(fallback?.id ?? '')
    }
    return true
  }

  function ingestServerVersion(version: PostVersion, nextDraftId?: string | null) {
    if (nextDraftId) {
      setDraftId(nextDraftId)
    }
    setVersions((prev) => {
      if (prev.some((item) => item.id === version.id)) {
        return prev
      }
      return [...prev, version]
    })
    setCurrentId(version.id)
  }

  function syncFromDraft(next: GenerationDraft) {
    replaceFromDraft(next)
  }

  return {
    draftId,
    versions,
    current,
    currentId,
    isSyncing,
    appendVersion,
    selectVersion,
    deleteVersion,
    ingestServerVersion,
    syncFromDraft,
  }
}
