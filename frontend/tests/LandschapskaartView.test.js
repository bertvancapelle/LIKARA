/** Tests — LandschapskaartView v3 (ADR-025, Cytoscape; drie modi + zoek/filter/set/detail). */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { createPinia, setActivePinia } from 'pinia'
import { useAuthStore } from '@/store/auth'

// Cytoscape gemockt (via de frontend-wrapper): de graaf-rendering is een side-effect;
// de panelen zijn de testbare laag.
vi.mock('@/composables/cytoscape', () => ({
  default: vi.fn(() => ({
    on: vi.fn(),
    elements: () => ({ remove: vi.fn(), unselect: vi.fn() }),
    nodes: () => ({ forEach: () => {}, map: () => [], length: 0 }), // LI032 — positie-capture in tekenGraaf
    getElementById: () => ({ length: 0, select: vi.fn() }),
    animate: vi.fn(),
    zoom: () => 1,
    add: vi.fn(),
    layout: () => ({ run: vi.fn() }),
    resize: vi.fn(),
    fit: vi.fn(),
    destroy: vi.fn(),
  })),
}))
vi.mock('@/api', () => ({
  api: {
    landschapskaart: { haalGrafdata: vi.fn(), subgraaf: vi.fn() }, // Fase B — set-scoped subgraaf
    componenten: { opties: vi.fn(), lijst: vi.fn() }, // LI019 1b — type-catalogus + beginscherm-zoek (LI052)
    partijen: { lijst: vi.fn() }, // LI019 1b — leverancier-zoek (externe partijen)
    // ADR-033 2c — opgeslagen views.
    impactViews: { lijst: vi.fn(), haal: vi.fn(), maak: vi.fn(), werkBij: vi.fn(), verwijder: vi.fn() },
  },
}))

// LI033 — de blok→kaart handoff (default: niets klaar → null; specifieke test overschrijft).
vi.mock('@/composables/kaartHandoff', () => ({ neemKaartHandoff: vi.fn(() => null) }))

import cytoscape from '@/composables/cytoscape'
import { api } from '@/api'
import { neemKaartHandoff } from '@/composables/kaartHandoff'
import LandschapskaartView from '@modules/bwb_ontvlechting/frontend/views/LandschapskaartView.vue'
import KaartBeginscherm from '@modules/bwb_ontvlechting/frontend/views/KaartBeginscherm.vue'

const GRAF = () => ({
  nodes: [
    { id: 'a1', naam: 'Zaaksysteem', element_type: 'applicatie', laag: 'application', lifecycle_status: 'migratieklaar', domein: 'applicatie', hosting_model: 'saas', leverancier_naam: 'SaaS BV', leverancier_id: 'l1', blokkades_open: 0, eigenaar_organisatie_id: 'p1' },
    { id: 'a2', naam: 'Documentbeheer', element_type: 'applicatie', laag: 'application', lifecycle_status: 'geblokkeerd', domein: 'applicatie', hosting_model: 'on_premise', leverancier_naam: null, leverancier_id: null, blokkades_open: 1, plateau_naam: 'Plateau 2026', plateau_dispositie: 'Migreren', eigenaar_organisatie_id: 'p1' },
    { id: 'd1', naam: 'Klantdatabank', element_type: 'database', laag: 'technology', lifecycle_status: 'concept', domein: 'Database', hosting_model: 'on_premise', blokkades_open: 0 },
    { id: 'p1', naam: 'Org', element_type: 'partij', laag: 'business', soort: 'organisatie', blokkades_open: 0 },
    { id: 'k1', naam: 'Contract X', element_type: 'contract', laag: 'business', blokkades_open: 0 },
  ],
  edges: [{ bron_id: 'a1', doel_id: 'a2', relatietype: 'flow', label: 'koppeling', ring: 'applicaties', richting: 'eenrichting', protocol: 'rest' }],
})

// Fase B (strategie A) — één setter voedt zowel `haalGrafdata` (hele-landschap-modus) als de
// `subgraaf`-mock (set-modus geeft dezelfde graaf terug), zodat de bestaande full-graph-asserties
// geldig blijven nadat een set is opgebouwd. `subgraaf` leest `_graf` live (zie beforeEach).
let _graf = GRAF()
function zetGraf(g) {
  _graf = g
  api.landschapskaart.haalGrafdata.mockResolvedValue(g)
  return g
}

async function mountView({ query = '', rollen = ['medewerker'], heleLandschap = true } = {}) {
  const pinia = createPinia()
  setActivePinia(pinia)
  const auth = useAuthStore()
  auth.user = { roles: rollen } // ADR-033 2c — beheer-recht op views via hasRole
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'home', component: { template: '<div/>' } },
      { path: '/landschapskaart', name: 'landschapskaart', component: { template: '<div/>' } },
      { path: '/applicaties/:id', name: 'applicatie-detail', component: { template: '<div/>' } },
      { path: '/componenten/:id', name: 'component-detail', component: { template: '<div/>' } },
    ],
  })
  await router.push(`/landschapskaart${query}`)
  await router.isReady()
  const pushSpy = vi.spyOn(router, 'push')
  const w = mount(LandschapskaartView, { global: { plugins: [pinia, router] } })
  await flushPromises()
  // Fase B (strategie A) — laad standaard het hele landschap zodat de bestaande full-graph-tests
  // (filters/scope/ego/impact/swimlane/history/ringen) een gevulde graaf hebben. Een ?center-deeplink
  // laadt al een subgraaf; nieuwe beginscherm-/set-tests passeren heleLandschap:false.
  if (heleLandschap && !query.includes('center')) {
    w.vm.toonHeleLandschap()
    await flushPromises()
  }
  return { w, pushSpy }
}

// ADR-033 — klikken op een component in de lijst = toevoegen/verwijderen uit de actieve set.
// ADR-040 F1 stap 2a — één component kiezen (toevoegen) = dat component inspecteren → praatplaat,
// centraal op die node (weergave 'praatplaat', modus-adapter → 'ego'). Deselecteren zet geen praatplaat.
// LI029 — de resultatenlijst is nu gated (alleen zichtbaar bij zoekterm/filter in kaart-modus);
// set-opbouw via dezelfde handler die de naam-klik aanroept, onafhankelijk van lijst-zichtbaarheid.
const kies = async (w, id) => {
  w.vm.kiesComponent(id)
  await flushPromises()
}
// De praatplaat/overzicht rendert op het canvas; de testbare laag is de afgeleide
// node-/edge-set (getekendeNodes/zichtbareEdges), niet de pixelrender.
const getekendeIds = (w) => w.vm.getekendeNodes.map((n) => n.id).sort()

