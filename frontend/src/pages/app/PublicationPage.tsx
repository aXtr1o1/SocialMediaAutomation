import { useLocation, useNavigate } from "react-router-dom";
import { useConnectedAccounts } from "../../hooks/useConnectedAccounts";
import { isReviewState, type GeneratedPost, type GeneratePlatform, type GenerationDraft } from "../../lib/generations";
import { useMemo, useState } from "react";
import { getAccountPlatformId, getAccountSubtitle, getAccountTitle, type ConnectedAccount } from "../../lib/accounts";
import { paths } from "../../lib/paths";
import { MaterialIcon } from "../../components/ui/MaterialIcon";
import { LinkedInIcon } from "../../assets/icons/LinkedInIcon";
import { BlueskyIcon } from "../../assets/icons/BlueskyIcon";
import { publishMultiplePosts, publishPost , type PublicationResponse} from "../../lib/publications";


type ReviewPublicationState = {
    posts: GeneratedPost[],
    drafts?: GenerationDraft[],
}

function PlatformIcon({ platform }: { platform: GeneratePlatform }) {
    if (platform === 'linkedin') {
        return (
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#0077b5] text-white">
            <LinkedInIcon className="h-5 w-5" />
        </div>
        )
    }

    return (
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#0085FF] text-white">
        <BlueskyIcon className="h-6 w-6" />
        </div>
    )
}

function platformName(platform: GeneratePlatform) {
    return platform === 'linkedin' ? 'LinkedIn' : 'Bluesky'
}

function isEligibleAccount(account: ConnectedAccount, platform: GeneratePlatform) {
    return (
        account.is_enabled && getAccountPlatformId(account) === platform
    )
}

