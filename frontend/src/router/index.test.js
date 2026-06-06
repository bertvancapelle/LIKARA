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
})
