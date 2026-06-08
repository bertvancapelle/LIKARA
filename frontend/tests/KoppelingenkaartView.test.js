/** Tests — KoppelingenkaartView (CD023, #13): ego-graaf-mapping + interactie + a11y. */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'

vi.mock('@/api', () => ({
  api: {
    applicaties: { lijst: vi.fn() },
    koppelingen: { lijst: vi.fn() },
  },
}))

import { api } from '@/api'
import KoppelingenkaartView from '@/views/KoppelingenkaartView.vue'

const APPS = [
  { id: 'a1', naam: 'Zaaksysteem', lifecycle_status: 'concept', hostingmodel: 'saas' },
  { id: 'a2', naam: 'DMS', lifecycle_status: 'in_inventarisatie', hostingmodel: 'on_premise' },
  { id: 'a3', naam: 'GIS', lifecycle_status: 'concept', hostingmodel: 'saas' },
]
const UIT_A1 = {
  id: 'k1', bron_applicatie_id: 'a1', doel_applicatie_id: 'a2',
  tegenpartij_naam: 'DMS', richting: 'eenrichting', protocol: 'api', impact_bij_verbreking: 'hoog',
}
const IN_A1 = {
  id: 'k2', bron_applicatie_id: 'a3', doel_applicatie_id: 'a1',
  tegenpartij_naam: 'GIS', richting: 'tweerichting', protocol: 'database_link', impact_bij_verbreking: 'midden',
}

async function mountKaart({ query = '' } = {}) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/koppelingenkaart', name: 'koppelingenkaart', component: KoppelingenkaartView },
      { path: '/applicaties/:id', name: 'applicatie-detail', component: { template: '<div/>' }, props: true },
    ],
  })
  await router.push(`/koppelingenkaart${query}`)
  await router.isReady()
  const wrapper = mount(KoppelingenkaartView, {
    global: { plugins: [createPinia(), [PrimeVue, { unstyled: true }], router] },
  })
  await flushPromises()
  await flushPromises() // watch(geselecteerd) → laadRelaties
  return wrapper
}

beforeEach(() => {
  vi.clearAllMocks()
  api.applicaties.lijst.mockResolvedValue({ items: APPS, volgende_cursor: null })
  api.koppelingen.lijst.mockImplementation(({ bronApplicatieId, doelApplicatieId }) => {
    if (bronApplicatieId === 'a1') return Promise.resolve({ items: [UIT_A1], volgende_cursor: null })
    if (doelApplicatieId === 'a1') return Promise.resolve({ items: [IN_A1], volgende_cursor: null })
    return Promise.resolve({ items: [], volgende_cursor: null })
  })
})
afterEach(() => vi.restoreAllMocks())

describe('KoppelingenkaartView', () => {
  it('vult de app-kiezer en selecteert de eerste applicatie als default', async () => {
    const w = await mountKaart()
    expect(w.find('[data-testid="kaart-app-select"]').findAll('option').length).toBe(3)
    expect(w.text()).toContain('Zaaksysteem')
  })

  it('SVG is role=img met een samenvattende aria-label (toegankelijke verrijking)', async () => {
    const w = await mountKaart()
    const svg = w.find('[data-testid="kaart-svg"]')
    expect(svg.attributes('role')).toBe('img')
    expect(svg.attributes('aria-label')).toContain('Zaaksysteem')
    expect(svg.attributes('aria-label')).toContain('1 inkomend')
    expect(svg.attributes('aria-label')).toContain('1 uitgaand')
  })

  it('relatietabel toont de uitgaande koppeling (tegenpartij/protocol/impact)', async () => {
    const w = await mountKaart()
    const rij = w.find('[data-testid="kaart-rij-k1"]')
    expect(rij.exists()).toBe(true)
    expect(rij.text()).toContain('DMS')
    expect(rij.text()).toContain('API')
  })

  it('AppTabs-wissel naar Inkomend toont de inkomende koppeling', async () => {
    const w = await mountKaart()
    await w.find('[data-testid="kaartrel-tab-inkomend"]').trigger('click')
    await flushPromises()
    expect(w.find('[data-testid="kaart-rij-k2"]').exists()).toBe(true)
    expect(w.find('[data-testid="kaart-rij-k2"]').text()).toContain('GIS')
  })

  it('hercentreren via de tabel laadt de relaties van de tegenpartij', async () => {
    const w = await mountKaart()
    await w.find('[data-testid="kaart-hercentreer-k1"]').trigger('click') // tegenpartij = a2 (doel)
    await flushPromises()
    const params = api.koppelingen.lijst.mock.calls.map((c) => c[0])
    expect(params.some((p) => p.bronApplicatieId === 'a2')).toBe(true)
    expect(params.some((p) => p.doelApplicatieId === 'a2')).toBe(true)
  })

  it('deep-link ?app=a2 selecteert die applicatie', async () => {
    const w = await mountKaart({ query: '?app=a2' })
    expect(w.find('[data-testid="kaart-app-select"]').element.value).toBe('a2')
    expect(w.text()).toContain('DMS')
  })
})
