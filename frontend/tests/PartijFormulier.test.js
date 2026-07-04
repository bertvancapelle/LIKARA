/** Tests — PartijFormulier (ADR-024 slice 2a): aard-keuze bij aanmaken, soort optioneel,
 *  naam verplicht client-side, 422-veldfout-mapping. */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'

vi.mock('@/api', () => ({
  api: { partijen: { maak: vi.fn(), werkBij: vi.fn(), haal: vi.fn(), soorten: vi.fn(), lijst: vi.fn() } },
}))

import { api } from '@/api'
import PartijFormulier from '@modules/bwb_ontvlechting/frontend/views/PartijFormulier.vue'

function maakRouter() {
  const r = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/partijen', name: 'partij-lijst', component: { template: '<div/>' } },
      { path: '/partijen/nieuw', name: 'partij-nieuw', component: PartijFormulier },
      { path: '/partijen/:id', name: 'partij-detail', component: { template: '<div/>' } },
      { path: '/partijen/:id/bewerken', name: 'partij-bewerken', component: PartijFormulier, props: true },
    ],
  })
  return r
}

function _querystring(query) {
  const q = new URLSearchParams(query).toString()
  return q ? `?${q}` : ''
}

async function mountForm({ id = null, query = null } = {}) {
  const router = maakRouter()
  await router.push(id ? `/partijen/${id}/bewerken` : `/partijen/nieuw${_querystring(query)}`)
  await router.isReady()
  const w = mount(PartijFormulier, {
    props: { id },
    global: { plugins: [createPinia(), [PrimeVue, { unstyled: true }], ToastService, router], stubs: { teleport: true } },
  })
  await flushPromises()
  return { w, router }
}

// ZoekSelect-interactie (CD049): focus → zoek → klik resultaat (mousedown).
async function kiesZoek(w, prefix, id) {
  await w.find(`[data-testid="${prefix}-input"]`).trigger('focus')
  await flushPromises()
  await w.find(`[data-testid="${prefix}-optie-${id}"]`).trigger('mousedown')
  await flushPromises()
}

beforeEach(() => {
  vi.clearAllMocks()
  api.partijen.soorten.mockResolvedValue([{ optie_sleutel: 'leverancier', label: 'Leverancier' }])
  // ZoekSelect-zoekresultaten voor de "hoort bij"-pickers (één organisatie beschikbaar).
  api.partijen.lijst.mockResolvedValue({
    items: [{ id: 'org1', naam: 'Gemeente X', aard: 'organisatie' }], volgende_cursor: null,
  })
  // Label-resolutie voor reeds-gekozen ouder-ids (ZoekSelect initieel-weergave).
  api.partijen.haal.mockResolvedValue({ id: 'org1', naam: 'Gemeente X', aard: 'organisatie' })
})
afterEach(() => vi.restoreAllMocks())

