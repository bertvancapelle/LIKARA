/** Tests — sessietype-detectie in de auth-store (ADR-019 fase 2E-b). */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import { useAuthStore } from '@/store/auth'

beforeEach(() => setActivePinia(createPinia()))
afterEach(() => vi.unstubAllGlobals())

function _stubFetch(map) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (url) => {
      for (const sleutel of Object.keys(map)) if (url.includes(sleutel)) return map[sleutel]
      return { ok: false, status: 404, json: async () => ({}) }
    }),
  )
}

const _ok = (body) => ({ ok: true, status: 200, json: async () => body })
const _fail = (status) => ({ ok: false, status, json: async () => ({}) })

describe('auth.fetchSession — sessietype', () => {
  it('tenant: /auth/me ok → sessionType=tenant', async () => {
    _stubFetch({
      '/auth/platform/me': _fail(403),
      '/auth/me': _ok({ sub: 't', tenant_id: 'x', email: 't@x.nl', roles: ['beheerder'] }),
    })
    const auth = useAuthStore()
    await auth.fetchSession()
    expect(auth.sessionType).toBe('tenant')
    expect(auth.isTenant).toBe(true)
    expect(auth.isPlatform).toBe(false)
    expect(auth.tenantId).toBe('x')
  })

  it('platform: /auth/me 403 → val terug op /auth/platform/me → sessionType=platform', async () => {
    _stubFetch({
      '/auth/platform/me': _ok({ sub: 'p', email: 'p@x.nl', roles: ['platformbeheerder'] }),
      '/auth/me': _fail(403),
    })
    const auth = useAuthStore()
    await auth.fetchSession()
    expect(auth.sessionType).toBe('platform')
    expect(auth.isPlatform).toBe(true)
    expect(auth.tenantId).toBeNull()
    expect(auth.hasRole('platformbeheerder')).toBe(true)
  })

  it('geen sessie: beide falen → null', async () => {
    _stubFetch({ '/auth/platform/me': _fail(401), '/auth/me': _fail(401) })
    const auth = useAuthStore()
    await auth.fetchSession()
    expect(auth.user).toBeNull()
    expect(auth.sessionType).toBeNull()
    expect(auth.isAuthenticated).toBe(false)
  })
})
