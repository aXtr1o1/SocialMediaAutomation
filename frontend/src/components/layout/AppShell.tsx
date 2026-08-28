import { Outlet } from 'react-router-dom'
import { Header } from './Header'
import { Sidebar } from './Sidebar'

export function AppShell() {
  return (
    <div className="min-h-screen bg-background font-body-md text-on-surface">
      <Sidebar />
      <div className="flex min-h-screen flex-col pl-64">
        <Header />
        <main className="flex h-full w-full flex-1 flex-col bg-surface pt-16">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
