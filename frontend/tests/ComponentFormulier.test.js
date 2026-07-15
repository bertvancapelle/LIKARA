/** Tests — ComponentFormulier als OVERLAY (ADR-042 4b; aanmaken/bewerken élk componenttype). */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'

vi.mock('@/api', () => ({
  api: {
    componenten: { opties: vi.fn(), haal: vi.fn(), maak: vi.fn(), werkBij: vi.fn() },
    // ADR-043 gate 4 — bij aanmaken grof koppelen; bij bewerken de direct-opslaande sectie.
    bedrijfsfuncties: { lijst: vi.fn(), haal: vi.fn() },
    functievervullingen: { maak: vi.fn(), componentKoppelingen: vi.fn(), verwijder: vi.fn(), zetOordeel: vi.fn() },
    partijen: { lijst: vi.fn() },
  },
}))

import { api } from '@/api'
import { useAuthStore } from '@/store/auth'
import ComponentFormulier from '@modules/bwb_ontvlechting/frontend/views/ComponentFormulier.vue'

function maakRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'dashboard', component: { template: '<div/>' } },
      { path: '/processen', name: 'proces-lijst', component: { template: '<div/>' } },
      { path: '/processen/:id', name: 'proces-detail', component: { template: '<div/>' } },
    ],
  })
}

async function mountForm({ id = null, rollen = ['medewerker'] } = {}) {
  const router = maakRouter()
  await router.push('/')
  await router.isReady()
  const pinia = createPinia()
  const auth = useAuthStore(pinia)
  auth.user = { sub: 's', tenant_id: 't', email: 'a@b.nl', roles: rollen }
  const w = mount(ComponentFormulier, {
    props: { visible: true, id },
    attachTo: document.body,
    global: { plugins: [pinia, [PrimeVue, { unstyled: true }], ToastService, router], stubs: { teleport: true } },
  })
  await flushPromises()
  return { w, router }
}

