/** Tests — OP-16: tenantId-getter leest tenant_id; thema-doorwerking. */
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import { useAuthStore } from '@/store/auth'
import { useTheme } from '@/composables/useTheme'

beforeEach(() => {
  setActivePinia(createPinia())
})
afterEach(() => {
  // Opruimen van eventueel toegevoegde thema-links.
  document.head.querySelectorAll('link[rel="stylesheet"]').forEach((l) => l.remove())
})

describe('auth.tenantId (OP-16)', () => {
  it('geeft het tenant_id terug (niet null) — was tenant_slug', () => {
    const auth = useAuthStore()
    auth.user = { sub: 's', tenant_id: '11111111-1111-1111-1111-111111111111', email: 'a@b.nl', roles: [] }
    expect(auth.tenantId).toBe('11111111-1111-1111-1111-111111111111')
  })

  it('valt terug op null zonder sessie/veld (geen crash)', () => {
    const auth = useAuthStore()
    expect(auth.tenantId).toBeNull()
    auth.user = { sub: 's', email: 'a@b.nl', roles: [] } // geen tenant_id
    expect(auth.tenantId).toBeNull()
  })
})

describe('useTheme — thema-doorwerking op tenantId', () => {
  it('bouwt de thema-href uit de (niet-null) tenant-identifier', () => {
    const auth = useAuthStore()
    auth.user = { sub: 's', tenant_id: 'tenant-x', email: 'a@b.nl', roles: [] }
    useTheme(auth.tenantId) // promise resolvet pas bij load; we checken het <link>
    const link = document.head.querySelector('link[rel="stylesheet"]')
    expect(link).not.toBeNull()
    expect(link.getAttribute('href')).toBe('/themes/tenant-x.css')
  })
})
