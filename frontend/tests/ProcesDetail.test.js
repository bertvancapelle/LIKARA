/** Tests — ProcesDetail + ProcesComponentenSectie (ADR-042 slice 4a). */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'

vi.mock('@/api', () => ({
  api: {
    processen: { haal: vi.fn(), lijst: vi.fn(), maak: vi.fn(), rollup: vi.fn() },
    procesvervullingen: { lijst: vi.fn(), functies: vi.fn(), maak: vi.fn(), werkBij: vi.fn(), verwijder: vi.fn() },
    componenten: { lijst: vi.fn() },
  },
}))

// LI035 succes-standaard — helper gemockt zodat de succes-flows assertbaar zijn.
vi.mock('@/meldingen', () => ({ toastSucces: vi.fn() }))

import { api } from '@/api'
import { toastSucces } from '@/meldingen'
import { useAuthStore } from '@/store/auth'
import ProcesDetail from '@modules/bwb_ontvlechting/frontend/views/ProcesDetail.vue'

const _PROCESSEN = {
  vv: { id: 'vv', naam: 'Vergunningverlening', toelichting: 'Bedrijfsproces.', ouder_id: null },
  ab: { id: 'ab', naam: 'Aanvraag behandelen', toelichting: 'Werkproces.', ouder_id: 'vv' },
}

const _regel = (id, comp, functieLabel, extra = {}) => ({
  vervulling_id: id,
  applicatiefunctie: functieLabel.toLowerCase(),
  applicatiefunctie_label: functieLabel,
  toelichting: null,
  component_id: `c-${id}`,
  component_naam: comp,
  componenttype: 'applicatie',
  componenttype_label: 'Applicatie',
  ...extra,
})

const _FUNCTIES = [
  { optie_sleutel: 'registreren', label: 'Registreren' },
  { optie_sleutel: 'raadplegen', label: 'Raadplegen' },
]

// Param-filterende component-mock (LI032-les: nooit een vaste set die filters negeert).
const _COMPONENTEN = [
  { id: 'zs', naam: 'Zaaksysteem', componenttype: 'applicatie', componenttype_label: 'Applicatie' },
  { id: 'db', naam: 'Shared DB-server', componenttype: 'database', componenttype_label: 'Database' },
]

function maakRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/processen', name: 'proces-lijst', component: { template: '<div/>' } },
      { path: '/processen/:id', name: 'proces-detail', component: ProcesDetail, props: true },
      { path: '/componenten/:id', name: 'component-detail', component: { template: '<div/>' } },
    ],
  })
}

async function mountDetail({ id = 'ab', rollen = ['medewerker'] } = {}) {
  const router = maakRouter()
  await router.push(`/processen/${id}`)
  await router.isReady()
  const pinia = createPinia()
  const auth = useAuthStore(pinia)
  auth.user = { sub: 's', tenant_id: 't', email: 'a@b.nl', roles: rollen }
  const w = mount(ProcesDetail, {
    props: { id },
    global: { plugins: [pinia, [PrimeVue, { unstyled: true }], ToastService, router], stubs: { teleport: true } },
  })
  await flushPromises()
  return w
}

beforeEach(() => {
  vi.clearAllMocks()
  sessionStorage.clear()
  api.processen.haal.mockImplementation(async (id) => _PROCESSEN[id])
  api.processen.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
  api.processen.rollup.mockResolvedValue([]) // slice 5 — default geen doorgerolde regels
  api.procesvervullingen.lijst.mockResolvedValue([
    _regel('r1', 'Zaaksysteem', 'Registreren'),
    _regel('r2', 'DMS', 'Archiveren', { toelichting: 'Besluitdocumenten.' }),
  ])
  api.procesvervullingen.functies.mockResolvedValue(_FUNCTIES)
  api.componenten.lijst.mockImplementation(async (params = {}) => {
    const term = (params.zoek || '').toLowerCase()
    return { items: _COMPONENTEN.filter((c) => !term || c.naam.toLowerCase().includes(term)), volgende_cursor: null }
  })
})
afterEach(() => vi.restoreAllMocks())

