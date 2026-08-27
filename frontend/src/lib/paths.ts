export const paths = {
  home: '/',
  signIn: '/signin',
  signUp: '/signup',
  forgotPassword: '/forgot-password',
  callback: '/auth/callback',
  connectedAccounts: '/connected-accounts',
  connectAccount: '/connected-accounts/connect',
  discover: '/discover',
  sources: '/sources',
  generations: '/generations',
  generationsCompose: '/generations/compose',
  publicationHistory: '/publication-history',
  profile: '/profile',
} as const

export const POST_LOGIN_PATH = paths.connectedAccounts
