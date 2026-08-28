export type ConnectPlatform = {
  id: 'linkedin' | 'bluesky'
  name: string
  description: string
  actionLabel: string
  accentClass: string
  glowClass: string
  buttonClass: string
}

export const CONNECT_PLATFORMS: ConnectPlatform[] = [
  {
    id: 'linkedin',
    name: 'LinkedIn',
    description: 'Publish professional posts to your LinkedIn page and track engagement metrics.',
    actionLabel: 'Connect with LinkedIn',
    accentClass: 'text-[#0077B5]',
    glowClass: 'bg-[#0077B5]/5 group-hover:bg-[#0077B5]/10',
    buttonClass: 'bg-[#0077B5] hover:bg-[#0077B5]/90',
  },
  {
    id: 'bluesky',
    name: 'Bluesky',
    description: 'Share short-form updates to your Bluesky feed directly from SMAP.',
    actionLabel: 'Connect with Bluesky',
    accentClass: 'text-[#0085FF]',
    glowClass: 'bg-[#0085FF]/5 group-hover:bg-[#0085FF]/10',
    buttonClass: 'bg-[#0085FF] hover:bg-[#0085FF]/90',
  },
]