describe('ProcesDetail — kop en context', () => {
  it('toont naam, toelichting en een KLIKBARE broodkruimel naar boven', async () => {
    const w = await mountDetail({ id: 'ab' })
    expect(w.find('#proces-titel').text()).toBe('Aanvraag behandelen')
    expect(w.find('[data-testid="proces-toelichting"]').text()).toContain('Werkproces.')
    const kruimel = w.find('[data-testid="proces-broodkruimel"]')
    expect(kruimel.text()).toContain('Vergunningverlening')
    expect(kruimel.find('a').attributes('href')).toContain('/processen/vv')
  })

  it('een top-level proces heeft geen broodkruimel', async () => {
    const w = await mountDetail({ id: 'vv' })
    expect(w.find('[data-testid="proces-broodkruimel"]').exists()).toBe(false)
  })
})

describe('ProcesDetail — deelprocessen', () => {
  it('toont de directe kinderen en linkt door', async () => {
    api.processen.lijst.mockResolvedValue({ items: [_PROCESSEN.ab], volgende_cursor: null })
    const w = await mountDetail({ id: 'vv' })
    expect(api.processen.lijst).toHaveBeenCalledWith(expect.objectContaining({ ouder_id: 'vv' }))
    expect(w.find('[data-testid="deelproces-link"]').attributes('href')).toContain('/processen/ab')
  })

  it('"+ Deelproces toevoegen" heeft de ouder voorgevuld en stuurt ouder_id mee', async () => {
    api.processen.maak.mockResolvedValue({ id: 'nieuw' })
    const w = await mountDetail({ id: 'vv' })
    await w.find('[data-testid="deelproces-toevoegen"]').trigger('click')
    expect(w.find('[data-testid="deelproces-ouder"]').text()).toBe('Vergunningverlening')
    await w.find('[data-testid="deelproces-naam"]').setValue('Bezwaar afhandelen')
    await w.find('[data-testid="deelproces-opslaan"]').trigger('submit')
    await flushPromises()
    expect(api.processen.maak).toHaveBeenCalledWith({
      naam: 'Bezwaar afhandelen', toelichting: null, ouder_id: 'vv',
    })
    expect(toastSucces).toHaveBeenCalledWith(expect.anything(), 'Deelproces aangemaakt')
  })

  // ADR-042 slice 5 (samengevoegd blok) — "Onderliggende processen" staat er altijd
  // (lege staat + toevoegknop op een blad-proces), maar de rollup-fetch loopt alléén
  // als er deelprocessen zijn; de componenten-sectie staat erbóven.
  it('samengevoegd "Onderliggende processen"-blok: altijd aanwezig, rollup alleen bij deelprocessen', async () => {
    const blad = await mountDetail({ id: 'ab' })
    expect(blad.find('[data-testid="onderliggend-sectie"]').exists()).toBe(true)
    expect(blad.find('[data-testid="deelprocessen-leeg"]').exists()).toBe(true)
    expect(api.processen.rollup).not.toHaveBeenCalled()

    api.processen.lijst.mockResolvedValue({ items: [_PROCESSEN.ab], volgende_cursor: null })
    const w = await mountDetail({ id: 'vv' })
    expect(api.processen.rollup).toHaveBeenCalledWith('vv')
    // Volgorde: eerst de registratie op dít niveau, dan het onderliggende blok.
    const html = w.html()
    expect(html.indexOf('proces-componenten-sectie')).toBeLessThan(html.indexOf('onderliggend-sectie'))
  })

  it('lege staat wijst de route naar de actie', async () => {
    const w = await mountDetail({ id: 'ab' })
    expect(w.find('[data-testid="deelprocessen-leeg"]').text()).toContain('Deelproces toevoegen')
  })
})

