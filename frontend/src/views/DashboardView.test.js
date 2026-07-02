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
  readiness_per_type: [
    {
      componenttype: 'applicatie',
      componenttype_label: 'Applicatie',
      telling: { concept: 3, in_inventarisatie: 2, geblokkeerd: 1, migratieklaar: 4 },
      totaal: 10,
      migratieklaar: 4,
    },
    {
      componenttype: 'database',
      componenttype_label: 'Database',
      telling: { concept: 1, in_inventarisatie: 0, geblokkeerd: 0, migratieklaar: 2 },
      totaal: 3,
      migratieklaar: 2,
    },
  ],
  open_blokkades: 5,
  recent_gewijzigd: [
    { id: 'a1', naam: 'Zaaksysteem', lifecycle_status: 'geblokkeerd', gewijzigd_op: '2026-06-07T10:00:00Z' },
    { id: 'a2', naam: 'DMS', lifecycle_status: 'migratieklaar', gewijzigd_op: '2026-06-06T09:00:00Z' },
  ],
  klaar_verklaard: 7,
  klaar_met_afwijking: 2,
}

function maakRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'dashboard', component: DashboardView },
      { path: '/applicaties/:id', name: 'applicatie-detail', component: { template: '<div/>' } },
      { path: '/componenten/:id', name: 'component-detail', component: { template: '<div/>' } },
      { path: '/blokkades', name: 'blokkades', component: { template: '<div/>' } },
      { path: '/componenten', name: 'component-lijst', component: { template: '<div/>' } },
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
  it('rendert per type een readiness-blok met label, tellingen en de "n van m"-rollup', async () => {
    const w = await mountDashboard()
    const blok = w.find('[data-testid="readiness-type-applicatie"]')
    expect(blok.exists()).toBe(true)
    expect(blok.text()).toContain('Applicatie')
    expect(blok.find('[data-testid="telling-applicatie-concept"]').text()).toContain('3')
    expect(blok.find('[data-testid="telling-applicatie-geblokkeerd"]').text()).toContain('1')
    expect(blok.find('[data-testid="telling-applicatie-migratieklaar"]').text()).toContain('4')
    const rollup = w.find('[data-testid="readiness-rollup-applicatie"]')
    expect(rollup.exists()).toBe(true)
    expect(rollup.text()).toContain('4 van 10 migratieklaar')
  })

  it('B3: kop is "Gereedheid per componenttype" (geen "Readiness")', async () => {
    const w = await mountDashboard()
    expect(w.find('#dashboard-readiness-titel').text()).toBe('Gereedheid per componenttype')
    expect(w.text()).not.toContain('Readiness')
  })

  it('statustegel is een doorklik-link naar de componentenlijst met status + type', async () => {
    const w = await mountDashboard()
    const tegel = w.find('[data-testid="telling-applicatie-geblokkeerd"]')
    expect(tegel.exists()).toBe(true)
    // Klikbare tegel = een <a> met de juiste query (exacte tegel-match: status + type).
    expect(tegel.element.tagName).toBe('A')
    const href = tegel.attributes('href')
    expect(href).toContain('/componenten')
    expect(href).toContain('status=geblokkeerd')
    expect(href).toContain('type=applicatie')
  })

  it('rendert twee verschillende typen als twee gescheiden blokken (geen vermenging)', async () => {
    const w = await mountDashboard()
    const blokken = w.findAll('[data-testid^="readiness-type-"]')
    expect(blokken).toHaveLength(2)
    const db = w.find('[data-testid="readiness-type-database"]')
    expect(db.exists()).toBe(true)
    expect(db.text()).toContain('Database')
    // De database-telling staat in het database-blok, niet in het applicatie-blok.
    expect(db.find('[data-testid="telling-database-migratieklaar"]').text()).toContain('2')
    expect(w.find('[data-testid="readiness-rollup-database"]').text()).toContain('2 van 3 migratieklaar')
    expect(w.find('[data-testid="readiness-type-applicatie"]').find('[data-testid="telling-database-migratieklaar"]').exists()).toBe(false)
  })

  it('defaultt ontbrekende statussen naar 0 in de telling', async () => {
    const w = await mountDashboard()
    const db = w.find('[data-testid="readiness-type-database"]')
    expect(db.find('[data-testid="telling-database-in_inventarisatie"]').text()).toContain('0')
  })

  it('toont de open-blokkades-teller als doorklik naar het blokkadesoverzicht', async () => {
    const w = await mountDashboard()
    const teller = w.find('[data-testid="open-blokkades"]')
    expect(teller.exists()).toBe(true)
    expect(teller.text()).toContain('5')
    expect(teller.text()).toContain('actieve blokkades')
    // doorklik naar de blokkades-route met het actieve-statusfilter voorgeselecteerd
    expect(teller.attributes('href')).toContain('/blokkades')
    expect(teller.attributes('href')).toContain('status=actief')
  })

  it('toont de recent gewijzigde applicaties met links naar detail', async () => {
    const w = await mountDashboard()
    const links = w.findAll('[data-testid="recent-link"]')
    expect(links).toHaveLength(2)
    expect(links[0].text()).toBe('Zaaksysteem')
    expect(links[0].attributes('href')).toContain('/componenten/a1')
  })
})

