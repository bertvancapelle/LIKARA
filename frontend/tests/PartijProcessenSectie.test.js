/** Tests — PartijProcessenSectie (ADR-042 slice 5): afgeleid organisatie-procesbeeld. */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'

vi.mock('@/api', () => ({
  api: { partijen: { processen: vi.fn() } },
}))

import { api } from '@/api'
import PartijProcessenSectie from '@modules/bwb_ontvlechting/frontend/views/PartijProcessenSectie.vue'

const _BEELD = [
  {
    proces_id: 'vv',
    proces_naam: 'Vergunningverlening',
    proces_ouder_naam: null,
    component_aantal: 3,
    componenten: [
      { component_id: 'zs', component_naam: 'Zaaksysteem', componenttype: 'applicatie', componenttype_label: 'Applicatie' },
      { component_id: 'db', component_naam: 'Shared DB', componenttype: 'database', componenttype_label: 'Database' },
      { component_id: 'dms', component_naam: 'DMS', componenttype: 'applicatie', componenttype_label: 'Applicatie' },
    ],
  },
  {
    proces_id: 'ab',
    proces_naam: 'Aanvraag behandelen',
    proces_ouder_naam: 'Vergunningverlening',
    component_aantal: 1,
    componenten: [
      { component_id: 'zs', component_naam: 'Zaaksysteem', componenttype: 'applicatie', componenttype_label: 'Applicatie' },
    ],
  },
]

function maakRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'dashboard', component: { template: '<div/>' } },
      { path: '/processen/:id', name: 'proces-detail', component: { template: '<div/>' } },
      { path: '/componenten/:id', name: 'component-detail', component: { template: '<div/>' } },
    ],
  })
}

async function mountSectie({ partijId = 'org1' } = {}) {
  const router = maakRouter()
  await router.push('/')
  await router.isReady()
  const w = mount(PartijProcessenSectie, {
    props: { partijId },
    attachTo: document.body,
    global: { plugins: [createPinia(), [PrimeVue, { unstyled: true }], router] },
  })
  await flushPromises()
  return w
}

beforeEach(() => {
  vi.clearAllMocks()
  api.partijen.processen.mockResolvedValue(_BEELD)
})
afterEach(() => vi.restoreAllMocks())

describe('PartijProcessenSectie — afgeleid beeld', () => {
  it('toont per proces de telling en linkt de procesnaam door (mét ouder-context)', async () => {
    const w = await mountSectie()
    expect(api.partijen.processen).toHaveBeenCalledWith('org1')
    const regels = w.findAll('[data-testid^="pps-regel-"]')
    expect(regels).toHaveLength(2)
    expect(regels[0].find('[data-testid="pps-proces-link"]').attributes('href')).toContain('/processen/vv')
    expect(regels[0].find('[data-testid="pps-wissel-vv"]').text()).toContain('via 3 component(en)')
    // Ouder-context bij een deelproces.
    expect(regels[1].text()).toContain('Aanvraag behandelen')
    expect(regels[1].text()).toContain('— Vergunningverlening')
    expect(regels[1].find('[data-testid="pps-wissel-ab"]').text()).toContain('via 1 component(en)')
  })

  it('uitklap toont de brug-componenten, klikbaar naar het component', async () => {
    const w = await mountSectie()
    expect(w.find('[data-testid="pps-componenten-vv"]').exists()).toBe(false)
    const wissel = w.find('[data-testid="pps-wissel-vv"]')
    expect(wissel.attributes('aria-expanded')).toBe('false')
    await wissel.trigger('click')
    expect(w.find('[data-testid="pps-wissel-vv"]').attributes('aria-expanded')).toBe('true')
    const uitklap = w.find('[data-testid="pps-componenten-vv"]')
    expect(uitklap.exists()).toBe(true)
    const links = uitklap.findAll('[data-testid="pps-component-link"]')
    expect(links).toHaveLength(3)
    expect(links[0].attributes('href')).toContain('/componenten/zs')
    expect(uitklap.text()).toContain('(Database)') // type-label bij de brug-component
    // Andere regels blijven dicht (uitklap is per proces).
    expect(w.find('[data-testid="pps-componenten-ab"]').exists()).toBe(false)
  })

  it('heeft een (i)-uitleg die het als afgeleid beeld framet', async () => {
    const w = await mountSectie()
    const knop = w.find('[data-testid="uitleg-organisatie-processen-knop"]')
    expect(knop.exists()).toBe(true)
    await knop.trigger('click')
    const paneel = w.find('[data-testid="uitleg-organisatie-processen-paneel"]')
    expect(paneel.exists()).toBe(true)
    expect(paneel.text()).toContain('afgeleid')
    expect(paneel.text()).toContain('Hier wordt niets geregistreerd')
  })

  it('is read-only: geen bewerk- of verwijder-acties', async () => {
    const w = await mountSectie()
    const sectie = w.find('[data-testid="partij-processen-sectie"]')
    expect(sectie.text()).not.toContain('Bewerken')
    expect(sectie.text()).not.toContain('Verwijderen')
    expect(sectie.text()).not.toContain('Toevoegen')
  })

  it('rustige lege staat zonder componenten-brug', async () => {
    api.partijen.processen.mockResolvedValue([])
    const w = await mountSectie()
    expect(w.find('[data-testid="pps-leeg"]').text()).toContain('Nog geen processen via componenten van deze organisatie')
  })

  it('fout bij laden toont een MeldingBanner (geen stil falen)', async () => {
    api.partijen.processen.mockRejectedValue({ status: 500 })
    const w = await mountSectie()
    expect(w.find('[data-testid="pps-fout"]').exists()).toBe(true)
    expect(w.find('[data-testid="pps-fout"]').text()).toContain('mislukt')
  })
})
