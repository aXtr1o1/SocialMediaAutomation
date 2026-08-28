import { Link } from 'react-router-dom'
import { MaterialIcon } from '../ui/MaterialIcon'
import { paths } from '../../lib/paths'

export function AddAccountCard() {
  return (
    <Link
      className="group flex min-h-[220px] flex-col items-center justify-center rounded-xl border-2 border-dashed border-surface-variant bg-surface p-md transition-all hover:border-primary hover:bg-primary/5"
      to={paths.connectAccount}
    >
      <div className="mb-sm flex h-12 w-12 items-center justify-center rounded-full bg-surface-container-high transition-colors group-hover:bg-primary/20 group-hover:text-primary">
        <MaterialIcon name="add" className="text-[24px]" />
      </div>
      <h3 className="mb-xs font-headline-sm text-headline-sm text-on-surface">Add Account</h3>
      <p className="max-w-[220px] text-center font-body-md text-body-md text-on-surface-variant">
        Add another profile. Only one LinkedIn and one Bluesky account can be connected at a time.
      </p>
    </Link>
  )
}
