import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import PrimeVue from 'primevue/config'

// useRoute mocken zodat we de query (sessie_verlopen / next) per test sturen.
let mockQuery = {}
vi.mock('vue-router', () => ({
  useRoute: () => ({ query: mockQuery }),
}))

import LoginView from './LoginView.vue'

let assignMock

function mountView() {
  return mount(LoginView, {
    global: { plugins: [[PrimeVue, { unstyled: true }]] },
  })
}

beforeEach(() => {
  mockQuery = {}
  assignMock = vi.fn()
  vi.stubGlobal('location', { assign: assignMock, href: 'http://localhost:3000/login' })
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('LoginView', () => {
  it('rendert de Inloggen-knop', () => {
    const w = mountView()
    const knop = w.find('[data-testid="inloggen-knop"]')
    expect(knop.exists()).toBe(true)
    expect(w.text()).toContain('Inloggen')
  })

  it('start de Keycloak-redirect naar het backend-login-endpoint bij klik', async () => {
    const w = mountView()
    await w.find('[data-testid="inloggen-knop"]').trigger('click')
    expect(assignMock).toHaveBeenCalledTimes(1)
    expect(assignMock).toHaveBeenCalledWith('/api/v1/auth/login')
  })

  it('geeft een geldig same-origin next-pad door', async () => {
    mockQuery = { next: '/dashboard' }
    const w = mountView()
    await w.find('[data-testid="inloggen-knop"]').trigger('click')
    expect(assignMock).toHaveBeenCalledWith(
      `/api/v1/auth/login?next=${encodeURIComponent('/dashboard')}`,
    )
  })

  it('negeert een onveilig next-pad (open-redirect-bescherming)', async () => {
    mockQuery = { next: 'https://evil.example/phish' }
    const w = mountView()
    await w.find('[data-testid="inloggen-knop"]').trigger('click')
    expect(assignMock).toHaveBeenCalledWith('/api/v1/auth/login')
  })

  it('negeert een protocol-relatief next-pad (//evil)', async () => {
    mockQuery = { next: '//evil.example' }
    const w = mountView()
    await w.find('[data-testid="inloggen-knop"]').trigger('click')
    expect(assignMock).toHaveBeenCalledWith('/api/v1/auth/login')
  })

  it('toont de sessie-verlopen-melding bij ?sessie_verlopen=1', () => {
    mockQuery = { sessie_verlopen: '1' }
    const w = mountView()
    const melding = w.find('[data-testid="sessie-verlopen"]')
    expect(melding.exists()).toBe(true)
    expect(melding.attributes('role')).toBe('alert')
  })

  it('toont de melding niet zonder sessie_verlopen', () => {
    const w = mountView()
    expect(w.find('[data-testid="sessie-verlopen"]').exists()).toBe(false)
  })

  it('toont een laadstatus en blokkeert de knop na klik', async () => {
    const w = mountView()
    await w.find('[data-testid="inloggen-knop"]').trigger('click')
    expect(w.find('[data-testid="bezig"]').exists()).toBe(true)
    expect(w.find('[data-testid="inloggen-knop"]').attributes('disabled')).toBeDefined()
  })
})
