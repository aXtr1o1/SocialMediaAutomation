import { useEffect, useState } from 'react'
import {
  Link,
  useLocation,
} from 'react-router-dom'

import { SourceArticleCard } from '../../components/sources/SourceArticleCard'
import { SourcesLoadingCard } from '../../components/sources/SourcesLoadingCard'

import { useSourcesWorkflow } from '../../hooks/useSourcesWorkflow'

import { paths } from '../../lib/paths'

import {
  createNewSourcesSelection,
  getRememberedSourcesSelection,
  isSourcesSelection,
  rememberSourcesSelection,
  type SourcesSelection,
} from '../../lib/sources'

import { MaterialIcon } from '../../components/ui/MaterialIcon'

export function SourcesPage() {
  const location =
    useLocation()

  const locationSelection =
    isSourcesSelection(
      location.state,
    )
      ? location.state
      : null

  /*
   * Keep the selection in React state.
   *
   * Do NOT calculate selection from location/sessionStorage
   * on every render.
   */
  const [selection, setSelection] =
    useState<SourcesSelection | null>(
      () =>
        locationSelection ??
        getRememberedSourcesSelection(),
    )

  /*
   * This is a UI-level guard against any late backend
   * response reopening the search after the user clicked Stop.
   */
  const [searchStopped, setSearchStopped] =
    useState(
      () =>
        locationSelection?.searchStatus ===
          'CANCELLED' ||
        getRememberedSourcesSelection()
          ?.searchStatus ===
          'CANCELLED',
    )

  /*
   * If Discover sends us a genuinely new selection,
   * update the local selection.
   *
   * We do NOT do this on every render.
   */
  useEffect(() => {
    if (!locationSelection) {
      return
    }

    setSelection(
      (current) => {
        if (
          current?.runId ===
          locationSelection.runId
        ) {
          return current
        }

        setSearchStopped(
          locationSelection.searchStatus ===
            'CANCELLED',
        )

        rememberSourcesSelection(
          locationSelection,
        )

        return locationSelection
      },
    )
  }, [locationSelection?.runId])

  const {
    articles,
    domainName,
    isRunning,
    isCancelling,
    progress,
    jobStatus,
    error,
    stopWorkflow,
  } =
    useSourcesWorkflow(
      selection,
    )

  /*
   * Keep the stopped state explicit.
   *
   * This prevents a late polling response from making
   * the loading card appear again.
   */
  const showStoppedState =
    searchStopped ||
    jobStatus === 'CANCELLED' ||
    selection?.searchStatus ===
      'CANCELLED'

  const showLoading =
    Boolean(selection) &&
    isRunning &&
    !showStoppedState

  const selectedDomain =
    domainName ||
    selection?.domainName ||
    ''

  const selectedSubdomains = (
    selection?.subdomainNames ||
    []
  ).filter(Boolean)

  async function handleStop() {
    if (
      !selection ||
      isCancelling
    ) {
      return
    }

    /*
     * Immediately update the UI.
     */
    setSearchStopped(true)

    /*
     * Persist the selection immediately.
     */
    const cancelledSelection:
      SourcesSelection =
      {
        ...selection,

        searchStatus:
          'CANCELLED',

        workflowRunId:
          selection.workflowRunId ??
          null,
      }

    setSelection(
      cancelledSelection,
    )

    rememberSourcesSelection(
      cancelledSelection,
    )

    /*
     * Then perform backend cancellation.
     */
    await stopWorkflow()
  }

  function handleStartSearchAgain() {
    if (!selection) {
      return
    }

    /*
     * This is the ONLY action that creates a new
     * client source-search run.
     */
    const nextSelection =
      createNewSourcesSelection(
        selection,
      )

    /*
     * Immediately remove the stopped state.
     */
    setSearchStopped(false)

    /*
     * Replace the old cancelled run with the new one.
     */
    setSelection(
      nextSelection,
    )

    rememberSourcesSelection(
      nextSelection,
    )
  }

  if (!selection) {
    return (
      <div className="mx-auto flex w-full max-w-5xl flex-col gap-lg p-lg lg:p-xl">
        <h1 className="font-display-lg text-display-lg text-on-surface">
          Sources
        </h1>

        <p className="font-body-lg text-body-lg text-on-surface-variant">
          Select a domain and subdomains in Discover
          first, then continue here.
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
    <div className="mx-auto flex min-h-[calc(100vh-64px)] w-full max-w-5xl flex-col gap-lg p-lg lg:p-xl">
      {/* ------------------------------------------------------------------ */}
      {/* Header                                                             */}
      {/* ------------------------------------------------------------------ */}

      <div className="flex flex-col gap-md">
        <div className="flex flex-col gap-xs">
          <h1 className="font-display-lg text-display-lg text-on-surface">
            Sources
          </h1>

          <p className="font-body-lg text-body-lg text-on-surface-variant">
            Related content for your selected domain
            and subdomains.
          </p>
        </div>

        {/* -------------------------------------------------------------- */}
        {/* Selected topics                                                */}
        {/* -------------------------------------------------------------- */}

        <div className="rounded-xl border border-surface-variant bg-surface-container-lowest px-md py-md">
          <p className="font-label-sm text-label-sm uppercase tracking-widest text-on-surface-variant">
            Selected topics
          </p>

          <div className="mt-sm flex flex-col gap-sm">
            <div>
              <p className="font-label-md text-label-md text-on-surface-variant">
                Domain
              </p>

              <p className="mt-0.5 font-headline-sm text-headline-sm text-on-surface">
                {selectedDomain || '—'}
              </p>
            </div>

            <div>
              <p className="font-label-md text-label-md text-on-surface-variant">
                Subdomains
              </p>

              {selectedSubdomains.length ? (
                <ul className="mt-2 flex flex-wrap gap-2">
                  {selectedSubdomains.map(
                    (name) => (
                      <li
                        key={name}
                        className="rounded-md border border-surface-variant bg-surface px-2.5 py-1 font-label-md text-label-md text-on-surface"
                      >
                        {name}
                      </li>
                    ),
                  )}
                </ul>
              ) : (
                <p className="mt-0.5 font-body-md text-body-md text-on-surface-variant">
                  —
                </p>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Results status                                                    */}
      {/* ------------------------------------------------------------------ */}

      <div className="flex items-center justify-end border-b border-surface-variant py-sm">
        <div className="font-label-md text-label-md text-on-surface-variant">
          {showLoading
            ? 'Finding sources...'
            : `Showing ${articles.length} results`}
        </div>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Error                                                              */}
      {/* ------------------------------------------------------------------ */}

      {error ? (
        <p className="font-body-md text-body-md text-error">
          {error}
        </p>
      ) : null}

      {/* ------------------------------------------------------------------ */}
      {/* Loading                                                            */}
      {/* ------------------------------------------------------------------ */}

      {showLoading ? (
        <SourcesLoadingCard
          domainName={
            selectedDomain
          }
          subdomainNames={
            selectedSubdomains
          }
          progress={progress}
          onStop={() => {
            void handleStop()
          }}
          isStopping={
            isCancelling
          }
        />
      ) : null}

      {/* ------------------------------------------------------------------ */}
      {/* Explicitly stopped                                                */}
      {/* ------------------------------------------------------------------ */}

      {showStoppedState ? (
        <div className="flex flex-col items-center justify-center rounded-[14px] border border-surface-variant bg-surface-container-lowest px-lg py-10 text-center">
          <div className="flex h-14 w-14 items-center justify-center rounded-full bg-surface-container text-on-surface-variant">
            <MaterialIcon
              name="pause_circle"
              className="text-[28px]"
            />
          </div>

          <h2 className="mt-md font-headline-sm text-headline-sm text-on-surface">
            Search stopped
          </h2>

          <p className="mt-xs max-w-md font-body-md text-body-md text-on-surface-variant">
            The source search has been stopped.
            Nothing will restart automatically.
          </p>

          <button
            type="button"
            onClick={
              handleStartSearchAgain
            }
            className="mt-lg inline-flex h-11 items-center gap-2 rounded-lg bg-primary px-lg font-label-md text-label-md text-on-primary shadow-sm transition-colors hover:bg-primary/90"
          >
            <MaterialIcon
              name="refresh"
              className="text-[18px]"
            />

            Start Search Again
          </button>
        </div>
      ) : null}

      {/* ------------------------------------------------------------------ */}
      {/* No results                                                         */}
      {/* ------------------------------------------------------------------ */}

      {!showLoading &&
      !showStoppedState &&
      !error &&
      articles.length === 0 ? (
        <p className="font-body-md text-body-md text-on-surface-variant">
          No matching source material was found
          for this selection.
        </p>
      ) : null}

      {/* ------------------------------------------------------------------ */}
      {/* Articles                                                           */}
      {/* ------------------------------------------------------------------ */}

      <div className="flex flex-col gap-md">
        {articles.map(
          (article) => (
            <SourceArticleCard
              key={article.id}
              article={article}
              sourcesSelection={
                selection
              }
            />
          ),
        )}
      </div>
    </div>
  )
}