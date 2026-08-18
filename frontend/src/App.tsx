import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { GuestRoute, ProtectedRoute } from './components/AuthRoutes'
import { AppShell } from './components/layout/AppShell'
import { AuthProvider } from './context/AuthContext'
import { ThemeProvider } from './context/ThemeContext'
import { paths } from './lib/paths'
import { AuthCallbackPage } from './pages/AuthCallbackPage'
import { ConnectedAccountsPage } from './pages/app/ConnectedAccountsPage'
import { ConnectAccountPage } from './pages/app/ConnectAccountPage'
import { DiscoverPage } from './pages/app/DiscoverPage'
import { PlaceholderPage } from './pages/app/PlaceholderPage'
import { ProfilePage } from './pages/app/ProfilePage'
import { SignInPage } from './pages/SignInPage'
import { SignUpPage } from './pages/SignUpPage'

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path={paths.callback} element={<AuthCallbackPage />} />
            <Route
              path={paths.signIn}
              element={
                <GuestRoute>
                  <SignInPage />
                </GuestRoute>
              }
            />
            <Route
              path={paths.signUp}
              element={
                <GuestRoute>
                  <SignUpPage />
                </GuestRoute>
              }
            />
            <Route
              element={
                <ProtectedRoute>
                  <AppShell />
                </ProtectedRoute>
              }
            >
              <Route path={paths.home} element={<Navigate to={paths.connectedAccounts} replace />} />
              <Route path={paths.connectedAccounts} element={<ConnectedAccountsPage />} />
              <Route path={paths.connectAccount} element={<ConnectAccountPage />} />
              <Route path={paths.discover} element={<DiscoverPage />} />
              <Route path={paths.profile} element={<ProfilePage />} />
              <Route
                path={paths.publicationHistory}
                element={
                  <PlaceholderPage
                    title="Publication History"
                    description="See what has already been published from this workspace."
                  />
                }
              />
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  )
}