describe('ProcesComponentenSectie — koppelregels', () => {
  it('toont de regels als leesbare zinnen met klikbaar component en Bewerken/Verwijderen-acties', async () => {
    const w = await mountDetail({ id: 'ab' })
    const regel = w.find('[data-testid="pcs-regel-r1"]')
    expect(regel.text()).toContain('Zaaksysteem')
    expect(regel.text()).toContain('Registreren')
    expect(regel.find('[data-testid="pcs-component-link"]').attributes('href')).toContain('/componenten/c-r1')
    expect(w.find('[data-testid="pcs-regel-r2"]').text()).toContain('Besluitdocumenten.')
    expect(w.find('[data-testid="pcs-bewerk-r1"]').exists()).toBe(true)
    expect(w.find('[data-testid="pcs-verwijder-r1"]').exists()).toBe(true)
  })

  it('verwijderen vraagt bevestiging met de regel leesbaar; bevestigen = call, annuleren = geen call (LI035)', async () => {
    const w = await mountDetail({ id: 'ab' })
    // Annuleren eerst: geen call.
    await w.find('[data-testid="pcs-verwijder-r1"]').trigger('click')
    await flushPromises()
    const omschrijving = w.find('[data-testid="pcs-verwijder-omschrijving"]')
    expect(omschrijving.text()).toContain('Registreren')
    expect(omschrijving.text()).toContain('Aanvraag behandelen') // de procesnaam leesbaar in de vraag
    expect(omschrijving.text()).toContain('Zaaksysteem')
    await w.find('[data-testid="pcs-verwijder-annuleer"]').trigger('click')
    await flushPromises()
    expect(api.procesvervullingen.verwijder).not.toHaveBeenCalled()
    // Dan bevestigen: één call + herladen.
    await w.find('[data-testid="pcs-verwijder-r1"]').trigger('click')
    await flushPromises()
    await w.find('[data-testid="pcs-verwijder-bevestig"]').trigger('click')
    await flushPromises()
    expect(api.procesvervullingen.verwijder).toHaveBeenCalledWith('r1')
    expect(toastSucces).toHaveBeenCalledWith(expect.anything(), 'Verwijderd')
  })

  it('bewerken opent voorgevuld (ankers read-only) en PATCHt alleen de kenmerk-velden', async () => {
    api.procesvervullingen.werkBij.mockResolvedValue({})
    const w = await mountDetail({ id: 'ab' })
    await w.find('[data-testid="pcs-bewerk-r2"]').trigger('click')
    // Identiteit read-only zichtbaar: component + proces.
    const identiteit = w.find('[data-testid="pcs-bewerk-identiteit"]')
    expect(identiteit.text()).toContain('DMS')
    expect(identiteit.text()).toContain('Aanvraag behandelen')
    // Voorgevuld met de huidige kenmerken.
    expect(w.find('[data-testid="pcs-bewerk-toelichting"]').element.value).toBe('Besluitdocumenten.')
    await w.find('[data-testid="pcs-bewerk-functie"]').setValue('raadplegen')
    await w.find('[data-testid="pcs-bewerk-toelichting"]').setValue('Bijgesteld.')
    await w.find('[data-testid="pcs-bewerk-opslaan"]').trigger('submit')
    await flushPromises()
    expect(api.procesvervullingen.werkBij).toHaveBeenCalledWith('r2', {
      applicatiefunctie: 'raadplegen', toelichting: 'Bijgesteld.',
    })
    expect(toastSucces).toHaveBeenCalledWith(expect.anything(), 'Opgeslagen')
  })

  it('bewerken: een inactieve huidige functie blijft als label kiesbaar/zichtbaar', async () => {
    api.procesvervullingen.lijst.mockResolvedValue([
      _regel('r9', 'Zaaksysteem', 'Oud-functie', { applicatiefunctie: 'oud_functie' }),
    ])
    const w = await mountDetail({ id: 'ab' })
    await w.find('[data-testid="pcs-bewerk-r9"]').trigger('click')
    const opties = w.find('[data-testid="pcs-bewerk-functie"]').findAll('option').map((o) => o.text())
    expect(opties).toContain('Oud-functie (niet meer actief)')
    expect(w.find('[data-testid="pcs-bewerk-functie"]').element.value).toBe('oud_functie')
  })

  it('bewerken naar een bestaand tripel (409) → rustige melding in de dialoog', async () => {
    const err = new Error('bestaat al')
    err.status = 409
    err.code = 'VERVULLING_BESTAAT'
    api.procesvervullingen.werkBij.mockRejectedValue(err)
    const w = await mountDetail({ id: 'ab' })
    await w.find('[data-testid="pcs-bewerk-r1"]').trigger('click')
    await w.find('[data-testid="pcs-bewerk-functie"]').setValue('raadplegen')
    await w.find('[data-testid="pcs-bewerk-opslaan"]').trigger('submit')
    await flushPromises()
    const melding = w.find('[data-testid="pcs-bewerk-melding"]')
    expect(melding.exists()).toBe(true)
    expect(melding.attributes('role')).toBe('status')
    expect(melding.text()).toContain('bestaat al')
    // LI035 — óók in de dialoog een zichtbare warn-banner met icoon.
    expect(melding.classes().join(' ')).toContain('lk-color-warning')
    expect(w.find('[data-testid="pcs-bewerk-melding-icoon"]').text()).toBe('⚠')
    // Verdwijnt zodra de invoer in de dialoog wijzigt.
    await w.find('[data-testid="pcs-bewerk-toelichting"]').setValue('nieuwe poging')
    await flushPromises()
    expect(w.find('[data-testid="pcs-bewerk-melding"]').exists()).toBe(false)
  })

  it('koppelregel leggen: picker (component-breed, type-label zichtbaar) + functie → maak', async () => {
    api.procesvervullingen.maak.mockResolvedValue({})
    const w = await mountDetail({ id: 'ab' })
    // Open de picker echt (LI032-norm) — de startlijst toont ALLE typen mét type-label.
    await w.find('[data-testid="pcs-component-input"]').trigger('focus')
    await flushPromises()
    const dbOptie = w.find('[data-testid="pcs-component-optie-db"]')
    expect(dbOptie.text()).toContain('Shared DB-server — Database') // component-breed + type-label
    await dbOptie.trigger('mousedown')
    await w.find('[data-testid="pcs-functie-select"]').setValue('registreren')
    await w.find('[data-testid="pcs-toelichting"]').setValue('Ondersteunt het domein.')
    await w.find('[data-testid="pcs-toevoegregel"]').trigger('submit')
    await flushPromises()
    expect(api.procesvervullingen.maak).toHaveBeenCalledWith({
      component_id: 'db', proces_id: 'ab',
      applicatiefunctie: 'registreren', toelichting: 'Ondersteunt het domein.',
    })
    expect(toastSucces).toHaveBeenCalledWith(expect.anything(), 'Toegevoegd')
  })

  it('409 VERVULLING_BESTAAT → vriendelijke melding (role=status, geen role=alert)', async () => {
    const err = new Error('bestaat al')
    err.status = 409
    err.code = 'VERVULLING_BESTAAT'
    api.procesvervullingen.maak.mockRejectedValue(err)
    const w = await mountDetail({ id: 'ab' })
    await w.find('[data-testid="pcs-component-input"]').trigger('focus')
    await flushPromises()
    await w.find('[data-testid="pcs-component-optie-zs"]').trigger('mousedown')
    await w.find('[data-testid="pcs-functie-select"]').setValue('registreren')
    await w.find('[data-testid="pcs-toevoegregel"]').trigger('submit')
    await flushPromises()
    const melding = w.find('[data-testid="pcs-melding"]')
    expect(melding.exists()).toBe(true)
    expect(melding.attributes('role')).toBe('status')
    expect(melding.text()).toContain('bestaat al')
    // LI035 — onmiskenbare warn-banner (kleur + icoon), geen stille grijze tekst.
    expect(melding.classes().join(' ')).toContain('lk-color-warning')
    expect(w.find('[data-testid="pcs-melding-icoon"]').text()).toBe('⚠')
    // LI035 positie-fix: de banner staat BOVEN de invoervelden (leesvolgorde vóór
    // de te corrigeren velden) — DOM-volgorde in het toevoegregel-formulier.
    const formHtml = w.find('[data-testid="pcs-toevoegregel"]').html()
    expect(formHtml.indexOf('pcs-melding')).toBeGreaterThan(-1)
    expect(formHtml.indexOf('pcs-melding')).toBeLessThan(formHtml.indexOf('pcs-component-input'))
    // De banner verdwijnt zodra de invoer wijzigt (hoort bij de geweigerde poging).
    await w.find('[data-testid="pcs-functie-select"]').setValue('raadplegen')
    await flushPromises()
    expect(w.find('[data-testid="pcs-melding"]').exists()).toBe(false)
  })

  it('rol-gating: viewer ziet regels maar geen toevoegregel/verwijderkruisjes', async () => {
    const w = await mountDetail({ id: 'ab', rollen: ['viewer'] })
    expect(w.find('[data-testid="pcs-regel-r1"]').exists()).toBe(true)
    expect(w.find('[data-testid="pcs-toevoegregel"]').exists()).toBe(false)
    expect(w.find('[data-testid="pcs-verwijder-r1"]').exists()).toBe(false)
  })
})