beforeEach(() => {
  vi.clearAllMocks()
  api.componenten.opties.mockResolvedValue({
    componenttype: [
      { optie_sleutel: 'database', label: 'Database' },
      { optie_sleutel: 'fileshare', label: 'Fileshare' },
      { optie_sleutel: 'applicatie', label: 'Applicatie' },
    ],
    structuurrelatie_type: [],
    componentrol_opties: [
      { optie_sleutel: 'interne_applicatie', label: 'Interne applicatie' },
      { optie_sleutel: 'externe_dataprovider', label: 'Externe dataprovider' },
    ],
    biv_niveaus: [
      { optie_sleutel: 'laag', label: 'Laag' },
      { optie_sleutel: 'midden', label: 'Midden' },
      { optie_sleutel: 'hoog', label: 'Hoog' },
    ],
  })
  api.bedrijfsfuncties.lijst.mockResolvedValue({
    items: [
      { id: 'vv', naam: 'Vergunningverlening', ouder_ids: [], vervallen: false },
      { id: 'ab', naam: 'Aanvraag behandelen', ouder_ids: ['vv'], vervallen: false },
    ],
    volgende_cursor: null,
  })
  api.functievervullingen.componentKoppelingen.mockResolvedValue([])
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('ComponentFormulier — overlay + layout (ADR-042 4b)', () => {
  it('rendert als overlay met twee kolommen en een vaste voetbalk', async () => {
    const { w } = await mountForm()
    const overlay = w.find('[data-testid="component-form-overlay"]')
    expect(overlay.exists()).toBe(true)
    // BREEDTE-BORGING (browserbevinding 4b): het Dialog-preset capt élke dialog op
    // max-w-lg (512px); zonder een !important-max-w-override op de root wint die cap
    // en drukken de twee kolommen samen (overlappende BIV-labels, afgekapte selects).
    // Deze assert had die misser gevangen: de override MOET op de dialog-root staan.
    // (De preset-classes zelf zitten niet in de test-mount — unstyled zonder pt;
    // de te borgen invariant is dat de root de !important-override draagt.)
    const klassen = overlay.classes().join(' ')
    expect(klassen).toContain('!max-w-[min(60rem,95vw)]')
    expect(klassen).toContain('!w-[min(60rem,95vw)]')
    // Twee-kolommen-grid (smal scherm stapelt via grid-cols-1 → md:grid-cols-2).
    const grid = w.find('[data-testid="component-form"]').find('.md\\:grid-cols-2')
    expect(grid.exists()).toBe(true)
    // BIV-drieluik en plaatsing-2×2: selects vullen hun cel (geen afgekapte waarden).
    expect(w.find('[data-testid="veld-biv_beschikbaarheid"]').classes()).toContain('w-full')
    expect(w.find('[data-testid="veld-hostingmodel"]').classes()).toContain('w-full')
    // VOETBALK-STRUCTUUR (browserbevinding 4b): de knoppenbalk staat in het
    // #footer-slot van de Dialog — BUITEN het formulier/scroll-gebied — zodat hij
    // bij lange inhoud in beeld blijft. Opslaan blijft via het form-attribuut een
    // echte submit van het formulier (Enter in een veld werkt dus ook).
    const formEl = w.find('[data-testid="component-form"]')
    const voetbalk = w.find('[data-testid="form-voetbalk"]')
    expect(voetbalk.exists()).toBe(true)
    expect(formEl.find('[data-testid="form-voetbalk"]').exists()).toBe(false)
    const opslaan = voetbalk.find('[data-testid="opslaan-knop"]')
    expect(opslaan.exists()).toBe(true)
    expect(opslaan.attributes('form')).toBe('component-form-el')
    expect(formEl.attributes('id')).toBe('component-form-el')
    // OMLIJNING-INVARIANT (browserbevinding 4b): de view bouwt GEEN eigen
    // scroll-gebied — zo'n binnen-wrapper omzeilt de preset-padding en clipt de
    // veldranden/focus-ringen aan de linkerrand af. Scrollen (incl. scroll-schaduw)
    // hoort bij het preset-content van de Dialog-primitive; zie dialogPreset.test.js.
    expect(formEl.element.querySelector('.overflow-y-auto')).toBe(null)
  })

  it('de type-select bevat "applicatie" (convergente aanmaak)', async () => {
    const { w } = await mountForm()
    const waarden = w.find('[data-testid="veld-componenttype"]').findAll('option').map((o) => o.attributes('value'))
    expect(waarden).toContain('database')
    expect(waarden).toContain('fileshare')
    expect(waarden).toContain('applicatie')
  })

  it('naam is verplicht (geen API-call bij leeg)', async () => {
    const { w } = await mountForm()
    await w.find('[data-testid="veld-componenttype"]').setValue('database')
    await w.find('[data-testid="component-form"]').trigger('submit')
    await flushPromises()
    expect(w.find('[data-testid="fout-naam"]').exists()).toBe(true)
    expect(api.componenten.maak).not.toHaveBeenCalled()
  })

  it('aanmaken stuurt de payload (incl. transitie/rol/BIV) en emit opgeslagen + sluiten', async () => {
    api.componenten.maak.mockResolvedValueOnce({ id: 'new-1' })
    const { w } = await mountForm()
    await w.find('[data-testid="veld-naam"]').setValue('Geo-fileshare')
    await w.find('[data-testid="veld-componenttype"]').setValue('fileshare')
    // ADR-046 — `uitfaseren` is een LEVENSFASE, geen bedoeling meer; de bedoeling
    // (migratiepad) kent alleen bestemmingen.
    await w.find('[data-testid="veld-migratiepad"]').setValue('vervangen')
    await w.find('[data-testid="veld-levensfase"]').setValue('uitfaseren')
    await w.find('[data-testid="veld-componentrol"]').setValue('externe_dataprovider')
    await w.find('[data-testid="veld-biv_vertrouwelijkheid"]').setValue('hoog')
    await w.find('[data-testid="component-form"]').trigger('submit')
    await flushPromises()
    expect(api.componenten.maak).toHaveBeenCalledWith(
      expect.objectContaining({
        naam: 'Geo-fileshare', componenttype: 'fileshare', migratiepad: 'vervangen',
        levensfase: 'uitfaseren',
        // LI040 — oordelen niet aangeraakt in dit formulier → null (geen gratis 'midden').
        complexiteit: null, prioriteit: null,
        componentrol: 'externe_dataprovider',
        biv_beschikbaarheid: null, biv_integriteit: null, biv_vertrouwelijkheid: 'hoog',
      }),
    )
    expect(w.emitted('opgeslagen')[0][0]).toEqual({ id: 'new-1' })
    expect(w.emitted('update:visible').at(-1)).toEqual([false])
  })

  it('levensfase én bedoeling mogen LEEG blijven — opslaan met null, geen verzonnen waarde (LI040)', async () => {
    api.componenten.maak.mockResolvedValueOnce({ id: 'new-2' })
    const { w } = await mountForm()
    // Beide keuzelijsten bieden de leeg-optie expliciet aan als "nog niet vastgelegd".
    const faseOpties = w.find('[data-testid="veld-levensfase"]').findAll('option').map((o) => o.text())
    expect(faseOpties[0]).toContain('nog niet vastgelegd')
    expect(faseOpties).toEqual(expect.arrayContaining(['In ontwikkeling', 'In productie', 'Uitfaseren']))
    const padOpties = w.find('[data-testid="veld-migratiepad"]').findAll('option').map((o) => o.text())
    expect(padOpties[0]).toContain('nog niet vastgelegd')
    expect(padOpties).not.toContain('Onbekend') // LI040 — de sentinel is weg
    await w.find('[data-testid="veld-naam"]').setValue('Zonder fase')
    await w.find('[data-testid="veld-componenttype"]').setValue('fileshare')
    await w.find('[data-testid="component-form"]').trigger('submit')
    await flushPromises()
    expect(api.componenten.maak).toHaveBeenCalledWith(
      expect.objectContaining({ naam: 'Zonder fase', levensfase: null, migratiepad: null }),
    )
  })

  it('foutmapping: 422-veldfout van de backend landt op het veld; ONGELDIGE_ROL op rol', async () => {
    api.componenten.maak.mockRejectedValueOnce({
      status: 422,
      detail: [{ loc: ['body', 'naam'], msg: 'Ongeldige naam.' }],
    })
    const { w } = await mountForm()
    await w.find('[data-testid="veld-naam"]').setValue('x')
    await w.find('[data-testid="veld-componenttype"]').setValue('database')
    await w.find('[data-testid="component-form"]').trigger('submit')
    await flushPromises()
    expect(w.find('[data-testid="fout-naam"]').text()).toContain('Ongeldige naam.')

    api.componenten.maak.mockRejectedValueOnce({ status: 422, code: 'ONGELDIGE_ROL', message: 'Kies een geldige rol.' })
    await w.find('[data-testid="veld-naam"]').setValue('X')
    await w.find('[data-testid="component-form"]').trigger('submit')
    await flushPromises()
    expect(w.find('[data-testid="fout-componentrol"]').text()).toContain('Kies een geldige rol.')
  })
})

describe('ComponentFormulier — verzamel-bedrijfsfunctiekoppelingen bij aanmaken (grof)', () => {
  async function kiesFunctie(w, id) {
    await w.find('[data-testid="regel-bedrijfsfunctie-input"]').trigger('focus')
    await flushPromises()
    await w.find(`[data-testid="regel-bedrijfsfunctie-optie-${id}"]`).trigger('mousedown')
    await flushPromises()
  }

  it('koppelingen samenstellen met "+" (functienaam in lijstje); kruisje verwijdert', async () => {
    const { w } = await mountForm()
    await w.find('[data-testid="regel-bedrijfsfunctie-input"]').trigger('focus')
    await flushPromises()
    expect(w.find('[data-testid="regel-bedrijfsfunctie-optie-ab"]').text()).toContain('Aanvraag behandelen')
    await w.find('[data-testid="regel-bedrijfsfunctie-optie-ab"]').trigger('mousedown')
    await flushPromises()
    await w.find('[data-testid="regel-toevoegen"]').trigger('click')
    const lijst = w.find('[data-testid="regels-lijst"]')
    expect(lijst.text()).toContain('Aanvraag behandelen')
    expect(lijst.text()).toContain('geldt overal')
    await w.find('[data-testid="regel-verwijder-0"]').trigger('click')
    expect(w.find('[data-testid="regels-lijst"]').exists()).toBe(false)
  })

  it('verzamelde koppelingen worden ná het component in één keer grof opgeslagen', async () => {
    api.componenten.maak.mockResolvedValueOnce({ id: 'c-pr' })
    api.functievervullingen.maak.mockResolvedValue({})
    const { w } = await mountForm()
    await w.find('[data-testid="veld-naam"]').setValue('Zaaksysteem 2')
    await w.find('[data-testid="veld-componenttype"]').setValue('applicatie')
    await kiesFunctie(w, 'ab')
    await w.find('[data-testid="regel-oordeel"]').setValue('noodoplossing')
    await w.find('[data-testid="regel-toevoegen"]').trigger('click')
    await w.find('[data-testid="component-form"]').trigger('submit')
    await flushPromises()
    expect(api.functievervullingen.maak).toHaveBeenCalledWith({
      component_id: 'c-pr', functie_id: 'ab', ouder_functie_id: null,
      oordeel: 'noodoplossing', toelichting: null,
    })
    expect(w.emitted('opgeslagen')).toBeTruthy()
  })

  it('faalt een koppeling → component stáát, danger-banner met de functienaam; retry maakt het component NIET opnieuw', async () => {
    api.componenten.maak.mockResolvedValueOnce({ id: 'c-half' })
    const err = new Error('bestaat al')
    err.status = 409
    err.code = 'KOPPELING_BESTAAT'
    api.functievervullingen.maak.mockRejectedValueOnce(err).mockResolvedValueOnce({})
    const { w } = await mountForm()
    await w.find('[data-testid="veld-naam"]').setValue('Half')
    await w.find('[data-testid="veld-componenttype"]').setValue('database')
    await kiesFunctie(w, 'ab')
    await w.find('[data-testid="regel-toevoegen"]').trigger('click')
    await w.find('[data-testid="component-form"]').trigger('submit')
    await flushPromises()
    expect(w.emitted('opgeslagen')).toBeFalsy()
    const banner = w.find('[data-testid="regels-opslaanfout"]')
    expect(banner.text()).toContain('Aanvraag behandelen')
    expect(banner.text()).toContain('bestaat al')
    expect(w.find('[data-testid="opslaan-knop"]').text()).toContain('Opnieuw proberen')
    // Retry: component-maak NIET opnieuw, alleen de resterende koppeling.
    await w.find('[data-testid="component-form"]').trigger('submit')
    await flushPromises()
    expect(api.componenten.maak).toHaveBeenCalledTimes(1)
    expect(api.functievervullingen.maak).toHaveBeenCalledTimes(2)
    expect(w.emitted('opgeslagen')[0][0]).toEqual({ id: 'c-half' })
  })
})

describe('ComponentFormulier — bewerken (voorgevuld, identiek aan aanmaken)', () => {
  it('bewerken laadt de bestaande waarden (incl. rol + BIV) en PATCHt', async () => {
    api.componenten.haal.mockResolvedValueOnce({
      id: 'c-9', naam: 'Extern koppelpunt', componenttype: 'fileshare', hostingmodel: 'onbekend',
      migratiepad: null, complexiteit: 'midden', prioriteit: 'midden',
      eigenaar_organisatie_id: null, eigenaar_organisatie_naam: '', beschrijving: '',
      componentrol: 'externe_dataprovider', biv_beschikbaarheid: 'laag', biv_integriteit: null, biv_vertrouwelijkheid: 'hoog',
    })
    api.componenten.werkBij.mockResolvedValueOnce({ id: 'c-9' })
    const { w } = await mountForm({ id: 'c-9' })
    expect(w.find('[data-testid="veld-naam"]').element.value).toBe('Extern koppelpunt')
    expect(w.find('[data-testid="veld-componentrol"]').element.value).toBe('externe_dataprovider')
    expect(w.find('[data-testid="veld-biv_beschikbaarheid"]').element.value).toBe('laag')
    expect(w.find('[data-testid="veld-biv_integriteit"]').element.value).toBe('')
    await w.find('[data-testid="veld-naam"]').setValue('Koppelpunt v2')
    await w.find('[data-testid="component-form"]').trigger('submit')
    await flushPromises()
    expect(api.componenten.werkBij).toHaveBeenCalledWith('c-9', expect.objectContaining({ naam: 'Koppelpunt v2' }))
    expect(w.emitted('opgeslagen')).toBeTruthy()
  })

  it('bewerken toont de direct-opslaande bedrijfsfunctie-sectie (zelfde semantiek als het Overzicht)', async () => {
    api.componenten.haal.mockResolvedValueOnce({
      id: 'c-9', naam: 'X', componenttype: 'database', hostingmodel: 'onbekend',
      migratiepad: null, complexiteit: 'midden', prioriteit: 'midden',
      eigenaar_organisatie_id: null, eigenaar_organisatie_naam: '', beschrijving: '',
      componentrol: 'interne_applicatie', biv_beschikbaarheid: null, biv_integriteit: null, biv_vertrouwelijkheid: null,
    })
    const { w } = await mountForm({ id: 'c-9' })
    expect(w.find('[data-testid="component-bedrijfsfunctie-sectie"]').exists()).toBe(true)
    expect(w.find('[data-testid="regels-verzamelaar"]').exists()).toBe(false)
  })
})

describe('ComponentFormulier — annuleren-bevestiging', () => {
  it('ongewijzigd annuleren sluit direct (geen bevestiging)', async () => {
    const { w } = await mountForm()
    await w.find('[data-testid="annuleer-knop"]').trigger('click')
    await flushPromises()
    expect(w.find('[data-testid="form-annuleer-dialog"]').exists()).toBe(false)
    expect(w.emitted('update:visible').at(-1)).toEqual([false])
  })

  it('gewijzigd annuleren vraagt bevestiging; verwerpen sluit, annuleren-daarvan houdt open', async () => {
    const { w } = await mountForm()
    await w.find('[data-testid="veld-naam"]').setValue('Half ingevuld')
    await w.find('[data-testid="annuleer-knop"]').trigger('click')
    await flushPromises()
    expect(w.find('[data-testid="form-annuleer-dialog"]').exists()).toBe(true)
    expect(w.emitted('update:visible')).toBeFalsy() // nog niet gesloten
    await w.find('[data-testid="form-annuleer-annuleer"]').trigger('click')
    await flushPromises()
    expect(w.emitted('update:visible')).toBeFalsy() // open gebleven
    await w.find('[data-testid="annuleer-knop"]').trigger('click')
    await flushPromises()
    await w.find('[data-testid="form-annuleer-bevestig"]').trigger('click')
    await flushPromises()
    expect(w.emitted('update:visible').at(-1)).toEqual([false])
  })
})
