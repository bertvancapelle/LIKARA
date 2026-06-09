/** Tests — sessietype-bewuste routeringsbeslissing (ADR-019 fase 2E-b). */
import { describe, expect, it } from 'vitest'

import { routeBeslissing } from '@/router'

const auth = (over = {}) => ({
  isAuthenticated: true,
  sessionType: 'tenant',
  hasRole: () => true,
  ...over,
})

describe('routeBeslissing', () => {
  it('publieke route → altijd toegestaan', () => {
    expect(routeBeslissing({ meta: { public: true } }, auth({ isAuthenticated: false }))).toBe(true)
  })

  it('niet ingelogd → naar login', () => {
    expect(routeBeslissing({ meta: {} }, auth({ isAuthenticated: false }))).toEqual({
      name: 'login',
      query: { sessie_verlopen: '1' },
    })
  })

  it('tenant-sessie op platform-route → terug naar /', () => {
    expect(routeBeslissing({ meta: { platform: true } }, auth({ sessionType: 'tenant' }))).toEqual({
      path: '/',
    })
  })

  it('platform-sessie op tenant-route → naar /beheer', () => {
    expect(routeBeslissing({ meta: {} }, auth({ sessionType: 'platform' }))).toEqual({
      path: '/beheer',
    })
  })

  it('platform-sessie op platform-route → toegestaan', () => {
    expect(routeBeslissing({ meta: { platform: true } }, auth({ sessionType: 'platform' }))).toBe(true)
  })

  it('tenant-sessie op tenant-route → toegestaan', () => {
    expect(routeBeslissing({ meta: {} }, auth({ sessionType: 'tenant' }))).toBe(true)
  })

  it('rol-gating: ontbrekende rol → verboden', () => {
    expect(
      routeBeslissing({ meta: { roles: ['x'] } }, auth({ sessionType: 'tenant', hasRole: () => false })),
    ).toEqual({ name: 'verboden' })
  })
})
