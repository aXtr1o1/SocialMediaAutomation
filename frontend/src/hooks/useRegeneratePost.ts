import { useState } from 'react'

import { ApiError } from '../lib/api'
import {
  countOccurrences,
  regenerateSnippet,
  type GeneratePlatform,
  type RegenerateSnippetResponse,
} from '../lib/generations'

type UseRegeneratePostArgs = {
  platform: GeneratePlatform
  fullPost: string
  articleId?: string
  draftId?: string | null
  onSuccess: (result: RegenerateSnippetResponse, instruction: string) => void
}

export function useRegeneratePost({
  platform,
  fullPost,
  articleId,
  draftId,
  onSuccess,
}: UseRegeneratePostArgs) {
  const [targetText, setTargetText] = useState('')
  const [instruction, setInstruction] = useState('')
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  function validate() {
    const target = targetText
    const comment = instruction.trim()
    if (!target.trim()) {
      return 'Paste the exact text you want to change.'
    }
    if (comment.length < 3) {
      return 'Add a short comment describing what to change.'
    }
    const hits = countOccurrences(fullPost, target)
    if (hits === 0) {
      return 'That text was not found in the post. Copy and paste it exactly.'
    }
    if (hits > 1) {
      return 'That text appears more than once. Paste a longer unique section.'
    }
    return ''
  }

  async function submit() {
    const validationError = validate()
    if (validationError) {
      setError(validationError)
      return
    }

    const comment = instruction.trim()
    setIsSubmitting(true)
    setError('')
    try {
      const result = await regenerateSnippet({
        platform,
        full_post: fullPost,
        target_text: targetText,
        instruction: comment,
        article_id: articleId,
        draft_id: draftId || undefined,
        label: comment,
      })
      onSuccess(result, comment)
      setTargetText('')
    } catch (caught) {
      if (caught instanceof ApiError) {
        setError(caught.message)
      } else {
        setError(caught instanceof Error ? caught.message : 'Could not regenerate that section')
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  return {
    targetText,
    setTargetText,
    instruction,
    setInstruction,
    error,
    isSubmitting,
    submit,
  }
}
