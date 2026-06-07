/** Tests — RP-initiated logout-flow (OP-4): store.logout(). */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import { useAuthStore } from '@/store/auth'

let navigatedTo
let origLocation

beforeEach(() => {
  setActivePinia(createPinia())
  navigatedTo = null
  origLocation = Object.getOwnPropertyDescriptor(window, 'location')
  Object.defineProperty(window, 'location', {
    configurable: true,
    value: {
      set href(v) {
        navigatedTo = v
      },
      get href() {
        return navigatedTo
      },
    },
  })
})

afterEach(() => {
  vi.unstubAllGlobals()
  if (origLocation) Object.defineProperty(window, 'location', origLocation)
})

function _stubFetch(impl) {
  vi.stubGlobal('fetch', vi.fn(impl))
}

describe('store.logout — RP-initiated', () => {
  it('navigeert naar de Keycloak end-session-URL en reset de auth-state', async () => {
    const url = 'http://localhost:8080/realms/complidata/protocol/openid-connect/logout?client_id=x'
    const calls = []
    _stubFetch((u) => {
      calls.push(u)
      return Promise.resolve({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ status: 'uitgelogd', keycloak_logout_url: url }),
      })
    })

    const auth = useAuthStore()
    auth.user = { sub: 's', tenant_id: 't', email: 'a@b.nl', roles: ['beheerder'] }
    await auth.logout()

    expect(auth.user).toBeNull() // lokale state direct gereset
    expect(navigatedTo).toBe(url) // doorgestuurd naar Keycloak end-session
    // logout gaat via store-fetch, NIET via api.request → geen refresh-on-401
    expect(calls).toEqual(['/api/v1/auth/logout'])
    expect(calls.some((u) => String(u).includes('/auth/refresh'))).toBe(false)
  })

  it('valt terug op /login als er geen keycloak_logout_url is', async () => {
    _stubFetch(() =>
      Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({ status: 'uitgelogd' }) }),
    )
    const auth = useAuthStore()
    auth.user = { sub: 's', email: 'a@b.nl', roles: [] }
    await auth.logout()
    expect(auth.user).toBeNull()
    expect(navigatedTo).toBe('/login')
  })
})