describe('PartijFormulier — aanmaken', () => {
  it('toont het functietitel-veld bij aard=persoon en verbergt het bij andere aarden (ADR-024)', async () => {
    const { w } = await mountForm()
    await w.find('[data-testid="veld-aard"]').setValue('persoon')
    expect(w.find('[data-testid="veld-functietitel"]').exists()).toBe(true)
    await w.find('[data-testid="veld-aard"]').setValue('organisatie')
    expect(w.find('[data-testid="veld-functietitel"]').exists()).toBe(false)
    await w.find('[data-testid="veld-aard"]').setValue('externe_partij')
    expect(w.find('[data-testid="veld-functietitel"]').exists()).toBe(false)
  })

  it('verbergt organisatie-/afdeling-/functietitel-veld bij aard=organisatie', async () => {
    const { w } = await mountForm()
    // persoon: organisatie-veld zichtbaar (referentie)
    await w.find('[data-testid="veld-aard"]').setValue('persoon')
    expect(w.find('[data-testid="veld-organisatie-input"]').exists()).toBe(true)
    // organisatie: geen ouder-organisatie, geen afdeling, geen functietitel
    await w.find('[data-testid="veld-aard"]').setValue('organisatie')
    expect(w.find('[data-testid="veld-organisatie-input"]').exists()).toBe(false)
    expect(w.find('[data-testid="veld-afdeling-input"]').exists()).toBe(false)
    expect(w.find('[data-testid="veld-functietitel"]').exists()).toBe(false)
  })

  // ADR-038 — intern/extern.
  it('toont intern/extern (default Extern) bij aard=organisatie en niet bij afdeling/persoon', async () => {
    const { w } = await mountForm()
    await w.find('[data-testid="veld-aard"]').setValue('organisatie')
    expect(w.find('[data-testid="veld-scope-wrap"]').exists()).toBe(true)
    expect(w.find('[data-testid="scope-radio-extern"]').element.checked).toBe(true)   // default Extern
    expect(w.find('[data-testid="scope-radio-intern"]').element.checked).toBe(false)
    await w.find('[data-testid="veld-aard"]').setValue('persoon')
    expect(w.find('[data-testid="veld-scope-wrap"]').exists()).toBe(false)
    expect(w.find('[data-testid="veld-scope-vast"]').exists()).toBe(false)
  })

  it('toont vast "Extern" (niet kiesbaar) bij aard=externe_partij', async () => {
    const { w } = await mountForm()
    await w.find('[data-testid="veld-aard"]').setValue('externe_partij')
    expect(w.find('[data-testid="veld-scope-vast"]').exists()).toBe(true)
    expect(w.find('[data-testid="veld-scope-wrap"]').exists()).toBe(false)
  })

  it('aanmaken organisatie stuurt de gekozen scope mee (intern)', async () => {
    api.partijen.maak.mockResolvedValueOnce({ id: 'o1' })
    const { w } = await mountForm()
    await w.find('[data-testid="veld-aard"]').setValue('organisatie')
    await w.find('[data-testid="veld-naam"]').setValue('BvoWB')
    await w.find('[data-testid="scope-radio-intern"]').setValue()
    await w.find('[data-testid="partij-form"]').trigger('submit')
    await flushPromises()
    expect(api.partijen.maak).toHaveBeenCalledWith(expect.objectContaining({ aard: 'organisatie', scope: 'intern' }))
  })

  it('aanmaken persoon stuurt geen scope (null)', async () => {
    api.partijen.maak.mockResolvedValueOnce({ id: 'p1' })
    const { w } = await mountForm()
    await w.find('[data-testid="veld-aard"]').setValue('persoon')
    await w.find('[data-testid="veld-naam"]').setValue('J. de Vries')
    await kiesZoek(w, 'veld-organisatie', 'org1')
    await w.find('[data-testid="partij-form"]').trigger('submit')
    await flushPromises()
    expect(api.partijen.maak).toHaveBeenCalledWith(expect.objectContaining({ scope: null }))
  })

  it('bewerken van een organisatie vult de scope voor (intern)', async () => {
    api.partijen.haal.mockResolvedValue({ id: 'o1', aard: 'organisatie', naam: 'BvoWB', scope: 'intern' })
    const { w } = await mountForm({ id: 'o1' })
    expect(w.find('[data-testid="scope-radio-intern"]').element.checked).toBe(true)
  })

  it('naam leeg ⇒ validatiefout, geen API-call', async () => {
    const { w } = await mountForm()
    await w.find('[data-testid="veld-aard"]').setValue('persoon')
    await w.find('[data-testid="partij-form"]').trigger('submit')
    expect(w.find('[data-testid="fout-naam"]').exists()).toBe(true)
    expect(api.partijen.maak).not.toHaveBeenCalled()
  })

  it('aard verplicht bij aanmaken', async () => {
    const { w } = await mountForm()
    await w.find('[data-testid="veld-naam"]').setValue('J. de Vries')
    await w.find('[data-testid="partij-form"]').trigger('submit')
    expect(w.find('[data-testid="fout-aard"]').exists()).toBe(true)
    expect(api.partijen.maak).not.toHaveBeenCalled()
  })

  it('persoon zonder organisatie ⇒ validatiefout, geen API-call', async () => {
    const { w } = await mountForm()
    await w.find('[data-testid="veld-aard"]').setValue('persoon')
    await w.find('[data-testid="veld-naam"]').setValue('J. de Vries')
    await w.find('[data-testid="partij-form"]').trigger('submit')
    expect(w.find('[data-testid="fout-organisatie_id"]').exists()).toBe(true)
    expect(api.partijen.maak).not.toHaveBeenCalled()
  })

  it('aanmaken persoon stuurt aard + naam + soort + organisatie', async () => {
    api.partijen.maak.mockResolvedValueOnce({ id: 'p1' })
    const { w, router } = await mountForm()
    await w.find('[data-testid="veld-aard"]').setValue('persoon')
    await w.find('[data-testid="veld-naam"]').setValue('J. de Vries')
    await w.find('[data-testid="veld-soort"]').setValue('leverancier')
    await kiesZoek(w, 'veld-organisatie', 'org1')  // verplicht voor persoon (ZoekSelect)
    await w.find('[data-testid="partij-form"]').trigger('submit')
    await flushPromises()
    expect(api.partijen.maak).toHaveBeenCalledWith(
      expect.objectContaining({ aard: 'persoon', naam: 'J. de Vries', soort: 'leverancier', organisatie_id: 'org1' }),
    )
    expect(router.currentRoute.value.name).toBe('partij-detail')
  })

  it('de organisatie-kiezer is een ZoekSelect-combobox (geen statische select)', async () => {
    const { w } = await mountForm()
    await w.find('[data-testid="veld-aard"]').setValue('persoon')
    const input = w.find('[data-testid="veld-organisatie-input"]')
    expect(input.exists()).toBe(true)
    expect(input.attributes('role')).toBe('combobox')
  })

  it('de afdeling-kiezer verschijnt pas nadat een organisatie is gekozen', async () => {
    const { w } = await mountForm()
    await w.find('[data-testid="veld-aard"]').setValue('persoon')
    expect(w.find('[data-testid="veld-afdeling-input"]').exists()).toBe(false)
    await kiesZoek(w, 'veld-organisatie', 'org1')
    expect(w.find('[data-testid="veld-afdeling-input"]').exists()).toBe(true)
  })

  it('soort-dropdown wordt gevuld uit de catalogus', async () => {
    const { w } = await mountForm()
    const opties = w.find('[data-testid="veld-soort"]').findAll('option').map((o) => o.text())
    expect(opties).toContain('Leverancier')
  })

  it('422-veldfout van de backend landt op het juiste veld', async () => {
    api.partijen.maak.mockRejectedValueOnce({ status: 422, detail: [{ loc: ['body', 'naam'], msg: 'Te lang.' }] })
    const { w } = await mountForm()
    await w.find('[data-testid="veld-aard"]').setValue('organisatie')
    await w.find('[data-testid="veld-naam"]').setValue('X')
    await w.find('[data-testid="partij-form"]').trigger('submit')
    await flushPromises()
    expect(w.find('[data-testid="fout-naam"]').text()).toContain('Te lang.')
  })
})

