import { Link } from 'react-router-dom'
import { MaterialIcon } from '../../components/ui/MaterialIcon'
import { paths } from '../../lib/paths'

export function ConnectedAccountsPage() {
  return (
    <div className="flex h-full w-full flex-1 flex-col">
      <div className="w-full px-lg py-xl">
        <h1 className="mb-xs font-display-lg text-display-lg text-on-surface">Connected Accounts</h1>
        <p className="max-w-2xl font-body-md text-body-md text-on-surface-variant">
          Manage the social profiles linked to your SMAP workspace. Ensure connections remain active to avoid
          publishing interruptions.
        </p>
      </div>

      <div className="flex w-full flex-1 flex-col items-center justify-center p-lg">
        <Link
          className="group flex w-full max-w-[400px] flex-col items-center justify-center rounded-2xl border-2 border-dashed border-outline-variant bg-surface-container-lowest px-8 py-12 shadow-sm transition-all hover:border-primary hover:bg-primary/5"
          to={paths.connectAccount}
        >
          <div className="mb-md flex h-16 w-16 items-center justify-center rounded-full bg-primary/10 transition-all group-hover:scale-105 group-hover:bg-primary/20">
            <MaterialIcon name="add" className="text-[32px] text-primary" />
          </div>
          <h3 className="mb-xs font-headline-md text-headline-md font-semibold text-on-surface">Add Account</h3>
          <p className="max-w-[240px] text-center font-body-md text-body-md text-on-surface-variant">
            Connect a new social profile to your workspace.
          </p>
        </Link>

        <Link
          className="mt-lg font-body-md text-on-surface-variant underline transition-colors hover:text-on-surface"
          to={paths.discover}
        >
          Skip for now
        </Link>
      </div>
    </div>
  )
}
