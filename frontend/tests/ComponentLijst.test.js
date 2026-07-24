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
    // LI048 — de filters wonen in een Dialog, die naar body teleporteert; zonder deze stub
    // ziet `find()` de velden niet.
    global: { plugins: [pinia, [PrimeVue, { unstyled: true }], router], stubs: { teleport: true } },
  })
  await flushPromises()
  return wrapper
}

/**
 * LI048 — een filter zetten loopt sinds deze slice via het filtervenster: openen, kiezen,
 * toepassen. Dat is precies de weg die de consultant loopt; de toetsen die hier doorheen gaan
 * bewijzen dus de KETEN (venster → concept → toepassen → api-call), niet alleen de api-laag.
 *
 * `zet` krijgt de geopende wrapper en doet de veldbediening; daarna wordt toegepast.
 */
async function viaFilterVenster(w, zet) {
  await w.find('[data-testid="filter-knop"]').trigger('click')
  await flushPromises()
  await zet(w)
  await flushPromises()
  await w.find('[data-testid="filter-toepassen"]').trigger('click')
  await flushPromises()
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
    await viaFilterVenster(w, (w) => w.find('[data-testid="filter-type"]').setValue('database'))
    expect(api.componenten.lijst).toHaveBeenLastCalledWith(
      expect.objectContaining({ componenttype: 'database', after: undefined }),
    )
  })

  it('laag-filter (ADR-023 Fase C) stuurt laag mee en reset de cursor', async () => {
    api.componenten.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
    const w = await mountLijst()
    // Het laag-filter wordt uit de catalogus-typing afgeleid (application/technology).
    await viaFilterVenster(w, (w) => w.find('[data-testid="filter-laag"]').setValue('technology'))
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
    await viaFilterVenster(w, async (w) => {
      await w.find('[data-testid="filter-status-trigger"]').trigger('click')
      await w.find('[data-testid="filter-status-checkbox-geblokkeerd"]').trigger('change')
    })
    expect(api.componenten.lijst).toHaveBeenLastCalledWith(
      expect.objectContaining({ status: ['geblokkeerd'], after: undefined }),
    )
  })

  it('hostingmodel- en eigenaar-filter worden meegestuurd', async () => {
    api.componenten.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
    const w = await mountLijst()
    await viaFilterVenster(w, (w) => w.find('[data-testid="filter-hosting"]').setValue('saas'))
    expect(api.componenten.lijst).toHaveBeenLastCalledWith(expect.objectContaining({ hostingmodel: 'saas' }))
    // UX-B6-b — eigenaar-filter is een organisatie-keuze (ZoekSelect op eigenaar_organisatie_id).
    await viaFilterVenster(w, async (w) => {
      await w.find('[data-testid="filter-eigenaar-input"]').trigger('focus')
      await flushPromises()
      await w.find('[data-testid="filter-eigenaar-optie-org-1"]').trigger('mousedown')
    })
    expect(api.componenten.lijst).toHaveBeenLastCalledWith(expect.objectContaining({ eigenaar_organisatie_id: 'org-1' }))
  })

  it('ADR-046: het levensfase-filter belandt END-TO-END in de api-call en wist mee (V012-les)', async () => {
    api.componenten.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
    const w = await mountLijst()
    await viaFilterVenster(w, (w) => w.find('[data-testid="filter-levensfase"]').setValue('uitfaseren'))
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
    await viaFilterVenster(w, async (w) => {
      await w.find('[data-testid="filter-rol-trigger"]').trigger('click')
      await w.find('[data-testid="filter-rol-checkbox-externe_dataprovider"]').trigger('change')
    })
    expect(api.componenten.lijst).toHaveBeenLastCalledWith(
      expect.objectContaining({ componentrol: ['externe_dataprovider'], after: undefined }),
    )
    // LI040 — één BIV-filter (hoogste as ≥ drempel) i.p.v. drie per-as-dropdowns.
    await viaFilterVenster(w, (w) => w.find('[data-testid="filter-biv"]').setValue('hoog'))
    expect(api.componenten.lijst).toHaveBeenLastCalledWith(
      expect.objectContaining({ componentrol: ['externe_dataprovider'], biv_min: 'hoog' }),
    )
  })

  it('LI040: BIV "nog niet vastgelegd" stuurt biv_ontbreekt (het gat vindbaar)', async () => {
    api.componenten.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
    const w = await mountLijst()
    await viaFilterVenster(w, (w) => w.find('[data-testid="filter-biv"]').setValue('__zonder__'))
    const call = api.componenten.lijst.mock.calls.at(-1)[0]
    expect(call.biv_ontbreekt).toBe(1)
    expect(call.biv_min).toBeUndefined()
  })

  it('LI040: het bedoeling-filter belandt END-TO-END in de api-call (param migratiepad)', async () => {
    api.componenten.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
    const w = await mountLijst()
    await viaFilterVenster(w, (w) => w.find('[data-testid="filter-bedoeling"]').setValue('vervangen'))
    expect(api.componenten.lijst).toHaveBeenLastCalledWith(
      expect.objectContaining({ migratiepad: 'vervangen', after: undefined }),
    )
  })

  it('LI040: de resultaatregel toont "X van Y componenten" + chips; één chip wissen wist ALLEEN die filter', async () => {
    api.componenten.lijst.mockResolvedValue({ items: [], volgende_cursor: null, totaal: 0, totaal_ongefilterd: 19 })
    const w = await mountLijst()
    await viaFilterVenster(w, async (w) => {
      await w.find('[data-testid="filter-levensfase"]').setValue('in_ontwikkeling')
      await w.find('[data-testid="filter-ondersteunt-werk"]').setValue('nee')
    })
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
    await viaFilterVenster(w, (w) => w.find('[data-testid="filter-levensfase"]').setValue('__zonder__'))
    let call = api.componenten.lijst.mock.calls.at(-1)[0]
    expect(call.levensfase_ontbreekt).toBe(1)
    expect(call.levensfase).toBeUndefined() // afwezigheid, geen sentinel-waarde
    expect(w.find('[data-testid="filter-chip-levensfase"]').text()).toContain('Levensfase: nog niet vastgelegd')
    await viaFilterVenster(w, (w) => w.find('[data-testid="filter-bedoeling"]').setValue('__zonder__'))
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
    await viaFilterVenster(w, (w) => w.find('[data-testid="filter-complexiteit"]').setValue('hoog'))
    expect(api.componenten.lijst).toHaveBeenLastCalledWith(
      expect.objectContaining({ complexiteit: 'hoog', after: undefined }),
    )
    await viaFilterVenster(w, (w) => w.find('[data-testid="filter-prioriteit"]').setValue('__zonder__'))
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
    await viaFilterVenster(w, async (w) => {
      await w.find('[data-testid="filter-biv"]').setValue('midden')
      await w.find('[data-testid="filter-bedoeling"]').setValue('herbouw')
    })
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
    await viaFilterVenster(w, (w) => w.find('[data-testid="filter-ondersteunt-werk"]').setValue('nee'))
    expect(api.componenten.lijst).toHaveBeenLastCalledWith(
      expect.objectContaining({ ondersteunt_werk: false, after: undefined }),
    )
    await viaFilterVenster(w, (w) => w.find('[data-testid="filter-ondersteunt-werk"]').setValue('ja'))
    expect(api.componenten.lijst).toHaveBeenLastCalledWith(
      expect.objectContaining({ ondersteunt_werk: true }),
    )
    // Terug naar "Alle": de param verdwijnt volledig uit de call (default-pad).
    await viaFilterVenster(w, (w) => w.find('[data-testid="filter-ondersteunt-werk"]').setValue(''))
    expect(api.componenten.lijst.mock.calls.at(-1)[0].ondersteunt_werk).toBeUndefined()
  })

  it('ADR-045: wisFilters wist ook het ondersteunt-werk-filter', async () => {
    api.componenten.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
    const w = await mountLijst()
    await viaFilterVenster(w, (w) => w.find('[data-testid="filter-ondersteunt-werk"]').setValue('nee'))
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
    // LI048 — de voorgezette selectie is zichtbaar ZONDER het filtervenster te openen: als chip
    // én in de knoptelling. Dat is de kern: wie via een dashboard-doorklik binnenkomt moet kunnen
    // zien waaróm hij een deelverzameling ziet. (Voorheen toetste dit de dropdown-trigger; die
    // zit nu in het venster en zegt dus niets over wat de gebruiker ziet.)
    // (De chiprij zelf rendert alleen mét een server-totaal — dat toetst de LI040-chiptoets
    // hierboven, die wél een `totaal` mockt. Hier gaat het om de knoptelling, die altijd staat.)
    expect(w.find('[data-testid="filter-knop-teller"]').text()).toBe('(1)')
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
    // LI048: het veld woont in het filtervenster, dus dat moet open om het te kunnen zien. De
    // conceptstaat kopieert de herstelde waarde mee — anders zou de gebruiker bij het openen
    // een leeg eigenaarveld zien terwijl het filter wél actief is (en zou Toepassen het wissen).
    await w.find('[data-testid="filter-knop"]').trigger('click')
    await flushPromises()
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
    await viaFilterVenster(w, (w) => w.find('[data-testid="filter-type"]').setValue('database'))
    window.dispatchEvent(new Event('beforeunload'))
    const bewaard = JSON.parse(sessionStorage.getItem('lijst-state:component-lijst'))
    expect(bewaard.filterType).toBe('database')
    w.unmount()
  })
})

