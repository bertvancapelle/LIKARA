import { describe, expect, it } from 'vitest'
import { router } from './index'

describe('router-structuur', () => {
  it('plaatst dashboard als geauthenticeerde child onder de app-shell (requiresAuth)', () => {
    const resolved = router.resolve({ name: 'dashboard' })
    // requiresAuth erft via de meta-merge van de parent (AppLayout).
    expect(resolved.meta.requiresAuth).toBe(true)
    expect(resolved.meta.public).toBeUndefined()
    // Twee matched records: parent-layout + dashboard-child.
    expect(resolved.matched.length).toBe(2)
  })

  it('houdt login publiek en standalone (geen app-shell, geen requiresAuth)', () => {
    const resolved = router.resolve({ name: 'login' })
    expect(resolved.meta.public).toBe(true)
    expect(resolved.meta.requiresAuth).toBeUndefined()
    expect(resolved.matched.length).toBe(1)
  })

  it('houdt de publieke auth-callback- en verboden-routes standalone', () => {
    expect(router.resolve({ name: 'auth-callback' }).meta.public).toBe(true)
    expect(router.resolve({ name: 'verboden' }).meta.public).toBe(true)
  })

  it('leidt /applicaties (lijst) door naar Componenten met typefilter=applicatie (CD054b W1)', () => {
    // De oude Applicaties-lijst is opgegaan in de verenigde Componenten-lijst;
    // de naam blijft bestaan zodat bestaande navigaties/bookmarks niet breken.
    // (router.resolve volgt geen redirect — we inspecteren de route-definitie zelf.)
    const route = router.getRoutes().find((r) => r.name === 'applicatie-lijst')
    expect(route.redirect).toEqual({ name: 'component-lijst', query: { type: 'applicatie' } })
  })

  it('behoudt het rijke applicatie-detail (/applicaties/:id) als subtype-view', () => {
    const resolved = router.resolve({ name: 'applicatie-detail', params: { id: 'x' } })
    expect(resolved.name).toBe('applicatie-detail')
    expect(resolved.matched.length).toBe(2)
  })
})
