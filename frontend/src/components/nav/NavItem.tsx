import { NavLink } from 'react-router-dom'
import { cn } from '../../lib/cn'
import { MaterialIcon } from '../ui/MaterialIcon'

type NavItemProps = {
  to: string
  icon: string
  label: string
}

export function NavItem({ to, icon, label }: NavItemProps) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        cn(
          'group flex items-center rounded-lg px-3 py-2 transition-all',
          isActive
            ? 'bg-surface-container-high font-semibold text-on-surface'
            : 'text-on-surface-variant hover:bg-surface-container hover:text-on-surface',
        )
      }
    >
      <MaterialIcon name={icon} className="mr-3 text-[20px]" />
      <span className="font-body-md">{label}</span>
    </NavLink>
  )
}
