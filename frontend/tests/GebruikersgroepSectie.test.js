/** Tests — GebruikersgroepSectie (child-sectie via @modules). */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'

vi.mock('@/api', () => ({
  api: {
    gebruikersgroepen: {
      lijst: vi.fn(),
      maak: vi.fn(),
      werkBij: vi.fn(),
      verwijder: vi.fn(),
    },
    // ADR-038 — ZoekSelect voor de organisatie-keuze (partijen, aard_in=['organisatie']).
    partijen: { lijst: vi.fn(), haal: vi.fn(), maak: vi.fn() },
  },
}))

import { createRouter, createMemoryHistory } from 'vue-router'

import { api } from '@/api'
import { useAuthStore } from '@/store/auth'
import GebruikersgroepSectie from '@modules/bwb_ontvlechting/frontend/views/GebruikersgroepSectie.vue'

const APP = 'app-1'
const STUB = { template: '<div/>' }

async function mountSectie({ rollen = ['beheerder'] } = {}) {
  const pinia = createPinia()
  const auth = useAuthStore(pinia)
  auth.user = { sub: 's', tenant_id: 't', email: 'a@b.nl', roles: rollen }
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'home', component: STUB },
      { path: '/partijen/:id', name: 'partij-detail', component: STUB },
    ],
  })
  await router.push('/')
  await router.isReady()
  const wrapper = mount(GebruikersgroepSectie, {
    props: { applicatieId: APP },
    attachTo: document.body,
    global: { plugins: [pinia, [PrimeVue, { unstyled: true }], ToastService, router], stubs: { teleport: true } },
  })
  await flushPromises()
  return wrapper
}

beforeEach(() => {
  vi.clearAllMocks()
  api.gebruikersgroepen.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
  api.partijen.lijst.mockResolvedValue({ items: [{ id: 'org-1', naam: 'Gemeente Tiel', aard: 'organisatie' }], volgende_cursor: null })
  api.partijen.haal.mockResolvedValue({ id: 'org-1', naam: 'Gemeente Tiel', aard: 'organisatie' })
})
afterEach(() => vi.restoreAllMocks())

