import {
  getAccountSubtitle,
  getAccountTitle,
  type ConnectedAccount,
} from '../../lib/accounts'
import { MaterialIcon } from '../ui/MaterialIcon'

type DeleteAccountModalProps = {
  account: ConnectedAccount
  isDeleting?: boolean
  error?: string
  onCancel: () => void
  onConfirm: () => void
}

export function DeleteAccountModal({
  account,
  isDeleting = false,
  error = '',
  onCancel,
  onConfirm,
}: DeleteAccountModalProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-on-surface/40 px-lg">
      <button
        type="button"
        className="absolute inset-0 cursor-default"
        aria-label="Close dialog"
        disabled={isDeleting}
        onClick={onCancel}
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="delete-account-title"
        className="relative z-10 w-full max-w-md rounded-xl bg-surface-container-lowest p-lg shadow-lg"
      >
        <h2 id="delete-account-title" className="mb-xs font-headline-sm text-headline-sm text-on-surface">
          Delete this account?
        </h2>
        <p className="mb-md font-body-md text-body-md text-on-surface-variant">
          This permanently removes the account from your workspace. You&apos;ll need to connect it again to use it.
        </p>

        <div className="mb-lg rounded-xl bg-surface-container p-md">
          <p className="mb-sm font-label-sm text-label-sm text-on-surface-variant">Account to delete</p>
          <div className="flex items-start justify-between gap-md">
            <div>
              <p className="font-headline-sm text-headline-sm text-on-surface">{getAccountTitle(account)}</p>
              <p className="font-body-md text-body-md text-on-surface-variant">{getAccountSubtitle(account)}</p>
            </div>
            <div
              className={`flex shrink-0 items-center gap-1 rounded-full px-3 py-1 font-label-sm text-label-sm ${
                account.is_enabled
                  ? 'bg-primary-fixed/20 text-on-primary-fixed'
                  : 'bg-surface-container-high text-on-surface-variant'
              }`}
            >
              {account.is_enabled ? <span className="h-1.5 w-1.5 rounded-full bg-primary" /> : null}
              {account.is_enabled ? 'Connected' : 'Disconnected'}
            </div>
          </div>
        </div>

        {error ? <p className="mb-md font-body-md text-body-md text-error">{error}</p> : null}

        <div className="flex gap-sm">
          <button
            type="button"
            disabled={isDeleting}
            onClick={onCancel}
            className="flex flex-1 items-center justify-center rounded-lg bg-surface-container-high py-2 font-label-md text-label-md text-on-surface transition-colors hover:bg-surface-variant disabled:cursor-not-allowed disabled:opacity-60"
          >
            Cancel
          </button>
          <button
            type="button"
            disabled={isDeleting}
            onClick={onConfirm}
            className="flex flex-1 items-center justify-center gap-2 rounded-lg bg-error py-2 font-label-md text-label-md text-on-primary transition-colors hover:bg-error/90 disabled:cursor-not-allowed disabled:opacity-60"
          >
            <MaterialIcon name="delete" className="text-[18px]" />
            {isDeleting ? 'Deleting...' : 'Yes, delete'}
          </button>
        </div>
      </div>
    </div>
  )
}
