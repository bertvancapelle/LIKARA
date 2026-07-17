/** Tests — ComponentLijst (technische laag; ADR-021 Fase D, CD054b). */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'

vi.mock('@/api', () => ({
  // UX-B6-b — partijen.lijst voedt de eigenaar-organisatie-ZoekSelect (filter).
  api: { componenten: { lijst: vi.fn(), opties: vi.fn() }, partijen: { lijst: vi.fn() } },
}))

import { api } from '@/api'
import { Column, DataTable } from '@/primevue'
import ComponentLijst from '@modules/bwb_ontvlechting/frontend/views/ComponentLijst.vue'
import { VELD_LABELS } from '@modules/bwb_ontvlechting/frontend/labels'
import { useAuthStore } from '@/store/auth'

function maakRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/componenten', name: 'component-lijst', component: ComponentLijst },
      { path: '/componenten/nieuw', name: 'component-nieuw', component: { template: '<div/>' } },
      { path: '/componenten/:id', name: 'component-detail', component: { template: '<div/>' } },
      { path: '/applicaties/:id', name: 'applicatie-detail', component: { template: '<div/>' } },
      { path: '/partijen/:id', name: 'partij-detail', component: { template: '<div/>' } },
    ],
  })
}

async function mountLijst({ rollen = ['medewerker'], pad = '/componenten' } = {}) {
  const router = maakRouter()
  await router.push(pad)
  await router.isReady()
  const pinia = createPinia()
  const auth = useAuthStore(pinia)
  auth.user = { sub: 's', tenant_id: 't', email: 'a@b.nl', roles: rollen }
  const wrapper = mount(ComponentLijst, {
    global: { plugins: [pinia, [PrimeVue, { unstyled: true }], router] },
  })
  await flushPromises()
  return wrapper
}

const _comp = (naam, id, { type = 'database', label = 'Database', subtype = false } = {}) => ({
  id,
  naam,
  componenttype: type,
  componenttype_label: label,
  // ADR-023 Fase C: ArchiMate-typing-projectie (laag/element) uit de catalogus.
  archimate_element: subtype ? 'application_component' : 'system_software',
  laag: subtype ? 'application' : 'technology',
  hostingmodel: 'on_premise',
  heeft_applicatie_subtype: subtype,
  // Besturingsvelden (CD054b W1) — gevuld voor subtypen, null voor kale infra.
  eigenaar_organisatie_id: subtype ? 'org-1' : null,
  eigenaar_organisatie_naam: subtype ? 'Gemeente Veldendam' : null,
  complexiteit: subtype ? 'midden' : null,
  prioriteit: subtype ? 'hoog' : null,
  lifecycle_status: subtype ? 'concept' : null,
})