export function PublicationPage() {
    const location = useLocation();
    const navigate = useNavigate();

    const {accounts, isLoading: accountsLoading, error: accountsError} = useConnectedAccounts()

    const review =  isReviewState(location.state) ? (location.state as ReviewPublicationState) : null

    const posts = review?.posts ?? []
    const drafts = review?.drafts ?? []

    const [selectedAccounts, setSelectedAccounts] = useState<Record<string, boolean>>({})

    const [isPublishing, setIsPublishing] = useState(false)
    const [publicationResults, setPublicationResults] = useState<PublicationResponse[]>([])
    const [publicationError, setPublicationError] = useState('')

    const availablePlatforms = useMemo<GeneratePlatform[]>(() => {
        const platforms: GeneratePlatform[] = []

        if(posts.some(post => post.platform === 'linkedin')) {
            platforms.push('linkedin')
        }
        if(posts.some(post => post.platform === 'bluesky')) {
            platforms.push('bluesky')
        }
        return platforms 
    },  [posts])

    const accountsByPlatform = useMemo(() => {
        const result: Record<GeneratePlatform, ConnectedAccount[]> = {
            linkedin: [],
            bluesky: [],
        }
        for (const platform of availablePlatforms) {
            result[platform] = accounts.filter(account => isEligibleAccount(account, platform))
        }
        return result
    }, [accounts, availablePlatforms])

    const publishablePlatforms = useMemo(() => {
        return availablePlatforms.filter((platform) => {
            const draft = drafts.find((item) => item.platform === platform)
            return Boolean(
                draft?.id && draft.current_version_id && accountsByPlatform[platform].length > 0
            )
        })
    }, [availablePlatforms, drafts, accountsByPlatform])

    const selectedAccountIds = useMemo(() => 
        Object.entries(selectedAccounts)
            .filter(([_, selected]) => selected)
            .map(([accountId, _]) => accountId), 
        [selectedAccounts],
    )


    const allSelected = selectedAccountIds.length > 0 && selectedAccountIds.length === accountsByPlatform.linkedin.length + accountsByPlatform.bluesky.length

    function toggleAccount(accountId: string) {
        setSelectedAccounts((current) => ({
            ...current,
            [accountId]: !current[accountId]
        }))
    }

    function toggleAll() {
        if(allSelected) {
            setSelectedAccounts({})
            return
        }

        const next: Record<string, boolean> = {}
        
        for (const account of accounts) {
        if (
            account.is_enabled &&
            getAccountPlatformId(account) &&
            availablePlatforms.includes(
            getAccountPlatformId(account) as GeneratePlatform,
            )
        ) {
            next[account.id] = true
        }
        }
        setSelectedAccounts(next)
    }

    async function handlePublish() {
        if (selectedAccountIds.length === 0) {
            setPublicationError('Select at least one account to publish to.')
            return
        }

        setPublicationError('')
        setPublicationResults([])
        setIsPublishing(true)
        try{


            const publications = selectedAccountIds.map((accountId) => {
                const account = accounts.find((item) => item.id === accountId)

                if (!account) {return null}

                const platform = getAccountPlatformId(account)

                if (platform !== 'linkedin' && platform !== 'bluesky') {return null}

                const draft = drafts.find((item) => item.platform === platform)

                if (!draft || !draft.id || !draft.current_version_id) {return null}

                return {
                    draft_id: draft.id,
                    connected_account_id: account.id,
                }
            }).filter((item): item is { draft_id: string; connected_account_id: string } => item !== null)
            
            if (publications.length === 0) {
                throw new Error('No valid publications to publish.')
            }

            let results: PublicationResponse[]

            if (publications.length === 1) {
                const result = await publishPost(publications[0])

                results = [result]
            } else {
                const result = await publishMultiplePosts(publications)

                results = result.publications
            }

            setPublicationResults(results)
        } catch (caught) {
            setPublicationError(
                caught instanceof Error
                ? caught.message
                : 'Could not publish the selected posts.',
            )
        } finally {
            setIsPublishing(false)
        }
    }

    if (!review) {
        return (
        <div className="mx-auto flex w-full max-w-5xl flex-col gap-md p-xl">
            <h1 className="font-headline-md text-headline-md text-on-surface">
            Publish
            </h1>

            <p className="font-body-md text-body-md text-on-surface-variant">
            No generated posts were provided. Return to generation review
            and choose the content you want to publish.
            </p>

            <button
            type="button"
            onClick={() => navigate(paths.generations)}
            className="mt-md w-fit rounded-lg bg-primary px-lg py-3 font-label-md text-label-md text-on-primary transition-colors hover:bg-primary/90"
            >
            Back to Review
            </button>
        </div>
        )
    }

    const totalConnectedAccounts =
        accountsByPlatform.linkedin.length +
        accountsByPlatform.bluesky.length

    const canPublish =
        !accountsLoading &&
        publishablePlatforms.length > 0 &&
        selectedAccountIds.length > 0 &&
        !isPublishing

    return (
        <div className="flex w-full flex-col pb-28">
        {/* Header */}
        <div className="flex flex-col gap-sm px-xl py-lg">
            <button
            type="button"
            onClick={() => navigate(-1)}
            className="mb-xs inline-flex w-fit items-center gap-xs text-on-surface-variant transition-colors hover:text-on-surface"
            >
            <MaterialIcon
                name="arrow_back"
                className="text-[18px]"
            />
            <span className="font-label-md text-label-md">
                Back
            </span>
            </button>

            <h1 className="font-headline-md text-headline-md text-on-surface">
            Publish
            </h1>

            <p className="max-w-2xl font-body-md text-body-md text-on-surface-variant">
            Choose the connected social accounts where you want to
            publish the reviewed content.
            </p>
        </div>

        {/* Errors */}
        {accountsError ? (
            <div className="mx-xl mb-md rounded-lg border border-error/30 bg-error-container/20 px-md py-sm">
            <p className="font-body-md text-body-md text-error">
                {accountsError}
            </p>
            </div>
        ) : null}

        {publicationError ? (
            <div className="mx-xl mb-md flex items-start justify-between gap-md rounded-lg border border-error/30 bg-error-container/20 px-md py-sm">
            <p className="font-body-md text-body-md text-error">
                {publicationError}
            </p>

            <button
                type="button"
                onClick={() => setPublicationError('')}
                className="shrink-0 font-label-md text-label-md text-on-surface-variant hover:text-on-surface"
            >
                Dismiss
            </button>
            </div>
        ) : null}

        {/* Content */}
        <div className="flex flex-col gap-lg px-xl">
            {/* Generated content summary */}
            <section className="rounded-2xl bg-surface-container-lowest p-lg shadow-sm">
            <div className="mb-md flex items-center justify-between gap-md">
                <div>
                <h2 className="font-headline-sm text-headline-sm text-on-surface">
                    Content to publish
                </h2>

                <p className="mt-xs font-body-sm text-body-sm text-on-surface-variant">
                    The currently selected version of each generated post
                    will be published.
                </p>
                </div>
            </div>
        <div className="grid gap-md md:grid-cols-2">
            {availablePlatforms.map((platform) => {
              const post = posts.find(
                (item) => item.platform === platform,
              )

              const draft = drafts.find(
                (item) => item.platform === platform,
              )

              const currentVersion = draft?.versions.find(
                (version) =>
                  version.id === draft.current_version_id,
              )

              const previewText =
                currentVersion?.full_post ||
                post?.full_post ||
                ''

              return (
                <div
                  key={platform}
                  className="rounded-xl bg-surface-container p-md"
                >
                  <div className="mb-sm flex items-center gap-sm">
                    <PlatformIcon platform={platform} />

                    <div>
                      <h3 className="font-label-lg text-label-lg text-on-surface">
                        {platformName(platform)}
                      </h3>

                      {currentVersion ? (
                        <p className="font-body-sm text-body-sm text-on-surface-variant">
                          Version {currentVersion.version}
                        </p>
                      ) : null}
                    </div>
                  </div>

                  <p className="line-clamp-5 whitespace-pre-wrap font-body-md text-body-md text-on-surface-variant">
                    {previewText}
                  </p>
                </div>
              )
            })}
          </div>
        </section>

        {/* Account selection */}
        <section className="rounded-2xl bg-surface-container-lowest p-lg shadow-sm">
          <div className="mb-lg flex items-center justify-between gap-md">
            <div>
              <h2 className="font-headline-sm text-headline-sm text-on-surface">
                Publish to
              </h2>

              <p className="mt-xs font-body-sm text-body-sm text-on-surface-variant">
                {accountsLoading
                  ? 'Loading connected accounts...'
                  : `${totalConnectedAccounts} connected account${
                      totalConnectedAccounts === 1 ? '' : 's'
                    } available`}
              </p>
            </div>

            {!accountsLoading && totalConnectedAccounts > 0 ? (
              <button
                type="button"
                onClick={toggleAll}
                className="font-label-md text-label-md text-primary hover:underline"
              >
                {allSelected ? 'Clear all' : 'Select all'}
              </button>
            ) : null}
          </div>

          {accountsLoading ? (
            <div className="py-xl text-center">
              <p className="font-body-md text-body-md text-on-surface-variant">
                Loading accounts...
              </p>
            </div>
          ) : totalConnectedAccounts === 0 ? (
            <div className="rounded-xl bg-surface-container p-lg text-center">
              <MaterialIcon
                name="link_off"
                className="mb-sm text-[28px] text-on-surface-variant"
              />

              <h3 className="font-headline-sm text-headline-sm text-on-surface">
                No connected accounts
              </h3>

              <p className="mx-auto mt-xs max-w-md font-body-md text-body-md text-on-surface-variant">
                Connect a LinkedIn or Bluesky account before
                publishing.
              </p>

              <button
                type="button"
                onClick={() =>
                  navigate(paths.connectedAccounts)
                }
                className="mt-md rounded-lg bg-primary px-lg py-3 font-label-md text-label-md text-on-primary hover:bg-primary/90"
              >
                Manage Accounts
              </button>
            </div>
          ) : (
            <div className="flex flex-col gap-lg">
              {availablePlatforms.map((platform) => {
                const platformAccounts =
                  accountsByPlatform[platform]

                return (
                  <div key={platform}>
                    <div className="mb-sm flex items-center gap-sm">
                      <PlatformIcon platform={platform} />

                      <h3 className="font-label-lg text-label-lg text-on-surface">
                        {platformName(platform)}
                      </h3>
                    </div>

                    {platformAccounts.length === 0 ? (
                      <div className="rounded-xl bg-surface-container p-md">
                        <p className="font-body-md text-body-md text-on-surface-variant">
                          No connected {platformName(platform)}{' '}
                          account is available.
                        </p>
                      </div>
                    ) : (
                      <div className="grid gap-sm md:grid-cols-2 lg:grid-cols-3">
                        {platformAccounts.map((account) => {
                          const selected =
                            Boolean(selectedAccounts[account.id])

                          return (
                            <button
                              key={account.id}
                              type="button"
                              onClick={() =>
                                toggleAccount(account.id)
                              }
                              className={`flex items-center gap-md rounded-xl border p-md text-left transition-all ${
                                selected
                                  ? 'border-primary bg-primary/10 shadow-sm'
                                  : 'border-surface-variant bg-surface-container hover:border-primary/40 hover:bg-surface-container-high'
                              }`}
                            >
                              <div
                                className={`flex h-5 w-5 shrink-0 items-center justify-center rounded border ${
                                  selected
                                    ? 'border-primary bg-primary text-on-primary'
                                    : 'border-outline'
                                }`}
                              >
                                {selected ? (
                                  <MaterialIcon
                                    name="check"
                                    className="text-[14px]"
                                  />
                                ) : null}
                              </div>

                              <div className="min-w-0 flex-1">
                                <p className="truncate font-label-md text-label-md text-on-surface">
                                  {getAccountTitle(account)}
                                </p>

                                <p className="truncate font-body-sm text-body-sm text-on-surface-variant">
                                  {getAccountSubtitle(account)}
                                </p>
                              </div>
                            </button>
                          )
                        })}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </section>

        {/* Selection summary */}
        <section className="rounded-xl bg-surface-container p-md">
          <div className="flex items-center gap-sm">
            <MaterialIcon
              name="info"
              className="text-[18px] text-primary"
            />

            <p className="font-body-md text-body-md text-on-surface-variant">
              {selectedAccountIds.length === 0
                ? 'Select one or more accounts to publish.'
                : `${selectedAccountIds.length} account${
                    selectedAccountIds.length === 1
                      ? ''
                      : 's'
                  } selected for publishing.`}
            </p>
          </div>
        </section>
      </div>

      {/* Bottom action bar */}
      <div className="fixed bottom-0 left-64 right-0 z-40 flex items-center justify-between border-t border-surface-variant bg-surface/80 p-4 backdrop-blur-xl">
        <div>
          {publicationResults.length > 0 ? (
            <p className="font-body-md text-body-md text-primary">
              {publicationResults.length} publication
              {publicationResults.length === 1 ? '' : 's'} processed.
            </p>
          ) : (
            <p className="font-body-md text-body-md text-on-surface-variant">
              {selectedAccountIds.length} selected
            </p>
          )}
        </div>

        <button
          type="button"
          disabled={!canPublish}
          onClick={() => {
            void handlePublish()
          }}
          className="flex h-12 items-center justify-center rounded-full bg-primary px-xl font-semibold text-on-primary shadow-md shadow-primary/20 transition-colors hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <MaterialIcon
            name={isPublishing ? 'progress_activity' : 'send'}
            className={`mr-2 text-[20px] ${
              isPublishing ? 'animate-spin' : ''
            }`}
          />

          {isPublishing
            ? 'Publishing...'
            : selectedAccountIds.length > 1
              ? `Publish to ${selectedAccountIds.length} accounts`
              : 'Publish'}
        </button>
      </div>
    </div>
  )
}