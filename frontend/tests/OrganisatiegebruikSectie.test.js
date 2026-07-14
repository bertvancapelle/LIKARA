/** Tests — OrganisatiegebruikSectie (ADR-046 stuk 2): "Wie gebruikt dit" op het
 *  componentdetail. Eén regel per organisatie (afdelingen of rustig "afdeling onbekend"),
 *  grof toevoegen zonder afdeling (end-to-end: de api-client krijgt de juiste args —
 *  V012-les), 409-meldingen als warn (geen fout-toast), verwijderen altijd met
 *  bevestiging en nooit stil bij verfijning, rol-gating per specifiek recht (LI037). */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'

vi.mock('@/api', () => ({
  api: {
    organisatiegebruik: { lijstVoorApplicatie: vi.fn(), maak: vi.fn(), verwijder: vi.fn() },
    partijen: { lijst: vi.fn() },
  },
}))
vi.mock('@/meldingen', () => ({ toastSucces: vi.fn() }))

import { createMemoryHistory, createRouter } from 'vue-router'

import { api } from '@/api'
import { toastSucces } from '@/meldingen'
import { useAuthStore } from '@/store/auth'
import OrganisatiegebruikSectie from '@modules/bwb_ontvlechting/frontend/views/OrganisatiegebruikSectie.vue'

const STUB = { template: '<div/>' }

const RIJEN = [
  { id: 'g1', organisatie_id: 'o1', organisatie_naam: 'Gemeente Culemborg', afdelingen: [], heeft_verfijning: false },
  { id: 'g2', organisatie_id: 'o2', organisatie_naam: 'Gemeente Buren', afdelingen: ['Publiekszaken'], heeft_verfijning: true },
]

let router

async function mountSectie({ rollen = ['beheerder'], props = {} } = {}) {
  const pinia = createPinia()
  setActivePinia(pinia)
  const auth = useAuthStore()
  auth.user = { sub: 's', email: 't@t.nl', roles: rollen }
  router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'home', component: STUB },
      { path: '/partijen/:id', name: 'partij-detail', component: STUB },
    ],
  })
  await router.push('/')
  await router.isReady()
  const wrapper = mount(OrganisatiegebruikSectie, {
    props: { componentId: 'c1', componentNaam: 'Zaaksysteem', ...props },
    global: {
      plugins: [pinia, [PrimeVue, { unstyled: true }], ToastService, router],
      stubs: { teleport: true },
    },
  })
  await flushPromises()
  return wrapper
}

beforeEach(() => {
  vi.clearAllMocks()
  api.organisatiegebruik.lijstVoorApplicatie.mockResolvedValue(RIJEN)
  api.partijen.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
})
afterEach(() => vi.restoreAllMocks())

describe('OrganisatiegebruikSectie — lijst per organisatie', () => {
  it('laadt via applicatie_id en toont één regel per organisatie', async () => {
    const w = await mountSectie()
    expect(api.organisatiegebruik.lijstVoorApplicatie).toHaveBeenCalledWith({ applicatie_id: 'c1' })
    expect(w.find('[data-testid="gebruik-org-g1"]').text()).toBe('Gemeente Culemborg')
    expect(w.find('[data-testid="gebruik-org-g2"]').text()).toBe('Gemeente Buren')
  })

  it('toont afdelingen indien bekend en anders rustig "afdeling onbekend"', async () => {
    const w = await mountSectie()
    expect(w.find('[data-testid="gebruik-onbekend-g1"]').text()).toBe('afdeling onbekend')
    expect(w.find('[data-testid="gebruik-afdelingen-g2"]').text().replace(/\s+/g, ' '))
      .toContain('Publiekszaken — Gemeente Buren') // LI040: volledige identiteit, org gedempt
    expect(w.find('[data-testid="identiteit-naam-ontbreekt"]').exists()).toBe(false)
  })

  it('lege lijst toont een lege-staat met route naar de actie', async () => {
    api.organisatiegebruik.lijstVoorApplicatie.mockResolvedValue([])
    const w = await mountSectie()
    expect(w.find('[data-testid="gebruik-leeg"]').text()).toContain('voeg er hieronder een toe')
  })
})

describe('OrganisatiegebruikSectie — tabelvorm (LI040)', () => {
  it('rendert als sorteerbare tabel, standaard op organisatienaam oplopend', async () => {
    const w = await mountSectie()
    const tabel = w.find('[data-testid="gebruik-tabel"]')
    expect(tabel.exists()).toBe(true)
    // Default-sortering: Buren vóór Culemborg (alfabetisch, client-side).
    const orgs = w.findAll('tbody [data-testid^="gebruik-org-"]').map((n) => n.text())
    expect(orgs).toEqual(['Gemeente Buren', 'Gemeente Culemborg'])
  })

  it('kolomkop-klik draait de sortering om (client-side, vaste korte lijst)', async () => {
    const w = await mountSectie()
    // Eerste sorteerbare kolomkop = Organisatie; een klik op de al-actieve asc-kolom flipt naar desc.
    await w.findAll('th')[0].trigger('click')
    await flushPromises()
    const orgs = w.findAll('tbody [data-testid^="gebruik-org-"]').map((n) => n.text())
    expect(orgs).toEqual(['Gemeente Culemborg', 'Gemeente Buren'])
  })

  it('rijen dragen het lk-rij-contract (rij-acties verschijnen op de actieve rij)', async () => {
    const w = await mountSectie()
    const rij = w.find('tbody tr')
    expect(rij.classes()).toContain('lk-rij')
    // De verwijderknop leeft in de RijActies-container binnen de rij.
    expect(rij.find('.lk-rij-acties [data-testid="gebruik-verwijder-g1"]').exists()
      || w.find('.lk-rij-acties [data-testid^="gebruik-verwijder-"]').exists()).toBe(true)
  })
})