beforeEach(() => {
  vi.clearAllMocks()
  sessionStorage.clear() // lijststaat (useLijstStaat) mag niet tussen tests lekken
  api.partijen.lijst.mockResolvedValue({ items: [{ id: 'org-1', naam: 'Gemeente Veldendam', aard: 'organisatie' }], volgende_cursor: null })
  api.componenten.opties.mockResolvedValue({
    componenttype: [
      { optie_sleutel: 'database', label: 'Database', laag: 'technology', archimate_element: 'system_software' },
      { optie_sleutel: 'applicatie', label: 'Applicatie', laag: 'application', archimate_element: 'application_component' },
    ],
    structuurrelatie_type: [],
    // ADR-028 — rol-opties + ordinale BIV-niveaus.
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
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('ComponentLijst', () => {
  it('rendert de geladen componenten met type-label', async () => {
    api.componenten.lijst.mockResolvedValueOnce({
      items: [
        _comp('Oracle FIN-DB', 'db-1'),
        _comp('Belastingsysteem', 'app-1', { type: 'applicatie', label: 'Applicatie', subtype: true }),
      ],
      volgende_cursor: null,
    })
    const w = await mountLijst()
    const tekst = w.find('[data-testid="componenten-tabel"]').text()
    expect(tekst).toContain('Oracle FIN-DB')
    expect(tekst).toContain('Database')
    expect(tekst).toContain('Belastingsysteem')
  })

  it('elke rij (subtype én niet-subtype) linkt naar ComponentDetail (LI059)', async () => {
    api.componenten.lijst.mockResolvedValueOnce({
      items: [
        _comp('Oracle FIN-DB', 'db-1'),
        _comp('Belastingsysteem', 'app-1', { type: 'applicatie', label: 'Applicatie', subtype: true }),
      ],
      volgende_cursor: null,
    })
    const w = await mountLijst()
    const links = w.findAll('[data-testid="rij-link"]')
    const hrefs = links.map((l) => l.attributes('href'))
    expect(hrefs.some((h) => h.includes('/componenten/db-1'))).toBe(true)
    expect(hrefs.some((h) => h.includes('/componenten/app-1'))).toBe(true)
  })

  it('type-filter stuurt componenttype mee en reset de cursor', async () => {
    api.componenten.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
    const w = await mountLijst()
    await w.find('[data-testid="filter-type"]').setValue('database')
    await flushPromises()
    expect(api.componenten.lijst).toHaveBeenLastCalledWith(
      expect.objectContaining({ componenttype: 'database', after: undefined }),
    )
  })

  it('laag-filter (ADR-023 Fase C) stuurt laag mee en reset de cursor', async () => {
    api.componenten.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
    const w = await mountLijst()
    // Het laag-filter wordt uit de catalogus-typing afgeleid (application/technology).
    await w.find('[data-testid="filter-laag"]').setValue('technology')
    await flushPromises()
    expect(api.componenten.lijst).toHaveBeenLastCalledWith(
      expect.objectContaining({ laag: 'technology', after: undefined }),
    )
  })

  it('toont per rij een ArchiMate-laag-label', async () => {
    api.componenten.lijst.mockResolvedValueOnce({
      items: [_comp('Oracle FIN-DB', 'db-1')],
      volgende_cursor: null,
    })
    const w = await mountLijst()
    expect(w.find('[data-testid="rij-laag"]').text()).toBe('Technologie')
    // Het element-label staat als verfijning onder de laag.
    expect(w.find('[data-testid="componenten-tabel"]').text()).toContain('Systeemsoftware')
  })

  it('zoekfilter (gedebounced) stuurt zoek mee', async () => {
    vi.useFakeTimers()
    api.componenten.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
    const w = await mountLijst()
    await w.find('[data-testid="filter-zoek"]').setValue('oracle')
    vi.advanceTimersByTime(350)
    vi.useRealTimers()
    await flushPromises()
    expect(api.componenten.lijst).toHaveBeenLastCalledWith(
      expect.objectContaining({ zoek: 'oracle' }),
    )
  })

  it('"Meer laden" gebruikt de cursor en voegt resultaten toe', async () => {
    api.componenten.lijst
      .mockResolvedValueOnce({ items: [_comp('A', 'a-1')], volgende_cursor: 'cur-1' })
      .mockResolvedValueOnce({ items: [_comp('B', 'b-1')], volgende_cursor: null })
    const w = await mountLijst()
    expect(w.find('[data-testid="meer-laden"]').exists()).toBe(true)
    await w.find('[data-testid="meer-laden"]').trigger('click')
    await flushPromises()
    expect(api.componenten.lijst).toHaveBeenLastCalledWith(
      expect.objectContaining({ after: 'cur-1' }),
    )
    expect(w.find('[data-testid="componenten-tabel"]').text()).toContain('B')
  })

  it('zonder schrijfrol geen "Nieuw component"-knop', async () => {
    api.componenten.lijst.mockResolvedValueOnce({ items: [], volgende_cursor: null })
    const w = await mountLijst({ rollen: ['viewer'] })
    expect(w.find('[data-testid="nieuw-component"]').exists()).toBe(false)
  })

  it('toont besturingskolommen gevuld voor subtypen en "—" voor kale infra', async () => {
    api.componenten.lijst.mockResolvedValueOnce({
      items: [
        _comp('Belastingsysteem', 'app-1', { type: 'applicatie', label: 'Applicatie', subtype: true }),
        _comp('Oracle FIN-DB', 'db-1'),
      ],
      volgende_cursor: null,
    })
    const w = await mountLijst()
    const tekst = w.find('[data-testid="componenten-tabel"]').text()
    // Subtype: eigenaar + niveaus + status-Tag gevuld.
    expect(tekst).toContain('Gemeente Veldendam')
    expect(tekst).toContain('Concept')
    // Kale infra: minstens één "—" voor de lege besturingsvelden.
    expect(w.findAll('[data-testid="status-leeg"]').length).toBeGreaterThan(0)
  })

  it('status-filter (multi-select dropdown) stuurt de status-array mee en reset de cursor', async () => {
    api.componenten.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
    const w = await mountLijst()
    // Multi-select dropdown: open de trigger, vink een status aan.
    await w.find('[data-testid="filter-status-trigger"]').trigger('click')
    await w.find('[data-testid="filter-status-checkbox-geblokkeerd"]').trigger('change')
    await flushPromises()
    expect(api.componenten.lijst).toHaveBeenLastCalledWith(
      expect.objectContaining({ status: ['geblokkeerd'], after: undefined }),
    )
  })

  it('hostingmodel- en eigenaar-filter worden meegestuurd', async () => {
    api.componenten.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
    const w = await mountLijst()
    await w.find('[data-testid="filter-hosting"]').setValue('saas')
    await flushPromises()
    expect(api.componenten.lijst).toHaveBeenLastCalledWith(expect.objectContaining({ hostingmodel: 'saas' }))
    // UX-B6-b — eigenaar-filter is een organisatie-keuze (ZoekSelect op eigenaar_organisatie_id).
    await w.find('[data-testid="filter-eigenaar-input"]').trigger('focus')
    await flushPromises()
    await w.find('[data-testid="filter-eigenaar-optie-org-1"]').trigger('mousedown')
    await flushPromises()
    expect(api.componenten.lijst).toHaveBeenLastCalledWith(expect.objectContaining({ eigenaar_organisatie_id: 'org-1' }))
  })

  it('ADR-046: het levensfase-filter belandt END-TO-END in de api-call en wist mee (V012-les)', async () => {
    api.componenten.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
    const w = await mountLijst()
    await w.find('[data-testid="filter-levensfase"]').setValue('uitfaseren')
    await flushPromises()
    // De client zet de filter écht in de call (snake_case, exact de backend-param).
    expect(api.componenten.lijst).toHaveBeenLastCalledWith(
      expect.objectContaining({ levensfase: 'uitfaseren', after: undefined }),
    )
    // Filters wissen → de param verdwijnt uit de volgende call (wisbaar).
    await w.find('[data-testid="filters-wissen"]').trigger('click')
    await flushPromises()
    expect(api.componenten.lijst).toHaveBeenLastCalledWith(
      expect.not.objectContaining({ levensfase: expect.anything() }),
    )
  })

  it('ADR-046: de levensfase-kolom toont het label en het gat gedempt ("nog niet vastgelegd")', async () => {
    api.componenten.lijst.mockResolvedValue({
      items: [
        { ..._comp('Zaaksysteem', 'c1', { subtype: true }), levensfase: 'uitfaseren' },
        { ..._comp('Archiefbeheer', 'c2'), levensfase: null },
      ],
      volgende_cursor: null,
    })
    const w = await mountLijst()
    // Zichtbare TEKST (niet alleen "rendert") — de LI040-les: assert op inhoud.
    expect(w.find('[data-testid="rij-levensfase"]').text()).toBe('Uitfaseren')
    const leeg = w.find('[data-testid="levensfase-leeg"]')
    expect(leeg.exists()).toBe(true)
    expect(leeg.text()).toBe('nog niet vastgelegd')
  })

  it('ADR-028: rol-multiselect + BIV-drempel belanden in de api-call en resetten de cursor', async () => {
    api.componenten.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
    const w = await mountLijst()
    // Rol-multiselect (zelfde component als status): open + vink externe_dataprovider.
    await w.find('[data-testid="filter-rol-trigger"]').trigger('click')
    await w.find('[data-testid="filter-rol-checkbox-externe_dataprovider"]').trigger('change')
    await flushPromises()
    expect(api.componenten.lijst).toHaveBeenLastCalledWith(
      expect.objectContaining({ componentrol: ['externe_dataprovider'], after: undefined }),
    )
    // LI040 — één BIV-filter (hoogste as ≥ drempel) i.p.v. drie per-as-dropdowns.
    await w.find('[data-testid="filter-biv"]').setValue('hoog')
    await flushPromises()
    expect(api.componenten.lijst).toHaveBeenLastCalledWith(
      expect.objectContaining({ componentrol: ['externe_dataprovider'], biv_min: 'hoog' }),
    )
  })

  it('LI040: BIV "nog niet vastgelegd" stuurt biv_ontbreekt (het gat vindbaar)', async () => {
    api.componenten.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
    const w = await mountLijst()
    await w.find('[data-testid="filter-biv"]').setValue('__zonder__')
    await flushPromises()
    const call = api.componenten.lijst.mock.calls.at(-1)[0]
    expect(call.biv_ontbreekt).toBe(1)
    expect(call.biv_min).toBeUndefined()
  })

  it('LI040: het bedoeling-filter belandt END-TO-END in de api-call (param migratiepad)', async () => {
    api.componenten.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
    const w = await mountLijst()
    await w.find('[data-testid="filter-bedoeling"]').setValue('vervangen')
    await flushPromises()
    expect(api.componenten.lijst).toHaveBeenLastCalledWith(
      expect.objectContaining({ migratiepad: 'vervangen', after: undefined }),
    )
  })

  it('LI040: de resultaatregel toont "X van Y componenten" + chips; één chip wissen wist ALLEEN die filter', async () => {
    api.componenten.lijst.mockResolvedValue({ items: [], volgende_cursor: null, totaal: 0, totaal_ongefilterd: 19 })
    const w = await mountLijst()
    await w.find('[data-testid="filter-levensfase"]').setValue('in_ontwikkeling')
    await w.find('[data-testid="filter-ondersteunt-werk"]').setValue('nee')
    await flushPromises()
    // Het aantal + de twee actieve filters staan uitgeschreven naast de lege-melding.
    expect(w.find('[data-testid="resultaat-aantal"]').text()).toBe('0 van 19 componenten')
    expect(w.find('[data-testid="filter-chip-levensfase"]').text()).toContain('Levensfase: In ontwikkeling')
    expect(w.find('[data-testid="filter-chip-werk"]').text()).toContain('Ondersteunt werk: Nee')
    expect(w.find('[data-testid="lijst-geen-match"]').exists()).toBe(true) // leeg naast zijn reden
    // Eén chip wissen → alleen dat filter verdwijnt uit de volgende call; de ander blijft.
    await w.find('[data-testid="chip-wis-levensfase"]').trigger('click')
    await flushPromises()
    const call = api.componenten.lijst.mock.calls.at(-1)[0]
    expect(call.levensfase).toBeUndefined()
    expect(call.ondersteunt_werk).toBe(false)
    expect(w.find('[data-testid="filter-chip-levensfase"]').exists()).toBe(false)
    expect(w.find('[data-testid="filter-chip-werk"]').exists()).toBe(true)
  })

  it('LI040: zonder filters toont de regel het kale totaal ("19 componenten")', async () => {
    api.componenten.lijst.mockResolvedValue({
      items: [_comp('Oracle FIN-DB', 'db-1')], volgende_cursor: null, totaal: 19, totaal_ongefilterd: 19,
    })
    const w = await mountLijst()
    expect(w.find('[data-testid="resultaat-aantal"]').text()).toBe('19 componenten')
  })

  it('LI040: "nog niet vastgelegd" filtert op AFWEZIGHEID (levensfase_ontbreekt/migratiepad_ontbreekt) + chips', async () => {
    api.componenten.lijst.mockResolvedValue({ items: [], volgende_cursor: null, totaal: 13, totaal_ongefilterd: 19 })
    const w = await mountLijst()
    await w.find('[data-testid="filter-levensfase"]').setValue('__zonder__')
    await flushPromises()
    let call = api.componenten.lijst.mock.calls.at(-1)[0]
    expect(call.levensfase_ontbreekt).toBe(1)
    expect(call.levensfase).toBeUndefined() // afwezigheid, geen sentinel-waarde
    expect(w.find('[data-testid="filter-chip-levensfase"]').text()).toContain('Levensfase: nog niet vastgelegd')
    await w.find('[data-testid="filter-bedoeling"]').setValue('__zonder__')
    await flushPromises()
    call = api.componenten.lijst.mock.calls.at(-1)[0]
    expect(call.migratiepad_ontbreekt).toBe(1)
    expect(call.migratiepad).toBeUndefined()
    expect(w.find('[data-testid="filter-chip-bedoeling"]').text()).toContain('Bedoeling: nog niet vastgelegd')
    // Chip wissen haalt alléén dat ontbreekt-filter weg.
    await w.find('[data-testid="chip-wis-levensfase"]').trigger('click')
    await flushPromises()
    call = api.componenten.lijst.mock.calls.at(-1)[0]
    expect(call.levensfase_ontbreekt).toBeUndefined()
    expect(call.migratiepad_ontbreekt).toBe(1)
  })

  it('LI040: de bedoeling-kolom toont het gat gedempt ("nog niet vastgelegd", nooit "Onbekend")', async () => {
    api.componenten.lijst.mockResolvedValue({
      items: [
        { ..._comp('Zaaksysteem', 'c1', { subtype: true }), migratiepad: 'vervangen' },
        { ..._comp('Archiefbeheer', 'c2'), migratiepad: null },
      ],
      volgende_cursor: null,
    })
    const w = await mountLijst()
    expect(w.find('[data-testid="rij-bedoeling"]').text()).toBe('Vervangen')
    const leeg = w.find('[data-testid="bedoeling-leeg"]')
    expect(leeg.exists()).toBe(true)
    expect(leeg.text()).toBe('nog niet vastgelegd')
    expect(w.find('[data-testid="componenten-tabel"]').text()).not.toContain('Onbekend')
  })

  it('LI040: oordeel-filters end-to-end — waarde én "nog niet vastgelegd" (complexiteit/prioriteit)', async () => {
    api.componenten.lijst.mockResolvedValue({ items: [], volgende_cursor: null, totaal: 0, totaal_ongefilterd: 19 })
    const w = await mountLijst()
    await w.find('[data-testid="filter-complexiteit"]').setValue('hoog')
    await flushPromises()
    expect(api.componenten.lijst).toHaveBeenLastCalledWith(
      expect.objectContaining({ complexiteit: 'hoog', after: undefined }),
    )
    await w.find('[data-testid="filter-prioriteit"]').setValue('__zonder__')
    await flushPromises()
    const call = api.componenten.lijst.mock.calls.at(-1)[0]
    expect(call.prioriteit_ontbreekt).toBe(1)
    expect(call.prioriteit).toBeUndefined() // afwezigheid, geen sentinel-waarde
    expect(w.find('[data-testid="filter-chip-complexiteit"]').text()).toContain('Complexiteit: Hoog')
    expect(w.find('[data-testid="filter-chip-prioriteit"]').text()).toContain('Prioriteit: nog niet vastgelegd')
    // Eén chip wissen wist alléén dat oordeel-filter.
    await w.find('[data-testid="chip-wis-complexiteit"]').trigger('click')
    await flushPromises()
    const na = api.componenten.lijst.mock.calls.at(-1)[0]
    expect(na.complexiteit).toBeUndefined()
    expect(na.prioriteit_ontbreekt).toBe(1)
  })

  it('LI040: oordeel-kolommen tonen het gat gedempt — nergens een verzonnen "Midden"', async () => {
    api.componenten.lijst.mockResolvedValue({
      items: [
        { ..._comp('Zaaksysteem', 'c1', { subtype: true }), complexiteit: 'hoog', prioriteit: null },
        { ..._comp('Archiefbeheer', 'c2'), complexiteit: null, prioriteit: null },
      ],
      volgende_cursor: null,
    })
    const w = await mountLijst()
    expect(w.find('[data-testid="rij-complexiteit"]').text()).toBe('Hoog')
    const leeg = w.find('[data-testid="prioriteit-leeg"]')
    expect(leeg.exists()).toBe(true)
    expect(leeg.text()).toBe('nog niet vastgelegd')
    // Geen verzonnen oordeel meer in beeld bij componenten zonder oordeel.
    expect(w.find('[data-testid="componenten-tabel"]').text()).not.toContain('Midden')
  })

  it('ADR-028/LI040: wisFilters wist ook rol + BIV + bedoeling', async () => {
    api.componenten.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
    const w = await mountLijst()
    await w.find('[data-testid="filter-biv"]').setValue('midden')
    await w.find('[data-testid="filter-bedoeling"]').setValue('herbouw')
    await flushPromises()
    expect(api.componenten.lijst).toHaveBeenLastCalledWith(
      expect.objectContaining({ biv_min: 'midden', migratiepad: 'herbouw' }),
    )
    await w.find('[data-testid="filters-wissen"]').trigger('click')
    await flushPromises()
    const laatste = api.componenten.lijst.mock.calls.at(-1)[0]
    expect(laatste.biv_min).toBeUndefined()
    expect(laatste.migratiepad).toBeUndefined()
    expect(laatste.componentrol).toBeUndefined()
  })

  it('ADR-045: ondersteunt-werk-filter belandt als boolean in de api-call en reset de cursor', async () => {
    api.componenten.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
    const w = await mountLijst()
    await w.find('[data-testid="filter-ondersteunt-werk"]').setValue('nee')
    await flushPromises()
    expect(api.componenten.lijst).toHaveBeenLastCalledWith(
      expect.objectContaining({ ondersteunt_werk: false, after: undefined }),
    )
    await w.find('[data-testid="filter-ondersteunt-werk"]').setValue('ja')
    await flushPromises()
    expect(api.componenten.lijst).toHaveBeenLastCalledWith(
      expect.objectContaining({ ondersteunt_werk: true }),
    )
    // Terug naar "Alle": de param verdwijnt volledig uit de call (default-pad).
    await w.find('[data-testid="filter-ondersteunt-werk"]').setValue('')
    await flushPromises()
    expect(api.componenten.lijst.mock.calls.at(-1)[0].ondersteunt_werk).toBeUndefined()
  })

  it('ADR-045: wisFilters wist ook het ondersteunt-werk-filter', async () => {
    api.componenten.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
    const w = await mountLijst()
    await w.find('[data-testid="filter-ondersteunt-werk"]').setValue('nee')
    await flushPromises()
    expect(api.componenten.lijst).toHaveBeenLastCalledWith(expect.objectContaining({ ondersteunt_werk: false }))
    await w.find('[data-testid="filters-wissen"]').trigger('click')
    await flushPromises()
    expect(api.componenten.lijst.mock.calls.at(-1)[0].ondersteunt_werk).toBeUndefined()
  })

  it('een ?type=applicatie-query preselecteert het typefilter (Applicaties-redirect)', async () => {
    api.componenten.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
    await mountLijst({ pad: '/componenten?type=applicatie' })
    expect(api.componenten.lijst).toHaveBeenLastCalledWith(
      expect.objectContaining({ componenttype: 'applicatie' }),
    )
  })

  it('een ?status=geblokkeerd-query preselecteert het statusfilter (dashboard-doorklik)', async () => {
    api.componenten.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
    const w = await mountLijst({ pad: '/componenten?status=geblokkeerd' })
    expect(api.componenten.lijst).toHaveBeenLastCalledWith(
      expect.objectContaining({ status: ['geblokkeerd'] }),
    )
    // De dropdown-trigger toont de voorgezette selectie (1 gekozen → het statuslabel).
    expect(w.find('[data-testid="filter-status-trigger"]').text()).toContain('Geblokkeerd')
  })

  it('ADR-027: ?klaarverklaring=klaar belandt als api-filter + toont de wisbare chip', async () => {
    api.componenten.lijst.mockResolvedValue({ items: [], volgende_cursor: null, totaal: 0, totaal_ongefilterd: 19 })
    const w = await mountLijst({ pad: '/componenten?klaarverklaring=klaar' })
    expect(api.componenten.lijst).toHaveBeenLastCalledWith(
      expect.objectContaining({ klaarverklaring: 'klaar' }),
    )
    // LI040 — de doorklik-filter staat uitgeschreven in de resultaatregel-chips.
    expect(w.find('[data-testid="filter-chip-klaarverklaring"]').exists()).toBe(true)
  })

  it('ADR-027: ?afwijking=1 belandt als afwijking-filter (impliceert geen losse klaarverklaring-param)', async () => {
    api.componenten.lijst.mockResolvedValue({ items: [], volgende_cursor: null, totaal: 0, totaal_ongefilterd: 19 })
    const w = await mountLijst({ pad: '/componenten?afwijking=1' })
    const call = api.componenten.lijst.mock.calls.at(-1)[0]
    expect(call.afwijking).toBe(1)
    expect(call.klaarverklaring).toBeUndefined() // afwijking impliceert server-side de klaar-join
    expect(w.find('[data-testid="filter-chip-afwijking"]').text()).toContain('nog niet compleet')
  })

  it('ADR-027/LI040: chip wissen verwijdert de filter uit de volgende api-call', async () => {
    api.componenten.lijst.mockResolvedValue({ items: [], volgende_cursor: null, totaal: 0, totaal_ongefilterd: 19 })
    const w = await mountLijst({ pad: '/componenten?afwijking=1' })
    await w.find('[data-testid="chip-wis-afwijking"]').trigger('click')
    const call = api.componenten.lijst.mock.calls.at(-1)[0]
    expect(call.afwijking).toBeUndefined()
    expect(call.klaarverklaring).toBeUndefined()
    expect(w.find('[data-testid="filter-chip-afwijking"]').exists()).toBe(false)
  })

  it('?status= + ?type= samen zetten beide filters voor (exacte dashboard-tegel-match)', async () => {
    api.componenten.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
    await mountLijst({ pad: '/componenten?status=migratieklaar&type=applicatie' })
    expect(api.componenten.lijst).toHaveBeenLastCalledWith(
      expect.objectContaining({ status: ['migratieklaar'], componenttype: 'applicatie' }),
    )
  })

  it('een ongeldige ?status=-waarde wordt genegeerd (default-gedrag)', async () => {
    api.componenten.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
    await mountLijst({ pad: '/componenten?status=onzin' })
    const call = api.componenten.lijst.mock.calls.at(-1)[0]
    expect(call.status).toBeUndefined()
  })

  // ── Server-side kolomsortering (ADR-017) ───────────────────────────────────
  it('default-laad stuurt GEEN sort/order mee (server-default created_at asc)', async () => {
    api.componenten.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
    await mountLijst()
    const call = api.componenten.lijst.mock.calls.at(-1)[0]
    expect(call.sort).toBeUndefined()
    expect(call.order).toBeUndefined()
  })

  it('een sorteerklik stuurt sort/order mee, reset de cursor en herlaadt', async () => {
    api.componenten.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
    const w = await mountLijst()
    w.findComponent(DataTable).vm.$emit('sort', { sortField: 'hostingmodel', sortOrder: -1 })
    await flushPromises()
    expect(api.componenten.lijst).toHaveBeenLastCalledWith(
      expect.objectContaining({ sort: 'hostingmodel', order: 'desc', after: undefined }),
    )
  })

  it('de 9 kolommen zijn sorteerbaar en Laag bewust niet', async () => {
    api.componenten.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
    const w = await mountLijst()
    const sortFields = w.findAllComponents(Column).map((c) => ({
      header: c.props('header'),
      sortable: c.props('sortable'),
    }))
    const sorteerbaar = sortFields.filter((c) => c.sortable).map((c) => c.header)
    expect(sorteerbaar).toEqual(
      // ADR-046 — Levensfase is een echte, server-side sorteerbare kolom (v2n NULLS-LAST).
      // LI040 — Bedoeling is een echte, server-side sorteerbare kolom (naast Levensfase).
      // LI043 — het beoordelings-veldlabel is "Beoordelingsstatus" (uit VELD_LABELS, was "Status").
      expect.arrayContaining(['Naam', 'Type', 'Eigenaar', 'Hosting', 'Complexiteit', 'Prioriteit', 'Levensfase', 'Bedoeling', 'Beoordelingsstatus']),
    )
    expect(sorteerbaar).toHaveLength(9)
    expect(sorteerbaar).not.toContain('Laag')
  })

  it('LI043 single source — de drie lijst-plekken lezen het beoordelings-veldlabel UIT de bron', async () => {
    // De bron (VELD_LABELS) tijdelijk op een sentinel; elke plek die 'm via `veldLabel` leest volgt mee.
    // Zou een plek het label opnieuw hardcoden ("Status"), dan breekt deze test.
    const origineel = VELD_LABELS.lifecycle_status
    try {
      VELD_LABELS.lifecycle_status = 'BRON_SENTINEL'
      api.componenten.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
      const w = await mountLijst()
      // 1) kolomkop (Column-header-prop)
      expect(w.findAllComponents(Column).map((c) => c.props('header'))).toContain('BRON_SENTINEL')
      // 2) filter-kop (altijd gerenderd in de filterbalk)
      expect(w.text()).toContain('BRON_SENTINEL')
      // 3) filterchip (verschijnt zodra het statusfilter actief is)
      w.vm.filterStatus = ['concept']
      await flushPromises()
      expect(w.vm.filterChips.find((c) => c.sleutel === 'status').label).toBe('BRON_SENTINEL')
    } finally {
      VELD_LABELS.lifecycle_status = origineel // gedeelde module-singleton — altijd herstellen
    }
  })

  it('sorteren behoudt een actief filter', async () => {
    api.componenten.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
    const w = await mountLijst({ pad: '/componenten?type=applicatie' })
    w.findComponent(DataTable).vm.$emit('sort', { sortField: 'naam', sortOrder: 1 })
    await flushPromises()
    expect(api.componenten.lijst).toHaveBeenLastCalledWith(
      expect.objectContaining({ sort: 'naam', order: 'asc', componenttype: 'applicatie' }),
    )
  })
})

describe('ComponentLijst — lijststaat behouden bij terugnavigeren (useLijstStaat)', () => {
  it('herstelt de bewaarde lijststaat end-to-end, incl. het eigenaar-label (LI032)', async () => {
    sessionStorage.setItem(
      'lijst-state:component-lijst',
      JSON.stringify({
        filterStatus: ['geblokkeerd'],
        filterType: 'database',
        filterZoek: 'zaak',
        filterEigenaarId: 'org-1',
        filterEigenaarNaam: 'Gemeente Veldendam',
        sortVeld: 'naam',
        sortRichting: 'asc',
      }),
    )
    api.componenten.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
    const w = await mountLijst()
    // V012-les: bewijs de keten — de herstelde stand belandt in de api-call.
    expect(api.componenten.lijst).toHaveBeenCalledWith(
      expect.objectContaining({
        status: ['geblokkeerd'],
        componenttype: 'database',
        zoek: 'zaak',
        eigenaar_organisatie_id: 'org-1',
        sort: 'naam',
        order: 'asc',
      }),
    )
    // LI032: het herstelde eigenaar-id toont zijn naam — geen leeg veld op een actief filter.
    expect(w.find('[data-testid="filter-eigenaar-input"]').element.value).toBe('Gemeente Veldendam')
  })

  it('een doorklik-query WINT van de bewaarde staat (vervangt hem volledig)', async () => {
    sessionStorage.setItem(
      'lijst-state:component-lijst',
      JSON.stringify({ filterType: 'database', filterZoek: 'zaak', sortVeld: 'naam', sortRichting: 'desc' }),
    )
    api.componenten.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
    await mountLijst({ pad: '/componenten?type=applicatie' })
    const params = api.componenten.lijst.mock.calls[0][0]
    expect(params.componenttype).toBe('applicatie') // de doorklik
    expect(params.zoek).toBeUndefined() // de oude zoekterm dunt de doorklik niet stil uit
    expect(params.sort).toBeUndefined() // ook de bewaarde sortering herstelt niet
  })

  it('pruned bewaarde catalogus-sleutels die niet (meer) bestaan (stale BIV → geen 422)', async () => {
    sessionStorage.setItem(
      'lijst-state:component-lijst',
      JSON.stringify({ filterType: 'verwijderd_type', filterBiv: 'verwijderd_niveau', filterZoek: 'zaak' }),
    )
    api.componenten.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
    await mountLijst()
    const params = api.componenten.lijst.mock.calls[0][0]
    expect(params.componenttype).toBeUndefined()
    expect(params.biv_min).toBeUndefined()
    expect(params.zoek).toBe('zaak') // geldige velden blijven hersteld
  })

  it('bewaart een wijziging ná herstel (beforeunload-pad = F5-gedrag)', async () => {
    api.componenten.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
    const w = await mountLijst()
    await w.find('[data-testid="filter-type"]').setValue('database')
    await flushPromises()
    window.dispatchEvent(new Event('beforeunload'))
    const bewaard = JSON.parse(sessionStorage.getItem('lijst-state:component-lijst'))
    expect(bewaard.filterType).toBe('database')
    w.unmount()
  })
})