describe('DashboardView — laad/leeg/fout', () => {
  it('toont een laadindicatie vóór de respons', async () => {
    api.dashboard.mockReturnValue(new Promise(() => {})) // nooit resolved
    const w = await mountDashboard({ flush: false })
    expect(w.find('[data-testid="dashboard-laden"]').exists()).toBe(true)
  })

  it('toont een lege-staat als er geen recent gewijzigde componenten zijn', async () => {
    api.dashboard.mockResolvedValue({
      readiness_per_type: [],
      open_blokkades: 0,
      recent_gewijzigd: [],
    })
    const w = await mountDashboard()
    expect(w.find('[data-testid="recent-leeg"]').exists()).toBe(true)
    expect(w.find('[data-testid="recent-lijst"]').exists()).toBe(false)
  })

  it('toont een lege-staat als er geen beoordeelde componenttypen zijn', async () => {
    api.dashboard.mockResolvedValue({
      readiness_per_type: [],
      open_blokkades: 0,
      recent_gewijzigd: [],
    })
    const w = await mountDashboard()
    expect(w.find('[data-testid="readiness-leeg"]').exists()).toBe(true)
    expect(w.findAll('[data-testid^="readiness-type-"]')).toHaveLength(0)
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

describe('DashboardView — ADR-027 slice 3 klaarverklaring-voortgang', () => {
  it('toont de twee tellingen met doorklik naar de gefilterde componentlijst', async () => {
    const w = await mountDashboard()
    const klaar = w.find('[data-testid="telling-klaar-verklaard"]')
    const afw = w.find('[data-testid="telling-klaar-afwijking"]')
    expect(klaar.text()).toContain('7')
    expect(afw.text()).toContain('2')
    // doorklik-queries
    expect(klaar.attributes('href')).toContain('klaarverklaring=klaar')
    expect(afw.attributes('href')).toContain('afwijking=1')
  })

  it('afwijkingstegel krijgt nadruk (warn) bij >0 en is niet alleen-kleur (label + icoon)', async () => {
    const w = await mountDashboard()
    const afw = w.find('[data-testid="telling-klaar-afwijking"]')
    expect(afw.text()).toContain('checklist nog niet compleet') // tekstueel, niet alleen kleur
    expect(afw.html()).toContain('var(--lk-color-warn)')
  })

  it('afwijkingstegel zonder afwijking: neutrale weergave (0)', async () => {
    api.dashboard.mockResolvedValue({ ...VOORBEELD, klaar_met_afwijking: 0 })
    const w = await mountDashboard()
    const afw = w.find('[data-testid="telling-klaar-afwijking"]')
    expect(afw.text()).toContain('0')
    // bij 0: neutrale (muted) telling i.p.v. warn-nadruk
    expect(afw.html()).toContain('var(--lk-color-text-muted)')
    expect(afw.attributes('class')).toContain('var(--lk-color-surface)')
  })
})
