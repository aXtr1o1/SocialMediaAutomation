import type { ReactNode } from 'react'
import { cn } from '../../lib/cn'
import { ThemeToggle } from '../ui/ThemeToggle'

type AuthLayoutProps = {
  children?: ReactNode
  className?: string
}

export function AuthLayout({ children, className }: AuthLayoutProps) {
  return (
    <main className={cn('relative flex min-h-screen w-full items-center justify-center p-4', className)}>
      <div className="absolute right-4 top-4 z-50">
        <ThemeToggle />
      </div>
      {children}
    </main>
  )
}
