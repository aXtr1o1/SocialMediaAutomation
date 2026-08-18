import type { ReactNode } from 'react'
import { cn } from '../../lib/cn'

type AuthCardProps = {
  children: ReactNode
  className?: string
  contentClassName?: string
}

export function AuthCard({ children, className, contentClassName }: AuthCardProps) {
  return (
    <div className={cn('relative overflow-hidden bg-surface-container-lowest', className)}>
      <div className="absolute left-0 top-0 h-[4px] w-full bg-primary" />
      <div className={cn('relative z-10 flex flex-col', contentClassName)}>{children}</div>
    </div>
  )
}