describe('GebruikersgroepSectie', () => {
  it('LI040: de afdeling-kolom toont de volledige identiteit (afdeling + gedempte organisatie)', async () => {
    api.gebruikersgroepen.lijst.mockResolvedValueOnce({
      items: [{ id: 'g1', organisatie_id: 'org-1', organisatie_naam: 'Gemeente Tiel', afdeling: 'Burgerzaken', aantal_gebruikers: 12 }],
      volgende_cursor: null,
    })
    const w = await mountSectie()
    expect(w.text().replace(/\s+/g, ' ')).toContain('Burgerzaken — Gemeente Tiel')
    expect(w.find('[data-testid="identiteit-naam-ontbreekt"]').exists()).toBe(false)
  })

  it('rendert de gebruikersgroepen; de organisatie is doorklikbaar naar de partij', async () => {
    api.gebruikersgroepen.lijst.mockResolvedValueOnce({
      items: [{ id: 'g1', organisatie_id: 'org-1', organisatie_naam: 'Gemeente Tiel', afdeling: 'Burgerzaken', aantal_gebruikers: 12 }],
      volgende_cursor: null,
    })
    const w = await mountSectie()
    expect(api.gebruikersgroepen.lijst).toHaveBeenCalledWith({ applicatie_id: APP, limit: 25, after: undefined })
    expect(w.text()).toContain('Gemeente Tiel')
    const link = w.find('[data-testid="gg-org-link-g1"]')
    expect(link.exists()).toBe(true)
    expect(link.attributes('href')).toContain('/partijen/org-1')
  })

  it('toont een streepje wanneer er geen organisatie gekoppeld is', async () => {
    api.gebruikersgroepen.lijst.mockResolvedValueOnce({
      items: [{ id: 'g2', organisatie_id: null, organisatie_naam: null, afdeling: null, aantal_gebruikers: null }],
      volgende_cursor: null,
    })
    const w = await mountSectie()
    expect(w.find('[data-testid="gg-org-link-g2"]').exists()).toBe(false)
  })

  it('rol-gating: viewer geen Toevoegen, medewerker wel', async () => {
    expect((await mountSectie({ rollen: ['viewer'] })).find('[data-testid="gg-toevoegen"]').exists()).toBe(false)
    expect((await mountSectie({ rollen: ['medewerker'] })).find('[data-testid="gg-toevoegen"]').exists()).toBe(true)
  })

  it('LI037 rol-gating: medewerker mag bewerken maar NIET verwijderen (VERWIJDEREN = beheerder)', async () => {
    api.gebruikersgroepen.lijst.mockResolvedValue({
      items: [{ id: 'g1', organisatie_id: 'org-1', organisatie_naam: 'Gemeente Tiel', afdeling: 'Burgerzaken', aantal_gebruikers: 12 }],
      volgende_cursor: null,
    })
    const m = await mountSectie({ rollen: ['medewerker'] })
    expect(m.find('[data-testid="gg-bewerk-g1"]').exists()).toBe(true)
    expect(m.find('[data-testid="gg-verwijder-g1"]').exists()).toBe(false)
    const b = await mountSectie({ rollen: ['beheerder'] })
    expect(b.find('[data-testid="gg-verwijder-g1"]').exists()).toBe(true)
  })

  it('weigert een negatief aantal gebruikers client-side', async () => {
    const w = await mountSectie()
    await w.find('[data-testid="gg-toevoegen"]').trigger('click')
    await flushPromises()
    await w.find('[data-testid="gg-veld-aantal"]').setValue('-3')
    await w.find('[data-testid="gg-form"]').trigger('submit')
    await flushPromises()
    expect(w.find('[data-testid="gg-fout-aantal"]').exists()).toBe(true)
    expect(api.gebruikersgroepen.maak).not.toHaveBeenCalled()
  })

  it('focust het organisatie-zoekveld bij openen', async () => {
    const w = await mountSectie()
    await w.find('[data-testid="gg-toevoegen"]').trigger('click')
    await flushPromises()
    await new Promise((r) => setTimeout(r, 0))
    expect(document.activeElement).toBe(w.find('[data-testid="gg-veld-organisatie-input"]').element)
  })

  it('kiest een organisatie via de zoek-combobox en stuurt het id mee', async () => {
    api.gebruikersgroepen.maak.mockResolvedValueOnce({ id: 'new' })
    const w = await mountSectie()
    await w.find('[data-testid="gg-toevoegen"]').trigger('click')
    await flushPromises()
    // Open de combobox (focus → server-zoek) en kies de organisatie-optie.
    await w.find('[data-testid="gg-veld-organisatie-input"]').trigger('focus')
    await flushPromises()
    expect(api.partijen.lijst).toHaveBeenCalledWith(expect.objectContaining({ aard_in: ['organisatie'] }))
    await w.find('[data-testid="gg-veld-organisatie-optie-org-1"]').trigger('mousedown')
    await flushPromises()
    await w.find('[data-testid="gg-form"]').trigger('submit')
    await flushPromises()
    expect(api.gebruikersgroepen.maak).toHaveBeenCalledWith({
      organisatie_id: 'org-1',
      afdeling_id: null,
      aantal_gebruikers: null,
      applicatie_id: APP,
    })
  })

  it('afdeling-picker verschijnt zodra een organisatie is gekozen en is verborgen zonder', async () => {
    const w = await mountSectie()
    await w.find('[data-testid="gg-toevoegen"]').trigger('click')
    await flushPromises()
    // zonder organisatie → geen afdeling-picker
    expect(w.find('[data-testid="gg-afdeling-input"]').exists()).toBe(false)
    // organisatie kiezen → afdeling-picker verschijnt (ADR-038 — geen aard-check meer)
    await w.find('[data-testid="gg-veld-organisatie-input"]').trigger('focus')
    await flushPromises()
    await w.find('[data-testid="gg-veld-organisatie-optie-org-1"]').trigger('mousedown')
    await flushPromises()
    expect(w.find('[data-testid="gg-afdeling-input"]').exists()).toBe(true)
  })

  it('blokkeert opslaan zonder organisatie met een inline-melding (client-side)', async () => {
    const w = await mountSectie()
    await w.find('[data-testid="gg-toevoegen"]').trigger('click')
    await flushPromises()
    // submit zonder organisatie → inline-fout, geen server-call (ADR-038 — organisatie verplicht)
    await w.find('[data-testid="gg-form"]').trigger('submit')
    await flushPromises()
    expect(w.find('[data-testid="gg-fout-organisatie"]').exists()).toBe(true)
    expect(api.gebruikersgroepen.maak).not.toHaveBeenCalled()
  })

  it('afdeling-selectie reset bij het wisselen van organisatie', async () => {
    api.gebruikersgroepen.maak.mockResolvedValueOnce({ id: 'new' })
    const w = await mountSectie()
    await w.find('[data-testid="gg-toevoegen"]').trigger('click')
    await flushPromises()
    await w.find('[data-testid="gg-veld-organisatie-input"]').trigger('focus')
    await flushPromises()
    await w.find('[data-testid="gg-veld-organisatie-optie-org-1"]').trigger('mousedown')
    await flushPromises()
    // afdeling kiezen (structurele verwijzing: afdeling_id)
    api.partijen.lijst.mockResolvedValue({ items: [{ id: 'afd-1', naam: 'Burgerzaken', aard: 'organisatie_eenheid' }], volgende_cursor: null })
    api.partijen.haal.mockResolvedValue({ id: 'afd-1', naam: 'Burgerzaken', aard: 'organisatie_eenheid' })
    await w.find('[data-testid="gg-afdeling-input"]').trigger('focus')
    await flushPromises()
    await w.find('[data-testid="gg-afdeling-optie-afd-1"]').trigger('mousedown')
    await flushPromises()
    // wissel naar een andere organisatie → afdeling reset
    api.partijen.lijst.mockResolvedValue({ items: [{ id: 'org-2', naam: 'Andere org', aard: 'organisatie' }], volgende_cursor: null })
    api.partijen.haal.mockResolvedValue({ id: 'org-2', naam: 'Andere org', aard: 'organisatie' })
    await w.find('[data-testid="gg-veld-organisatie-input"]').trigger('focus')
    await flushPromises()
    await w.find('[data-testid="gg-veld-organisatie-optie-org-2"]').trigger('mousedown')
    await flushPromises()
    await w.find('[data-testid="gg-form"]').trigger('submit')
    await flushPromises()
    expect(api.gebruikersgroepen.maak).toHaveBeenCalledWith(expect.objectContaining({ organisatie_id: 'org-2', afdeling_id: null }))
  })

  it('afdeling-keuze stuurt afdeling_id mee', async () => {
    api.gebruikersgroepen.maak.mockResolvedValueOnce({ id: 'new' })
    const w = await mountSectie()
    await w.find('[data-testid="gg-toevoegen"]').trigger('click')
    await flushPromises()
    await w.find('[data-testid="gg-veld-organisatie-input"]').trigger('focus')
    await flushPromises()
    await w.find('[data-testid="gg-veld-organisatie-optie-org-1"]').trigger('mousedown')
    await flushPromises()
    api.partijen.lijst.mockResolvedValue({ items: [{ id: 'afd-1', naam: 'Burgerzaken', aard: 'organisatie_eenheid' }], volgende_cursor: null })
    await w.find('[data-testid="gg-afdeling-input"]').trigger('focus')
    await flushPromises()
    await w.find('[data-testid="gg-afdeling-optie-afd-1"]').trigger('mousedown')
    await flushPromises()
    await w.find('[data-testid="gg-form"]').trigger('submit')
    await flushPromises()
    expect(api.gebruikersgroepen.maak).toHaveBeenCalledWith(expect.objectContaining({ organisatie_id: 'org-1', afdeling_id: 'afd-1' }))
  })

  it('search-first: geen altijd-zichtbare aanmaakknop; aanmaken vanuit de lege zoekstaat + bevestiging', async () => {
    api.gebruikersgroepen.maak.mockResolvedValueOnce({ id: 'new' })
    api.partijen.maak.mockResolvedValueOnce({ id: 'afd-nieuw', naam: 'Finance' })
    const w = await mountSectie()
    await w.find('[data-testid="gg-toevoegen"]').trigger('click')
    await flushPromises()
    // Geen losstaande "+ Nieuwe afdeling"-knop meer.
    expect(w.find('[data-testid="gg-nieuwe-afdeling"]').exists()).toBe(false)
    await w.find('[data-testid="gg-veld-organisatie-input"]').trigger('focus')
    await flushPromises()
    await w.find('[data-testid="gg-veld-organisatie-optie-org-1"]').trigger('mousedown')
    await flushPromises()
    // Afdeling-zoek levert geen match → aanmaak-actie verschijnt ín de lege zoekstaat (gedeelde
    // AfdelingSelect: getinte omrande zijstap, geen twee-staps-waarschuwing meer).
    api.partijen.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
    vi.useFakeTimers()
    await w.find('[data-testid="gg-afdeling-input"]').setValue('Finance')
    vi.advanceTimersByTime(300)
    vi.useRealTimers()
    await flushPromises()
    const aanmaak = w.find('[data-testid="gg-afdeling-aanmaak-open"]')
    expect(aanmaak.exists()).toBe(true)
    // Open het aanmaak-blok (getinte zijstap); naam voorgevuld met de zoekterm; aanmaken en kiezen.
    await aanmaak.trigger('mousedown')
    await aanmaak.trigger('click')
    await flushPromises()
    expect(w.find('[data-testid="gg-afdeling-naam"]').element.value).toBe('Finance')
    await w.find('[data-testid="gg-afdeling-aanmaak-bevestig"]').trigger('click')
    await flushPromises()
    expect(api.partijen.maak).toHaveBeenCalledWith({ aard: 'organisatie_eenheid', naam: 'Finance', organisatie_id: 'org-1' })
    // Nieuwe afdeling is geselecteerd → save stuurt afdeling_id.
    await w.find('[data-testid="gg-form"]').trigger('submit')
    await flushPromises()
    expect(api.gebruikersgroepen.maak).toHaveBeenCalledWith(expect.objectContaining({ organisatie_id: 'org-1', afdeling_id: 'afd-nieuw' }))
  })

  it('bewerken voert organisatie, afdeling én aantal correct voor; opslaan zonder wijziging ontkoppelt niet', async () => {
    api.gebruikersgroepen.lijst.mockResolvedValueOnce({
      items: [{ id: 'g1', organisatie_id: 'org-1', organisatie_naam: 'Gemeente Tiel', afdeling_id: 'afd-1', afdeling: 'Burgerzaken', aantal_gebruikers: 12 }],
      volgende_cursor: null,
    })
    api.gebruikersgroepen.werkBij.mockResolvedValueOnce({ id: 'g1' })
    const w = await mountSectie()
    await w.find('[data-testid="gg-bewerk-g1"]').trigger('click')
    await flushPromises() // openBewerken → api.partijen.haal (orgAard/orgNaam)
    // Voorvulling: organisatie-naam zichtbaar (ADR-036: uit organisatie_naam), afdeling + aantal ingevuld.
    expect(w.find('[data-testid="gg-veld-organisatie-input"]').element.value).toBe('Gemeente Tiel')
    expect(w.find('[data-testid="gg-afdeling-input"]').element.value).toBe('Burgerzaken')
    expect(w.find('[data-testid="gg-veld-aantal"]').element.value).toBe('12')
    // Direct opslaan zonder wijziging → koppelingen ongemoeid (geen stille ontkoppeling).
    await w.find('[data-testid="gg-form"]').trigger('submit')
    await flushPromises()
    expect(api.gebruikersgroepen.werkBij).toHaveBeenCalledWith('g1', {
      organisatie_id: 'org-1',
      afdeling_id: 'afd-1',
      aantal_gebruikers: 12,
    })
  })

  it('bewerken van een org-loze groep: organisatie leeg, geen afdeling-veld', async () => {
    api.gebruikersgroepen.lijst.mockResolvedValueOnce({
      items: [{ id: 'g2', organisatie_id: null, organisatie_naam: null, afdeling_id: null, afdeling: null, aantal_gebruikers: 5 }],
      volgende_cursor: null,
    })
    const w = await mountSectie()
    await w.find('[data-testid="gg-bewerk-g2"]').trigger('click')
    await flushPromises()
    expect(w.find('[data-testid="gg-veld-organisatie-input"]').element.value).toBe('')
    expect(w.find('[data-testid="gg-afdeling-input"]').exists()).toBe(false)
    expect(w.find('[data-testid="gg-veld-aantal"]').element.value).toBe('5')
  })
})