// ── LI048 — de filters wonen in een venster; wat er zichtbaar blijft is de kern ──────────────
// Een verstopt filter is een onzichtbaar filter: een consultant die naar een stiekem gefilterde
// lijst kijkt, trekt verkeerde conclusies over zijn landschap. De vraag "waarom zie ik er maar
// zeven?" moet altijd beantwoord zijn zónder iets te openen.
describe('ComponentLijst — filtervenster (LI048)', () => {
  it('bovenin staat alleen het zoekveld en de Filter-knop; de filtervelden zitten in het venster', async () => {
    api.componenten.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
    const w = await mountLijst()
    // Zoeken blijft direct bereikbaar — dat is waar de consultant mee begint.
    expect(w.find('[data-testid="filter-zoek"]').exists()).toBe(true)
    expect(w.find('[data-testid="filter-knop"]').exists()).toBe(true)
    // De filtervelden zijn er niet zolang het venster dicht is.
    expect(w.find('[data-testid="filter-type"]').exists()).toBe(false)
    expect(w.find('[data-testid="filter-biv"]').exists()).toBe(false)
    await w.find('[data-testid="filter-knop"]').trigger('click')
    await flushPromises()
    // ALLE velden staan erin — geen selectie van "de meest gebruikte" achter een "toon meer".
    for (const veld of ['type', 'laag', 'hosting', 'levensfase', 'bedoeling', 'complexiteit',
                        'prioriteit', 'ondersteunt-werk', 'biv', 'eigenaar-input']) {
      expect(w.find(`[data-testid="filter-${veld}"]`).exists(), `filter-${veld} ontbreekt`).toBe(true)
    }
  })

  it('het getal op de knop is exact het aantal actieve filters — en verdwijnt bij nul', async () => {
    api.componenten.lijst.mockResolvedValue({ items: [], volgende_cursor: null, totaal: 3, totaal_ongefilterd: 19 })
    const w = await mountLijst()
    expect(w.find('[data-testid="filter-knop-teller"]').exists(), 'nul draagt een getal').toBe(false)

    await viaFilterVenster(w, (w) => w.find('[data-testid="filter-type"]').setValue('database'))
    expect(w.find('[data-testid="filter-knop-teller"]').text()).toBe('(1)')
    await viaFilterVenster(w, (w) => w.find('[data-testid="filter-hosting"]').setValue('saas'))
    expect(w.find('[data-testid="filter-knop-teller"]').text()).toBe('(2)')

    await w.find('[data-testid="filters-wissen"]').trigger('click')
    await flushPromises()
    expect(w.find('[data-testid="filter-knop-teller"]').exists()).toBe(false)
  })

  it('élk actief filter krijgt een chip — knoptelling en chiprij kunnen niet uiteenlopen', async () => {
    // DIT is het defect dat de opdracht wil voorkomen: een filter dat wél werkt maar geen chip
    // krijgt, filtert onzichtbaar. Beide lezen `filterChips`, dus de toets legt ze tegen elkaar.
    api.componenten.lijst.mockResolvedValue({ items: [], volgende_cursor: null, totaal: 2, totaal_ongefilterd: 19 })
    const w = await mountLijst()
    await viaFilterVenster(w, async (w) => {
      await w.find('[data-testid="filter-type"]').setValue('database')
      await w.find('[data-testid="filter-hosting"]').setValue('saas')
      await w.find('[data-testid="filter-levensfase"]').setValue('uitfaseren')
    })
    const chips = w.findAll('[data-testid^="filter-chip-"]')
    expect(chips.length, 'niet elk actief filter heeft een chip').toBe(3)
    expect(w.find('[data-testid="filter-knop-teller"]').text()).toBe(`(${chips.length})`)
    // En het aantal getoonde componenten staat ernaast — de vraag "waarom maar 2?" is beantwoord.
    expect(w.find('[data-testid="resultaat-aantal"]').text()).toContain('2 van 19')
  })

  it('een chip wegklikken werkt zonder het venster te openen', async () => {
    api.componenten.lijst.mockResolvedValue({ items: [], volgende_cursor: null, totaal: 2, totaal_ongefilterd: 19 })
    const w = await mountLijst()
    await viaFilterVenster(w, async (w) => {
      await w.find('[data-testid="filter-type"]').setValue('database')
      await w.find('[data-testid="filter-hosting"]').setValue('saas')
    })
    await w.find('[data-testid="chip-wis-type"]').trigger('click')
    await flushPromises()
    const call = api.componenten.lijst.mock.calls.at(-1)[0]
    expect(call.componenttype).toBeUndefined()
    expect(call.hostingmodel).toBe('saas') // alléén die ene filter weg
    expect(w.find('[data-testid="filter-knop-teller"]').text()).toBe('(1)')
  })

  it('kiezen past nog niets toe; pas de knop onderin commit — en Annuleren gooit het weg', async () => {
    // De timers lopen hier ECHT door: de live-teller draait tijdens het kiezen, en juist dán moet
    // blijken dat het concept niet naar de echte filters lekt. Zonder die stap oefent de toets
    // het geval niet en zou een lek onopgemerkt blijven.
    vi.useFakeTimers()
    api.componenten.lijst.mockResolvedValue({ items: [], volgende_cursor: null, totaal: 5, totaal_ongefilterd: 19 })
    const w = await mountLijst()

    await w.find('[data-testid="filter-knop"]').trigger('click')
    await flushPromises()
    await w.find('[data-testid="filter-type"]').setValue('database')
    vi.advanceTimersByTime(300) // de teller draait
    vi.useRealTimers()
    await flushPromises()
    // De teller heeft geteld, maar de LIJST is niet omgegooid: hij kan van gedachten veranderen.
    // (De laatste call is de telling — `limit: 1`; die telt niet als "toegepast".)
    expect(w.find('[data-testid="filter-knop-teller"]').exists(),
           'het concept lekte naar de toegepaste filters vóór Toepassen').toBe(false)
    const naTellen = api.componenten.lijst.mock.calls.length

    await w.find('[data-testid="filter-annuleer"]').trigger('click')
    await flushPromises()
    expect(w.find('[data-testid="filter-knop-teller"]').exists(), 'annuleren liet het filter staan').toBe(false)
    expect(api.componenten.lijst.mock.calls.length).toBe(naTellen) // geen herlaad na annuleren
  })

  it('de teller in het venster leest dezelfde bron als de teller naast de chips', async () => {
    // Eén filterwaarheid: beide komen uit het lijst-endpoint (`svc.tel` deelt `_pas_filters_toe`
    // met `lijst`). Zou het venster zelf tellen, dan zegt het "7" terwijl de lijst er acht toont.
    vi.useFakeTimers()
    api.componenten.lijst.mockResolvedValue({ items: [], volgende_cursor: null, totaal: 7, totaal_ongefilterd: 19 })
    const w = await mountLijst()
    await w.find('[data-testid="filter-knop"]').trigger('click')
    await flushPromises()
    await w.find('[data-testid="filter-type"]').setValue('database')
    vi.advanceTimersByTime(300)
    vi.useRealTimers()
    await flushPromises()
    // De tel-aanroep is hetzelfde endpoint met de CONCEPT-filters (limit 1 — alleen het getal).
    const telCall = api.componenten.lijst.mock.calls.at(-1)[0]
    expect(telCall.limit).toBe(1)
    expect(telCall.componenttype).toBe('database')
    // En het venster toont dat getal, ook op de knop.
    expect(w.find('[data-testid="filter-venster-telling"]').text()).toContain('7 van 19')
    expect(w.find('[data-testid="filter-toepassen"]').text()).toContain('Toon 7 componenten')
  })

  it('een combinatie die op nul uitkomt waarschuwt vóór het sluiten', async () => {
    vi.useFakeTimers()
    api.componenten.lijst.mockResolvedValue({ items: [], volgende_cursor: null, totaal: 0, totaal_ongefilterd: 19 })
    const w = await mountLijst()
    await w.find('[data-testid="filter-knop"]').trigger('click')
    await flushPromises()
    await w.find('[data-testid="filter-type"]').setValue('database')
    vi.advanceTimersByTime(300)
    vi.useRealTimers()
    await flushPromises()
    expect(w.find('[data-testid="filter-venster-telling"]').text()).toContain('Geen componenten')
  })
})

