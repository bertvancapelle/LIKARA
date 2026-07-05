/** Tests — GebruikteApplicatiesSectie (LI033): één gedeeld blok voor organisatie + afdeling,
 *  op één bron per niveau, met de grof-only-markering en de kaart-doorklik. */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'

vi.mock('@/api', () => ({
  api: {
    organisatiegebruik: { lijstVoorOrganisatie: vi.fn() },
    gebruikersgroepen: { contextComponenten: vi.fn() },
  },
}))
vi.mock('@/composables/kaartHandoff', () => ({ zetKaartHandoff: vi.fn() }))

import { createMemoryHistory, createRouter } from 'vue-router'

import { api } from '@/api'
import { zetKaartHandoff } from '@/composables/kaartHandoff'
import GebruikteApplicatiesSectie from '@modules/bwb_ontvlechting/frontend/views/GebruikteApplicatiesSectie.vue'

const STUB = { template: '<div/>' }
let router

async function mountSectie(props) {
  const pinia = createPinia()
  router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'home', component: STUB },
      { path: '/componenten/:id', name: 'component-detail', component: STUB },
      { path: '/landschapskaart', name: 'landschapskaart', component: STUB },
    ],
  })
  await router.push('/')
  await router.isReady()
  const wrapper = mount(GebruikteApplicatiesSectie, {
    props,
    global: { plugins: [pinia, [PrimeVue, { unstyled: true }], ToastService, router] },
  })
  await flushPromises()
  return wrapper
}

beforeEach(() => {
  vi.clearAllMocks()
  api.organisatiegebruik.lijstVoorOrganisatie.mockResolvedValue([])
  api.gebruikersgroepen.contextComponenten.mockResolvedValue([])
})
afterEach(() => vi.restoreAllMocks())

describe('GebruikteApplicatiesSectie — organisatie', () => {
  it('leest uit de org-bron; grof-only krijgt "Nog niet verfijnd", verfijnd niet', async () => {
    api.organisatiegebruik.lijstVoorOrganisatie.mockResolvedValueOnce([
      { component_id: 'a1', component_naam: 'Zaaksysteem', componenttype: 'applicatie', verfijnd: true },
      { component_id: 'a2', component_naam: 'BRP', componenttype: 'applicatie', verfijnd: false },
    ])
    const w = await mountSectie({ niveau: 'organisatie', organisatieId: 'org-1' })
    expect(api.organisatiegebruik.lijstVoorOrganisatie).toHaveBeenCalledWith({ organisatie_id: 'org-1' })
    expect(api.gebruikersgroepen.contextComponenten).not.toHaveBeenCalled()
    expect(w.text()).toContain('Zaaksysteem')
    expect(w.find('[data-testid="ga-link-a1"]').exists()).toBe(true)
    // Grof-only markering alleen op de niet-verfijnde rij.
    expect(w.find('[data-testid="ga-grofonly-a2"]').exists()).toBe(true)
    expect(w.find('[data-testid="ga-grofonly-a1"]').exists()).toBe(false)
  })

  it('lege staat toont de organisatie-tekst', async () => {
    const w = await mountSectie({ niveau: 'organisatie', organisatieId: 'org-1' })
    expect(w.find('[data-testid="ga-leeg"]').text()).toContain('Deze organisatie gebruikt nog geen applicaties')
  })

  it('"Toon op de landschapskaart" zet de handoff (set + grof-only) en navigeert', async () => {
    api.organisatiegebruik.lijstVoorOrganisatie.mockResolvedValueOnce([
      { component_id: 'a1', component_naam: 'Zaaksysteem', componenttype: 'applicatie', verfijnd: true },
      { component_id: 'a2', component_naam: 'BRP', componenttype: 'applicatie', verfijnd: false },
    ])
    const w = await mountSectie({ niveau: 'organisatie', organisatieId: 'org-1' })
    const push = vi.spyOn(router, 'push')
    await w.find('[data-testid="ga-toon-kaart"]').trigger('click')
    expect(zetKaartHandoff).toHaveBeenCalledWith({ componentIds: ['a1', 'a2'], grofOnlyIds: ['a2'] })
    expect(push).toHaveBeenCalledWith({ name: 'landschapskaart' })
  })
})

describe('GebruikteApplicatiesSectie — afdeling', () => {
  it('leest uit de context-bron; nooit een grof-only-markering', async () => {
    api.gebruikersgroepen.contextComponenten.mockResolvedValueOnce([
      { component_id: 'a1', component_naam: 'Zaaksysteem', componenttype: 'applicatie' },
    ])
    const w = await mountSectie({ niveau: 'afdeling', organisatieId: 'org-1', afdelingId: 'afd-1' })
    expect(api.gebruikersgroepen.contextComponenten).toHaveBeenCalledWith({ organisatie_id: 'org-1', afdeling_id: 'afd-1' })
    expect(api.organisatiegebruik.lijstVoorOrganisatie).not.toHaveBeenCalled()
    expect(w.text()).toContain('Zaaksysteem')
    expect(w.find('[data-testid="ga-grofonly-a1"]').exists()).toBe(false)
  })

  it('lege staat toont de afdeling-tekst', async () => {
    const w = await mountSectie({ niveau: 'afdeling', organisatieId: 'org-1', afdelingId: 'afd-1' })
    expect(w.find('[data-testid="ga-leeg"]').text()).toContain('Deze afdeling gebruikt nog geen applicaties')
  })
})
