/**
 * Tests — DashboardView (CD014, #9): tenant-breed overzicht.
 *
 * api gemockt (geen echte fetch), memory-router voor de recent-links,
 * PrimeVue (unstyled) voor Tag. Gedekt: begroeting/rollen, lifecycle-telling,
 * open-blokkades, recent-lijst, en het laad-/leeg-/foutpad.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'

vi.mock('@/api', () => ({
  api: { dashboard: vi.fn() },
}))

import { api } from '@/api'
import DashboardView from './DashboardView.vue'
import { useAuthStore } from '../store/auth'

const VOORBEELD = {
  lifecycle_telling: { concept: 3, in_inventarisatie: 2, geblokkeerd: 1, migratieklaar: 4 },
  open_blokkades: 5,
  recent_gewijzigd: [
    { id: 'a1', naam: 'Zaaksysteem', lifecycle_status: 'geblokkeerd', gewijzigd_op: '2026-06-07T10:00:00Z' },
    { id: 'a2', naam: 'DMS', lifecycle_status: 'migratieklaar', gewijzigd_op: '2026-06-06T09:00:00Z' },
  ],
}

function maakRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'dashboard', component: DashboardView },
      { path: '/applicaties/:id', name: 'applicatie-detail', component: { template: '<div/>' } },
      { path: '/blokkades', name: 'blokkades', component: { template: '<div/>' } },
    ],
  })
}

async function mountDashboard({ user = { email: 'jan@example.nl', roles: ['medewerker'] }, flush = true } = {}) {
  const router = maakRouter()
  await router.push('/')
  await router.isReady()
  const pinia = createPinia()
  const auth = useAuthStore(pinia)
  auth.user = user
  const wrapper = mount(DashboardView, {
    global: { plugins: [pinia, [PrimeVue, { unstyled: true }], router] },
  })
  if (flush) await flushPromises()
  return wrapper
}

afterEach(() => {
  vi.clearAllMocks()
})
beforeEach(() => {
  api.dashboard.mockResolvedValue(VOORBEELD)
})

describe('DashboardView — begroeting', () => {
  it('begroet de ingelogde gebruiker met e-mail', async () => {
    const w = await mountDashboard({ user: { email: 'jan@example.nl', roles: ['medewerker'] } })
    expect(w.text()).toContain('Welkom')
    expect(w.text()).toContain('jan@example.nl')
  })

  it('toont de rol(len) van de gebruiker', async () => {
    const w = await mountDashboard({ user: { email: 'a@b.nl', roles: ['beheerder', 'auditor'] } })
    const rollen = w.find('[data-testid="dashboard-rollen"]')
    expect(rollen.exists()).toBe(true)
    expect(rollen.text()).toContain('beheerder')
    expect(rollen.text()).toContain('auditor')
  })

  it('toont geen rol-regel zonder rollen', async () => {
    const w = await mountDashboard({ user: { email: 'a@b.nl', roles: [] } })
    expect(w.find('[data-testid="dashboard-rollen"]').exists()).toBe(false)
  })
})

describe('DashboardView — data', () => {
  it('toont de lifecycle-telling per status', async () => {
    const w = await mountDashboard()
    expect(w.find('[data-testid="lifecycle-telling"]').exists()).toBe(true)
    expect(w.find('[data-testid="telling-concept"]').text()).toContain('3')
    expect(w.find('[data-testid="telling-geblokkeerd"]').text()).toContain('1')
    expect(w.find('[data-testid="telling-migratieklaar"]').text()).toContain('4')
  })

  it('toont de open-blokkades-teller als doorklik naar het blokkadesoverzicht', async () => {
    const w = await mountDashboard()
    const teller = w.find('[data-testid="open-blokkades"]')
    expect(teller.exists()).toBe(true)
    expect(teller.text()).toContain('5')
    expect(teller.text()).toContain('open blokkades')
    // doorklik naar de blokkades-route met het actieve-statusfilter voorgeselecteerd
    expect(teller.attributes('href')).toContain('/blokkades')
    expect(teller.attributes('href')).toContain('status=actief')
  })

  it('toont de recent gewijzigde applicaties met links naar detail', async () => {
    const w = await mountDashboard()
    const links = w.findAll('[data-testid="recent-link"]')
    expect(links).toHaveLength(2)
    expect(links[0].text()).toBe('Zaaksysteem')
    expect(links[0].attributes('href')).toContain('/applicaties/a1')
  })
})

describe('DashboardView — laad/leeg/fout', () => {
  it('toont een laadindicatie vóór de respons', async () => {
    api.dashboard.mockReturnValue(new Promise(() => {})) // nooit resolved
    const w = await mountDashboard({ flush: false })
    expect(w.find('[data-testid="dashboard-laden"]').exists()).toBe(true)
  })

  it('toont een lege-staat als er geen recent gewijzigde applicaties zijn', async () => {
    api.dashboard.mockResolvedValue({
      lifecycle_telling: { concept: 0, in_inventarisatie: 0, geblokkeerd: 0, migratieklaar: 0 },
      open_blokkades: 0,
      recent_gewijzigd: [],
    })
    const w = await mountDashboard()
    expect(w.find('[data-testid="recent-leeg"]').exists()).toBe(true)
    expect(w.find('[data-testid="recent-lijst"]').exists()).toBe(false)
  })

  it('toont een foutmelding in role="alert" bij een fout', async () => {
    api.dashboard.mockRejectedValue(new Error('Boem'))
    const w = await mountDashboard()
    const fout = w.find('[data-testid="dashboard-fout"]')
    expect(fout.exists()).toBe(true)
    expect(fout.attributes('role')).toBe('alert')
    expect(fout.text()).toContain('Boem')
  })
})