describe('ComponentLijst — LI048: de gedeelde lijstkop', () => {
  it('draagt de gedeelde LijstKop met naam en aanmaakactie op vaste plek', async () => {
    const w = await mountLijst({ rollen: ['beheerder'] })
    const kop = w.find('[data-testid="lijst-kop"]')
    expect(kop.exists()).toBe(true)
    // De actie is het laatste kind — op élk lijstscherm, zodat de consultant hem niet
    // per scherm opnieuw hoeft te zoeken.
    const kinderen = [...kop.element.children].map((el) => el.getAttribute('data-testid'))
    expect(kinderen[kinderen.length - 1]).toBe('lijst-kop-actie')
  })

  it('heeft precies één zoekveld', async () => {
    // Twee zoekvelden met elk hun eigen binding tonen een lijst die bij geen van beide hoort.
    // Dat stond hier: één in de kop, één in de filterbalk eronder.
    const w = await mountLijst()
    expect(w.findAll('input[type="search"]').length).toBe(1)
  })

  // LI051 — lijst-soort: melding tussen zoekveld en aantal wanneer de zoekterm onzichtbare tekens
  // bevatte; de opgeschoonde term staat in het veld én in de melding, en gaat opgeschoond naar de API.
  it('LI051 — geplakte rommel in het zoekveld: melding met de opgeschoonde term, veld toont schoon', async () => {
    vi.useFakeTimers()
    api.componenten.lijst.mockResolvedValue({ items: [], volgende_cursor: null, totaal: 1, totaal_ongefilterd: 19 })
    const w = await mountLijst()
    await w.find('[data-testid="filter-zoek"]').setValue('zaak\x00systeem') // rommel geplakt
    await vi.advanceTimersByTimeAsync(300) // debounce → laad()
    vi.useRealTimers()
    await flushPromises()
    const melding = w.find('[data-testid="zoek-opschoon-melding"]')
    expect(melding.exists()).toBe(true)
    expect(melding.text()).toContain('zaaksysteem')
    expect(w.find('[data-testid="filter-zoek"]').element.value).toBe('zaaksysteem')
    expect(api.componenten.lijst.mock.calls.at(-1)[0].zoek).toBe('zaaksysteem') // opgeschoond naar de API
  })

  it('LI051 — een gewone zoekopdracht toont geen melding', async () => {
    vi.useFakeTimers()
    api.componenten.lijst.mockResolvedValue({ items: [], volgende_cursor: null, totaal: 1, totaal_ongefilterd: 19 })
    const w = await mountLijst()
    await w.find('[data-testid="filter-zoek"]').setValue('zaaksysteem')
    await vi.advanceTimersByTimeAsync(300)
    vi.useRealTimers()
    await flushPromises()
    expect(w.find('[data-testid="zoek-opschoon-melding"]').exists()).toBe(false)
  })

  // LI051 blok C — een vaste spatie wordt een gewone: de woordgrens blijft (zaak systeem, niet
  // zaaksysteem), er verandert niets zichtbaars → GEEN melding.
  it('LI051 — vaste spatie: woordgrens blijft, veld toont een gewone spatie, geen melding', async () => {
    vi.useFakeTimers()
    api.componenten.lijst.mockResolvedValue({ items: [], volgende_cursor: null, totaal: 1, totaal_ongefilterd: 19 })
    const w = await mountLijst()
    const nbsp = String.fromCharCode(0x00a0)
    await w.find('[data-testid="filter-zoek"]').setValue('zaak' + nbsp + 'systeem')
    await vi.advanceTimersByTimeAsync(300)
    vi.useRealTimers()
    await flushPromises()
    expect(w.find('[data-testid="filter-zoek"]').element.value).toBe('zaak systeem') // gewone spatie
    expect(api.componenten.lijst.mock.calls.at(-1)[0].zoek).toBe('zaak systeem') // woordgrens naar de API
    expect(w.find('[data-testid="zoek-opschoon-melding"]').exists()).toBe(false) // niets verdwenen
  })
})
