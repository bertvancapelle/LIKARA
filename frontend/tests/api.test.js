/**
 * Tests — api.js foutcontract (ADR-014): 401 status-gebaseerd, 422 native detail.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import { api } from '@/api'
import { useAuthStore } from '@/store/auth'

function _resp({ status, body }) {
  return {
    status,
    ok: status >= 200 && status < 300,
    json: () => Promise.resolve(body),
  }
}

beforeEach(() => {
  setActivePinia(createPinia())
})
afterEach(() => {
  vi.unstubAllGlobals()
})

describe('api.request — 401 (status-gebaseerd)', () => {
  it('herkent 401 met envelope NIET_GEAUTHENTICEERD (status, niet code)', async () => {
    vi.stubGlobal('fetch', vi.fn(() =>
      Promise.resolve(_resp({ status: 401, body: { fout: { code: 'NIET_GEAUTHENTICEERD', http_status: 401, bericht: 'x' } } })),
    ))
    await expect(api.componenten.lijst()).rejects.toMatchObject({
      message: 'NIET_GEAUTHENTICEERD',
      status: 401,
      code: 'NIET_GEAUTHENTICEERD',
    })
  })

  it('behandelt 401 met code ID_TOKEN_ONGELDIG identiek (status-gebaseerd)', async () => {
    vi.stubGlobal('fetch', vi.fn(() =>
      Promise.resolve(_resp({ status: 401, body: { fout: { code: 'ID_TOKEN_ONGELDIG', http_status: 401, bericht: 'x' } } })),
    ))
    // Zelfde signaal (message), status 401 — alleen de code verschilt.
    await expect(api.componenten.haal('id')).rejects.toMatchObject({
      message: 'NIET_GEAUTHENTICEERD',
      status: 401,
      code: 'ID_TOKEN_ONGELDIG',
    })
  })
})

describe('api.request — 422 (bewust native detail)', () => {
  it('behoudt de detail-lijst voor veldmapping (CD003/CD004-formulieren)', async () => {
    const detail = [{ loc: ['body', 'naam'], msg: 'verplicht', type: 'missing' }]
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve(_resp({ status: 422, body: { detail } }))))
    await expect(
      api.componenten.maak({ naam: '' }),
    ).rejects.toMatchObject({ status: 422, detail })
  })
})

describe('store.fetchSession — sessie-verloop op status', () => {
  it('zet user op null bij een 401 (ongeacht body-vorm)', async () => {
    vi.stubGlobal('fetch', vi.fn(() =>
      Promise.resolve(_resp({ status: 401, body: { fout: { code: 'NIET_GEAUTHENTICEERD' } } })),
    ))
    const auth = useAuthStore()
    auth.user = { sub: 's', email: 'a@b.nl', roles: [] }
    await auth.fetchSession()
    expect(auth.user).toBeNull()
    expect(auth.isAuthenticated).toBe(false)
  })

  it('zet user bij een geldige sessie (200)', async () => {
    const user = { sub: 's', tenant_id: 't', email: 'a@b.nl', roles: ['beheerder'] }
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve(_resp({ status: 200, body: user }))))
    const auth = useAuthStore()
    await auth.fetchSession()
    expect(auth.user).toEqual(user)
    expect(auth.isAuthenticated).toBe(true)
  })
})

describe('api.request — single-flight refresh-on-401 (ADR-015 B6)', () => {
  it('vernieuwt bij 401 en herprobeert de originele request', async () => {
    let dataCalls = 0
    let refreshCalls = 0
    vi.stubGlobal('fetch', vi.fn((url) => {
      if (url.endsWith('/auth/refresh')) {
        refreshCalls++
        return Promise.resolve(_resp({ status: 204, body: null }))
      }
      dataCalls++
      return Promise.resolve(
        dataCalls === 1
          ? _resp({ status: 401, body: { fout: { code: 'NIET_GEAUTHENTICEERD' } } })
          : _resp({ status: 200, body: { items: [], volgende_cursor: null } }),
      )
    }))
    const res = await api.componenten.lijst()
    expect(refreshCalls).toBe(1)
    expect(res).toEqual({ items: [], volgende_cursor: null })
  })

  it('valt terug op sessie-verloop als refresh faalt (geen lus)', async () => {
    let dataCalls = 0
    let refreshCalls = 0
    vi.stubGlobal('fetch', vi.fn((url) => {
      if (url.endsWith('/auth/refresh')) {
        refreshCalls++
        return Promise.resolve(_resp({ status: 401, body: { fout: { code: 'NIET_GEAUTHENTICEERD' } } }))
      }
      dataCalls++
      return Promise.resolve(_resp({ status: 401, body: { fout: { code: 'NIET_GEAUTHENTICEERD' } } }))
    }))
    await expect(api.componenten.lijst()).rejects.toMatchObject({
      status: 401,
      code: 'NIET_GEAUTHENTICEERD',
    })
    expect(refreshCalls).toBe(1) // precies één poging
    expect(dataCalls).toBe(1) // geen retry want refresh faalde → geen lus
  })

  it('deelt één refresh-poging bij gelijktijdige 401\'s (single-flight)', async () => {
    let refreshCalls = 0
    const perUrl = {}
    vi.stubGlobal('fetch', vi.fn((url) => {
      if (url.endsWith('/auth/refresh')) {
        refreshCalls++
        return Promise.resolve(_resp({ status: 204, body: null }))
      }
      perUrl[url] = (perUrl[url] || 0) + 1
      return Promise.resolve(
        perUrl[url] === 1
          ? _resp({ status: 401, body: { fout: { code: 'NIET_GEAUTHENTICEERD' } } })
          : _resp({ status: 200, body: { ok: true } }),
      )
    }))
    const [a, b] = await Promise.all([api.componenten.haal('1'), api.componenten.haal('2')])
    expect(refreshCalls).toBe(1) // één refresh voor beide gelijktijdige 401's
    expect(a).toEqual({ ok: true })
    expect(b).toEqual({ ok: true })
  })
})
