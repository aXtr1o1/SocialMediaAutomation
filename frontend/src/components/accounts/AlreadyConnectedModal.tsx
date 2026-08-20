import {
  getAccountPlatformName,
  getAccountSubtitle,
  getAccountTitle,
  type ConnectedAccount,
} from '../../lib/accounts'
import { MaterialIcon } from '../ui/MaterialIcon'

type AlreadyConnectedModalProps = {
  account: ConnectedAccount
  onClose: () => void
}

export function AlreadyConnectedModal({ account, onClose }: AlreadyConnectedModalProps) {
  const platformName = getAccountPlatformName(account)

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-on-surface/40 px-lg">
      <button
        type="button"
        className="absolute inset-0 cursor-default"
        aria-label="Close dialog"
        onClick={onClose}
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="already-connected-title"
        className="relative z-10 w-full max-w-md rounded-xl bg-surface-container-lowest p-lg shadow-lg"
      >
        <h2 id="already-connected-title" className="mb-xs font-headline-sm text-headline-sm text-on-surface">
          An account is already connected
        </h2>
        <p className="mb-md font-body-md text-body-md text-on-surface-variant">
          Only one {platformName} account can be connected at a time. Disconnect this account first, then connect the
          other one.
        </p>

        <div className="mb-lg rounded-xl bg-surface-container p-md">
          <p className="mb-sm font-label-sm text-label-sm text-on-surface-variant">Currently connected</p>
          <div className="flex items-start justify-between gap-md">
            <div>
              <p className="font-headline-sm text-headline-sm text-on-surface">{getAccountTitle(account)}</p>
              <p className="font-body-md text-body-md text-on-surface-variant">{getAccountSubtitle(account)}</p>
            </div>
            <div className="flex shrink-0 items-center gap-1 rounded-full bg-primary-fixed/20 px-3 py-1 font-label-sm text-label-sm text-on-primary-fixed">
              <span className="h-1.5 w-1.5 rounded-full bg-primary" />
              Connected
            </div>
          </div>
        </div>

        <button
          type="button"
          onClick={onClose}
          className="flex w-full items-center justify-center gap-2 rounded-lg bg-primary py-2 font-label-md text-label-md text-on-primary"
        >
          <MaterialIcon name="check" className="text-[18px]" />
          Got it
        </button>
      </div>
    </div>
  )
}
