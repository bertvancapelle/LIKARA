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
    // ADR-041 slice 2 — componenttype-catalogus + persoonlijke voorkeur.
    componenten: { opties: vi.fn() },
    voorkeuren: { haalAlle: vi.fn(), zet: vi.fn(), herroep: vi.fn() },
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
  api.componenten.opties.mockResolvedValue({
    componenttype: [
      { optie_sleutel: 'applicatie', label: 'Applicatie' },
      { optie_sleutel: 'database', label: 'Database' },
    ],
  })
  api.voorkeuren.haalAlle.mockResolvedValue([]) // geen voorkeur → baseline (applicatie)
  api.voorkeuren.zet.mockResolvedValue({})
  api.voorkeuren.herroep.mockResolvedValue(undefined)
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
    expect(w.find('[data-testid="ga-leeg"]').text()).toContain('Deze organisatie gebruikt nog geen componenten')
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
    expect(w.find('[data-testid="ga-leeg"]').text()).toContain('Deze afdeling gebruikt nog geen componenten')
  })

  it('toont GEEN voorkeur-control (die hoort bij de organisatie)', async () => {
    const w = await mountSectie({ niveau: 'afdeling', organisatieId: 'org-1', afdelingId: 'afd-1' })
    expect(w.find('[data-testid="ga-voorkeur"]').exists()).toBe(false)
    expect(api.componenten.opties).not.toHaveBeenCalled()
    expect(api.voorkeuren.haalAlle).not.toHaveBeenCalled()
  })
})

describe('GebruikteApplicatiesSectie — kop + voorkeur (ADR-041 slice 2)', () => {
  it('de sectiekop is vast "Gebruikte componenten"', async () => {
    const w = await mountSectie({ niveau: 'organisatie', organisatieId: 'org-1' })
    expect(w.find('#sectie-gebruikte-componenten').text()).toBe('Gebruikte componenten')
  })

  it('zonder voorkeur = baseline (applicatie aangevinkt); status "Je standaard"; opslaan inactief', async () => {
    const w = await mountSectie({ niveau: 'organisatie', organisatieId: 'org-1' })
    expect(w.find('[data-testid="ga-type-applicatie"]').element.checked).toBe(true)
    expect(w.find('[data-testid="ga-type-database"]').element.checked).toBe(false)
    expect(w.find('[data-testid="ga-voorkeur-status"]').text()).toBe('Je standaard')
    expect(w.find('[data-testid="ga-voorkeur-opslaan"]').attributes('disabled')).toBeDefined()
  })

  it('een extra type aanvinken → "Gewijzigd"; opslaan actief; opslaan PUT en terug naar "Je standaard"', async () => {
    const w = await mountSectie({ niveau: 'organisatie', organisatieId: 'org-1' })
    await w.find('[data-testid="ga-type-database"]').setValue(true)
    expect(w.find('[data-testid="ga-voorkeur-status"]').text()).toContain('Gewijzigd')
    expect(w.find('[data-testid="ga-voorkeur-opslaan"]').attributes('disabled')).toBeUndefined()
    await w.find('[data-testid="ga-voorkeur-opslaan"]').trigger('click')
    await flushPromises()
    expect(api.voorkeuren.zet).toHaveBeenCalledWith('gebruikte_componenttypen', { typen: ['applicatie', 'database'] })
    expect(w.find('[data-testid="ga-voorkeur-status"]').text()).toBe('Je standaard')
    expect(w.find('[data-testid="ga-voorkeur-opslaan"]').attributes('disabled')).toBeDefined()
  })

  it('opgeslagen voorkeur wordt geladen (database aangevinkt, applicatie niet)', async () => {
    api.voorkeuren.haalAlle.mockResolvedValueOnce([
      { voorkeur_sleutel: 'gebruikte_componenttypen', waarde: { typen: ['database'] }, updated_at: 'x' },
    ])
    const w = await mountSectie({ niveau: 'organisatie', organisatieId: 'org-1' })
    expect(w.find('[data-testid="ga-type-database"]').element.checked).toBe(true)
    expect(w.find('[data-testid="ga-type-applicatie"]').element.checked).toBe(false)
    expect(w.find('[data-testid="ga-voorkeur-status"]').text()).toBe('Je standaard')
  })

  it('alles weghalen + opslaan = herroep (DELETE) → terug naar baseline (applicatie)', async () => {
    api.voorkeuren.haalAlle.mockResolvedValueOnce([
      { voorkeur_sleutel: 'gebruikte_componenttypen', waarde: { typen: ['database'] }, updated_at: 'x' },
    ])
    const w = await mountSectie({ niveau: 'organisatie', organisatieId: 'org-1' })
    await w.find('[data-testid="ga-type-database"]').setValue(false) // selectie nu leeg
    await w.find('[data-testid="ga-voorkeur-opslaan"]').trigger('click')
    await flushPromises()
    expect(api.voorkeuren.herroep).toHaveBeenCalledWith('gebruikte_componenttypen')
    expect(api.voorkeuren.zet).not.toHaveBeenCalled()
    // Terug naar baseline: applicatie aangevinkt, status "Je standaard".
    expect(w.find('[data-testid="ga-type-applicatie"]').element.checked).toBe(true)
    expect(w.find('[data-testid="ga-voorkeur-status"]').text()).toBe('Je standaard')
  })

  it('de kijkfilter-hint is zichtbaar', async () => {
    const w = await mountSectie({ niveau: 'organisatie', organisatieId: 'org-1' })
    expect(w.find('[data-testid="ga-voorkeur-hint"]').text()).toContain('kijkfilter')
  })
})

describe('GebruikteApplicatiesSectie — voorkeur = weergavefilter met directe preview (ADR-041 herzien)', () => {
  const GEMENGD = [
    { component_id: 'a1', component_naam: 'Zaaksysteem', componenttype: 'applicatie', verfijnd: true },
    { component_id: 'd1', component_naam: 'Klantdatabank', componenttype: 'database', verfijnd: true },
  ]

  it('baseline {applicatie} verbergt de database-rij en benoemt "buiten kijk-scope" (verbergt niets echt)', async () => {
    api.organisatiegebruik.lijstVoorOrganisatie.mockResolvedValueOnce(GEMENGD)
    const w = await mountSectie({ niveau: 'organisatie', organisatieId: 'org-1' })
    expect(w.find('[data-testid="ga-item-a1"]').exists()).toBe(true)
    expect(w.find('[data-testid="ga-item-d1"]').exists()).toBe(false)
    expect(w.find('[data-testid="ga-buiten-scope"]').text()).toContain('1')
  })

  it('database aanvinken = directe preview: de database-rij verschijnt meteen (vóór opslaan)', async () => {
    api.organisatiegebruik.lijstVoorOrganisatie.mockResolvedValueOnce(GEMENGD)
    const w = await mountSectie({ niveau: 'organisatie', organisatieId: 'org-1' })
    expect(w.find('[data-testid="ga-item-d1"]').exists()).toBe(false)
    await w.find('[data-testid="ga-type-database"]').setValue(true)
    expect(w.find('[data-testid="ga-item-d1"]').exists()).toBe(true) // meteen zichtbaar
    expect(w.find('[data-testid="ga-buiten-scope"]').exists()).toBe(false)
    expect(w.find('[data-testid="ga-voorkeur-status"]').text()).toContain('Gewijzigd') // nog niet opgeslagen
    expect(api.voorkeuren.zet).not.toHaveBeenCalled()
  })
})
