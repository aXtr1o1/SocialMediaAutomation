import { paths } from '../../lib/paths'
import { NavItem } from '../nav/NavItem'

export function Sidebar() {
  return (
    <aside className="fixed left-0 top-0 z-50 flex h-full w-64 flex-col border-r border-surface-variant bg-surface-container-lowest">
      <div className="flex items-center gap-3 px-6 py-8">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-sm font-semibold text-on-primary">
          S
        </div>
        <span className="font-headline-sm text-headline-sm tracking-tight text-on-surface">SMAP</span>
      </div>

      <nav className="flex-1 space-y-1 px-3">
        <NavItem to={paths.discover} icon="explore" label="Discover" />
        <NavItem to={paths.connectedAccounts} icon="link" label="Connected Accounts" />
        <NavItem to={paths.publicationHistory} icon="history" label="Publication History" />
      </nav>
    </aside>
  )
}
