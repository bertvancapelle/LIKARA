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

  it('leidt het oude /applicaties/:id door naar component-detail (LI059 Slice 4)', () => {
    // ApplicatieDetail is opgegaan in het generieke ComponentDetail; de oude route blijft
    // als redirect bestaan zodat bookmarks/deep-links niet breken (functie-redirect met id).
    const route = router.getRoutes().find((r) => r.name === 'applicatie-detail')
    expect(typeof route.redirect).toBe('function')
    expect(route.redirect({ params: { id: 'x' } })).toEqual({ name: 'component-detail', params: { id: 'x' } })
  })

  it('leidt /applicaties/nieuw en /:id/bewerken door naar de component-varianten (LI059)', () => {
    const nieuw = router.getRoutes().find((r) => r.name === 'applicatie-nieuw')
    expect(nieuw.redirect).toEqual({ name: 'component-nieuw' })
    const bewerken = router.getRoutes().find((r) => r.name === 'applicatie-bewerken')
    expect(bewerken.redirect({ params: { id: 'x' } })).toEqual({ name: 'component-bewerken', params: { id: 'x' } })
  })
})
