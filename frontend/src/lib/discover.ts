import { supabase } from './supabaseClient'

export type DomainRow = {
  id: string
  name: string
  description: string
}

export type SubdomainRow = {
  id: string
  name: string
  description: string
  domainId: string
}

type DomainRecord = {
  id: string | number
  name: string | null
  description: string | null
}

type SubdomainRecord = {
  id: string | number
  name: string | null
  description: string | null
  domain_id: string | number | null
}

function asText(value: string | null | undefined) {
  return value?.trim() ?? ''
}

function asId(value: string | number | null | undefined) {
  return value == null ? '' : String(value)
}

export function getDomainIcon(name: string) {
  const normalized = name.trim().toLowerCase()

  if (normalized.includes('artificial intelligence') || /\bai\b/.test(normalized)) {
    return 'psychology'
  }

  if (normalized.includes('machine learning') || normalized.includes('data')) {
    return 'analytics'
  }

  if (normalized.includes('security') || normalized.includes('cyber')) {
    return 'security'
  }

  if (normalized.includes('cloud') || normalized.includes('infrastructure')) {
    return 'cloud'
  }

  if (normalized.includes('design') || normalized.includes('product')) {
    return 'design_services'
  }

  if (normalized.includes('marketing') || normalized.includes('content')) {
    return 'campaign'
  }

  if (normalized.includes('finance') || normalized.includes('business')) {
    return 'payments'
  }

  return 'hub'
}

export async function fetchDiscoverCatalog() {
  const [domainsResult, subdomainsResult] = await Promise.all([
    supabase.from('domains').select('id, name, description').order('name'),
    supabase.from('subdomains').select('id, name, description, domain_id').order('name'),
  ])

  if (domainsResult.error) {
    throw domainsResult.error
  }

  if (subdomainsResult.error) {
    throw subdomainsResult.error
  }

  const domains = ((domainsResult.data ?? []) as DomainRecord[]).map((row) => ({
    id: asId(row.id),
    name: asText(row.name),
    description: asText(row.description),
  }))

  const subdomains = ((subdomainsResult.data ?? []) as SubdomainRecord[])
    .map((row) => ({
      id: asId(row.id),
      name: asText(row.name),
      description: asText(row.description),
      domainId: asId(row.domain_id),
    }))
    .filter((row) => row.id && row.domainId)

  return { domains, subdomains }
}