describe('PartijFormulier — prefill vanaf organisatie/afdeling (UX-A2/A3)', () => {
  it('?aard=organisatie_eenheid&organisatie_id=org1 vult aard + organisatie voor', async () => {
    const { w } = await mountForm({ query: { aard: 'organisatie_eenheid', organisatie_id: 'org1' } })
    expect(w.find('[data-testid="veld-aard"]').element.value).toBe('organisatie_eenheid')
    // organisatie-veld zichtbaar (heeftOrgOuder) en voorgevuld — ZoekSelect toont het label.
    expect(w.find('[data-testid="veld-organisatie-input"]').element.value).toBe('Gemeente X')
  })

  it('?aard=persoon&organisatie_id=org1&afdeling_id=afd1 vult aard + organisatie + afdeling voor', async () => {
    // Label-resolutie per id (ZoekSelect initieel-weergave).
    api.partijen.haal.mockImplementation((id) =>
      Promise.resolve(id === 'afd1' ? { id: 'afd1', naam: 'Afdeling I&A' } : { id: 'org1', naam: 'Gemeente X' }),
    )
    const { w } = await mountForm({ query: { aard: 'persoon', organisatie_id: 'org1', afdeling_id: 'afd1' } })
    expect(w.find('[data-testid="veld-aard"]').element.value).toBe('persoon')
    expect(w.find('[data-testid="veld-organisatie-input"]').element.value).toBe('Gemeente X')
    expect(w.find('[data-testid="veld-afdeling-input"]').element.value).toBe('Afdeling I&A')
  })

  it('voorgevulde persoon is direct opslaanbaar (organisatie al ingevuld, geen validatiefout)', async () => {
    api.partijen.maak.mockResolvedValueOnce({ id: 'p9' })
    const { w } = await mountForm({ query: { aard: 'persoon', organisatie_id: 'org1' } })
    await w.find('[data-testid="veld-naam"]').setValue('J. de Vries')
    await w.find('[data-testid="partij-form"]').trigger('submit')
    await flushPromises()
    expect(w.find('[data-testid="fout-organisatie_id"]').exists()).toBe(false)
    expect(api.partijen.maak).toHaveBeenCalledWith(
      expect.objectContaining({ aard: 'persoon', naam: 'J. de Vries', organisatie_id: 'org1' }),
    )
  })

  it('na opslaan met organisatie-context → terug naar de organisatie (niet de nieuwe partij)', async () => {
    api.partijen.maak.mockResolvedValueOnce({ id: 'p9' })
    const { w, router } = await mountForm({ query: { aard: 'persoon', organisatie_id: 'org1' } })
    await w.find('[data-testid="veld-naam"]').setValue('J. de Vries')
    await w.find('[data-testid="partij-form"]').trigger('submit')
    await flushPromises()
    expect(router.currentRoute.value.name).toBe('partij-detail')
    expect(router.currentRoute.value.params.id).toBe('org1')  // terug naar de ouder
  })

  it('na opslaan met afdeling-context → terug naar de afdeling (afdeling vóór organisatie)', async () => {
    api.partijen.maak.mockResolvedValueOnce({ id: 'p9' })
    api.partijen.lijst.mockImplementation(({ aard } = {}) =>
      Promise.resolve(
        aard === 'organisatie_eenheid'
          ? { items: [{ id: 'afd1', naam: 'Afdeling I&A', aard: 'organisatie_eenheid' }], volgende_cursor: null }
          : { items: [{ id: 'org1', naam: 'Gemeente X', aard: 'organisatie' }], volgende_cursor: null },
      ),
    )
    const { w, router } = await mountForm({ query: { aard: 'persoon', organisatie_id: 'org1', afdeling_id: 'afd1' } })
    await w.find('[data-testid="veld-naam"]').setValue('J. de Vries')
    await w.find('[data-testid="partij-form"]').trigger('submit')
    await flushPromises()
    expect(router.currentRoute.value.params.id).toBe('afd1')  // afdeling wint van organisatie
  })

  it('gewone aanmaak zonder ouder-context → naar de nieuwe partij (ongewijzigd gedrag)', async () => {
    api.partijen.maak.mockResolvedValueOnce({ id: 'p9' })
    const { w, router } = await mountForm()
    await w.find('[data-testid="veld-aard"]').setValue('organisatie')
    await w.find('[data-testid="veld-naam"]').setValue('Gemeente Y')
    await w.find('[data-testid="partij-form"]').trigger('submit')
    await flushPromises()
    expect(router.currentRoute.value.params.id).toBe('p9')  // de nieuwe partij
  })
})

describe('PartijFormulier — bewerken', () => {
  it('aard is read-only (geen keuzeveld) en niet in de payload', async () => {
    // Afdeling hoort verplicht bij een organisatie (org1 zit in de kandidaten-mock).
    api.partijen.haal.mockResolvedValueOnce({ id: 'p1', aard: 'organisatie_eenheid', naam: 'Afdeling I&A', soort: null, organisatie_id: 'org1' })
    api.partijen.werkBij.mockResolvedValueOnce({ id: 'p1' })
    const { w } = await mountForm({ id: 'p1' })
    expect(w.find('[data-testid="veld-aard"]').exists()).toBe(false)
    expect(w.find('[data-testid="aard-readonly"]').text()).toContain('Afdeling')
    await w.find('[data-testid="veld-naam"]').setValue('Afdeling I&A (gewijzigd)')
    await w.find('[data-testid="partij-form"]').trigger('submit')
    await flushPromises()
    const payload = api.partijen.werkBij.mock.calls[0][1]
    expect('aard' in payload).toBe(false)
  })
})