beforeEach(() => {
  vi.clearAllMocks()
  sessionStorage.clear() // LI022 — voorkom dat bewaarde kaart-state tussen tests lekt
  zetGraf(GRAF())
  // Fase B — set-modus: de subgraaf-mock geeft de actuele `_graf` terug (zelfde graaf als haalGrafdata).
  api.landschapskaart.subgraaf.mockImplementation(() => Promise.resolve(_graf))
  // LI019 1b — type-catalogus + leverancier-zoek defaults.
  api.componenten.opties.mockResolvedValue({
    componenttype: [
      { optie_sleutel: 'applicatie', label: 'Applicatie' },
      { optie_sleutel: 'database', label: 'Database' },
    ],
    // ADR-028 — rol-catalogus + ordinale BIV-niveaus voor de kaartfilters.
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
  api.partijen.lijst.mockResolvedValue({ items: [{ id: 'l1', naam: 'SaaS BV', aard: 'externe_partij' }] })
  api.componenten.lijst.mockResolvedValue({ items: [] }) // LI052 — beginscherm-zoek default leeg
  // ADR-033 2c — geen opgeslagen views by default (geen startscherm). Tests die views willen
  // overschrijven dit per geval.
  api.impactViews.lijst.mockResolvedValue([])
  api.impactViews.maak.mockResolvedValue({ id: 'v-new' })
  api.impactViews.werkBij.mockResolvedValue({ id: 'v1' })
  api.impactViews.verwijder.mockResolvedValue(null)
})
afterEach(() => vi.restoreAllMocks())

describe('LandschapskaartView v3', () => {
  it('ADR-033 — start (lege set) in Geheel-modus en initialiseert Cytoscape; geen view-tabs meer', async () => {
    const { w } = await mountView()
    expect(cytoscape).toHaveBeenCalled()
    expect(w.find('[data-testid="lk-canvas"]').exists()).toBe(true)
    // ADR-040 — "hele landschap" = het volledige Overzicht: modus-adapter → 'geheel', schakelaar op
    // Overzicht, en GEEN automatisch centrum → de Praatplaat-knop is disabled (identiek aan het lege
    // beginscherm). De Praatplaat wordt pas actief zodra de gebruiker zelf een object kiest.
    expect(w.vm.modus).toBe('geheel')
    expect(w.vm.weergave).toBe('overzicht')
    expect(w.vm.kanPraatplaat).toBe(false)
    expect(w.find('[data-testid="lk-weergave-overzicht"]').attributes('aria-pressed')).toBe('true')
    expect(w.find('[data-testid="lk-weergave-praatplaat"]').attributes('disabled')).toBeDefined()
    // De drie handmatige view-tabs zijn volledig verdwenen.
    expect(w.find('[data-testid="lk-modus-ego"]').exists()).toBe(false)
    expect(w.find('[data-testid="lk-modus-impact"]').exists()).toBe(false)
    expect(w.find('[data-testid="lk-modus-geheel"]').exists()).toBe(false)
    // resultaten (LI029 — lijst is gated; toets de samenstelling op de data): applicaties (a1, a2)
    // + de eigen organisatie (p1) als vertrekpunt — niet het contract.
    const _ids = w.vm.gefilterdeNodes.map((n) => n.id)
    expect(_ids.length).toBe(3)
    expect(_ids).toContain('p1') // organisatie als vertrekpunt
    expect(_ids).not.toContain('k1') // contract niet
  })

  it('ADR-040 — de weergave volgt de handeling; de modus-adapter volgt de weergave', async () => {
    const { w } = await mountView()
    // Hele landschap → Overzicht (adapter → 'geheel').
    expect(w.vm.weergave).toBe('overzicht')
    expect(w.vm.modus).toBe('geheel')
    await kies(w, 'a1') // één component inspecteren → praatplaat, centraal op a1
    expect(w.vm.weergave).toBe('praatplaat')
    expect(w.vm.modus).toBe('ego')
    expect(w.vm.kanPraatplaat).toBe(true)
    await kies(w, 'a2') // nog een component kiezen = hercentreren → blijft praatplaat (op a2)
    expect(w.vm.weergave).toBe('praatplaat')
    expect(w.vm.modus).toBe('ego')
    // ADR-033 1c — geen HTML-lijst-overlay meer; alles rendert op het canvas.
    expect(w.find('[data-testid="lk-impact-verkenner"]').exists()).toBe(false)
    expect(w.find('[data-testid="lk-canvas"]').exists()).toBe(true)
    w.vm.toonOverzicht() // schakelaar → Overzicht (brede plaat)
    await flushPromises()
    expect(w.vm.weergave).toBe('overzicht')
    expect(w.vm.modus).toBe('geheel')
    w.vm.wisSet() // begin opnieuw → leeg beginscherm
    await flushPromises()
    expect(w.vm.modus).toBe('leeg')
  })

  it('ADR-040 — de schakelaar zet de weergave; de Praatplaat-knop is disabled zonder centrum', async () => {
    // Beginscherm (geen hele-landschap, lege set) → geen centrum geseed → Praatplaat disabled.
    const { w } = await mountView({ heleLandschap: false })
    expect(w.vm.kanPraatplaat).toBe(false)
    expect(w.find('[data-testid="lk-weergave-praatplaat"]').attributes('disabled')).toBeDefined()
    // Een component kiezen zet een centrum → de knop wordt bruikbaar en de weergave staat op praatplaat.
    await kies(w, 'a1')
    expect(w.vm.kanPraatplaat).toBe(true)
    expect(w.find('[data-testid="lk-weergave-praatplaat"]').attributes('disabled')).toBeUndefined()
    expect(w.find('[data-testid="lk-weergave-praatplaat"]').attributes('aria-pressed')).toBe('true')
    // Schakelaar → Overzicht en terug → Praatplaat; de knoppen sturen de weergave.
    await w.find('[data-testid="lk-weergave-overzicht"]').trigger('click')
    expect(w.vm.weergave).toBe('overzicht')
    expect(w.find('[data-testid="lk-weergave-overzicht"]').attributes('aria-pressed')).toBe('true')
    await w.find('[data-testid="lk-weergave-praatplaat"]').trigger('click')
    expect(w.vm.weergave).toBe('praatplaat')
  })

  it('ADR-040 — een weergave-wissel begint met een schone lei (spotlight + detail/selectie gereset)', async () => {
    const { w } = await mountView()
    await kies(w, 'a1') // praatplaat op a1; detail gevuld
    // Zet een legenda-spotlight + een node-selectie/detail (zoals na een klik).
    w.vm.toggleLegendaFilter('Component')
    w.vm.inspecteerNode('a1')
    await flushPromises()
    expect(w.vm.legendaTypeFilter).toBe('Component')
    expect(w.vm.geselecteerdNodeId).toBe('a1')
    expect(w.vm.detailNode?.id).toBe('a1')
    // Schakelaar → Overzicht: schone lei (spotlight uit, geen stale detail/selectie → geen lk-dim-restje).
    await w.find('[data-testid="lk-weergave-overzicht"]').trigger('click')
    expect(w.vm.weergave).toBe('overzicht')
    expect(w.vm.legendaTypeFilter).toBe(null)
    expect(w.vm.geselecteerdNodeId).toBe(null)
    expect(w.vm.detailNode).toBe(null)
    // Zet opnieuw een spotlight/selectie en schakel terug via de Praatplaat-knop (schakel-ingang, geen id).
    w.vm.toggleLegendaFilter('Component')
    w.vm.inspecteerNode('a1')
    await flushPromises()
    await w.find('[data-testid="lk-weergave-praatplaat"]').trigger('click')
    expect(w.vm.weergave).toBe('praatplaat')
    expect(w.vm.legendaTypeFilter).toBe(null)
    expect(w.vm.geselecteerdNodeId).toBe(null)
    expect(w.vm.detailNode).toBe(null)
  })

  it('ADR-040 — inspecteren (kies/drill) houdt zijn eigen detail; alleen de spotlight blijft ongemoeid binnen de weergave', async () => {
    const { w } = await mountView()
    w.vm.toggleLegendaFilter('Component') // spotlight actief binnen de weergave
    await kies(w, 'a1') // kiesComponent zet zelf het detail op de geklikte node → dat blijft staan
    await flushPromises()
    expect(w.vm.detailNode?.id).toBe('a1')
    // De inspectie-recenter (toonPraatplaat MÉT id) wist het net-gezette detail niet.
    w.vm.drillNaar('a2')
    await flushPromises()
    expect(w.vm.weergave).toBe('praatplaat')
    expect(w.vm.detailNode?.id).toBe('a2')
  })

  it('ADR-040 — "toon impact" (drillNaar) hercentreert de praatplaat; buren erbij / view → overzicht', async () => {
    const { w } = await mountView()
    // drillNaar = "toon impact" op één component → praatplaat centraal op dat component.
    w.vm.drillNaar('a2')
    await flushPromises()
    expect(w.vm.weergave).toBe('praatplaat')
    expect(w.vm.modus).toBe('ego')
    // Een set opbouwen via een ingang (voegComponentenToeAanSet) = brede plaat → overzicht.
    w.vm.voegComponentenToeAanSet([{ id: 'a1' }])
    await flushPromises()
    expect(w.vm.weergave).toBe('overzicht')
    expect(w.vm.modus).toBe('geheel')
  })

  // LI052 — spook-id: een set-lid dat de subgraaf niet als node oplevert wordt opgeruimd; teller/modus
  // volgen de geresolveerde leden → één echt component blijft N=1/Ego (geen "(2) met 1 regel", geen
  // spurieuze Impact) en er ontstaat geen refetch-lus.
  it('LI052 — niet-resolvend set-lid wordt opgeruimd → N-1, blijft Ego, geen refetch-lus', async () => {
    const { w } = await mountView()
    // Subgraaf levert a2 NIET terug → a2 is een spook (wel in de request, niet in de respons).
    api.landschapskaart.subgraaf.mockImplementation(() =>
      Promise.resolve({ nodes: _graf.nodes.filter((n) => n.id !== 'a2'), edges: [] }))
    await kies(w, 'a1')
    await kies(w, 'a2') // ruwe set = {a1,a2}, maar a2 resolveert niet
    await flushPromises()
    // De set is opgeschoond naar alleen materialiseerbare leden.
    expect([...w.vm.actieveSet].sort()).toEqual(['a1'])
    expect(w.vm.actieveSetNodes.map((n) => n.id)).toEqual(['a1'])
    // Teller/modus volgen de geresolveerde leden → praatplaat op het overgebleven centrum (Ego).
    expect(w.vm.modus).toBe('ego')
    // Anti-lus: extra ticks lokken geen nieuwe fetch uit (opschonen gebeurt één keer).
    const n1 = api.landschapskaart.subgraaf.mock.calls.length
    await flushPromises()
    await flushPromises()
    expect(api.landschapskaart.subgraaf.mock.calls.length).toBe(n1)
  })

  it('ADR-033 — klik in de lijst toggelt set-lidmaatschap (de losse "+"-knop is vervallen)', async () => {
    const { w } = await mountView()
    // De oude per-rij "+"-knop bestaat niet meer.
    expect(w.find('[data-testid="lk-res-set-a1"]').exists()).toBe(false)
    await kies(w, 'a1')
    expect([...w.vm.actieveSet]).toEqual(['a1'])
    await w.find('[data-testid="lk-zoek"]').setValue('zaak') // LI029 — lijst tonen (gated)
    await flushPromises()
    expect(w.find('[data-testid="lk-res-naam-a1"]').attributes('aria-pressed')).toBe('true')
    expect(w.find('[data-testid="lk-res-gekozen-a1"]').exists()).toBe(true) // ✓-markering
    await kies(w, 'a1') // opnieuw klikken → verwijderen → set leeg → beginscherm (Fase B: geen graaf meer)
    expect([...w.vm.actieveSet]).toEqual([])
    expect(w.vm.beginscherm).toBe(true)
  })

  it('LI019 1b — type-filter laadt de componenttype-catalogus als doorzoekbare multi-select', async () => {
    const { w } = await mountView()
    expect(api.componenten.opties).toHaveBeenCalled()
    // Nieuwe multi-select aanwezig; oude enkele dropdowns weg.
    expect(w.find('[data-testid="lk-filter-type-input"]').exists()).toBe(true)
    expect(w.find('[data-testid="lk-filter-leverancier-input"]').exists()).toBe(true)
    expect(w.find('[data-testid="lk-filter-domein"]').exists()).toBe(false)
    // De volledige catalogus (incl. Database) is kiesbaar, niet alleen de in de graaf aanwezige typen.
    await w.find('[data-testid="lk-filter-type-input"]').trigger('focus')
    await flushPromises()
    expect(w.find('[data-testid="lk-filter-type-optie-database"]').exists()).toBe(true)
  })

  it('LI019 1c-v2 — leverancier-filter: andere leverancier weg, kenmerkloos pas mee met "Zonder leverancier"', async () => {
    // Eigen graf: a1 (l1), a3 (andere leverancier l2), a2 (geen leverancier).
    zetGraf({
      nodes: [
        { id: 'a1', naam: 'App1', element_type: 'applicatie', laag: 'application', lifecycle_status: 'concept', leverancier_naam: 'SaaS BV', leverancier_id: 'l1', blokkades_open: 0 },
        { id: 'a3', naam: 'App3', element_type: 'applicatie', laag: 'application', lifecycle_status: 'concept', leverancier_naam: 'Andere BV', leverancier_id: 'l2', blokkades_open: 0 },
        { id: 'a2', naam: 'App2', element_type: 'applicatie', laag: 'application', lifecycle_status: 'concept', leverancier_naam: null, leverancier_id: null, blokkades_open: 0 },
      ],
      edges: [],
    })
    const { w } = await mountView()
    await w.find('[data-testid="lk-filter-leverancier-input"]').trigger('focus')
    await flushPromises()
    await w.find('[data-testid="lk-filter-leverancier-optie-l1"]').trigger('mousedown')
    await flushPromises()
    expect(w.find('[data-testid="lk-filter-leverancier-chip-l1"]').text()).toContain('SaaS BV')
    expect(w.find('[data-testid="lk-res-naam-a1"]').exists()).toBe(true) // l1 → matcht
    expect(w.find('[data-testid="lk-res-naam-a3"]').exists()).toBe(false) // l2 → andere leverancier, weg
    expect(w.find('[data-testid="lk-res-naam-a2"]').exists()).toBe(false) // geen leverancier → standaard weg
    // "Zonder leverancier" (vaste optie) neemt kenmerkloze nodes weer mee.
    await w.find('[data-testid="lk-filter-leverancier-input"]').trigger('focus')
    await flushPromises()
    await w.find('[data-testid="lk-filter-leverancier-optie-__zonder__"]').trigger('mousedown')
    await flushPromises()
    expect(w.find('[data-testid="lk-filter-leverancier-chip-__zonder__"]').text()).toContain('Zonder leverancier')
    expect(w.find('[data-testid="lk-res-naam-a2"]').exists()).toBe(true) // nu mee
    expect(w.find('[data-testid="lk-res-naam-a3"]').exists()).toBe(false) // l2 blijft weg
  })

  it('LI019 1c-v2 — "Zonder lifecycle" neemt kenmerkloze context-nodes weer mee (geheel-modus)', async () => {
    const { w } = await mountView() // lege set → geheel
    await w.find('[data-testid="lk-filter-lifecycle-input"]').trigger('focus')
    await flushPromises()
    await w.find('[data-testid="lk-filter-lifecycle-optie-migratieklaar"]').trigger('mousedown')
    await flushPromises()
    let ids = w.vm.zichtbareNodes.map((n) => n.id)
    expect(ids).toContain('a1') // migratieklaar — matcht
    expect(ids).not.toContain('a2') // geblokkeerd → weg
    expect(ids).not.toContain('p1') // partij (geen lifecycle) → standaard weg
    expect(ids).not.toContain('k1') // contract (geen lifecycle) → standaard weg
    // "Zonder lifecycle" toevoegen → kenmerkloze nodes terug.
    await w.find('[data-testid="lk-filter-lifecycle-input"]').trigger('focus')
    await flushPromises()
    await w.find('[data-testid="lk-filter-lifecycle-optie-__zonder__"]').trigger('mousedown')
    await flushPromises()
    ids = w.vm.zichtbareNodes.map((n) => n.id)
    expect(ids).toContain('a1')
    expect(ids).toContain('p1') // geen lifecycle → nu mee
    expect(ids).toContain('k1') // geen lifecycle → nu mee
    expect(ids).not.toContain('a2') // geblokkeerd heeft wél lifecycle, niet geselecteerd → blijft weg
  })

  it('LI019 1c-v2 — Ego: filter dat het centrum verbergt vraagt bevestiging (annuleren herstelt, doorgaan past toe)', async () => {
    const { w } = await mountView()
    await kies(w, 'a1') // 1 component → ego-modus, centrum = a1 (hosting saas)
    expect(w.vm.modus).toBe('ego')
    // Filter hosting=on_premise zou a1 (saas) verbergen → bevestigingsdialoog.
    await w.find('[data-testid="lk-filter-hosting-input"]').trigger('focus')
    await flushPromises()
    await w.find('[data-testid="lk-filter-hosting-optie-on_premise"]').trigger('mousedown')
    await flushPromises()
    expect(w.find('[data-testid="lk-ego-filter-dialog"]').exists()).toBe(true)
    // Annuleren → filter teruggedraaid (geen hosting-chip).
    await w.find('[data-testid="lk-ego-filter-annuleer"]').trigger('click')
    await flushPromises()
    expect(w.find('[data-testid="lk-ego-filter-dialog"]').exists()).toBe(false)
    expect(w.find('[data-testid="lk-filter-hosting-chip-on_premise"]').exists()).toBe(false)
    // Opnieuw kiezen, nu doorgaan → filter toegepast, centrum (a1) verdwijnt uit de kaart.
    await w.find('[data-testid="lk-filter-hosting-input"]').trigger('focus')
    await flushPromises()
    await w.find('[data-testid="lk-filter-hosting-optie-on_premise"]').trigger('mousedown')
    await flushPromises()
    await w.find('[data-testid="lk-ego-filter-doorgaan"]').trigger('click')
    await flushPromises()
    expect(w.find('[data-testid="lk-ego-filter-dialog"]').exists()).toBe(false)
    expect(w.find('[data-testid="lk-filter-hosting-chip-on_premise"]').exists()).toBe(true)
    expect(w.vm.zichtbareNodes.map((n) => n.id)).not.toContain('a1')
  })

  it('ADR-040 — praatplaat: een filter versmalt de ego-kring (het matchende centrum blijft)', async () => {
    zetGraf({
      nodes: [
        { id: 'a1', naam: 'Centrum', element_type: 'applicatie', laag: 'application', lifecycle_status: 'migratieklaar', blokkades_open: 0 },
        { id: 'n1', naam: 'BuurOk', element_type: 'applicatie', laag: 'application', lifecycle_status: 'migratieklaar', blokkades_open: 0 },
        { id: 'n2', naam: 'BuurWeg', element_type: 'applicatie', laag: 'application', lifecycle_status: 'geblokkeerd', blokkades_open: 0 },
      ],
      edges: [
        { bron_id: 'a1', doel_id: 'n1', relatietype: 'flow', label: 'koppeling', ring: 'applicaties' },
        { bron_id: 'a1', doel_id: 'n2', relatietype: 'flow', label: 'koppeling', ring: 'applicaties' },
      ],
    })
    const { w } = await mountView()
    await kies(w, 'a1') // praatplaat centraal op a1; ego-kring {a1, n1, n2}
    expect(w.vm.modus).toBe('ego')
    // Filter migratieklaar — het centrum a1 matcht zelf (geen centrum-verberg-dialoog); de kring versmalt.
    await w.find('[data-testid="lk-filter-lifecycle-input"]').trigger('focus')
    await flushPromises()
    await w.find('[data-testid="lk-filter-lifecycle-optie-migratieklaar"]').trigger('mousedown')
    await flushPromises()
    const ids = w.vm.zichtbareNodes.map((n) => n.id)
    expect(ids).toContain('a1') // het (matchende) centrum blijft
    expect(ids).toContain('n1') // buur matcht het filter
    expect(ids).not.toContain('n2') // buur matcht niet → weg
  })

  it('LI019 1d-v4 (bug 7) — actief filter behoudt context-nodes (contract) van zichtbare componenten', async () => {
    zetGraf({
      nodes: [
        { id: 'a1', naam: 'App', element_type: 'applicatie', laag: 'application', lifecycle_status: 'migratieklaar', blokkades_open: 0 },
        { id: 'k1', naam: 'Contract X', element_type: 'contract', laag: 'business', blokkades_open: 0 },
      ],
      edges: [{ bron_id: 'a1', doel_id: 'k1', relatietype: 'association', label: 'valt onder', ring: 'contracten' }],
    })
    const { w } = await mountView() // lege set → geheel
    await w.find('[data-testid="lk-filter-lifecycle-input"]').trigger('focus')
    await flushPromises()
    await w.find('[data-testid="lk-filter-lifecycle-optie-migratieklaar"]').trigger('mousedown')
    await flushPromises()
    const ids = w.vm.zichtbareNodes.map((n) => n.id)
    expect(ids).toContain('a1') // matcht het lifecycle-filter
    expect(ids).toContain('k1') // contract (geen lifecycle) → context van a1 via de contracten-ring → blijft
  })

  it('LI019 1d-v5 — node→lane-toewijzing robuust voor de werkelijke data', async () => {
    const { w } = await mountView()
    const lane = w.vm._laneVan
    expect(lane({ element_type: 'applicatie', laag: 'application' })).toBe('componenten')
    expect(lane({ element_type: 'database', laag: 'technology' })).toBe('infrastructuur')
    expect(lane({ element_type: 'gebruikersgroep', laag: 'business' })).toBe('gebruikers')
    expect(lane({ element_type: 'partij', laag: 'business' })).toBe('rollen')
    expect(lane({ element_type: 'contract', laag: 'business' })).toBe('contracten')
    // Bug 1: een componenttype zónder application-laag-typing (laag null/ontbrekend) → tóch componenten,
    // niet "Overig". Alleen technology-laag wijkt af (infrastructuur).
    expect(lane({ element_type: 'zaaksysteem_suite', laag: null })).toBe('componenten')
    expect(lane({ element_type: 'webservice' })).toBe('componenten')
    expect(lane({ element_type: 'fileshare', laag: 'technology' })).toBe('infrastructuur')
    // Alleen een node zónder element_type valt in Overig.
    expect(lane({})).toBe('overig')
  })

  it('LI019 swimlane-parkeren — layout-toggle is verborgen uit de UI; Radiaal is de enige layout', async () => {
    const { w } = await mountView()
    expect(w.vm.layoutModus).toBe('radiaal')
    // De swimlane-knop én de hele toggle zijn geparkeerd → niet in de DOM.
    expect(w.find('[data-testid="lk-layout-toggle"]').exists()).toBe(false)
    expect(w.find('[data-testid="lk-layout-swimlane"]').exists()).toBe(false)
    // De swimlane-codepaden blijven programmatisch bereikbaar (toekomstige herwrite).
    w.vm.setLayoutModus('swimlane')
    await flushPromises()
    expect(w.vm.layoutModus).toBe('swimlane')
  })

  it('LI019 swimlane-parkeren — layoutModus wordt niet uit sessionStorage hersteld (altijd radiaal)', async () => {
    sessionStorage.setItem('lk-state', JSON.stringify({ layoutModus: 'swimlane' }))
    const { w } = await mountView()
    expect(w.vm.layoutModus).toBe('radiaal')
  })

  const SWIM_GRAF = {
    nodes: [
      { id: 'app', naam: 'App', element_type: 'applicatie', laag: 'application', lifecycle_status: 'concept', blokkades_open: 0 },
      { id: 'db', naam: 'DB', element_type: 'database', laag: 'technology', lifecycle_status: 'concept', blokkades_open: 0 },
    ],
    edges: [{ bron_id: 'app', doel_id: 'db', relatietype: 'assignment', label: 'draait op', ring: 'infrastructuur' }],
  }
  async function mountSwimlane() {
    zetGraf(SWIM_GRAF)
    const { w } = await mountView()
    w.vm.setLayoutModus('swimlane')
    await flushPromises()
    return w
  }

  it('LI019 1d-v2 — swimlane-posities: componenten boven infrastructuur, x-gecentreerd, object-map', async () => {
    const w = await mountSwimlane()
    const pos = w.vm._swimlanePositions()
    expect(pos.app.y).toBeLessThan(pos.db.y) // "Componenten" (index 2) boven "Infrastructuur" (index 3)
    expect(pos.app.x).toBe(0) // enige node in de lane → gecentreerd
    // Regressie-guard: `positions` is een OBJECT-MAP gekeyed op node-id (string), géén callback.
    const cfg = w.vm._layout()
    expect(cfg.name).toBe('preset')
    expect(typeof cfg.positions).toBe('object')
    expect(cfg.positions.app).toBeDefined()
    expect(cfg.fit).toBe(true)
  })

  it('LI019 1d-v6 — nodes wrappen per lane in een grid; breedte begrensd, lane-hoogte schaalt', async () => {
    const nodes = []
    for (let i = 0; i < 8; i++) {
      nodes.push({ id: `c${i}`, naam: `Comp ${i}`, element_type: 'applicatie', laag: 'application', lifecycle_status: 'concept', blokkades_open: 0 })
    }
    zetGraf({ nodes, edges: [] })
    const { w } = await mountView()
    w.vm.setLayoutModus('swimlane')
    await flushPromises()
    // De 8 componenten zijn los (geen edges) — swimlane toont ze sowieso (geen edge-eis).
    const pos = w.vm._swimlanePositions()
    const xs = Object.values(pos).map((p) => p.x)
    const ys = new Set(Object.values(pos).map((p) => p.y))
    // 8 nodes, 6 kolommen → 2 rijen (2 distinct y); x begrensd (geen ~10.000px-spreiding).
    expect(ys.size).toBe(2)
    expect(Math.max(...xs.map((x) => Math.abs(x)))).toBeLessThan(600)
    // Lane-hoogte schaalt met het aantal rijen (2 rijen → ruim boven de min-hoogte).
    const comp = w.vm.laneBanden.find((b) => b.key === 'componenten')
    expect(comp.height).toBeGreaterThan(150)
  })

  it('LI019 1d-v8 — swimlane toont álle nodes uit zichtbareNodes (radiaal-data zonder edge-eis)', async () => {
    zetGraf({
      nodes: [
        { id: 'a1', naam: 'Zaaksysteem', element_type: 'applicatie', laag: 'application', lifecycle_status: 'concept', blokkades_open: 0, eigenaar_organisatie_id: 'p1' },
        { id: 'a2', naam: 'DMS', element_type: 'applicatie', laag: 'application', lifecycle_status: 'concept', blokkades_open: 0, eigenaar_organisatie_id: 'p1' },
        { id: 'p1', naam: 'Org (los)', element_type: 'partij', laag: 'business', soort: 'organisatie', blokkades_open: 0 },
      ],
      edges: [{ bron_id: 'a1', doel_id: 'a2', relatietype: 'flow', label: 'koppeling', ring: 'applicaties' }],
    })
    const { w } = await mountView()
    // Radiaal (geheel): edge-rakende nodes — a1,a2 verbonden, p1 los → verborgen.
    expect(w.vm.getekendeNodes.map((n) => n.id).sort()).toEqual(['a1', 'a2'])
    // Swimlane: álle nodes uit zichtbareNodes (= radiaal-data), incl. de losse p1 — geen edge-eis.
    w.vm.setLayoutModus('swimlane')
    await flushPromises()
    expect(w.vm.getekendeNodes.map((n) => n.id).sort()).toEqual(['a1', 'a2', 'p1'])
    // Terug naar radiaal + "Toon registratiegaps" AAN → óók daar de losse p1.
    w.vm.setLayoutModus('radiaal')
    await flushPromises()
    await w.find('[data-testid="lk-registratiegaps"]').setValue(true)
    await flushPromises()
    expect(w.vm.getekendeNodes.map((n) => n.id).sort()).toEqual(['a1', 'a2', 'p1'])
  })

  it('LI019 1d-v4 — banden in twee lagen rond het canvas: achtergronden niet-interactief, header interactief', async () => {
    const w = await mountSwimlane()
    // Achtergrond-laag (onder het canvas) + losse header-laag (boven het canvas) bestaan beide.
    const achtergrond = w.find('[data-testid="lk-lanes"]')
    const headers = w.find('[data-testid="lk-lane-headers"]')
    expect(achtergrond.exists()).toBe(true)
    expect(headers.exists()).toBe(true)
    // Beide container-lagen laten node-clicks door (pointer-events-none); de header zelf is wél
    // interactief (pointer-events-auto) → versleepbaar zonder node-clicks te blokkeren.
    expect(achtergrond.classes()).toContain('pointer-events-none')
    expect(headers.classes()).toContain('pointer-events-none')
    expect(w.find('[data-testid="lk-lane-header-componenten"]').classes()).toContain('pointer-events-auto')
  })

  it('LI019 1d-v2 — alle lanes tonen; "Verberg lege lanes" houdt alleen gevulde lanes', async () => {
    const w = await mountSwimlane()
    // Default: alle 6 lanes (incl. lege) zichtbaar; alleen componenten + infrastructuur gevuld.
    expect(w.vm.laneBanden.length).toBe(6)
    expect(w.vm.laneBanden.find((b) => b.key === 'rollen').leeg).toBe(true)
    expect(w.vm.laneBanden.find((b) => b.key === 'componenten').leeg).toBe(false)
    // "Verberg lege lanes" → alleen de gevulde lanes.
    await w.find('[data-testid="lk-verberg-lege"]').setValue(true)
    await flushPromises()
    expect(w.vm.laneBanden.map((b) => b.key).sort()).toEqual(['componenten', 'infrastructuur'])
  })

  it('LI019 1d-v3 — lane verslepen herschikt de volgorde en persisteert in sessionStorage', async () => {
    const w = await mountSwimlane()
    expect(w.vm.laneVolgorde).toEqual(['rollen', 'gebruikers', 'componenten', 'infrastructuur', 'overig', 'contracten'])
    w.vm._herschikLane('contracten', 'rollen') // contracten naar de positie van rollen (bovenaan)
    await flushPromises()
    expect(w.vm.laneVolgorde[0]).toBe('contracten')
    expect(w.vm.laneVolgorde[1]).toBe('rollen')
    // Direct opgeslagen (geen aparte bewaar-knop).
    expect(JSON.parse(sessionStorage.getItem('lk-state')).laneVolgorde[0]).toBe('contracten')
    // De zijbalk-lanevolgorde-lijst is verwijderd (bug 3).
    expect(w.find('[data-testid="lk-lane-volgorde"]').exists()).toBe(false)
    expect(w.find('[data-testid="lk-lane-reset"]').exists()).toBe(false)
  })

  it('LI019 1d-v8 — registratiegaps-toggle toont losse nodes in radiaal; swimlane toont ze sowieso', async () => {
    // p1 (partij) en k1 (contract) hebben geen edges → in radiaal standaard verborgen, mét toggle zichtbaar.
    const { w } = await mountView()
    expect(w.vm.getekendeNodes.map((n) => n.id)).not.toContain('p1') // los → verborgen (radiaal)
    await w.find('[data-testid="lk-registratiegaps"]').setValue(true)
    await flushPromises()
    const radiaalGaps = w.vm.getekendeNodes.map((n) => n.id)
    expect(radiaalGaps).toContain('p1') // nu zichtbaar in radiaal
    expect(radiaalGaps).toContain('k1')
    // Swimlane toont losse nodes sowieso (zonder toggle nodig).
    await w.find('[data-testid="lk-registratiegaps"]').setValue(false)
    await flushPromises()
    w.vm.setLayoutModus('swimlane')
    await flushPromises()
    const swimIds = w.vm.getekendeNodes.map((n) => n.id)
    expect(swimIds).toContain('p1') // in de Rollen-lane
    expect(swimIds).toContain('k1') // in de Contracten-lane
  })

  it('LI019 1d-v2 — lanevolgorde + verberg-lege hersteld uit sessionStorage', async () => {
    sessionStorage.setItem('lk-state', JSON.stringify({
      laneVolgorde: ['contracten', 'rollen', 'gebruikers', 'componenten', 'infrastructuur', 'overig'],
      verbergLegeLanes: true,
    }))
    const { w } = await mountView()
    expect(w.vm.laneVolgorde[0]).toBe('contracten')
    expect(w.vm.verbergLegeLanes).toBe(true)
  })

  it('LI019 1b-v2 — hosting- en lifecycle-multiselect versmallen de lijst', async () => {
    const { w } = await mountView()
    await w.find('[data-testid="lk-filter-hosting-input"]').trigger('focus')
    await flushPromises()
    await w.find('[data-testid="lk-filter-hosting-optie-saas"]').trigger('mousedown')
    await flushPromises()
    expect(w.find('[data-testid="lk-res-naam-a1"]').exists()).toBe(true) // saas
    expect(w.find('[data-testid="lk-res-naam-a2"]').exists()).toBe(false) // on_premise
    // Hosting-chip verwijderen, daarna op lifecycle filteren.
    await w.find('[data-testid="lk-filter-hosting-chip-verwijder-saas"]').trigger('click')
    await flushPromises()
    await w.find('[data-testid="lk-filter-lifecycle-input"]').trigger('focus')
    await flushPromises()
    await w.find('[data-testid="lk-filter-lifecycle-optie-migratieklaar"]').trigger('mousedown')
    await flushPromises()
    expect(w.find('[data-testid="lk-res-naam-a1"]').exists()).toBe(true) // migratieklaar
    expect(w.find('[data-testid="lk-res-naam-a2"]').exists()).toBe(false) // geblokkeerd
  })

  it('LI019 1b-v2 — type-filter werkt over alle ringen; type-loze nodes blijven (geheel-modus)', async () => {
    const { w } = await mountView() // lege set → geheel
    await w.find('[data-testid="lk-filter-type-input"]').trigger('focus')
    await flushPromises()
    await w.find('[data-testid="lk-filter-type-optie-applicatie"]').trigger('mousedown')
    await flushPromises()
    const ids = w.vm.zichtbareNodes.map((n) => n.id)
    expect(ids).toContain('a1') // applicatie — matcht
    expect(ids).not.toContain('d1') // database — ander type, weggefilterd
    expect(ids).toContain('p1') // partij — type-loos, blijft
    expect(ids).toContain('k1') // contract — type-loos, blijft
  })

  it('ADR-033 1b — samenstelling-ring: checkbox aanwezig (standaard aan), edge rendert gestreept mee', async () => {
    zetGraf({
      nodes: [
        { id: 'a1', naam: 'Geheel', element_type: 'applicatie', laag: 'application', lifecycle_status: 'concept', blokkades_open: 0 },
        { id: 'd1', naam: 'Onderdeel', element_type: 'applicatie', laag: 'application', lifecycle_status: 'concept', blokkades_open: 0 },
      ],
      edges: [{ bron_id: 'a1', doel_id: 'd1', relatietype: 'aggregation', label: 'bestaat uit', ring: 'samenstelling' }],
    })
    const { w } = await mountView() // lege set → geheel
    expect(w.find('[data-testid="lk-ring-samenstelling"]').exists()).toBe(true)
    // De samenstelling-edge is zichtbaar en verbindt beide nodes (beide getekend).
    expect(w.vm.zichtbareEdges.some((e) => e.ring === 'samenstelling')).toBe(true)
    expect(w.vm.getekendeNodes.map((n) => n.id).sort()).toEqual(['a1', 'd1'])
    // _edgeData: gestreepte lijn + leesbaar label uit de backend.
    const ed = w.vm._edgeData({ bron_id: 'a1', doel_id: 'd1', ring: 'samenstelling', label: 'bestaat uit' }, 0)
    expect(ed.ls).toBe('dashed')
    expect(ed.label).toBe('bestaat uit')
    // Ring uitvinken verbergt de samenstelling-edge.
    await w.find('[data-testid="lk-ring-samenstelling"]').trigger('change')
    await flushPromises()
    expect(w.vm.zichtbareEdges.some((e) => e.ring === 'samenstelling')).toBe(false)
  })

  it('toont de ring-checkboxes in ALLE (afgeleide) modi (regressie LI018)', async () => {
    const RINGEN = ['lk-ring-applicaties', 'lk-ring-rollen', 'lk-ring-gebruikers', 'lk-ring-contracten', 'lk-ring-infrastructuur']
    const alleRingenZichtbaar = (w) => RINGEN.every((t) => w.find(`[data-testid="${t}"]`).exists())
    const { w } = await mountView()
    expect(alleRingenZichtbaar(w)).toBe(true) // overzicht (lege set → 'geheel')
    await kies(w, 'a1')
    expect(w.vm.modus).toBe('ego')
    expect(alleRingenZichtbaar(w)).toBe(true) // praatplaat (ego)
    w.vm.toonOverzicht()
    await flushPromises()
    expect(w.vm.modus).toBe('geheel')
    expect(alleRingenZichtbaar(w)).toBe(true) // overzicht
  })

  it('ring uitvinken verbergt ook de nodes van die ring (LI019 Fix 2)', async () => {
    zetGraf({
      nodes: [
        { id: 'a1', naam: 'App1', element_type: 'applicatie', laag: 'application', lifecycle_status: 'concept', blokkades_open: 0 },
        { id: 'a2', naam: 'App2', element_type: 'applicatie', laag: 'application', lifecycle_status: 'concept', blokkades_open: 0 },
        { id: 'g1', naam: 'Groep', element_type: 'gebruikersgroep', laag: 'business', aantal_leden: 10, organisatie_id: null },
      ],
      edges: [
        { bron_id: 'a1', doel_id: 'a2', relatietype: 'flow', label: 'koppeling', ring: 'applicaties', richting: 'eenrichting', protocol: 'rest' },
        { bron_id: 'a1', doel_id: 'g1', relatietype: 'serving', label: 'gebruikt door', ring: 'gebruikers' },
      ],
    })
    const { w } = await mountView()
    expect(w.find('[data-testid="lk-zichtbaar-aantal"]').text()).toContain('3 in beeld') // a1, a2, g1
    // ring 'gebruikers' uit → g1 (alleen via die ring verbonden) verdwijnt; apps blijven via de flow
    await w.find('[data-testid="lk-ring-gebruikers"]').trigger('change')
    await flushPromises()
    expect(w.find('[data-testid="lk-zichtbaar-aantal"]').text()).toContain('2 in beeld')
  })

  it('zoekfilter vermindert de zichtbare resultaten', async () => {
    const { w } = await mountView()
    await w.find('[data-testid="lk-zoek"]').setValue('zaak')
    await flushPromises()
    expect(w.find('[data-testid="lk-res-naam-a1"]').exists()).toBe(true)
    expect(w.find('[data-testid="lk-res-naam-a2"]').exists()).toBe(false)
    expect(w.findAll('[data-testid^="lk-res-naam-"]').length).toBe(1)
  })

  // ── LI028 — zoekbalk raakt de graaf niet + expliciete "voeg toe"-knop ────────────────────────
  it('LI028 — typen in de zoekbalk verandert de graaf niet (geen herfetch, set ongemoeid)', async () => {
    const { w } = await mountView() // geheel, volledige graaf
    await flushPromises()
    const grafVoor = getekendeIds(w)
    const setVoor = [...w.vm.actieveSet]
    const fetchVoor = api.landschapskaart.subgraaf.mock.calls.length
    await w.find('[data-testid="lk-zoek"]').setValue('dms')
    await flushPromises()
    expect(getekendeIds(w)).toEqual(grafVoor) // graaf ongewijzigd
    expect([...w.vm.actieveSet]).toEqual(setVoor) // set ongewijzigd
    expect(api.landschapskaart.subgraaf.mock.calls.length).toBe(fetchVoor) // geen herfetch
  })

  it('LI028 — typen in ego-modus expandeert de graaf niet (regressie 13→24)', async () => {
    const { w } = await mountView()
    await flushPromises()
    w.vm.toggleSet('a1') // ego-modus op a1
    await flushPromises()
    const grafVoor = getekendeIds(w)
    await w.find('[data-testid="lk-zoek"]').setValue('zaak')
    await flushPromises()
    expect(getekendeIds(w)).toEqual(grafVoor) // zoekterm voegt geen context-buren toe
  })

  it('LI028 — "+"-knop voegt een resultaat toe aan het beeld; ✓ als het al in beeld is', async () => {
    const { w } = await mountView()
    await w.find('[data-testid="lk-zoek"]').setValue('doc') // LI029 — lijst gated; toon a2 (Documentbeheer)
    await flushPromises()
    expect(w.find('[data-testid="lk-res-voegtoe-a2"]').exists()).toBe(true) // niet in set → + knop
    expect(w.find('[data-testid="lk-res-gekozen-a2"]').exists()).toBe(false)
    await w.find('[data-testid="lk-res-voegtoe-a2"]').trigger('click')
    await flushPromises()
    expect(w.vm.actieveSet.has('a2')).toBe(true) // toggleSet uitgevoerd
    expect(w.find('[data-testid="lk-res-voegtoe-a2"]').exists()).toBe(false) // in set → geen + knop
    expect(w.find('[data-testid="lk-res-gekozen-a2"]').exists()).toBe(true) // ✓
  })

  // ── LI029 — zoekresultaten inline onder de zoekbalk (alleen kaart-modus, bij zoek/filter) ────
  describe('LI029 — inline zoekresultaten (kaart-modus)', () => {
    it('kaart-modus + zoekterm → resultatenblok zichtbaar', async () => {
      const { w } = await mountView() // beginschermOpen=false (hele landschap)
      expect(w.find('[data-testid="lk-kaartzoek"]').exists()).toBe(false) // nog geen zoekterm/filter
      await w.find('[data-testid="lk-zoek"]').setValue('doc')
      await flushPromises()
      expect(w.find('[data-testid="lk-kaartzoek"]').exists()).toBe(true)
      expect(w.find('[data-testid="lk-res-naam-a2"]').exists()).toBe(true) // Documentbeheer
    })

    it('beginscherm open → blok NIET zichtbaar (beginscherm heeft eigen zoek)', async () => {
      const { w } = await mountView({ heleLandschap: false }) // beginschermOpen blijft true
      await w.find('[data-testid="lk-zoek"]').setValue('doc')
      await flushPromises()
      expect(w.find('[data-testid="lk-kaartzoek"]').exists()).toBe(false)
    })

    it('kaart-modus zonder zoekterm én zonder filter → blok NIET zichtbaar', async () => {
      const { w } = await mountView()
      expect(w.find('[data-testid="lk-kaartzoek"]').exists()).toBe(false)
    })

    it("B′ — een actief filter toont het blok óók zonder zoekterm", async () => {
      const { w } = await mountView()
      await w.find('[data-testid="lk-filter-leverancier-input"]').trigger('focus')
      await flushPromises()
      await w.find('[data-testid="lk-filter-leverancier-optie-l1"]').trigger('mousedown')
      await flushPromises()
      expect(w.find('[data-testid="lk-kaartzoek"]').exists()).toBe(true)
      expect(w.find('[data-testid="lk-res-naam-a1"]').exists()).toBe(true) // l1 → matcht
    })
  })

  // ADR-040 F1 stap 2a — de Impact-verkenner (drill-down over de koppelingsketen, `modus === 'impact'`,
  // impactDirect/drillPad/huidigeFocus) is AFGESCHAFT: de Praatplaat (concentric centraal op één centrum
  // + ego-kring) vervangt haar. De bijbehorende gedragstests (directe-impact-één-laag, drill-down-groeit,
  // impact-dubbelklik-drill, vier-relaties-impact, gebruikersgroep-drill, drill-reset, hoort-bij-in-keten)
  // zijn met de machinerie verwijderd; de praatplaat-equivalenten staan bij de weergave-/schakelaar-tests.

  it('ADR-033 — lijnen zijn standaard NEUTRAAL in elke weergave (geen blanket-oranje)', async () => {
    const neutraal = (w) => w.vm._edgeData({ bron_id: 'a1', doel_id: 'a2', ring: 'applicaties', label: 'koppeling' }, 0).lc
    const { w } = await mountView() // geheel
    expect(neutraal(w)).toBe('#94a3b8')
    await kies(w, 'a1') // praatplaat (ego)
    expect(w.vm.modus).toBe('ego')
    expect(neutraal(w)).toBe('#94a3b8')
    w.vm.toonOverzicht() // schakel naar overzicht (geen blanket-oranje in welke weergave dan ook)
    await flushPromises()
    expect(w.vm.modus).toBe('geheel')
    expect(neutraal(w)).toBe('#94a3b8')
    // Geen enkele edge gehighlight zolang er niets geselecteerd is.
    expect(w.vm.geselecteerdNodeId).toBe(null)
    expect(w.vm._edgeGehighlight({ bron_id: 'a1', doel_id: 'a2' })).toBe(false)
  })

  it('ADR-033 — enkelklik highlight ALLEEN de incidente lijnen; tweede klik verplaatst; deselectie = neutraal', async () => {
    // a1↔a2 (flow) en a2↔a3 (flow): a2 raakt beide, a1/a3 elk één.
    zetGraf({
      nodes: [
        { id: 'a1', naam: 'A1', element_type: 'applicatie', laag: 'application', lifecycle_status: 'concept', blokkades_open: 0 },
        { id: 'a2', naam: 'A2', element_type: 'applicatie', laag: 'application', lifecycle_status: 'concept', blokkades_open: 0 },
        { id: 'a3', naam: 'A3', element_type: 'applicatie', laag: 'application', lifecycle_status: 'concept', blokkades_open: 0 },
      ],
      edges: [
        { bron_id: 'a1', doel_id: 'a2', relatietype: 'flow', label: 'koppeling', ring: 'applicaties' },
        { bron_id: 'a2', doel_id: 'a3', relatietype: 'flow', label: 'koppeling', ring: 'applicaties' },
      ],
    })
    const e12 = { bron_id: 'a1', doel_id: 'a2' }
    const e23 = { bron_id: 'a2', doel_id: 'a3' }
    const { w } = await mountView() // geheel-model (lijnen neutraal, niets geselecteerd)
    expect(w.vm._edgeGehighlight(e12)).toBe(false)
    // Enkelklik a1 → alleen a1's lijn (a1↔a2) highlight; a2↔a3 niet. Detail gezet.
    w.vm.inspecteerNode('a1')
    await flushPromises()
    expect(w.vm.geselecteerdNodeId).toBe('a1')
    expect(w.vm._edgeGehighlight(e12)).toBe(true)
    expect(w.vm._edgeGehighlight(e23)).toBe(false)
    // Ander component klikken → highlight verspringt (a2 raakt beide lijnen).
    w.vm.inspecteerNode('a2')
    await flushPromises()
    expect(w.vm._edgeGehighlight(e12)).toBe(true)
    expect(w.vm._edgeGehighlight(e23)).toBe(true)
    // Deselectie (sluit popup / leeg canvas) → alles weer neutraal.
    w.vm.sluitPopup()
    await flushPromises()
    expect(w.vm.geselecteerdNodeId).toBe(null)
    expect(w.vm._edgeGehighlight(e12)).toBe(false)
  })

  it('ADR-033 — ego-view: dubbelklik hercentreert (enkelklik niet)', async () => {
    const { w } = await mountView()
    await kies(w, 'a1') // ego, centrum a1
    expect(w.vm.modus).toBe('ego')
    vi.useFakeTimers()
    // Enkelklik a2 → inspecteren (geen hercentrering: egoStartId blijft a1).
    w.vm.onNodeTap('a2')
    vi.advanceTimersByTime(300)
    await flushPromises()
    expect(w.vm.geselecteerdNodeId).toBe('a2')
    // Dubbelklik a2 → focus op a2 → ego hercentreert (a2 in de actieve set).
    w.vm.onNodeTap('a2'); w.vm.onNodeTap('a2')
    await flushPromises()
    expect([...w.vm.actieveSet]).toEqual(['a2'])
    vi.useRealTimers()
  })

  it('ADR-033 1c — de oude HTML-lijst-weergave van de verkenner is volledig weg', async () => {
    const { w } = await mountView()
    await kies(w, 'a1')
    await kies(w, 'a2') // impact
    for (const t of ['lk-impact-verkenner', 'lk-impact-keten', 'lk-impact-topbalk', 'lk-impact-node-a2', 'lk-impact-top-a1']) {
      expect(w.find(`[data-testid="${t}"]`).exists()).toBe(false)
    }
  })

  it('ADR-040 — praatplaat: graaf-knopen in de ego-kring tonen lifecycle-kleur + blokkade-indicatie', async () => {
    zetGraf({
      nodes: [
        { id: 'a1', naam: 'App', element_type: 'applicatie', laag: 'application', lifecycle_status: 'concept', blokkades_open: 0 },
        { id: 'geblok', naam: 'Geblokkeerd', element_type: 'applicatie', laag: 'application', lifecycle_status: 'geblokkeerd', blokkades_open: 2 },
      ],
      edges: [{ bron_id: 'a1', doel_id: 'geblok', relatietype: 'flow', label: 'koppeling', ring: 'applicaties' }],
    })
    const { w } = await mountView()
    await kies(w, 'a1') // praatplaat centraal op a1; geblok is de directe buur (ego-kring)
    expect(w.vm.modus).toBe('ego')
    expect(getekendeIds(w)).toContain('geblok')
    const data = w.vm._nodeData(w.vm.grafNodes.find((n) => n.id === 'geblok'))
    expect(data.bg).toBe('#fee2e2') // lifecycle-kleur (geblokkeerd) als achtergrond
    expect(data.label).toContain('⚠') // open blokkade-indicatie
  })

  it('ADR-033 — Geheel-model (lege set) toont de verbonden nodes; de actieve set blijft leeg', async () => {
    const { w } = await mountView() // lege set → geheel
    expect(w.vm.modus).toBe('geheel')
    // LI020 — losse nodes (p1/k1 zonder edges) zijn altijd verborgen; de 2 via de flow verbonden
    // applicaties blijven. De actieve set wordt NIET meer automatisch gevuld (ADR-033).
    expect(w.find('[data-testid="lk-zichtbaar-aantal"]').text()).toContain('2 in beeld')
    expect(w.find('[data-testid="lk-rechts"]').text()).toContain('Actieve set (0)')
  })

  it('ADR-033 — dubbelklik focust op die node alleen → Ego-view met die node als centrum', async () => {
    zetGraf({
      nodes: [
        { id: 'a1', naam: 'App', element_type: 'applicatie', laag: 'application', lifecycle_status: 'concept', blokkades_open: 0 },
        { id: 'p1', naam: 'Provincie', element_type: 'partij', laag: 'business', soort: 'ketenpartner' },
      ],
      edges: [{ bron_id: 'p1', doel_id: 'a1', relatietype: 'roltoewijzing', label: 'Contractbeheer', ring: 'rollen' }],
    })
    const { w } = await mountView() // geheel
    // Dubbelklik op de partij-node (twee taps binnen de drempel) → set = {p1} → praatplaat met partij centraal.
    w.vm.onNodeTap('p1'); w.vm.onNodeTap('p1')
    await flushPromises()
    expect(w.vm.weergave).toBe('praatplaat')
    expect(w.vm.modus).toBe('ego')
    expect([...w.vm.actieveSet]).toEqual(['p1'])
    // Detailpaneel toont de partij + zijn aard.
    expect(w.find('[data-testid="lk-detail-aard"]').exists()).toBe(true)
    expect(w.find('[data-testid="lk-detail-naam"]').text()).toBe('Provincie')
  })

  it('node-klik (resultaatrij) toont het detail-paneel', async () => {
    const { w } = await mountView()
    expect(w.find('[data-testid="lk-detail-leeg"]').exists()).toBe(true)
    await w.find('[data-testid="lk-zoek"]').setValue('doc') // LI029 — lijst gated; toon a2
    await flushPromises()
    await w.find('[data-testid="lk-res-naam-a2"]').trigger('click')
    await flushPromises()
    expect(w.find('[data-testid="lk-detail-naam"]').text()).toBe('Documentbeheer')
  })

  it('"Open component →" navigeert naar het component-detail', async () => {
    const { w, pushSpy } = await mountView()
    await w.find('[data-testid="lk-zoek"]').setValue('zaak') // LI029 — lijst gated; toon a1
    await flushPromises()
    await w.find('[data-testid="lk-res-naam-a1"]').trigger('click')
    await flushPromises()
    await w.find('[data-testid="lk-detail-open"]').trigger('click')
    expect(pushSpy).toHaveBeenCalledWith({ name: 'component-detail', params: { id: 'a1' } })
  })

  it('"Voeg alle gefilterde toe" vult de actieve set', async () => {
    const { w } = await mountView()
    await w.find('[data-testid="lk-zoek"]').setValue('e') // LI029 — lijst gated; 'e' matcht a1 + a2
    await flushPromises()
    await w.find('[data-testid="lk-voeg-alle"]').trigger('click')
    await flushPromises()
    // de twee gefilterde applicaties (a1, a2) worden toegevoegd.
    expect(w.find('[data-testid="lk-rechts"]').text()).toContain('Actieve set (2)')
  })

  it('Fix 3: klik op een actieve-set-item selecteert de node (detail-paneel)', async () => {
    const { w } = await mountView()
    await kies(w, 'a1') // a1 in de set (klik = toevoegen)
    await w.find('[data-testid="lk-set-a1"]').find('button').trigger('click') // klik het set-item (naam)
    await flushPromises()
    expect(w.find('[data-testid="lk-detail-naam"]').text()).toBe('Zaaksysteem')
  })

  it('ADR-040 — deep-link ?center=<id> zet de component als enige in de actieve set → Praatplaat', async () => {
    const { w } = await mountView({ query: '?center=a1' })
    expect(w.vm.weergave).toBe('praatplaat') // deep-link → praatplaat
    expect(w.vm.modus).toBe('ego')
    // de center-applicatie staat in de actieve set en is het detail.
    expect(w.find('[data-testid="lk-rechts"]').text()).toContain('Actieve set (1)')
    expect(w.find('[data-testid="lk-detail-naam"]').text()).toBe('Zaaksysteem')
  })

  it('ADR-040 — lk-state herstelt de actieve set; de weergave staat default op overzicht (adapter → geheel)', async () => {
    // Bewaarde state met alleen de actieve set + een achterhaalde `modus`-sleutel (moet genegeerd).
    sessionStorage.setItem('lk-state', JSON.stringify({ actieveSet: ['a1', 'a2'], modus: 'ego' }))
    const { w } = await mountView({ heleLandschap: false }) // herstel de set; geen auto-hele-landschap die 'm wist
    expect([...w.vm.actieveSet].sort()).toEqual(['a1', 'a2'])
    // De weergave wordt niet uit lk-state hersteld (default overzicht) → modus-adapter = 'geheel',
    // niet de dode `modus`-sleutel.
    expect(w.vm.weergave).toBe('overzicht')
    expect(w.vm.modus).toBe('geheel')
  })

  it('v4: de diepte-toggle staat in het filterpaneel (ego) en is default 1 stap', async () => {
    const { w } = await mountView()
    expect(w.find('[data-testid="lk-diepte"]').exists()).toBe(true)
    expect(w.find('[data-testid="lk-diepte-1"]').attributes('aria-pressed')).toBe('true')
    expect(w.find('[data-testid="lk-diepte-2"]').attributes('aria-pressed')).toBe('false')
  })

  it('v4: 2 stappen herlaadt de grafdata met ?diepte=2', async () => {
    const { w } = await mountView()
    expect(api.landschapskaart.haalGrafdata).toHaveBeenLastCalledWith({ diepte: 1 }) // mount
    await w.find('[data-testid="lk-diepte-2"]').trigger('click')
    await flushPromises()
    expect(api.landschapskaart.haalGrafdata).toHaveBeenLastCalledWith({ diepte: 2 })
    expect(w.find('[data-testid="lk-diepte-2"]').attributes('aria-pressed')).toBe('true')
  })

  it('v4: het detail-paneel toont de migratieplaatsing (plateau + dispositie) indien gevuld', async () => {
    const { w } = await mountView()
    await w.find('[data-testid="lk-zoek"]').setValue('doc') // LI029 — lijst gated; toon a2
    await flushPromises()
    await w.find('[data-testid="lk-res-naam-a2"]').trigger('click') // a2 zit op een plateau
    await flushPromises()
    const plateau = w.find('[data-testid="lk-detail-plateau"]')
    expect(plateau.exists()).toBe(true)
    expect(plateau.text()).toContain('Plateau 2026')
    expect(plateau.text()).toContain('Migreren')
    // a1 zit niet op een plateau → geen migratieplaatsing-regel.
    await w.find('[data-testid="lk-zoek"]').setValue('zaak') // toon a1
    await flushPromises()
    await w.find('[data-testid="lk-res-naam-a1"]').trigger('click')
    await flushPromises()
    expect(w.find('[data-testid="lk-detail-plateau"]').exists()).toBe(false)
  })

  it('toont het blokkade-icoon op een node met open blokkades', async () => {
    const { w } = await mountView()
    await w.find('[data-testid="lk-zoek"]').setValue('e') // LI029 — lijst gated; 'e' matcht a1 + a2
    await flushPromises()
    expect(w.find('[data-testid="lk-res-blok-a2"]').exists()).toBe(true)
    expect(w.find('[data-testid="lk-res-blok-a1"]').exists()).toBe(false)
  })

  // ── ADR-033 slice 2c/2d — opgeslagen & deelbare views (voorkant) ───────────────────
  const VIEW = (over = {}) => ({ id: 'v1', naam: 'Eigen', component_ids: ['a1'], gedeeld: false, maker_naam: 'Ik', is_eigenaar: true, ...over })

  it('ADR-033 2c — View opslaan stuurt naam + huidige actieve set; deel-toggle zet gedeeld', async () => {
    const { w } = await mountView() // medewerker, 0 views → geen startscherm
    await kies(w, 'a1') // actieve set {a1}
    expect(w.find('[data-testid="lk-view-opslaan"]').exists()).toBe(true)
    await w.find('[data-testid="lk-view-opslaan"]').trigger('click')
    expect(w.find('[data-testid="lk-view-dialog"]').exists()).toBe(true)
    await w.find('[data-testid="lk-view-naam"]').setValue('Mijn view')
    await w.find('[data-testid="lk-view-gedeeld-toggle"]').setValue(true)
    await w.find('[data-testid="lk-view-bewaar"]').trigger('click')
    await flushPromises()
    expect(api.impactViews.maak).toHaveBeenCalledWith({ naam: 'Mijn view', component_ids: ['a1'], gedeeld: true })
    expect(w.find('[data-testid="lk-view-dialog"]').exists()).toBe(false) // sluit na opslaan
  })

  it('ADR-033 2c — views-lijst toont eigen + gedeelde; herkomst + beheer alleen bij is_eigenaar', async () => {
    api.impactViews.lijst.mockResolvedValue([
      VIEW({ id: 'v1', naam: 'Eigen' }),
      VIEW({ id: 'v2', naam: 'Van collega', gedeeld: true, maker_naam: 'Jan', is_eigenaar: false }),
    ])
    const { w } = await mountView({ heleLandschap: false }) // beginscherm + startscherm-flow
    await w.find('[data-testid="lk-startscherm-hele-kaart"]').trigger('click') // sluit startscherm
    await flushPromises()
    expect(w.find('[data-testid="lk-view-open-v1"]').text()).toBe('Eigen')
    expect(w.find('[data-testid="lk-view-open-v2"]').text()).toBe('Van collega')
    expect(w.find('[data-testid="lk-view-gedeeld-v2"]').text()).toContain('gedeeld door Jan')
    expect(w.find('[data-testid="lk-view-gedeeld-v1"]').exists()).toBe(false) // eigen → geen herkomst
    expect(w.find('[data-testid="lk-view-bewerk-v1"]').exists()).toBe(true) // eigen → beheer
    expect(w.find('[data-testid="lk-view-verwijder-v1"]').exists()).toBe(true)
    expect(w.find('[data-testid="lk-view-bewerk-v2"]').exists()).toBe(false) // van ander → geen beheer
    expect(w.find('[data-testid="lk-view-verwijder-v2"]').exists()).toBe(false)
  })

  it('ADR-040 2c — een view openen zet de bewaarde selectie als actieve set → Overzicht', async () => {
    api.impactViews.lijst.mockResolvedValue([VIEW({ id: 'v1', naam: 'Twee', component_ids: ['a1', 'a2'] })])
    const { w } = await mountView({ heleLandschap: false })
    await w.find('[data-testid="lk-startscherm-open-v1"]').trigger('click')
    await flushPromises()
    expect([...w.vm.actieveSet].sort()).toEqual(['a1', 'a2'])
    expect(w.vm.weergave).toBe('overzicht') // een view openen = brede plaat → overzicht
    expect(w.vm.modus).toBe('geheel')
    expect(w.find('[data-testid="lk-startscherm"]').exists()).toBe(false) // startscherm dicht
  })

  it('ADR-033 2c — bewerken stuurt naam + gedeeld; selectie-bijwerken voegt de huidige set toe', async () => {
    api.impactViews.lijst.mockResolvedValue([VIEW({ id: 'v1', naam: 'Oud', component_ids: ['a1'] })])
    const { w } = await mountView({ heleLandschap: false })
    await w.find('[data-testid="lk-startscherm-hele-kaart"]').trigger('click')
    await flushPromises()
    await kies(w, 'a2') // actieve set {a2} (afwijkend van de view-selectie)
    await w.find('[data-testid="lk-view-bewerk-v1"]').trigger('click')
    await w.find('[data-testid="lk-view-naam"]').setValue('Nieuw')
    await w.find('[data-testid="lk-view-gedeeld-toggle"]').setValue(true)
    await w.find('[data-testid="lk-view-selectie-bijwerken"]').setValue(true)
    await w.find('[data-testid="lk-view-bewaar"]').trigger('click')
    await flushPromises()
    expect(api.impactViews.werkBij).toHaveBeenCalledWith('v1', { naam: 'Nieuw', gedeeld: true, component_ids: ['a2'] })
  })

  it('ADR-033 2c — een eigen view verwijderen roept de API en herlaadt de lijst', async () => {
    api.impactViews.lijst.mockResolvedValue([VIEW({ id: 'v1', naam: 'Weg' })])
    const { w } = await mountView({ heleLandschap: false })
    await w.find('[data-testid="lk-startscherm-hele-kaart"]').trigger('click')
    await flushPromises()
    await w.find('[data-testid="lk-view-verwijder-v1"]').trigger('click')
    await flushPromises()
    expect(api.impactViews.verwijder).toHaveBeenCalledWith('v1')
    expect(api.impactViews.lijst).toHaveBeenCalledTimes(2) // mount + na verwijderen
  })

  it('ADR-033 2c — een viewer ziet geen opslaan/beheer-affordances (alleen openen)', async () => {
    api.impactViews.lijst.mockResolvedValue([VIEW({ id: 'v1', naam: 'Eigen' })])
    const { w } = await mountView({ rollen: ['viewer'], heleLandschap: false })
    await w.find('[data-testid="lk-startscherm-hele-kaart"]').trigger('click')
    await flushPromises()
    await kies(w, 'a1') // actieve set
    expect(w.find('[data-testid="lk-view-opslaan"]').exists()).toBe(false) // geen opslaan
    expect(w.find('[data-testid="lk-view-bewerk-v1"]').exists()).toBe(false) // geen beheer
    expect(w.find('[data-testid="lk-view-verwijder-v1"]').exists()).toBe(false)
    expect(w.find('[data-testid="lk-view-open-v1"]').exists()).toBe(true) // openen mag wel
  })

  it('ADR-033 2c — 422 op opslaan toont een inline veldfout op de naam (dialog blijft open)', async () => {
    api.impactViews.maak.mockRejectedValue(Object.assign(new Error('x'), { status: 422, detail: [{ msg: 'naam mag maximaal 150 tekens zijn' }] }))
    const { w } = await mountView()
    await kies(w, 'a1')
    await w.find('[data-testid="lk-view-opslaan"]').trigger('click')
    await w.find('[data-testid="lk-view-naam"]').setValue('x')
    await w.find('[data-testid="lk-view-bewaar"]').trigger('click')
    await flushPromises()
    expect(w.find('[data-testid="lk-view-naam-fout"]').exists()).toBe(true)
    expect(w.find('[data-testid="lk-view-naam-fout"]').text()).toContain('150')
    expect(w.find('[data-testid="lk-view-dialog"]').exists()).toBe(true)
  })

  it('ADR-033 2c — 409 dubbele naam wordt afgevangen (geen crash, geen inline-veldfout)', async () => {
    api.impactViews.maak.mockRejectedValue(Object.assign(new Error('x'), { status: 409, code: 'VIEW_NAAM_BESTAAT_AL' }))
    const { w } = await mountView()
    await kies(w, 'a1')
    await w.find('[data-testid="lk-view-opslaan"]').trigger('click')
    await w.find('[data-testid="lk-view-naam"]').setValue('Bestaat al')
    await w.find('[data-testid="lk-view-bewaar"]').trigger('click')
    await flushPromises()
    expect(w.find('[data-testid="lk-view-dialog"]').exists()).toBe(true) // geen crash; dialog open
    expect(w.find('[data-testid="lk-view-naam-fout"]').exists()).toBe(false) // 409 → Toast, geen inline
  })

  it('ADR-033 2d — ≥1 view → startscherm met werkende "begin met de hele kaart"-escape', async () => {
    api.impactViews.lijst.mockResolvedValue([VIEW({ id: 'v1', naam: 'X' })])
    const { w } = await mountView({ heleLandschap: false })
    expect(w.find('[data-testid="lk-startscherm"]').exists()).toBe(true)
    await w.find('[data-testid="lk-startscherm-hele-kaart"]').trigger('click')
    await flushPromises()
    expect(w.find('[data-testid="lk-startscherm"]').exists()).toBe(false)
    expect(w.vm.modus).toBe('geheel')
    expect([...w.vm.actieveSet]).toEqual([])
  })

  it('ADR-033 2d — 0 opgeslagen views → geen startscherm (direct geheel-model)', async () => {
    const { w } = await mountView() // lijst → [] (default)
    expect(w.find('[data-testid="lk-startscherm"]').exists()).toBe(false)
    expect(w.vm.modus).toBe('geheel')
  })

  it('ADR-033 2d — geen startscherm bij een deep-link (?center heeft voorrang)', async () => {
    api.impactViews.lijst.mockResolvedValue([VIEW({ id: 'v1', naam: 'X' })])
    const { w } = await mountView({ query: '?center=a1' })
    expect(w.find('[data-testid="lk-startscherm"]').exists()).toBe(false) // expliciete ingang
    expect(w.vm.modus).toBe('ego')
  })

  // ── ADR-024 — context-ring "Organisatiestructuur" (persoon-met-rol → afdeling → organisatie) ──
  const _osGraf = () => ({
    nodes: [
      { id: 'org', naam: 'Org', element_type: 'partij', laag: 'business', soort: 'organisatie' },
      { id: 'afd', naam: 'Afd', element_type: 'partij', laag: 'business', soort: 'organisatie_eenheid' },
      { id: 'per', naam: 'Persoon', element_type: 'partij', laag: 'business', soort: 'persoon' },
      { id: 'app', naam: 'App', element_type: 'applicatie', laag: 'application', lifecycle_status: 'concept', blokkades_open: 0 },
    ],
    edges: [
      { bron_id: 'per', doel_id: 'afd', relatietype: 'hoort_bij', label: 'hoort bij', ring: 'organisatiestructuur' },
      { bron_id: 'afd', doel_id: 'org', relatietype: 'hoort_bij', label: 'hoort bij', ring: 'organisatiestructuur' },
    ],
  })

  it('ADR-024 — Organisatiestructuur-ring: eigen toggle, standaard UIT; edges verschijnen pas bij aan', async () => {
    zetGraf(_osGraf())
    const { w } = await mountView()
    // Eigen ring-toggle aanwezig.
    expect(w.find('[data-testid="lk-ring-organisatiestructuur"]').exists()).toBe(true)
    // Standaard UIT → geen hoort-bij-edge zichtbaar.
    expect(w.vm.zichtbareEdges.some((e) => e.ring === 'organisatiestructuur')).toBe(false)
    // Aanzetten → beide hoort-bij-edges verschijnen.
    await w.find('[data-testid="lk-ring-organisatiestructuur"]').trigger('change')
    await flushPromises()
    expect(w.vm.zichtbareEdges.filter((e) => e.ring === 'organisatiestructuur')).toHaveLength(2)
  })

  it('ADR-024 — hoort-bij-edge is bereikbaar via de bestaande edge-popup', async () => {
    zetGraf(_osGraf())
    const { w } = await mountView()
    await w.find('[data-testid="lk-ring-organisatiestructuur"]').trigger('change')
    await flushPromises()
    w.vm.openEdgePopup({ bron_id: 'per', doel_id: 'afd', ring: 'organisatiestructuur', label: 'hoort bij' })
    await flushPromises()
    expect(w.vm.popupOpen).toBe(true) // popup opent zonder API-call (niet-flow ring)
  })

  // ── Toestand-geschiedenis (browser-model: terug/vooruit met cursor) ──
  it('geschiedenis — een wijziging pusht; terug herstelt de vorige; vooruit herstelt weer', async () => {
    const { w } = await mountView() // t0 = begintoestand (cursor 0)
    expect(w.vm.cursor).toBe(0)
    expect(w.vm.kanTerug).toBe(false)
    expect(w.vm.ringAan.has('contracten')).toBe(true) // standaard aan
    // Ring-toggle = een nieuwe toestand.
    await w.find('[data-testid="lk-ring-contracten"]').trigger('change')
    await flushPromises()
    expect(w.vm.cursor).toBe(1)
    expect(w.vm.ringAan.has('contracten')).toBe(false)
    // Terug → de vorige toestand (contracten weer aan).
    await w.find('[data-testid="lk-hist-terug"]').trigger('click')
    await flushPromises()
    expect(w.vm.cursor).toBe(0)
    expect(w.vm.ringAan.has('contracten')).toBe(true)
    // Vooruit → weer naar de gewijzigde toestand.
    await w.find('[data-testid="lk-hist-vooruit"]').trigger('click')
    await flushPromises()
    expect(w.vm.cursor).toBe(1)
    expect(w.vm.ringAan.has('contracten')).toBe(false)
  })

  it('geschiedenis — nieuwe wijziging vanaf een teruggehaalde toestand knipt de vooruit-tak af', async () => {
    const { w } = await mountView()
    await w.find('[data-testid="lk-ring-contracten"]').trigger('change') // t1
    await flushPromises()
    await w.find('[data-testid="lk-ring-infrastructuur"]').trigger('change') // t2
    await flushPromises()
    expect(w.vm.historie.length).toBe(3)
    // Terug naar t1 → er is een vooruit-tak (t2).
    await w.find('[data-testid="lk-hist-terug"]').trigger('click')
    await flushPromises()
    expect(w.vm.cursor).toBe(1)
    expect(w.vm.kanVooruit).toBe(true)
    // Nieuwe wijziging vanaf t1 → knipt t2 af en begint een nieuw pad.
    await w.find('[data-testid="lk-ring-gebruikers"]').trigger('change')
    await flushPromises()
    expect(w.vm.historie.length).toBe(3) // t0, t1, t2' (oude t2 vervangen)
    expect(w.vm.cursor).toBe(2)
    expect(w.vm.kanVooruit).toBe(false) // vooruit-tak afgeknipt
  })

  it('geschiedenis — knoppen disabled aan de randen', async () => {
    const { w } = await mountView()
    expect(w.find('[data-testid="lk-hist-terug"]').attributes('disabled')).toBeDefined()
    expect(w.find('[data-testid="lk-hist-vooruit"]').attributes('disabled')).toBeDefined()
    // De in-kaart-terug is een eigen actie (aria-label), niet "Terug naar Landschapskaart".
    expect(w.find('[data-testid="lk-hist-terug"]').attributes('aria-label')).toBe('Vorige kaarttoestand')
    await w.find('[data-testid="lk-ring-contracten"]').trigger('change')
    await flushPromises()
    expect(w.find('[data-testid="lk-hist-terug"]').attributes('disabled')).toBeUndefined() // terug kan
    expect(w.find('[data-testid="lk-hist-vooruit"]').attributes('disabled')).toBeDefined()  // geen vooruit
  })

  it('geschiedenis — een kijkhoek-wijziging (fullscreen, net als zoom/pan) pusht GEEN toestand', async () => {
    const { w } = await mountView()
    const n = w.vm.historie.length
    // Fullscreen/zoom/pan zitten bewust NIET in de toestand-signatuur → geen nieuwe entry.
    w.vm.toggleFullscreen()
    await flushPromises()
    expect(w.vm.historie.length).toBe(n)
    expect(w.vm.cursor).toBe(n - 1)
  })

  // ── Hang-fix: herstel zonder thrash + history begrenzen + filter-guard ──
  // Opname-cy: registreert layout-`animate` + viewport-ops, en vuurt de layout-`stop` (_naLayout)
  // synchroon — zo is het centreren-via-stop testbaar. `mockImplementationOnce` → de mount krijgt
  // deze cy, daarna valt cytoscape terug op de default-mock (geen lek naar andere tests).
  const _opnameCy = (rec) => () => {
    const cy = {
      on: vi.fn(), elements: () => ({ remove: vi.fn(), unselect: vi.fn() }),
      nodes: () => ({ removeClass: vi.fn(), forEach: () => {}, map: () => [], length: 0 }), edges: () => ({ removeClass: vi.fn() }),
      getElementById: () => ({ length: 0, select: vi.fn() }),
      animate: vi.fn(), zoom: () => 1, pan: () => ({ x: 0, y: 0 }), add: vi.fn(),
      layout: (opts) => ({ run: () => { rec.anim.push(opts && opts.animate); if (opts && opts.stop) opts.stop() } }),
      resize: vi.fn(), fit: () => { rec.viewport++ }, center: () => { rec.viewport++ }, destroy: vi.fn(),
    }
    return cy
  }

  it('hang-fix — terug tekent ZONDER layout-animatie en centreert via de layout-stop; geen nieuwe entry', async () => {
    const rec = { anim: [], viewport: 0 }
    cytoscape.mockImplementationOnce(_opnameCy(rec))
    const { w } = await mountView()
    await w.find('[data-testid="lk-ring-contracten"]').trigger('change') // t1 (echte wijziging)
    await flushPromises()
    const len = w.vm.historie.length, cur = w.vm.cursor
    rec.anim.length = 0; rec.viewport = 0
    await w.find('[data-testid="lk-hist-terug"]').trigger('click')
    await flushPromises()
    expect(rec.anim.length).toBeGreaterThan(0)             // er werd (her)getekend
    expect(rec.anim.every((a) => a === false)).toBe(true)  // maar ZONDER animatie (anti-thrash)
    expect(rec.viewport).toBeGreaterThan(0)                // centreren liep via de layout-stop (_naLayout)
    expect(w.vm.historie.length).toBe(len)                 // herstel pusht GEEN entry
    expect(w.vm.cursor).toBe(cur - 1)                      // cursor enkel door de navigatie
  })

  it('hang-fix — een herstel zonder zichtbare-graaf-wijziging tekent NIET opnieuw (geen relayout)', async () => {
    const rec = { anim: [], viewport: 0 }
    cytoscape.mockImplementationOnce(_opnameCy(rec))
    const { w } = await mountView()
    w.vm.inspecteerNode('a1'); await flushPromises() // push: enkel geselecteerdNodeId (geen teken-dep)
    rec.anim.length = 0
    await w.find('[data-testid="lk-hist-terug"]').trigger('click'); await flushPromises()
    expect(rec.anim.length).toBe(0)            // selectie-only herstel → géén relayout
    expect(w.vm.geselecteerdNodeId).toBe(null) // herstel klopt wél (sel terug naar begin)
  })

  it('hang-fix — history begrensd op ~50 (oudste eruit), cursor consistent, terug/vooruit binnen venster', async () => {
    const { w } = await mountView()
    for (let i = 0; i < 60; i++) {
      await w.find('[data-testid="lk-ring-contracten"]').trigger('change'); await flushPromises()
    }
    expect(w.vm.historie.length).toBeLessThanOrEqual(50)
    expect(w.vm.cursor).toBe(w.vm.historie.length - 1)
    const top = w.vm.cursor
    w.vm.terugInHistorie(); await flushPromises()
    expect(w.vm.cursor).toBe(top - 1)
    w.vm.vooruitInHistorie(); await flushPromises()
    expect(w.vm.cursor).toBe(top)
  })

  it('hang-fix — herstel opent GEEN ego-filterdialog (filter-watch afgeschermd)', async () => {
    const { w } = await mountView()
    await kies(w, 'a1') // ego, centrum a1 (applicatie)
    expect(w.vm.modus).toBe('ego')
    // Filter die het centrum verbergt → de dialog hoort bij een NORMALE wijziging te openen.
    await w.find('[data-testid="lk-filter-type-input"]').trigger('focus')
    await w.find('[data-testid="lk-filter-type-optie-database"]').trigger('mousedown')
    await flushPromises()
    expect(w.find('[data-testid="lk-ego-filter-dialog"]').exists()).toBe(true)
    await w.find('[data-testid="lk-ego-filter-doorgaan"]').trigger('click') // bevestig + sluit
    await flushPromises()
    expect(w.find('[data-testid="lk-ego-filter-dialog"]').exists()).toBe(false)
    // terug (filter eraf) → vooruit (filter weer aan = herstel dat a1 verbergt). De guard houdt
    // de dialog tijdens herstel dicht.
    await w.find('[data-testid="lk-hist-terug"]').trigger('click'); await flushPromises()
    await w.find('[data-testid="lk-hist-vooruit"]').trigger('click'); await flushPromises()
    expect(w.find('[data-testid="lk-ego-filter-dialog"]').exists()).toBe(false)
  })

  // ── Vorm per node-type (kleur blijft status) + uitklapbare legenda ──
  // Replica van de luminantie-keuze in _txtColor (zwart/wit op basis van de werkelijke vulkleur).
  const _lumKeuze = (bg) => {
    const h = String(bg || '').replace('#', '')
    if (h.length !== 6) return '#1a1a2e'
    const r = parseInt(h.slice(0, 2), 16), g = parseInt(h.slice(2, 4), 16), b = parseInt(h.slice(4, 6), 16)
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255 < 0.55 ? '#ffffff' : '#1a1a2e'
  }

  it('vorm-per-type — elk van de negen typen krijgt z\'n eigen native vorm via de gedeelde bron', async () => {
    const { w } = await mountView()
    const vorm = (n) => w.vm._nodeData(n).shape
    const m = {
      component: vorm({ id: 'c', element_type: 'applicatie', laag: 'application' }),
      infra: vorm({ id: 'i', element_type: 'database', laag: 'technology' }),
      contract: vorm({ id: 'k', element_type: 'contract', laag: 'business' }),
      persoon: vorm({ id: 'p', element_type: 'partij', soort: 'persoon' }),
      groep: vorm({ id: 'g', element_type: 'gebruikersgroep' }),
      organisatie: vorm({ id: 'o', element_type: 'partij', soort: 'organisatie' }),
      afdeling: vorm({ id: 'a', element_type: 'partij', soort: 'organisatie_eenheid' }),
      leverancier: vorm({ id: 'l', element_type: 'partij', soort: 'externe_partij' }),
    }
    expect(m).toEqual({
      component: 'round-rectangle', infra: 'barrel', contract: 'tag', persoon: 'ellipse',
      groep: 'octagon', organisatie: 'hexagon', afdeling: 'cut-rectangle',
      leverancier: 'rhomboid',
    })
    expect(new Set(Object.values(m)).size).toBe(8) // acht verschillende silhouetten (ADR-038 — burger weg)
    // de bijna-dubbele paren zijn echt verschillend
    expect(m.leverancier).not.toBe(m.contract)
    expect(m.afdeling).not.toBe(m.organisatie)
  })

  it('vorm-per-type — type-label verschijnt voor ALLE typen (tweede signaal naast de vorm)', async () => {
    const { w } = await mountView()
    const lbl = (n) => w.vm._nodeData(n).label
    expect(lbl({ element_type: 'partij', soort: 'persoon', naam: 'Jan' })).toContain('Persoon')
    expect(lbl({ element_type: 'partij', soort: 'organisatie_eenheid', naam: 'Afd' })).toContain('Afdeling')
    expect(lbl({ element_type: 'partij', soort: 'organisatie', naam: 'Org' })).toContain('Organisatie')
    expect(lbl({ element_type: 'partij', soort: 'externe_partij', naam: 'Lev' })).toContain('Leverancier')
    expect(lbl({ element_type: 'contract', naam: 'K' })).toContain('Contract')
    expect(lbl({ element_type: 'gebruikersgroep', naam: 'G', aantal_leden: 5 })).toContain('Gebruikersgroep')
    expect(lbl({ element_type: 'database', laag: 'technology', naam: 'DB' })).toContain('Infrastructuur')
    expect(lbl({ element_type: 'applicatie', laag: 'application', naam: 'App' })).toContain('Applicatie')
  })

  it('vorm-per-type — tekstkleur volgt ALTIJD de luminantie van de vulkleur (vorm × status)', async () => {
    const { w } = await mountView()
    const vormen = [
      { element_type: 'applicatie', laag: 'application' }, { element_type: 'database', laag: 'technology' },
      { element_type: 'contract' }, { element_type: 'partij', soort: 'persoon' },
      { element_type: 'gebruikersgroep' }, { element_type: 'partij', soort: 'organisatie' },
      { element_type: 'partij', soort: 'organisatie_eenheid' }, { element_type: 'partij', soort: 'externe_partij' },
    ]
    const statussen = ['migratieklaar', 'geblokkeerd', 'in_inventarisatie', 'concept', undefined]
    for (const v of vormen) {
      for (const s of statussen) {
        const d = w.vm._nodeData({ ...v, lifecycle_status: s, naam: 'X' })
        expect(d.txt).toBe(_lumKeuze(d.bg))           // exact de luminantie-keuze, niet vast per vorm
        expect(['#ffffff', '#1a1a2e']).toContain(d.txt) // leesbaar zwart óf wit, nooit iets anders
      }
    }
  })

  it('vorm-per-type — legenda uitklapbaar (standaard ingeklapt), twee secties, onthoudt voorkeur', async () => {
    let w = (await mountView()).w
    // Standaard ingeklapt → alleen de knop.
    expect(w.find('[data-testid="lk-legenda-toggle"]').exists()).toBe(true)
    expect(w.find('[data-testid="lk-legenda-paneel"]').exists()).toBe(false)
    await w.find('[data-testid="lk-legenda-toggle"]').trigger('click')
    await flushPromises()
    expect(w.find('[data-testid="lk-legenda-paneel"]').exists()).toBe(true)
    expect(w.find('[data-testid="lk-legenda-vorm"]').exists()).toBe(true)
    expect(w.find('[data-testid="lk-legenda-status"]').exists()).toBe(true)
    const vormtekst = w.find('[data-testid="lk-legenda-vorm"]').text()
    for (const t of ['Component', 'Infrastructuur', 'Contract', 'Persoon', 'Gebruikersgroep', 'Organisatie', 'Afdeling', 'Leverancier']) {
      expect(vormtekst).toContain(t)
    }
    // Voorkeur onthouden (sessionStorage): een nieuwe mount opent meteen uitgeklapt.
    w = (await mountView()).w
    expect(w.find('[data-testid="lk-legenda-paneel"]').exists()).toBe(true)
  })

  // ── "Organisaties in beeld"-balk (LI053) — bestuurt UITSLUITEND de organisatie-overlay ──
  // Org-nodes + hun (org-gebonden) gebruikersgroepen; componenten worden nooit geraakt.
  const _scopeGraf = () => ({
    nodes: [
      { id: 'oA', naam: 'Org A', element_type: 'partij', laag: 'business', soort: 'organisatie', blokkades_open: 0 },
      { id: 'oB', naam: 'Org B', element_type: 'partij', laag: 'business', soort: 'organisatie', blokkades_open: 0 },
      { id: 'appA', naam: 'App A', element_type: 'applicatie', laag: 'application', lifecycle_status: 'concept', blokkades_open: 0, eigenaar_organisatie_id: 'oA' },
      { id: 'appB', naam: 'App B', element_type: 'applicatie', laag: 'application', lifecycle_status: 'concept', blokkades_open: 0, eigenaar_organisatie_id: 'oB' },
      { id: 'ggA', naam: 'Groep A', element_type: 'gebruikersgroep', laag: 'business', organisatie_id: 'oA', aantal_leden: 5, blokkades_open: 0 },
      { id: 'ggLoos', naam: 'Burgers', element_type: 'gebruikersgroep', laag: 'business', organisatie_id: null, aantal_leden: 9, blokkades_open: 0 },
    ],
    edges: [
      { bron_id: 'appA', doel_id: 'ggA', relatietype: 'serving', label: 'gebruikt door', ring: 'gebruikers' },
      { bron_id: 'appB', doel_id: 'ggLoos', relatietype: 'serving', label: 'gebruikt door', ring: 'gebruikers' },
    ],
  })
  // Rauwe node-zichtbaarheid (groepeerPerOrg uit → individuele gg-nodes toetsbaar, geen aggregatie).
  const _zichtbaar = (w) => w.vm.zichtbareNodes.map((n) => n.id).sort()
  async function _mountScope() {
    zetGraf(_scopeGraf())
    const { w } = await mountView()
    w.vm.groepeerPerOrg = false
    await flushPromises()
    return { w }
  }

  it('LI053 — alle organisaties standaard AAN + label "Organisaties in beeld"', async () => {
    const { w } = await _mountScope()
    expect(w.find('[data-testid="lk-scope-org-oA"]').exists()).toBe(true)
    expect(w.find('[data-testid="lk-scope-org-oB"]').exists()).toBe(true)
    expect([...w.vm.scopeOrgs].sort()).toEqual(['oA', 'oB']) // default alle aan
    // Hernoemd label; geen zichtbare "Scope"-tekst meer, geen Biedt/Gebruikt-schakelaar.
    expect(w.find('[data-testid="lk-scopebalk"]').text()).toContain('Organisaties in beeld')
    expect(w.find('[data-testid="lk-scopebalk"]').text()).not.toMatch(/Scope/)
    expect(w.find('[data-testid="lk-scope-biedt"]').exists()).toBe(false)
    expect(w.find('[data-testid="lk-scope-gebruikt"]').exists()).toBe(false)
  })

  it('LI053 — organisatie uitvinken verbergt de org-node én haar gebruikersgroepen; componenten blijven', async () => {
    const { w } = await _mountScope()
    expect(_zichtbaar(w)).toEqual(['appA', 'appB', 'ggA', 'ggLoos', 'oA', 'oB'])
    await w.find('[data-testid="lk-scope-org-oA"]').trigger('change') // oA uit
    await flushPromises()
    // oA-node + ggA (org=oA) weg; appA/appB blijven (componenten nooit gescoopt); oB + ggLoos blijven.
    expect(_zichtbaar(w)).toEqual(['appA', 'appB', 'ggLoos', 'oB'])
  })

  it('LI053 — organisatieloze groep volgt de Gebruikers-ring, niet de organisatie-vinkjes; alles-uit = componentenlaag', async () => {
    const { w } = await _mountScope()
    await w.find('[data-testid="lk-scope-org-oA"]').trigger('change')
    await w.find('[data-testid="lk-scope-org-oB"]').trigger('change')
    await flushPromises()
    expect([...w.vm.scopeOrgs]).toEqual([]) // alles uit
    const zichtbaar = _zichtbaar(w)
    expect(zichtbaar).toEqual(['appA', 'appB', 'ggLoos']) // enkel componenten + de org-loze groep
    expect(zichtbaar).not.toContain('oA')
    expect(zichtbaar).not.toContain('oB')
    expect(zichtbaar).not.toContain('ggA') // org-gebonden groep verdwijnt met zijn organisatie
  })

  it('LI053 — een scope-wijziging pusht een toestand in de terug/vooruit-geschiedenis en herstelt', async () => {
    zetGraf(_scopeGraf())
    const { w } = await mountView()
    const cur = w.vm.cursor
    await w.find('[data-testid="lk-scope-org-oB"]').trigger('change') // oB uit
    await flushPromises()
    expect(w.vm.cursor).toBe(cur + 1) // betekenisvolle wijziging → nieuwe toestand
    expect([...w.vm.scopeOrgs].sort()).toEqual(['oA'])
    await w.find('[data-testid="lk-hist-terug"]').trigger('click') // terug herstelt de scope
    await flushPromises()
    expect([...w.vm.scopeOrgs].sort()).toEqual(['oA', 'oB'])
  })

  it('LI053 — history-restore laadt zowel oud-format (mét vervallen scopeModus) als nieuw-format (zonder)', async () => {
    zetGraf(_scopeGraf())
    const { w } = await mountView()
    const base = { ...w.vm.historie[w.vm.cursor] } // een geldige, volledige toestand als basis
    // index 0 = oud-format snapshot met het vervallen veld; index 1 = nieuw-format zonder.
    const oud = Object.freeze({ ...base, scopeOrgs: ['oA'], scopeModus: 'gebruikt' })
    const nieuw = Object.freeze({ ...base, scopeOrgs: ['oB'] })
    w.vm.historie = [oud, nieuw]
    w.vm.cursor = 1
    await flushPromises()
    // Terug naar het oude formaat → laadt schoon, het overtollige scopeModus-veld wordt genegeerd.
    await w.find('[data-testid="lk-hist-terug"]').trigger('click')
    await flushPromises()
    expect([...w.vm.scopeOrgs].sort()).toEqual(['oA'])
    expect(w.vm.scopeModus).toBeUndefined() // symbool bestaat niet meer op de component
    // Vooruit naar het nieuwe formaat → óók schoon.
    await w.find('[data-testid="lk-hist-vooruit"]').trigger('click')
    await flushPromises()
    expect([...w.vm.scopeOrgs].sort()).toEqual(['oB'])
  })

  it('scope — organisatie is als vertrekpunt selecteerbaar in de lijst', async () => {
    zetGraf(_scopeGraf())
    const { w } = await mountView()
    await w.find('[data-testid="lk-zoek"]').setValue('org a') // LI029 — lijst gated; toon oA
    await flushPromises()
    expect(w.find('[data-testid="lk-res-naam-oA"]').exists()).toBe(true) // org in de zoeklijst
    await kies(w, 'oA')
    expect(w.vm.actieveSet.has('oA')).toBe(true) // als vertrekpunt gekozen
  })

  // ── Fase B (LI022) slice 1 — set-gestuurd laadpad (alleen de bedrading; de verkenmechaniek
  //    op een subgraaf is bewust nog niet ontworpen — zie OPVOLGPUNTEN). ─────────────────────────
  describe('Fase B — set-gestuurd laadpad', () => {
    it('lege set + geen hele-landschap → geen fetch; beginscherm-placeholder zichtbaar', async () => {
      const { w } = await mountView({ heleLandschap: false })
      expect(api.landschapskaart.haalGrafdata).not.toHaveBeenCalled()
      expect(api.landschapskaart.subgraaf).not.toHaveBeenCalled()
      expect(w.vm.beginscherm).toBe(true)
      expect(w.find('[data-testid="lk-beginscherm"]').exists()).toBe(true)
      expect(w.find('[data-testid="lk-toon-hele-landschap"]').exists()).toBe(true)
      expect(w.vm.grafNodes.length).toBe(0)
    })

    it('niet-lege set → subgraaf met de set; nodes vervangen; toggleSet is weergave-neutraal', async () => {
      const { w } = await mountView({ heleLandschap: false })
      w.vm.toggleSet('a1')
      await flushPromises()
      expect(api.landschapskaart.subgraaf).toHaveBeenCalledWith(['a1'], 1)
      expect(api.landschapskaart.haalGrafdata).not.toHaveBeenCalled()
      expect(w.vm.beginscherm).toBe(false)
      // toggleSet bouwt de set maar zet geen praatplaat (weergave blijft overzicht → adapter 'geheel');
      // wél wordt het centrum gezet (single-set), zodat de Praatplaat-knop beschikbaar wordt.
      expect(w.vm.weergave).toBe('overzicht')
      expect(w.vm.modus).toBe('geheel')
      expect(w.vm.kanPraatplaat).toBe(true)
      expect(w.vm.grafNodes.length).toBe(5) // subgraaf-respons (mock = volledige _graf)
    })

    it('set-mutatie → herfetch met de volledige bijgewerkte set (hele set opnieuw)', async () => {
      const { w } = await mountView({ heleLandschap: false })
      w.vm.toggleSet('a1')
      await flushPromises()
      expect(api.landschapskaart.subgraaf).toHaveBeenLastCalledWith(['a1'], 1)
      w.vm.toggleSet('a2')
      await flushPromises()
      expect(api.landschapskaart.subgraaf).toHaveBeenLastCalledWith(['a1', 'a2'], 1)
      expect(w.vm.modus).toBe('geheel') // toggleSet weergave-neutraal → overzicht
    })

    it('"toon hele landschap" → full-graph-fetch én de set wordt geleegd', async () => {
      const { w } = await mountView({ heleLandschap: false })
      w.vm.toggleSet('a1')
      await flushPromises()
      w.vm.toonHeleLandschap()
      await flushPromises()
      expect(api.landschapskaart.haalGrafdata).toHaveBeenCalledWith({ diepte: 1 })
      expect([...w.vm.actieveSet]).toEqual([])
      expect(w.vm.heleLandschap).toBe(true)
      expect(w.vm.modus).toBe('geheel')
      expect(w.vm.beginscherm).toBe(false)
    })

    it('"begin opnieuw" (wisSet) → set leeg, hele-landschap-vlag uit, data weg, placeholder terug', async () => {
      const { w } = await mountView() // start gevuld in de hele-landschap-modus
      expect(w.vm.heleLandschap).toBe(true)
      expect(w.vm.grafNodes.length).toBeGreaterThan(0)
      w.vm.wisSet()
      await flushPromises()
      expect([...w.vm.actieveSet]).toEqual([])
      expect(w.vm.heleLandschap).toBe(false)
      expect(w.vm.beginscherm).toBe(true)
      expect(w.vm.grafNodes.length).toBe(0)
      expect(w.find('[data-testid="lk-beginscherm"]').exists()).toBe(true)
    })

    it('voortgangsteller is leeg ná het laden van het hele landschap (geen blijvende spinner)', async () => {
      const { w } = await mountView({ heleLandschap: false })
      w.vm.toonHeleLandschap()
      await flushPromises()
      expect(w.vm.tekenVoortgang).toBe(null)
      expect(w.vm.grafNodes.length).toBe(5)
    })

    it('zoek errort niet zonder geladen graaf (beginscherm) — geen resultaten, geen crash', async () => {
      const { w } = await mountView({ heleLandschap: false })
      await w.find('[data-testid="lk-zoek"]').setValue('zaak')
      await flushPromises()
      expect(w.vm.beginscherm).toBe(true)
      expect(w.findAll('[data-testid^="lk-res-naam-"]').length).toBe(0)
    })
  })

  // ── Fase B (LI023) slice 2b — "in beeld"-chips: tweede set-bewerkingsplek naast de context-routes,
  //    zichtbaar zodra de set ≥1 is (ego/impact), buiten het beginscherm. ─────────────────────────
  describe('Fase B — in-beeld-chips', () => {
    it('set ≥ 1 → chips zichtbaar (één per component)', async () => {
      const { w } = await mountView({ heleLandschap: false })
      w.vm.toggleSet('a1')
      await flushPromises()
      expect(w.find('[data-testid="lk-chips"]').exists()).toBe(true)
      expect(w.find('[data-testid="lk-chip-a1"]').exists()).toBe(true)
    })

    it('× op een chip verwijdert het component uit de set', async () => {
      const { w } = await mountView({ heleLandschap: false })
      w.vm.toggleSet('a1')
      await flushPromises()
      expect([...w.vm.actieveSet]).toEqual(['a1'])
      await w.find('[data-testid="lk-chip-verwijder-a1"]').trigger('click')
      await flushPromises()
      expect([...w.vm.actieveSet]).toEqual([])
    })

    it('lege set → geen chips', async () => {
      const { w } = await mountView() // hele-landschap, set leeg
      expect(w.vm.actieveSet.size).toBe(0)
      expect(w.find('[data-testid="lk-chips"]').exists()).toBe(false)
    })
  })

  // ── Fase B (LI023) slice 2b-v2 — beginscherm expliciet sluiten i.p.v. aan de set-grootte gekoppeld ──
  describe('Fase B — beginscherm expliciet sluiten', () => {
    it('"Toon op de kaart" sluit het beginscherm en toont de graaf (set blijft gevuld)', async () => {
      const { w } = await mountView({ heleLandschap: false })
      expect(w.vm.beginschermOpen).toBe(true)
      w.vm.toggleSet('a1') // bouw een set op terwijl het beginscherm open blijft (kern van v2)
      await flushPromises()
      expect(w.find('[data-testid="lk-beginscherm"]').exists()).toBe(true)
      await w.find('[data-testid="toon-op-kaart-knop"]').trigger('click') // @sluit
      await flushPromises()
      expect(w.vm.beginschermOpen).toBe(false)
      expect(w.find('[data-testid="lk-beginscherm"]').exists()).toBe(false)
      expect([...w.vm.actieveSet]).toEqual(['a1'])
      expect(w.vm.grafNodes.length).toBeGreaterThan(0)
    })

    it('"Begin opnieuw" (wisSet) heropent het beginscherm', async () => {
      const { w } = await mountView() // hele-landschap → beginschermOpen=false
      expect(w.vm.beginschermOpen).toBe(false)
      w.vm.wisSet()
      await flushPromises()
      expect(w.vm.beginschermOpen).toBe(true)
      expect(w.find('[data-testid="lk-beginscherm"]').exists()).toBe(true)
    })

    // LI052 — "Begin opnieuw" is altijd zichtbaar (ook op het beginscherm) én verst de zoek-picker:
    // na reset is niets meer aangevinkt en is elk component weer toevoegbaar (het disabled-euvel weg).
    it('LI052 — "Begin opnieuw" altijd zichtbaar en reset leegt de zoek-picker', async () => {
      api.componenten.lijst.mockResolvedValue({ items: [{ id: 'a1', naam: 'Zaaksysteem' }] })
      const { w } = await mountView({ heleLandschap: false }) // beginscherm open
      // Altijd-zichtbaar: de reset-knop staat er ook op het lege beginscherm.
      expect(w.find('[data-testid="lk-begin-opnieuw"]').exists()).toBe(true)
      // Kies Zaaksysteem via de beginscherm-picker → aangevinkt + in de set. `zoek()` direct aanroepen
      // op de child omzeilt de 300ms-debounce (zoals de KaartBeginscherm-tests).
      await w.find('[data-testid="kb-zoek"]').setValue('zaak')
      await w.findComponent(KaartBeginscherm).vm.zoek()
      await flushPromises()
      await w.find('[data-testid="kb-res-check-a1"]').trigger('change')
      await flushPromises()
      expect([...w.vm.actieveSet]).toContain('a1')
      // Begin opnieuw → set leeg + verse picker (remount via :key).
      await w.find('[data-testid="lk-begin-opnieuw"]').trigger('click')
      await flushPromises()
      expect([...w.vm.actieveSet]).toEqual([])
      // Opnieuw zoeken toont Zaaksysteem NIET aangevinkt en WEL toevoegbaar (buffer geleegd).
      await w.find('[data-testid="kb-zoek"]').setValue('zaak')
      await w.findComponent(KaartBeginscherm).vm.zoek()
      await flushPromises()
      const check = w.find('[data-testid="kb-res-check-a1"]')
      expect(check.exists()).toBe(true)
      expect(check.element.checked).toBe(false)
      expect(check.attributes('disabled')).toBeUndefined()
    })
  })

  // ── Slice 5 (LI023) — set-acties in het node-detail-paneel ──────────────────────────────────
  describe('slice 5 — set-acties in detail-paneel', () => {
    // Context-node-graaf: contract k1 ↔ component a1 (association/contracten).
    const CONTEXTGRAF = () => ({
      nodes: [
        { id: 'a1', naam: 'Zaaksysteem', element_type: 'applicatie', laag: 'application', blokkades_open: 0 },
        { id: 'k1', naam: 'Contract X', element_type: 'contract', laag: 'business', blokkades_open: 0 },
      ],
      edges: [{ bron_id: 'a1', doel_id: 'k1', relatietype: 'association', ring: 'contracten', label: 'valt onder' }],
    })

    it('toont "Haal buren erbij"-knop bij een component-node', async () => {
      const { w } = await mountView()
      w.vm.inspecteerNode('a1')
      await flushPromises()
      expect(w.find('[data-testid="haal-buren-erbij-knop"]').exists()).toBe(true)
      expect(w.find('[data-testid="voeg-context-componenten-toe-knop"]').exists()).toBe(false)
    })

    it('"Haal buren erbij" voegt de node + zijn component-buren toe aan de actieve set', async () => {
      const { w } = await mountView() // GRAF: a1 ↔ a2 (flow)
      w.vm.inspecteerNode('a1')
      await flushPromises()
      await w.find('[data-testid="haal-buren-erbij-knop"]').trigger('click')
      await flushPromises()
      expect([...w.vm.actieveSet].sort()).toEqual(['a1', 'a2'])
    })

    it('"Haal buren erbij" is disabled zonder component-buren', async () => {
      zetGraf({ nodes: [{ id: 'x1', naam: 'Solo', element_type: 'applicatie', laag: 'application', blokkades_open: 0 }], edges: [] })
      const { w } = await mountView()
      w.vm.inspecteerNode('x1')
      await flushPromises()
      expect(w.find('[data-testid="haal-buren-erbij-knop"]').attributes('disabled')).toBeDefined()
    })

    it('toont "Voeg alle componenten toe"-knop bij een context-node', async () => {
      zetGraf(CONTEXTGRAF())
      const { w } = await mountView()
      w.vm.inspecteerNode('k1')
      await flushPromises()
      expect(w.find('[data-testid="voeg-context-componenten-toe-knop"]').exists()).toBe(true)
      expect(w.find('[data-testid="haal-buren-erbij-knop"]').exists()).toBe(false)
    })

    it('"Voeg alle componenten toe" voegt de component-buren toe (niet de context-node zelf)', async () => {
      zetGraf(CONTEXTGRAF())
      const { w } = await mountView()
      w.vm.inspecteerNode('k1')
      await flushPromises()
      await w.find('[data-testid="voeg-context-componenten-toe-knop"]').trigger('click')
      await flushPromises()
      expect([...w.vm.actieveSet]).toEqual(['a1'])
    })
  })

  // ── LI023 — scope filtert in subgraaf-modus CONTEXT (org/gg), niet de componenten ──────────────
  describe('scope subgraaf-modus (LI053 — organisatie-overlay, identiek aan Geheel)', () => {
    const APP = { id: 'a1', element_type: 'applicatie', laag: 'application' }
    const ORG1 = { id: 'p1', element_type: 'partij', soort: 'organisatie' }

    // Subgraaf-modus (set ≥1) met de enige aanwezige org p1 → default AAN in scope.
    async function subgraafMetOrg() {
      const { w } = await mountView({ heleLandschap: false })
      w.vm.toggleSet('a1')
      await flushPromises()
      return w
    }

    it('set-lid altijd zichtbaar, ook als de scope leeg is', async () => {
      const w = await subgraafMetOrg()
      w.vm.toggleScopeOrg('p1') // alles uit
      await flushPromises()
      expect(w.vm._inScope(APP)).toBe(true) // a1 is set-lid → altijd
    })

    it('org-node: zichtbaar als aangevinkt (default aan), verborgen als uitgevinkt', async () => {
      const w = await subgraafMetOrg()
      expect(w.vm._inScope(ORG1)).toBe(true) // default aan
      w.vm.toggleScopeOrg('p1')
      await flushPromises()
      expect(w.vm._inScope(ORG1)).toBe(false)
    })

    it('gebruikersgroep volgt de organisatie-vinkjes; org-loze groep altijd zichtbaar', async () => {
      const w = await subgraafMetOrg() // scope = {p1}
      expect(w.vm._inScope({ id: 'gg-org-p1', element_type: 'gebruikersgroep', organisatie_id: 'p1' })).toBe(true)
      expect(w.vm._inScope({ id: 'gg-org-p2', element_type: 'gebruikersgroep', organisatie_id: 'p2' })).toBe(false)
      expect(w.vm._inScope({ id: 'gg-org-x', element_type: 'gebruikersgroep', organisatie_id: null })).toBe(true)
    })

    it('componenten/contract/infra worden nooit door de scope geraakt (ook niet-set-leden)', async () => {
      const w = await subgraafMetOrg()
      w.vm.toggleScopeOrg('p1') // alles uit
      await flushPromises()
      expect(w.vm._inScope({ id: 'k1', element_type: 'contract' })).toBe(true)
      expect(w.vm._inScope({ id: 'd1', element_type: 'component', laag: 'technology' })).toBe(true)
      expect(w.vm._inScope({ id: 'ander-comp', element_type: 'applicatie' })).toBe(true) // niet-set component ook
    })

    it('geen Biedt/Gebruikt-schakelaar meer (component-scoping vervallen)', async () => {
      const w = await subgraafMetOrg()
      expect(w.find('[data-testid="lk-scopebalk"]').exists()).toBe(true)
      expect(w.find('[data-testid="lk-scope-biedt"]').exists()).toBe(false)
      expect(w.find('[data-testid="lk-scope-gebruikt"]').exists()).toBe(false)
    })
  })

  // ── LI023 / ADR-040 F1 — generieke re-layout op de getekende node-samenstelling ─────────────────
  // ADR-040 F1: de 250ms-debounce is vervangen door de gecoalesceerde render-eigenaar (`_planRedraw`,
  // pending-vlag + nextTick). `naSettle` wacht ruim genoeg tot de gecoalesceerde redraw geland is.
  describe('generieke re-layout', () => {
    const naDebounce = () => new Promise((r) => setTimeout(r, 300)) // ruim > één tick (coalesce-redraw geland)

    it('re-layout wordt uitgevoerd als de getekende node-samenstelling verandert', async () => {
      const { w } = await mountView() // geheel, volledige graaf
      await naDebounce() // mount-/laad-relayout laten landen
      const voor = w.vm._relayoutTeller
      w.vm.toonRegistratiegaps = true // losse nodes erbij → getekendeNodes groeit (geen modus-/set-wijziging)
      await flushPromises()
      await naDebounce()
      expect(w.vm._relayoutTeller).toBeGreaterThan(voor)
    })

    it('geen re-layout als de samenstelling ongewijzigd blijft (irrelevante UI-wijziging)', async () => {
      const { w } = await mountView()
      await naDebounce()
      const voor = w.vm._relayoutTeller
      w.vm.toggleLegenda() // pure UI — geen node-/edge-/layout-wijziging
      await flushPromises()
      await naDebounce()
      expect(w.vm._relayoutTeller).toBe(voor)
    })

    it('LI037 — edge-only ring-toggle hertekent óók (nodes ongewijzigd, alleen edges wijzigen)', async () => {
      zetGraf({
        nodes: [
          { id: 'cA', naam: 'A', element_type: 'applicatie', laag: 'application', lifecycle_status: 'concept', blokkades_open: 0 },
          { id: 'cB', naam: 'B', element_type: 'applicatie', laag: 'application', lifecycle_status: 'concept', blokkades_open: 0 },
        ],
        edges: [
          { bron_id: 'cA', doel_id: 'cB', relatietype: 'flow', ring: 'applicaties' },
          { bron_id: 'cA', doel_id: 'cB', relatietype: 'aggregation', ring: 'samenstelling' },
        ],
      })
      const { w } = await mountView()
      await naDebounce()
      const voorIds = getekendeIds(w)
      const voor = w.vm._relayoutTeller
      // 'samenstelling' uit → die edge verdwijnt, maar cA/cB blijven (nog steeds verbonden via flow).
      await w.find('[data-testid="lk-ring-samenstelling"]').trigger('change')
      await flushPromises()
      await naDebounce()
      expect(getekendeIds(w)).toEqual(voorIds) // node-samenstelling ongewijzigd
      expect(w.vm._relayoutTeller).toBeGreaterThan(voor) // tóch hertekend (zichtbareEdges-trigger)
    })
  })

  // ── ADR-025 — "Bekijk op kaart"-deeplink (?center) ──────────────────────────────────────────────
  describe('deep-link ?center (Bekijk op kaart)', () => {
    it('?center → component in de set, ego-modus, beginscherm overgeslagen', async () => {
      const { w } = await mountView({ query: '?center=a1' })
      expect([...w.vm.actieveSet]).toEqual(['a1'])
      expect(w.vm.modus).toBe('ego')
      expect(w.vm.beginschermOpen).toBe(false)
    })

    it('zonder center → beginscherm blijft open (ongewijzigd)', async () => {
      const { w } = await mountView({ heleLandschap: false })
      expect(w.vm.beginschermOpen).toBe(true)
    })
  })

  // ── ADR-040 F1 — fcose-vrije layout: zowel praatplaat als overzicht gebruiken concentric ──
  // (Vervangt de LI030-test die impact→fcose borgde: fcose is verwijderd wegens de edges-onzichtbaar-bug.)
  describe('layout (ADR-040 F1 — fcose weg)', () => {
    it('praatplaat én overzicht gebruiken beide concentric (geen fcose meer)', async () => {
      const { w } = await mountView()
      await kies(w, 'a1') // praatplaat (ego)
      expect(w.vm.modus).toBe('ego')
      expect(w.vm._layout().name).toBe('concentric')
      w.vm.toonOverzicht() // overzicht (adapter → 'geheel')
      await flushPromises()
      expect(w.vm.modus).toBe('geheel')
      expect(w.vm._layout().name).toBe('concentric') // fcose vervangen door deterministische concentric
    })

    it('de set-nodes (ankers) blijven zichtbaar in de graaf', async () => {
      const { w } = await mountView()
      await kies(w, 'a1')
      await kies(w, 'a2')
      const ids = w.vm.getekendeNodes.map((n) => n.id)
      expect(ids).toContain('a1')
      expect(ids).toContain('a2')
    })
  })

  // ── LI031 — dubbele org-node: groepeer-per-org-aggregaat dubbelde de org-partij-node ─────────
  describe('dubbele ring-nodes — org-absorptie (LI031)', () => {
    it('org-node aanwezig → absorbeert haar gebruikersgroepen (geen dubbele org-genaamde node)', async () => {
      zetGraf({
        nodes: [
          { id: 'cA', naam: 'AppA', element_type: 'applicatie', laag: 'application', lifecycle_status: 'concept', blokkades_open: 0, eigenaar_organisatie_id: 'X' },
          { id: 'G', naam: 'Burgers', element_type: 'gebruikersgroep', laag: 'business', organisatie_id: 'X', aantal_leden: 100 },
          { id: 'X', naam: 'Gemeente', element_type: 'partij', laag: 'business', soort: 'organisatie' },
        ],
        edges: [{ bron_id: 'cA', doel_id: 'G', relatietype: 'serving', ring: 'gebruikers' }],
      })
      const { w } = await mountView() // groepeerPerOrg is default aan
      const ids = w.vm.grafNodes.map((n) => n.id)
      expect(ids).toContain('X') // de echte org-node
      expect(ids).not.toContain('gg-org-X') // géén tweede, org-genaamde aggregaat-node
      // de serving-edge naar de groep wijst nu naar de org-node (geen dangling/dubbel)
      expect(w.vm.grafEdges.some((e) => e.doel_id === 'X' && e.ring === 'gebruikers')).toBe(true)
    })

    it('zonder org-node blijft het synthetische per-org aggregaat bestaan', async () => {
      zetGraf({
        nodes: [
          { id: 'cA', naam: 'AppA', element_type: 'applicatie', laag: 'application', lifecycle_status: 'concept', blokkades_open: 0 },
          { id: 'G', naam: 'Burgers', element_type: 'gebruikersgroep', laag: 'business', organisatie_id: 'Y', aantal_leden: 100 },
        ],
        edges: [{ bron_id: 'cA', doel_id: 'G', relatietype: 'serving', ring: 'gebruikers' }],
      })
      const { w } = await mountView()
      expect(w.vm.grafNodes.map((n) => n.id)).toContain('gg-org-Y') // org niet als node → aggregaat blijft
    })
  })

  // ── ADR-040 F1 (stap 1+3) — positie-behoud vervallen: geen preset/fcose-mix-tak meer ─────────────
  // (Vervangt de LI032-tests die het `vorigePosities`-preset/fcose-mix-gedrag borgden; `_layout` kent
  //  geen positie-parameter meer.) `_layout` levert nu altijd een deterministische layout, géén fcose.
  describe('layout is deterministisch & fcose-vrij (ADR-040 F1)', () => {
    it('_layout neemt geen posities meer en levert nooit fcose (concentric of preset/swimlane)', async () => {
      const { w } = await mountView()
      expect(w.vm._layout().name).not.toBe('fcose')
      await kies(w, 'a1'); await kies(w, 'a2') // ≥2 (voorheen fcose)
      expect(w.vm._layout().name).not.toBe('fcose')
      expect(w.vm._layout().name).toBe('concentric')
    })
  })

  // ── ADR-040 F1 (stap 1+3) — scope-toggle geeft een schone hertekening; de edge-set komt volledig terug ─
  describe('scope-toggle (ADR-040 F1)', () => {
    it('org uit → org-gebonden edge weg (app↔app blijft); org weer aan → edge-set volledig terug + redraw', async () => {
      zetGraf({
        nodes: [
          { id: 'cA', naam: 'AppA', element_type: 'applicatie', laag: 'application', lifecycle_status: 'concept', blokkades_open: 0, eigenaar_organisatie_id: 'ORG' },
          { id: 'cB', naam: 'AppB', element_type: 'applicatie', laag: 'application', lifecycle_status: 'concept', blokkades_open: 0 },
          { id: 'ORG', naam: 'RID', element_type: 'partij', laag: 'business', soort: 'organisatie' },
        ],
        edges: [
          { bron_id: 'cA', doel_id: 'cB', relatietype: 'flow', ring: 'applicaties' }, // app↔app (los van ORG)
          { bron_id: 'ORG', doel_id: 'cA', relatietype: 'eigenaar', ring: 'eigenaar' }, // ORG-gebonden (ring default aan)
        ],
      })
      const { w } = await mountView() // geheel: alle nodes + scopeOrgs default aan
      const edgeKey = () => w.vm.zichtbareEdges.map((e) => `${e.bron_id}>${e.doel_id}`).sort().join(',')
      const volledig = edgeKey()
      expect(volledig).toContain('ORG>cA')
      expect(volledig).toContain('cA>cB')

      const voorTeller = w.vm._relayoutTeller
      w.vm.toggleScopeOrg('ORG') // ORG uit
      await flushPromises()
      expect(w.vm.zichtbareEdges.some((e) => e.bron_id === 'ORG')).toBe(false) // ORG-gebonden edge weg
      expect(w.vm.zichtbareEdges.some((e) => e.bron_id === 'cA' && e.doel_id === 'cB')).toBe(true) // app↔app blijft

      w.vm.toggleScopeOrg('ORG') // ORG weer aan
      await flushPromises()
      expect(edgeKey()).toBe(volledig) // edge-set volledig terug
      expect(w.vm._relayoutTeller).toBeGreaterThan(voorTeller) // er is (schoon) hertekend
    })
  })

  // ── LI033 — sleepbaar detail-paneel ──────────────────────────────────────────────────────────
  describe('detail-popup draggable (LI033)', () => {
    it('slepen verplaatst het detail-paneel; wisSet reset naar standaard', async () => {
      const { w } = await mountView()
      expect(w.vm.detailPos).toEqual({ x: null, y: null })
      w.vm.onDetailMousedown({ clientX: 100, clientY: 80, target: { closest: () => null }, preventDefault() {} })
      expect(w.vm.detailDragging).toBe(true)
      w.vm.onDetailMousemove({ clientX: 140, clientY: 120 }) // offset (100,80) → pos (40,40)
      expect(w.vm.detailPos).toEqual({ x: 40, y: 40 })
      w.vm.onDetailMouseup()
      expect(w.vm.detailDragging).toBe(false)
      w.vm.wisSet()
      expect(w.vm.detailPos).toEqual({ x: null, y: null })
    })

    it('mousedown op een knop/link/input start geen drag', async () => {
      const { w } = await mountView()
      w.vm.onDetailMousedown({ target: { closest: (sel) => (sel.includes('button') ? {} : null) }, preventDefault() {} })
      expect(w.vm.detailDragging).toBe(false)
    })

    it('LI034 — init vanuit DOM-positie: geen sprong naar de hoek bij de eerste beweging', async () => {
      const { w } = await mountView()
      // paneel staat (CSS) op rect.left=1200; mousedown op x=800 (binnen het paneel)
      w.vm.onDetailMousedown({
        clientX: 800, clientY: 100,
        target: { closest: () => null },
        currentTarget: { getBoundingClientRect: () => ({ left: 1200, top: 100 }) },
        preventDefault() {},
      })
      expect(w.vm.detailPos).toEqual({ x: 1200, y: 100 }) // geïnitialiseerd op de echte positie
      w.vm.onDetailMousemove({ clientX: 850, clientY: 100 }) // 50px naar rechts
      expect(w.vm.detailPos.x).toBe(1250) // schuift 50px, springt NIET naar de hoek
    })
  })

  // ── LI036 — eigenaar-ring (eigendom-edges verdwenen permanent: ring zonder checkbox) ─────────
  describe('eigenaar-ring (LI036)', () => {
    const _eigGraf = () => ({
      nodes: [
        { id: 'cA', naam: 'AppA', element_type: 'applicatie', laag: 'application', lifecycle_status: 'concept', blokkades_open: 0, eigenaar_organisatie_id: 'X' },
        { id: 'X', naam: 'Gemeente', element_type: 'partij', laag: 'business', soort: 'organisatie', blokkades_open: 0 },
      ],
      edges: [{ bron_id: 'X', doel_id: 'cA', relatietype: 'eigenaar', label: 'is eigendom van', ring: 'eigenaar' }],
    })

    it('eigenaar is een ring die default AAN staat (met checkbox)', async () => {
      zetGraf(_eigGraf())
      const { w } = await mountView()
      expect([...w.vm.ringAan]).toContain('eigenaar')
      expect(w.find('[data-testid="lk-ring-eigenaar"]').exists()).toBe(true)
    })

    it('eigenaar-edge is default zichtbaar; ring uitvinken verbergt de edge', async () => {
      zetGraf(_eigGraf())
      const { w } = await mountView()
      expect(w.vm.zichtbareEdges.some((e) => e.ring === 'eigenaar')).toBe(true)
      await w.find('[data-testid="lk-ring-eigenaar"]').trigger('change') // uitvinken
      await flushPromises()
      expect(w.vm.zichtbareEdges.some((e) => e.ring === 'eigenaar')).toBe(false)
    })
  })

  // ── LI025 — interactieve legenda-typefilter (dimmen, niet verbergen) ─────────────────────────
  describe('legenda-typefilter (LI025)', () => {
    it('toggle: klik type → filter; nogmaals → null; ander type → dat type', async () => {
      const { w } = await mountView()
      expect(w.vm.legendaTypeFilter).toBe(null)
      w.vm.toggleLegendaFilter('Component')
      expect(w.vm.legendaTypeFilter).toBe('Component')
      w.vm.toggleLegendaFilter('Component') // toggle uit
      expect(w.vm.legendaTypeFilter).toBe(null)
      w.vm.toggleLegendaFilter('Component')
      w.vm.toggleLegendaFilter('Contract') // ander type
      expect(w.vm.legendaTypeFilter).toBe('Contract')
    })

    it('filter laat de graaf ONGEWIJZIGD (dimmen, geen verbergen)', async () => {
      const { w } = await mountView()
      w.vm.setLayoutModus('swimlane') // tekent alle nodes ongeacht edges
      await flushPromises()
      const alle = getekendeIds(w)
      expect(alle).toEqual(['a1', 'a2', 'd1', 'k1', 'p1'])
      w.vm.toggleLegendaFilter('Contract')
      await flushPromises()
      expect(getekendeIds(w)).toEqual(alle) // niets verdwijnt
    })

    it('dimt niet-matchende nodes via cy (lk-dim); filter weg → geen lk-dim', async () => {
      // Eigen cy-stub met inspecteerbare nodes (de globale mock heeft geen nodes()).
      const mkNode = (data) => {
        const cls = new Set()
        return { data: () => data, addClass: (c) => cls.add(c), removeClass: (c) => cls.delete(c), heeft: (c) => cls.has(c) }
      }
      const nodes = [
        mkNode({ id: 'a1', element_type: 'applicatie', laag: 'application' }),
        mkNode({ id: 'd1', element_type: 'database', laag: 'technology' }),
        mkNode({ id: 'k1', element_type: 'contract', laag: 'business' }),
      ]
      const coll = { forEach: (f) => nodes.forEach(f), removeClass: (c) => nodes.forEach((n) => n.removeClass(c)) }
      const fakeCy = {
        on: vi.fn(), off: vi.fn(), elements: () => ({ remove: vi.fn(), unselect: vi.fn() }),
        getElementById: () => ({ length: 0, select: vi.fn() }), animate: vi.fn(), zoom: () => 1,
        pan: () => ({ x: 0, y: 0 }), add: vi.fn(), layout: () => ({ run: vi.fn() }),
        resize: vi.fn(), fit: vi.fn(), destroy: vi.fn(), edges: () => ({ removeClass: vi.fn() }),
        nodes: () => coll,
      }
      cytoscape.mockReturnValueOnce(fakeCy)
      const { w } = await mountView()

      w.vm.toggleLegendaFilter('Contract')
      await flushPromises()
      expect(nodes[2].heeft('lk-dim')).toBe(false) // contract = scherp
      expect(nodes[0].heeft('lk-dim')).toBe(true) // applicatie = gedimd
      expect(nodes[1].heeft('lk-dim')).toBe(true) // database = gedimd

      w.vm.toggleLegendaFilter('Contract') // filter weg
      await flushPromises()
      expect(nodes.every((n) => !n.heeft('lk-dim'))).toBe(true)
    })

    it('_legendaMatch mapt vorm-categorieën correct', async () => {
      const { w } = await mountView()
      const m = w.vm._legendaMatch
      expect(m({ element_type: 'applicatie', laag: 'application' }, 'Component')).toBe(true)
      expect(m({ element_type: 'database', laag: 'technology' }, 'Infrastructuur')).toBe(true)
      expect(m({ element_type: 'database', laag: 'technology' }, 'Component')).toBe(false)
      expect(m({ element_type: 'contract', laag: 'business' }, 'Contract')).toBe(true)
      expect(m({ element_type: 'partij', soort: 'organisatie' }, 'Organisatie')).toBe(true)
    })

    it('regressie dim-bug: cy-node.data() draagt element_type → _legendaMatch matcht', async () => {
      const { w } = await mountView()
      const data = w.vm._nodeData({ id: 'k1', naam: 'Contract X', element_type: 'contract', laag: 'business', blokkades_open: 0 })
      expect(data.element_type).toBe('contract') // vóór de fix ontbrak dit veld → dim matchte nooit
      expect(w.vm._legendaMatch(data, 'Contract')).toBe(true)
      expect(w.vm._legendaMatch(data, 'Component')).toBe(false)
    })

    it('floating: slepen verplaatst de legenda; wisSet reset naar standaard', async () => {
      const { w } = await mountView()
      expect(w.vm.legendaPos).toEqual({ x: null, y: null })
      w.vm.onLegendaMousedown({ clientX: 200, clientY: 150, target: { closest: () => null }, preventDefault() {} })
      expect(w.vm.legendaDragging).toBe(true)
      w.vm.onLegendaMousemove({ clientX: 260, clientY: 190 }) // offset = (200,150) → pos = (60,40)
      expect(w.vm.legendaPos).toEqual({ x: 60, y: 40 })
      w.vm.onLegendaMouseup()
      expect(w.vm.legendaDragging).toBe(false)
      w.vm.wisSet() // "Begin opnieuw" → terug naar standaardpositie
      expect(w.vm.legendaPos).toEqual({ x: null, y: null })
    })

    it('drag-handler negeert knoppen (filter blijft werken)', async () => {
      const { w } = await mountView()
      w.vm.onLegendaMousedown({ target: { closest: (sel) => (sel.includes('button') ? {} : null) }, preventDefault() {} })
      expect(w.vm.legendaDragging).toBe(false) // mousedown op een knop start geen drag
    })

    it('dubbelklik op een node heft de legenda-dim op (legendaTypeFilter → null)', async () => {
      const { w } = await mountView()
      w.vm.toggleLegendaFilter('Component')
      expect(w.vm.legendaTypeFilter).toBe('Component')
      w.vm.onNodeTap('a1') // eerste tap
      w.vm.onNodeTap('a1') // tweede tap binnen de drempel → dubbelklik
      expect(w.vm.legendaTypeFilter).toBe(null)
    })
  })

  describe('ADR-028 — rol/BIV-filter + randbehandeling', () => {
    it('externe_dataprovider krijgt de rol-rand in de node-data; overige nodes niet', async () => {
      const { w } = await mountView()
      const extern = w.vm._nodeData({ id: 'x', naam: 'BRP', element_type: 'applicatie', laag: 'application', componentrol: 'externe_dataprovider' })
      expect(extern.rol).toBe('externe_dataprovider')
      // een interne applicatie of een context-node draagt geen rol-rand
      expect(w.vm._nodeData({ id: 'y', naam: 'Intern', element_type: 'applicatie', componentrol: 'interne_applicatie' }).rol).toBe(null)
      expect(w.vm._nodeData({ id: 'k1', naam: 'Contract X', element_type: 'contract', laag: 'business' }).rol).toBe(null)
    })

    it('rol-filter: app-component mét andere rol valt weg; context-nodes zijn exempt', async () => {
      const { w } = await mountView()
      w.vm.filterRollen = ['externe_dataprovider']
      await flushPromises()
      expect(w.vm._filterMatch({ element_type: 'applicatie', componentrol: 'externe_dataprovider' })).toBe(true)
      expect(w.vm._filterMatch({ element_type: 'applicatie', componentrol: 'interne_applicatie' })).toBe(false)
      // filter-exemptie: rolloze context-nodes (partij/contract/gebruikersgroep) nooit wegfilteren
      expect(w.vm._filterMatch({ element_type: 'partij', soort: 'organisatie' })).toBe(true)
      expect(w.vm._filterMatch({ element_type: 'contract' })).toBe(true)
      expect(w.vm._filterMatch({ element_type: 'gebruikersgroep' })).toBe(true)
    })

    it('BIV-drempel: ordinaal (≥) op app-componenten; geen waarde valt weg; context exempt', async () => {
      const { w } = await mountView()
      w.vm.filterBivV = 'midden' // Vertrouwelijkheid ≥ midden (rang 1)
      await flushPromises()
      const app = (biv) => ({ element_type: 'applicatie', componentrol: 'interne_applicatie', biv_vertrouwelijkheid: biv })
      expect(w.vm._filterMatch(app('hoog'))).toBe(true) // rang 2 ≥ 1
      expect(w.vm._filterMatch(app('laag'))).toBe(false) // rang 0 < 1
      expect(w.vm._filterMatch(app(null))).toBe(false) // geen waarde → valt weg bij drempel
      // context-node zonder BIV blijft exempt (geen componentrol)
      expect(w.vm._filterMatch({ element_type: 'partij', soort: 'organisatie' })).toBe(true)
    })
  })

  // LI033 — grof-only markering (client-side) + blok→kaart handoff.
  describe('LI033 — grof-only + handoff', () => {
    it('voegComponentenToeAanSet markeert alléén componenten met grofOnly:true', async () => {
      const { w } = await mountView({ heleLandschap: false })
      w.vm.voegComponentenToeAanSet([{ id: 'a1', grofOnly: true }, { id: 'a2' }])
      await flushPromises()
      expect([...w.vm.actieveSet].sort()).toEqual(['a1', 'a2'])
      expect([...w.vm.grofOnlyIds]).toEqual(['a1'])
    })

    it('wisSet leegt óók de grof-only-markering', async () => {
      const { w } = await mountView({ heleLandschap: false })
      w.vm.voegComponentenToeAanSet([{ id: 'a1', grofOnly: true }])
      await flushPromises()
      expect([...w.vm.grofOnlyIds]).toEqual(['a1'])
      w.vm.wisSet()
      await flushPromises()
      expect([...w.vm.grofOnlyIds]).toEqual([])
    })

    it('handoff bij mount → opent exact die set + draagt de grof-only-markering', async () => {
      neemKaartHandoff.mockReturnValueOnce({ componentIds: ['a1', 'a2'], grofOnlyIds: ['a2'] })
      const { w } = await mountView({ heleLandschap: false })
      expect([...w.vm.actieveSet].sort()).toEqual(['a1', 'a2'])
      expect([...w.vm.grofOnlyIds]).toEqual(['a2'])
      expect(w.vm.beginschermOpen).toBe(false)
    })
  })
})