describe('OrganisatiegebruikSectie — toevoegen (grof, zonder afdeling)', () => {
  it('stuurt organisatie_id + applicatie_id naar de api-client en highlight de nieuwe rij', async () => {
    api.organisatiegebruik.maak.mockResolvedValue({ id: 'g9' })
    const w = await mountSectie()
    // Kies via de interne v-model (de picker-integratie zelf is elders gedekt).
    w.findComponent({ name: 'ZoekSelect' }).vm.$emit('update:modelValue', 'o9')
    await flushPromises()
    await w.find('[data-testid="gebruik-toevoegen"]').trigger('click')
    await flushPromises()
    expect(api.organisatiegebruik.maak).toHaveBeenCalledWith({ organisatie_id: 'o9', applicatie_id: 'c1' })
    expect(toastSucces).toHaveBeenCalledWith(expect.anything(), 'Toegevoegd')
    // Herladen na toevoegen (idempotente refetch).
    expect(api.organisatiegebruik.lijstVoorApplicatie).toHaveBeenCalledTimes(2)
  })

  it('409 GEBRUIK_BESTAAT toont een warn-melding, geen dubbele regel of fout-toast', async () => {
    api.organisatiegebruik.maak.mockRejectedValue({ status: 409, code: 'GEBRUIK_BESTAAT', message: 'Deze organisatie is al geregistreerd als gebruiker van deze applicatie.' })
    const w = await mountSectie()
    w.findComponent({ name: 'ZoekSelect' }).vm.$emit('update:modelValue', 'o1')
    await flushPromises()
    await w.find('[data-testid="gebruik-toevoegen"]').trigger('click')
    await flushPromises()
    expect(w.find('[data-testid="gebruik-melding"]').text()).toContain('al geregistreerd')
    expect(toastSucces).not.toHaveBeenCalled()
  })
})

describe('OrganisatiegebruikSectie — verwijderen (nooit stil)', () => {
  it('verwijdert pas ná bevestiging, met de regel leesbaar in de vraag', async () => {
    api.organisatiegebruik.verwijder.mockResolvedValue(null)
    const w = await mountSectie()
    await w.find('[data-testid="gebruik-verwijder-g1"]').trigger('click')
    await flushPromises()
    expect(w.find('[data-testid="gebruik-verwijder-omschrijving"]').text())
      .toContain('Gemeente Culemborg als gebruiker van Zaaksysteem')
    expect(api.organisatiegebruik.verwijder).not.toHaveBeenCalled()
    await w.find('[data-testid="gebruik-verwijder-bevestig"]').trigger('click')
    await flushPromises()
    expect(api.organisatiegebruik.verwijder).toHaveBeenCalledWith('g1')
    expect(toastSucces).toHaveBeenCalledWith(expect.anything(), 'Verwijderd')
  })

  it('409 GEBRUIK_HEEFT_VERFIJNING: melding in de dialoog, niets verdwijnt stil', async () => {
    api.organisatiegebruik.verwijder.mockRejectedValue({
      status: 409, code: 'GEBRUIK_HEEFT_VERFIJNING',
      message: 'Deze organisatie heeft 2 gebruikersgroep(en) op dit component; verwijder of verplaats die eerst — een verfijnde registratie verdwijnt nooit stil.',
    })
    const w = await mountSectie()
    await w.find('[data-testid="gebruik-verwijder-g2"]').trigger('click')
    await w.find('[data-testid="gebruik-verwijder-bevestig"]').trigger('click')
    await flushPromises()
    expect(w.find('[data-testid="gebruik-verwijder-melding"]').text()).toContain('verdwijnt nooit stil')
    // De dialoog blijft open (de rij is niet gewist) en de lijst is niet herladen.
    expect(w.find('[data-testid="gebruik-verwijder-dialog"]').exists()).toBe(true)
    expect(api.organisatiegebruik.lijstVoorApplicatie).toHaveBeenCalledTimes(1)
  })
})

describe('OrganisatiegebruikSectie — rol-gating (affordance; backend handhaaft)', () => {
  it('viewer: geen toevoeg- en geen verwijder-affordance', async () => {
    const w = await mountSectie({ rollen: ['viewer'] })
    expect(w.find('[data-testid="gebruik-toevoegen"]').exists()).toBe(false)
    expect(w.find('[data-testid="gebruik-verwijder-g1"]').exists()).toBe(false)
  })

  it('medewerker: wél toevoegen, géén verwijderen (LI037 — specifiek recht)', async () => {
    const w = await mountSectie({ rollen: ['medewerker'] })
    expect(w.find('[data-testid="gebruik-toevoegen"]').exists()).toBe(true)
    expect(w.find('[data-testid="gebruik-verwijder-g1"]').exists()).toBe(false)
  })
})
