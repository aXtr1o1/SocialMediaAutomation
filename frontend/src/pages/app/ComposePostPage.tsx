import { useEffect, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { PlatformChoiceCard } from '../../components/generations/PlatformChoiceCard'
import { MaterialIcon } from '../../components/ui/MaterialIcon'
import { LinkedInIcon } from '../../assets/icons/LinkedInIcon'
import { BlueskyIcon } from '../../assets/icons/BlueskyIcon'
import {
  cancelGeneration,
  generatePosts,
  isComposeState,
  platformsFromChoice,
  type PlatformChoice,
} from '../../lib/generations'
import {
  getWorkflowSession,
  updateWorkflowSession,
} from '../../lib/workflow'
import { paths } from '../../lib/paths'
import { cn } from '../../lib/cn'

export function ComposePostPage() {
  const location = useLocation()
  const navigate = useNavigate()

  const [selection, setSelection] = useState(
    isComposeState(location.state)
      ? location.state
      : null,
  )

  const [choice, setChoice] = useState<PlatformChoice | ''>('')
  const [isGenerating, setIsGenerating] = useState(false)
  const [generationId, setGenerationId] =
    useState<string | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (selection) {
      return
    }

    let alive = true

    void getWorkflowSession()
      .then((workflow) => {
        if (!alive) {
          return
        }

        const article =
          workflow.generated_article ??
          workflow.selected_source_posts?.[0]

        if (!article) {
          return
        }

        setSelection({
          article,
          sourcesSelection: undefined,
        })
      })
      .catch(() => undefined)

    return () => {
      alive = false
    }
  }, [selection])

  async function handleGenerate() {
    if (!selection || !choice) {
      return
    }

    setIsGenerating(true)
    setGenerationId(null)
    setError('')

    const targetPlatforms =
      platformsFromChoice(choice)

    try {
      /*
       * Persist the workflow BEFORE starting generation.
       *
       * This makes the backend the source of truth for:
       * - current workflow
       * - current step
       * - article being generated
       * - selected source post
       * - target platforms
       * - generation status
       */
      await updateWorkflowSession({
        current_workflow:
          'content_generation',

        current_step:
          'generate',

        generated_article:
          selection.article,

        selected_source_posts: [
          selection.article,
        ],

        target_platforms:
          targetPlatforms,

        generation_status:
          'GENERATING',
      })

      const articleId =
        selection.article.article_id ||
        selection.article.id

      /*
       * Start generation.
       *
       * As soon as generatePosts() gives us the generation ID,
       * immediately persist it to the workflow session.
       */
      const result = await generatePosts(
        articleId,
        platformsFromChoice(choice),
        (job) => {
          setGenerationId(
            job.generation_id,
          )

          void updateWorkflowSession({
            active_generation_id:
              job.generation_id,

            generated_article:
              selection.article,

            generation_status:
              job.status === 'QUEUED'
                ? 'QUEUED'
                : 'GENERATING',
          })
        },
      )

      /*
       * Generation completed successfully.
       *
       * Clear active_generation_id because there is no longer
       * an active generation job.
       *
       * Persist the generated content and move the workflow
       * to the review step.
       */
      await updateWorkflowSession({
        current_workflow:
          'content_generation',

        current_step:
          'review',

        generated_article:
          selection.article,

        active_generation_id:
          null,

        generated_content:
          result.posts,

        generation_drafts:
          result.drafts,

        target_platforms:
          targetPlatforms,

        generation_status:
          'COMPLETED',
      })

      setGenerationId(null)
      setIsGenerating(false)

      navigate(paths.generations, {
        state: {
          article:
            selection.article,

          posts:
            result.posts,

          drafts:
            result.drafts,

          sourcesSelection:
            selection.sourcesSelection,
        },
      })
    } catch (caught) {
      /*
       * Generation failed.
       *
       * Clear active_generation_id so the workflow does not
       * remain stuck with an old generation job.
       */
      try {
        await updateWorkflowSession({
          active_generation_id:
            null,

          generation_status:
            'FAILED',
        })
      } catch {
        /*
         * Do not replace the original generation error if
         * persistence of the FAILED state also fails.
         */
      }

      setError(
        caught instanceof Error
          ? caught.message
          : 'Could not generate the post',
      )

      setIsGenerating(false)
      setGenerationId(null)
    }
  }

  async function handleStopGeneration() {
    if (!generationId) {
      return
    }

    try {
      await cancelGeneration(generationId)

      setIsGenerating(false)
      setError('Generation stopped.')
      setGenerationId(null)

      await updateWorkflowSession({
        active_generation_id:
          null,

        generation_status:
          'CANCELLED',
      })
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : 'Could not stop generation',
      )
    }
  }

  if (!selection) {
    return (
      <div className="mx-auto flex w-full max-w-5xl flex-col gap-lg p-lg lg:p-xl">
        <h1 className="font-headline-md text-headline-md text-on-surface">
          Compose Post
        </h1>

        <p className="font-body-md text-body-md text-on-surface-variant">
          Choose a source article first, then generate a post.
        </p>

        <Link
          className="font-body-md text-primary underline"
          to={paths.discover}
        >
          Back to Discover
        </Link>
      </div>
    )
  }

  return (
    <div className="relative flex h-[calc(100vh-64px)] w-full flex-col items-center justify-center overflow-hidden bg-surface">
      <div className="pointer-events-none absolute -left-[10%] -top-[20%] h-[50%] w-[50%] rounded-full bg-primary/10 blur-[120px]" />

      <div className="pointer-events-none absolute -right-[10%] bottom-0 h-[60%] w-[40%] rounded-full bg-[#5952af]/10 blur-[100px]" />

      <div className="relative z-10 mx-md flex w-full max-w-[480px] flex-col gap-lg rounded-xl bg-surface-container-lowest p-xl shadow-xl">
        <div className="flex flex-col gap-xs text-center">
          <h1 className="font-headline-md text-headline-md text-on-surface">
            Compose Post
          </h1>

          <p className="font-body-md text-body-md text-on-surface-variant">
            Choose a platform to generate your post.
          </p>
        </div>

        <div className="grid grid-cols-3 gap-sm">
          <PlatformChoiceCard
            label="LinkedIn"
            selected={
              choice === 'linkedin'
            }
            disabled={isGenerating}
            onSelect={() =>
              setChoice('linkedin')
            }
          >
            <div className="mb-sm flex h-12 w-12 items-center justify-center rounded-full bg-surface-container transition-colors group-hover:bg-primary/5">
              <LinkedInIcon className="h-6 w-6 text-on-surface-variant group-hover:text-primary" />
            </div>
          </PlatformChoiceCard>

          <PlatformChoiceCard
            label="Bluesky"
            selected={
              choice === 'bluesky'
            }
            disabled={isGenerating}
            onSelect={() =>
              setChoice('bluesky')
            }
          >
            <div className="mb-sm flex h-12 w-12 items-center justify-center rounded-full bg-surface-container transition-colors group-hover:bg-primary/5">
              <BlueskyIcon className="h-6 w-6 text-on-surface-variant group-hover:text-primary" />
            </div>
          </PlatformChoiceCard>

          <PlatformChoiceCard
            label="Both"
            selected={
              choice === 'both'
            }
            disabled={isGenerating}
            onSelect={() =>
              setChoice('both')
            }
          >
            <div className="mb-sm flex items-center justify-center gap-xs">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-surface-container transition-colors group-hover:bg-primary/5">
                <LinkedInIcon className="h-4 w-4 text-on-surface-variant group-hover:text-primary" />
              </div>

              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-surface-container transition-colors group-hover:bg-primary/5">
                <BlueskyIcon className="h-4 w-4 text-on-surface-variant group-hover:text-primary" />
              </div>
            </div>
          </PlatformChoiceCard>
        </div>

        {error ? (
          <p className="text-center font-body-md text-body-md text-error">
            {error}
          </p>
        ) : null}

        {isGenerating ? (
          <div className="flex gap-sm">
            <button
              type="button"
              onClick={() => {
                void handleStopGeneration()
              }}
              className="flex h-10 flex-1 items-center justify-center gap-xs rounded-lg border border-error text-error"
            >
              <MaterialIcon
                name="stop"
                className="text-[18px]"
              />

              Stop generation
            </button>
          </div>
        ) : (
          <button
            type="button"
            disabled={!choice}
            onClick={() => {
              void handleGenerate()
            }}
            className={cn(
              'flex h-10 w-full items-center justify-center gap-xs rounded-lg font-label-md text-label-md transition-all',
              choice
                ? 'cursor-pointer bg-primary text-on-primary hover:bg-primary/90'
                : 'cursor-not-allowed bg-surface-variant text-on-surface-variant opacity-70',
            )}
          >
            <MaterialIcon
              name="auto_awesome"
              className="text-[18px]"
            />

            Generate
          </button>
        )}
      </div>
    </div>
  )
}