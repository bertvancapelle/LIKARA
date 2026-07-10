/** Tests — LandschapskaartView v3 (ADR-025, Cytoscape; drie modi + zoek/filter/set/detail). */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { createPinia, setActivePinia } from 'pinia'
import { useAuthStore } from '@/store/auth'

// Cytoscape gemockt (via de frontend-wrapper): de graaf-rendering is een side-effect;
// de panelen zijn de testbare laag.
vi.mock('@/composables/cytoscape', () => ({
  default: vi.fn(() => {
    // LI036 — minimaal element-register: een test kan per id een fake cy-element registreren
    // (length ≥ 1, hasClass/renderedBoundingBox voor de rol-tag-overlay); zonder registratie
    // geldt het oude {length:0}-gedrag voor alle bestaande tests.
    const els = new Map()
    return {
      on: vi.fn(),
      elements: () => ({ remove: vi.fn(), unselect: vi.fn() }),
      nodes: () => ({ forEach: () => {}, map: () => [], length: 0 }), // LI032 — positie-capture in tekenGraaf
      getElementById: (id) => els.get(id) || { length: 0, select: vi.fn() },
      _els: els,
      animate: vi.fn(),
      zoom: () => 1,
      add: vi.fn(),
      layout: () => ({ run: vi.fn() }),
      resize: vi.fn(),
      fit: vi.fn(),
      destroy: vi.fn(),
    }
  }),
}))
vi.mock('@/api', () => ({
  api: {
    landschapskaart: { haalGrafdata: vi.fn(), subgraaf: vi.fn() }, // Fase B — set-scoped subgraaf
    componenten: { opties: vi.fn(), lijst: vi.fn() }, // LI019 1b — type-catalogus + beginscherm-zoek (LI052)
    partijen: { lijst: vi.fn() }, // LI019 1b — leverancier-zoek (externe partijen)
    // ADR-033 2c — opgeslagen views.
    impactViews: { lijst: vi.fn(), haal: vi.fn(), maak: vi.fn(), werkBij: vi.fn(), verwijder: vi.fn() },
    // LI034/ADR-041 — persoonlijke standaardkijk (kaart-kijkfilter).
    voorkeuren: { haalAlle: vi.fn(), zet: vi.fn(), herroep: vi.fn() },
    // LI036 slice 2 — proces-popup (basis-detail hoofdproces).
    // LI037 fase 3 — proces-ingang: klim (haal), boom-vervullers (rollup + procesvervullingen)
    // en de "Via proces"-zoeker (lijst, gepagineerd).
    processen: { haal: vi.fn(), rollup: vi.fn(), lijst: vi.fn() },
    procesvervullingen: { lijst: vi.fn() },
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
  // LI034/ADR-041 — standaardkijk: default geen opgeslagen voorkeur (kale default).
  api.voorkeuren.haalAlle.mockResolvedValue([])
  api.voorkeuren.zet.mockResolvedValue({})
  api.voorkeuren.herroep.mockResolvedValue(undefined)
  api.processen.haal.mockResolvedValue({ id: 'pr1', naam: 'Vergunningverlening', toelichting: 'Primair proces' })
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

  it('ADR-040 → LI036 — drillNaar hercentreert de praatplaat; een SET-actie wijzigt de weergave NIET meer', async () => {
    const { w } = await mountView()
    // drillNaar = "toon impact" op één component → praatplaat centraal op dat component.
    w.vm.drillNaar('a2')
    await flushPromises()
    expect(w.vm.weergave).toBe('praatplaat')
    expect(w.vm.modus).toBe('ego')
    // LI036 stap 3 (bevestigd besluit) — voegComponentenToeAanSet wijzigt uitsluitend de SET:
    // je blijft in de weergave waar je was (de vroegere sprong naar Overzicht is vervallen).
    w.vm.voegComponentenToeAanSet([{ id: 'a1' }])
    await flushPromises()
    expect(w.vm.actieveSet.has('a1')).toBe(true)
    expect(w.vm.weergave).toBe('praatplaat')
    expect(w.vm.modus).toBe('ego')
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

  it('LI036 — "Lagen" is de derde weergave op de ENE weergave-as; de oude layout-toggle bestaat niet meer', async () => {
    const { w } = await mountView()
    expect(w.vm.weergave).toBe('overzicht')
    // De vroegere tweede as (layoutModus/setLayoutModus + geparkeerde toggle) is geconvergeerd.
    expect(w.vm.layoutModus).toBeUndefined()
    expect(w.vm.setLayoutModus).toBeUndefined()
    expect(w.find('[data-testid="lk-layout-toggle"]').exists()).toBe(false)
    expect(w.find('[data-testid="lk-layout-swimlane"]').exists()).toBe(false)
    // De derde knop op de weergave-schakelaar: altijd klikbaar, zet weergave 'lagen'.
    const knop = w.find('[data-testid="lk-weergave-lagen"]')
    expect(knop.exists()).toBe(true)
    expect(knop.attributes('aria-pressed')).toBe('false')
    await knop.trigger('click')
    await flushPromises()
    expect(w.vm.weergave).toBe('lagen')
    expect(w.find('[data-testid="lk-weergave-lagen"]').attributes('aria-pressed')).toBe('true')
    // De baan-layout hoort erbij (preset), en terug naar Overzicht herstelt de brede plaat.
    expect(w.vm._layout().name).toBe('preset')
    await w.find('[data-testid="lk-weergave-overzicht"]').trigger('click')
    expect(w.vm.weergave).toBe('overzicht')
  })

  it('LI036 — een oude layoutModus-sleutel in sessionStorage wordt genegeerd (weergave blijft default)', async () => {
    sessionStorage.setItem('lk-state', JSON.stringify({ layoutModus: 'swimlane' }))
    const { w } = await mountView()
    expect(w.vm.weergave).toBe('overzicht')
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
    w.vm.toonLagen() // LI036 — de Lagen-weergave op de ene weergave-as (voorheen setLayoutModus)
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
    w.vm.toonLagen()
    await flushPromises()
    // LI036 ring-uit-wint — losse componenten (echte gaps) tonen óók in Lagen alleen onder de
    // gaps-toggle (hun categorie-ring 'applicaties' staat default aan).
    await w.find('[data-testid="lk-registratiegaps"]').setValue(true)
    await flushPromises()
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

  it('LI036 ring-uit-wint — losse knopen tonen in Lagen alléén via de gaps-toggle + hun categorie-ring', async () => {
    zetGraf({
      nodes: [
        { id: 'a1', naam: 'Zaaksysteem', element_type: 'applicatie', laag: 'application', lifecycle_status: 'concept', blokkades_open: 0, eigenaar_organisatie_id: 'p1' },
        { id: 'a2', naam: 'DMS', element_type: 'applicatie', laag: 'application', lifecycle_status: 'concept', blokkades_open: 0, eigenaar_organisatie_id: 'p1' },
        { id: 'p1', naam: 'Org (los)', element_type: 'partij', laag: 'business', soort: 'organisatie', blokkades_open: 0 },
      ],
      edges: [{ bron_id: 'a1', doel_id: 'a2', relatietype: 'flow', label: 'koppeling', ring: 'applicaties' }],
    })
    const { w } = await mountView()
    // Overzicht: edge-rakende nodes — a1,a2 verbonden, p1 los → verborgen.
    expect(w.vm.getekendeNodes.map((n) => n.id).sort()).toEqual(['a1', 'a2'])
    // LI036 — de vroegere banen-uitzondering is vervallen: ook Lagen verbergt losse knopen
    // zonder de gaps-toggle.
    w.vm.toonLagen()
    await flushPromises()
    expect(w.vm.getekendeNodes.map((n) => n.id).sort()).toEqual(['a1', 'a2'])
    // Gaps-toggle AAN → p1 (échte gap; categorie-ring 'rollen' staat aan) verschijnt.
    await w.find('[data-testid="lk-registratiegaps"]').setValue(true)
    await flushPromises()
    expect(w.vm.getekendeNodes.map((n) => n.id).sort()).toEqual(['a1', 'a2', 'p1'])
    // Categorie-ring uit → de gap verdwijnt, óók met de toggle aan ("ring uit wint").
    await w.find('[data-testid="lk-ring-rollen"]').trigger('change')
    await flushPromises()
    expect(w.vm.getekendeNodes.map((n) => n.id).sort()).toEqual(['a1', 'a2'])
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
    // Default: alle 7 banen (incl. lege; LI036: + proceslaan) zichtbaar; componenten + infrastructuur gevuld.
    expect(w.vm.laneBanden.length).toBe(7)
    expect(w.vm.laneBanden.find((b) => b.key === 'rollen').leeg).toBe(true)
    expect(w.vm.laneBanden.find((b) => b.key === 'componenten').leeg).toBe(false)
    // "Verberg lege lanes" → alleen de gevulde lanes.
    await w.find('[data-testid="lk-verberg-lege"]').setValue(true)
    await flushPromises()
    expect(w.vm.laneBanden.map((b) => b.key).sort()).toEqual(['componenten', 'infrastructuur'])
  })

  it('LI019 1d-v3 — lane verslepen herschikt de volgorde en persisteert in sessionStorage', async () => {
    const w = await mountSwimlane()
    // LI036 — startvolgorde: Processen bovenaan (slice 2); … → Contracten → Overig (Overig onderaan).
    expect(w.vm.laneVolgorde).toEqual(['processen', 'rollen', 'gebruikers', 'componenten', 'infrastructuur', 'contracten', 'overig'])
    w.vm._herschikLane('contracten', 'rollen') // contracten naar de positie van rollen (na de proceslaan)
    await flushPromises()
    expect(w.vm.laneVolgorde[0]).toBe('processen') // LI036 — proceslaan blijft bovenaan
    expect(w.vm.laneVolgorde[1]).toBe('contracten')
    expect(w.vm.laneVolgorde[2]).toBe('rollen')
    // Direct opgeslagen (geen aparte bewaar-knop).
    expect(JSON.parse(sessionStorage.getItem('lk-state')).laneVolgorde[1]).toBe('contracten')
    // De zijbalk-lanevolgorde-lijst is verwijderd (bug 3).
    expect(w.find('[data-testid="lk-lane-volgorde"]').exists()).toBe(false)
    expect(w.find('[data-testid="lk-lane-reset"]').exists()).toBe(false)
  })

  it('LI036 — registratiegaps-toggle geldt in ALLE weergaven (Lagen niet meer "sowieso")', async () => {
    // p1 (partij) en k1 (contract) hebben geen edges → in radiaal standaard verborgen, mét toggle zichtbaar.
    const { w } = await mountView()
    expect(w.vm.getekendeNodes.map((n) => n.id)).not.toContain('p1') // los → verborgen (radiaal)
    await w.find('[data-testid="lk-registratiegaps"]').setValue(true)
    await flushPromises()
    const radiaalGaps = w.vm.getekendeNodes.map((n) => n.id)
    expect(radiaalGaps).toContain('p1') // nu zichtbaar in radiaal
    expect(radiaalGaps).toContain('k1')
    // LI036 — Lagen zonder toggle: losse nodes óók daar verborgen (geen banen-uitzondering meer).
    await w.find('[data-testid="lk-registratiegaps"]').setValue(false)
    await flushPromises()
    w.vm.toonLagen()
    await flushPromises()
    let swimIds = w.vm.getekendeNodes.map((n) => n.id)
    expect(swimIds).not.toContain('p1')
    expect(swimIds).not.toContain('k1')
    // Toggle aan → de gaps verschijnen in hun baan (rollen-/contracten-ring staan aan).
    await w.find('[data-testid="lk-registratiegaps"]').setValue(true)
    await flushPromises()
    swimIds = w.vm.getekendeNodes.map((n) => n.id)
    expect(swimIds).toContain('p1') // in de Rollen-baan
    expect(swimIds).toContain('k1') // in de Contracten-baan
  })

  it('LI019 1d-v2 — lanevolgorde + verberg-lege hersteld uit sessionStorage', async () => {
    sessionStorage.setItem('lk-state', JSON.stringify({
      laneVolgorde: ['contracten', 'processen', 'rollen', 'gebruikers', 'componenten', 'infrastructuur', 'overig'],
      verbergLegeLanes: true,
    }))
    const { w } = await mountView()
    expect(w.vm.laneVolgorde[0]).toBe('contracten')
    expect(w.vm.verbergLegeLanes).toBe(true)
  })

  it('LI036 — een legacy-volgorde zónder proceslaan valt terug op de default (processen bovenaan)', async () => {
    sessionStorage.setItem('lk-state', JSON.stringify({
      laneVolgorde: ['contracten', 'rollen', 'gebruikers', 'componenten', 'infrastructuur', 'overig'],
    }))
    const { w } = await mountView()
    expect(w.vm.laneVolgorde[0]).toBe('processen')
  })

  // ── LI036 slice 1 — "Lagen" als derde weergave (zelfde set, zelfde stijlbron, zelfde interactie) ──
  describe('LI036 — Lagen-weergave', () => {
    it('knoop-styling komt uit de ENE gedeelde bron: _nodeData is identiek in Overzicht en Lagen', async () => {
      const { w } = await mountView()
      const n = w.vm.grafNodes.find((x) => x.id === 'a2') // geblokkeerd + ⚠
      const inOverzicht = JSON.stringify(w.vm._nodeData(n))
      w.vm.toonLagen()
      await flushPromises()
      expect(JSON.stringify(w.vm._nodeData(n))).toBe(inOverzicht)
      // Vorm=type, kleur=lifecycle, ⚠ bij blokkade, type-label — ongewijzigd aanwezig.
      const d = w.vm._nodeData(n)
      expect(d.shape).toBe('round-rectangle')
      expect(d.label).toContain('⚠')
      expect(d.label).toContain('\n')
    })

    it('elke getekende node valt in de baan van zijn _laneVan; banen volgen laneVolgorde', async () => {
      const { w } = await mountView()
      w.vm.toonLagen()
      await flushPromises()
      const pos = w.vm._swimlanePositions()
      const banden = w.vm.laneBanden
      for (const n of w.vm.getekendeNodes) {
        const baan = banden.find((b) => b.key === w.vm._laneVan(n))
        expect(baan).toBeTruthy()
        expect(pos[n.id].y).toBeGreaterThanOrEqual(baan.top)
        expect(pos[n.id].y).toBeLessThanOrEqual(baan.top + baan.height)
      }
      expect(banden.map((b) => b.key)).toEqual(w.vm.laneVolgorde)
    })

    it('de scopebalk blijft zichtbaar op Lagen (scope werkt daar door — P8), verborgen op de praatplaat', async () => {
      const { w } = await mountView()
      // LI036 organisatiebalk — p1 (org zonder relaties) is pas "in beeld" via de gaps-toggle.
      await w.find('[data-testid="lk-registratiegaps"]').setValue(true)
      await flushPromises()
      expect(w.find('[data-testid="lk-scopebalk"]').exists()).toBe(true) // overzicht
      w.vm.toonLagen()
      await flushPromises()
      expect(w.find('[data-testid="lk-scopebalk"]').exists()).toBe(true) // lagen: control zichtbaar
      // Scope filtert óók op Lagen (org uitvinken → org-node weg uit de getekende set).
      await w.find('[data-testid="lk-scope-org-p1"]').trigger('change')
      await flushPromises()
      expect(getekendeIds(w)).not.toContain('p1')
      await w.find('[data-testid="lk-scope-org-p1"]').trigger('change') // terug aan
      await flushPromises()
      w.vm.toonPraatplaat('a1')
      await flushPromises()
      expect(w.find('[data-testid="lk-scopebalk"]').exists()).toBe(false) // praatplaat: verborgen
    })

    it('schakelen Lagen ↔ Overzicht ↔ Praatplaat behoudt de set; het canvas heeft in elke weergave nodes', async () => {
      const { w } = await mountView({ heleLandschap: false })
      await kies(w, 'a1'); await kies(w, 'a2') // set van 2 (kies zet praatplaat op de laatste)
      const set = [...w.vm.actieveSet].sort()
      w.vm.toonLagen()
      await flushPromises()
      expect([...w.vm.actieveSet].sort()).toEqual(set)
      expect(w.vm.getekendeNodes.length).toBeGreaterThan(0)
      expect(w.vm._layout().name).toBe('preset')
      w.vm.toonOverzicht()
      await flushPromises()
      expect([...w.vm.actieveSet].sort()).toEqual(set)
      expect(w.vm.getekendeNodes.length).toBeGreaterThan(0)
      w.vm.toonPraatplaat('a1')
      await flushPromises()
      expect([...w.vm.actieveSet].sort()).toEqual(set)
      expect(w.vm.getekendeNodes.length).toBeGreaterThan(0)
      expect(w.vm._layout().name).toBe('concentric')
    })

    it('de weergave-wissel naar Lagen is één history-entry; Terug herstelt de vorige weergave', async () => {
      const { w } = await mountView()
      expect(w.vm.weergave).toBe('overzicht')
      w.vm.toonLagen()
      await flushPromises()
      expect(w.vm.weergave).toBe('lagen')
      expect(w.vm.kanTerug).toBe(true)
      w.vm.terugInHistorie()
      await flushPromises()
      expect(w.vm.weergave).toBe('overzicht')
      w.vm.vooruitInHistorie()
      await flushPromises()
      expect(w.vm.weergave).toBe('lagen')
    })

    it('Lagen eerste opbouw: de edges zitten direct in de cy-add (niet pas na een klik)', async () => {
      // LI036-fix — de weergave-wissel naar Lagen is één volledige (her)opbouw: nodes ÉN edges in
      // dezelfde cy.add, en de preset-layout draait erna via de ene render-eigenaar. (Headless dekt
      // de visuele teken-timing niet — de browsercheck blijft beslissend; dit borgt de opbouw-kant.)
      const { w } = await mountView()
      const inst = cytoscape.mock.results.at(-1).value
      const addsVoor = inst.add.mock.calls.length
      w.vm.toonLagen()
      await flushPromises()
      expect(inst.add.mock.calls.length).toBeGreaterThan(addsVoor) // wissel → redraw gedraaid
      const elementen = inst.add.mock.calls.at(-1)[0]
      const nodes = elementen.filter((el) => el.data && !el.data.source)
      const edges = elementen.filter((el) => el.data?.source && el.data?.target)
      expect(nodes.length).toBeGreaterThan(0)
      expect(edges.length).toBeGreaterThan(0) // de a1→a2-flow zit in de EERSTE Lagen-opbouw
      expect(w.vm._layout().name).toBe('preset') // en de baan-layout is de bijbehorende layout
    })

    it('"Verberg lege banen" is alléén zichtbaar in de Lagen-weergave', async () => {
      const { w } = await mountView()
      expect(w.find('[data-testid="lk-verberg-lege"]').exists()).toBe(false) // overzicht
      w.vm.toonLagen()
      await flushPromises()
      expect(w.find('[data-testid="lk-verberg-lege"]').exists()).toBe(true)
      // Registratiegaps-toggle bestaat in beide weergaven (bestaand gedrag).
      expect(w.find('[data-testid="lk-registratiegaps"]').exists()).toBe(true)
    })
  })

  // ── LI036 rolbanen — partij in meerdere banen via de Lagen-only instance-projectie ──
  describe('LI036 — rolbanen (instance-projectie)', () => {
    // o1 gebruikt én beheert a1 (twee petten); lev1 levert via contract k1; p0 speelt geen rol.
    const ROLBAAN_GRAF = {
      nodes: [
        { id: 'a1', naam: 'DMS', element_type: 'applicatie', laag: 'application', lifecycle_status: 'concept', blokkades_open: 0 },
        { id: 'o1', naam: 'Gemeente Tiel', element_type: 'partij', laag: 'business', soort: 'organisatie', blokkades_open: 0 },
        { id: 'lev1', naam: 'SaaS BV', element_type: 'partij', laag: 'business', soort: 'externe_partij', blokkades_open: 0 },
        { id: 'p0', naam: 'P. Zonder Rol', element_type: 'partij', laag: 'business', soort: 'persoon', blokkades_open: 0 },
        { id: 'k1', naam: 'Contract X', element_type: 'contract', laag: 'business', blokkades_open: 0 },
      ],
      edges: [
        { bron_id: 'o1', doel_id: 'a1', relatietype: 'gebruikt', label: 'gebruikt', ring: 'gebruikt' },
        { bron_id: 'o1', doel_id: 'a1', relatietype: 'roltoewijzing', label: 'Technisch beheer', ring: 'rollen' },
        { bron_id: 'a1', doel_id: 'k1', relatietype: 'association', label: 'valt onder', ring: 'contracten' },
        { bron_id: 'k1', doel_id: 'lev1', relatietype: 'leverancier', label: 'geleverd door', ring: 'contracten' },
      ],
    }
    async function mountRolbanen() {
      zetGraf(ROLBAAN_GRAF)
      const { w } = await mountView()
      w.vm.toonLagen()
      await flushPromises()
      return w
    }
    const instVan = (w, logischId) => w.vm.instanceProjectie.instances.filter((i) => i.logischId === logischId)

    it('(a) partij met gebruikt- én beheer-edge → instance in Gebruikers ÉN Rollen & beheer (één logischId)', async () => {
      const w = await mountRolbanen()
      const o1 = instVan(w, 'o1')
      expect(o1.map((i) => i.baan).sort()).toEqual(['gebruikers', 'rollen'])
      expect(o1.map((i) => i.id).sort()).toEqual(['o1@gebruikers', 'o1@rollen'])
      expect(o1.every((i) => i.logischId === 'o1')).toBe(true)
      expect(o1.find((i) => i.baan === 'gebruikers').rollen).toEqual(['gebruikt'])
      expect(o1.find((i) => i.baan === 'rollen').rollen).toEqual(['beheert'])
      // Beide instances krijgen een baan-positie (distinct).
      const pos = w.vm._swimlanePositions()
      expect(pos['o1@gebruikers']).toBeDefined()
      expect(pos['o1@rollen']).toBeDefined()
      expect(pos['o1@gebruikers'].y).not.toBe(pos['o1@rollen'].y)
    })

    it('(b) instances delen de ENE stijlbron: identiek uiterlijk op id/logischId/rollen na', async () => {
      const w = await mountRolbanen()
      const els = w.vm._elementen ? w.vm._elementen() : null
      // _elementen is niet exposed — leid dezelfde data af via de laatste cy-add.
      const inst = cytoscape.mock.results.at(-1).value
      const elementen = els || inst.add.mock.calls.at(-1)[0]
      const o1s = elementen.filter((el) => el.data?.logischId === 'o1' && !el.data.source)
      expect(o1s.length).toBe(2)
      const kaal = ({ id, logischId, rollen, ...rest }) => rest
      expect(JSON.stringify(kaal(o1s[0].data))).toBe(JSON.stringify(kaal(o1s[1].data)))
    })

    it('(c) rol-edges hangen aan de instance van hun eigen ring; leverancier krijgt tag "levert"', async () => {
      const w = await mountRolbanen()
      const edges = w.vm.instanceProjectie.edges
      expect(edges.find((e) => e.ring === 'gebruikt').bron_id).toBe('o1@gebruikers')
      expect(edges.find((e) => e.ring === 'rollen').bron_id).toBe('o1@rollen')
      // lev1 heeft één pet → houdt de logische id; baan = rollen, tag = levert.
      const lev = instVan(w, 'lev1')
      expect(lev.length).toBe(1)
      expect(lev[0].id).toBe('lev1')
      expect(lev[0].baan).toBe('rollen')
      expect(lev[0].rollen).toEqual(['levert'])
      expect(edges.find((e) => e.relatietype === 'leverancier').doel_id).toBe('lev1')
    })

    it('(d) identiteitsbanen strikt één keer: component en contract hebben precies één instance', async () => {
      const w = await mountRolbanen()
      expect(instVan(w, 'a1').length).toBe(1)
      expect(instVan(w, 'k1').length).toBe(1)
      expect(instVan(w, 'k1')[0].baan).toBe('contracten')
    })

    it('(e) buiten Lagen (Overzicht) géén instance-duplicaten: projectie = identiteit', async () => {
      const w = await mountRolbanen()
      w.vm.toonOverzicht()
      await flushPromises()
      const p = w.vm.instanceProjectie
      expect(p.instances.every((i) => i.id === i.logischId && !String(i.id).includes('@'))).toBe(true)
      expect(p.edges.every((e) => !String(e.bron_id).includes('@') && !String(e.doel_id).includes('@'))).toBe(true)
    })

    it('(f) partij zonder rol → Rollen & beheer, zonder rol-tag (besluit B)', async () => {
      const w = await mountRolbanen()
      // LI036 ring-uit-wint — p0 is een échte gap (geen enkele relatie) → zichtbaar via de toggle.
      await w.find('[data-testid="lk-registratiegaps"]').setValue(true)
      await flushPromises()
      const p0 = instVan(w, 'p0')
      expect(p0.length).toBe(1)
      expect(p0[0].baan).toBe('rollen')
      expect(p0[0].rollen).toEqual([]) // geen rollen = geen tag (tags volgen inst.rollen)
    })

    it('rol-tag deelt de dim-staat van zijn knoop (leest lk-dim van het cy-element, geen kopie)', async () => {
      const w = await mountRolbanen()
      const inst = cytoscape.mock.results.at(-1).value
      const fake = (dim) => ({ length: 1, hasClass: (c) => c === 'lk-dim' && dim, renderedBoundingBox: () => ({ x1: 0, x2: 20, y1: 0, y2: 30 }) })
      inst._els.set('o1@gebruikers', fake(false)) // opgelicht → tag vol
      inst._els.set('o1@rollen', fake(true))      // gedimd → tag dimt mee
      inst._els.set('lev1', fake(true))
      w.vm._pasDim() // de dim-eigenaar synct de tag-overlay als laatste stap
      await flushPromises()
      const perId = Object.fromEntries(w.vm.rolTagPx.map((t) => [t.id, t.dim]))
      expect(perId['o1@gebruikers']).toBe(false)
      expect(perId['o1@rollen']).toBe(true)
      expect(perId['lev1']).toBe(true)
    })

    it('popup-rolcontext: partij in Lagen toont haar rollen; buiten Lagen leeg', async () => {
      const w = await mountRolbanen()
      await w.vm.openNodePopup('o1')
      await flushPromises()
      // Zonder tap-context (geen aangeklikte instance) staan alle rollen onder "Rollen:".
      expect(w.vm.popupRolActief).toEqual([])
      expect([...w.vm.popupRolOverig].sort()).toEqual(['beheert', 'gebruikt'])
      expect(w.find('[data-testid="lk-popup-rollen"]').exists()).toBe(true)
      expect(w.find('[data-testid="lk-popup-rol-gebruikt"]').exists()).toBe(true)
      w.vm.sluitPopup()
      w.vm.toonOverzicht()
      await flushPromises()
      await w.vm.openNodePopup('o1')
      await flushPromises()
      expect(w.vm.popupRolActief).toEqual([])
      expect(w.vm.popupRolOverig).toEqual([]) // rolcontext is Lagen-only
    })
  })

  // ── LI036 — maatwissel (Vergroten/Verkleinen): herfit op bestaande posities, géén re-layout ──
  describe('LI036 — maatwissel (Vergroten/Verkleinen)', () => {
    it('toggle hertekent NIET; het ene maatwissel-pad doet resize + dezelfde fit als _naLayout', async () => {
      const { w } = await mountView()
      const inst = cytoscape.mock.results.at(-1).value
      const addsVoor = inst.add.mock.calls.length
      inst.resize.mockClear()
      inst.fit.mockClear()
      w.vm.toggleFullscreen()
      await flushPromises()
      expect(w.vm.fullscreen).toBe(true)
      // Géén re-layout/hertekening door de toggle zelf (indeling/posities blijven staan).
      expect(inst.add.mock.calls.length).toBe(addsVoor)
      // De ResizeObserver-callback (_pasCanvasMaat) = resize + exact de _naLayout-fit (padding 50).
      w.vm._pasCanvasMaat()
      expect(inst.resize).toHaveBeenCalled()
      expect(inst.fit).toHaveBeenCalledWith(undefined, 50)
      // Terugschakelen: idem — geen redraw.
      w.vm.toggleFullscreen()
      await flushPromises()
      expect(w.vm.fullscreen).toBe(false)
      expect(inst.add.mock.calls.length).toBe(addsVoor)
    })
  })

  // ── LI036 slice 2 — proceslaan + ring "Processen" ──
  describe('LI036 slice 2 — proceslaan + ring Processen', () => {
    // LI037 fase 1-datavorm: de VOLLEDIGE subboom als knopen (incl. de ondersteuningsloze
    // schakel pr4), hiërarchie-edges kind→ouder, en vervult-edges op het GEREGISTREERDE
    // (deel)proces — twee bomen (Vergunningverlening 3 niveaus + Burgerzaken 2 niveaus).
    const PROCES_GRAF = () => ({
      nodes: [
        { id: 'a1', naam: 'Zaaksysteem', element_type: 'applicatie', laag: 'application', lifecycle_status: 'concept', blokkades_open: 0 },
        { id: 'a2', naam: 'DMS', element_type: 'applicatie', laag: 'application', lifecycle_status: 'concept', blokkades_open: 0 },
        { id: 'pr1', naam: 'Vergunningverlening', element_type: 'proces', laag: 'business', archimate_element: 'business_process', blokkades_open: 0 },
        { id: 'pr2', naam: 'Aanvraag behandelen', element_type: 'proces', laag: 'business', archimate_element: 'business_process', blokkades_open: 0 },
        { id: 'pr3', naam: 'Besluit vastleggen', element_type: 'proces', laag: 'business', archimate_element: 'business_process', blokkades_open: 0 },
        { id: 'pr4', naam: 'Bezwaar behandelen', element_type: 'proces', laag: 'business', archimate_element: 'business_process', blokkades_open: 0 },
        { id: 'pr5', naam: 'Burgerzaken', element_type: 'proces', laag: 'business', archimate_element: 'business_process', blokkades_open: 0 },
        { id: 'pr6', naam: 'Verhuizing verwerken', element_type: 'proces', laag: 'business', archimate_element: 'business_process', blokkades_open: 0 },
      ],
      edges: [
        { bron_id: 'a1', doel_id: 'a2', relatietype: 'flow', label: 'koppeling', ring: 'applicaties' },
        { bron_id: 'a1', doel_id: 'pr2', relatietype: 'procesvervulling', label: 'vervult', ring: 'processen', aantal: 2,
          herkomst: [
            { proces_id: 'pr2', proces_naam: 'Aanvraag behandelen', applicatiefunctie_label: 'Registreren' },
            { proces_id: 'pr2', proces_naam: 'Aanvraag behandelen', applicatiefunctie_label: 'Raadplegen' },
          ] },
        { bron_id: 'a2', doel_id: 'pr3', relatietype: 'procesvervulling', label: 'Registreren', ring: 'processen', aantal: 1,
          herkomst: [{ proces_id: 'pr3', proces_naam: 'Besluit vastleggen', applicatiefunctie_label: 'Registreren' }] },
        { bron_id: 'a2', doel_id: 'pr6', relatietype: 'procesvervulling', label: 'Registreren', ring: 'processen', aantal: 1,
          herkomst: [{ proces_id: 'pr6', proces_naam: 'Verhuizing verwerken', applicatiefunctie_label: 'Registreren' }] },
        { bron_id: 'pr2', doel_id: 'pr1', relatietype: 'proces_hierarchie', label: 'onderdeel van', ring: 'processen' },
        { bron_id: 'pr3', doel_id: 'pr2', relatietype: 'proces_hierarchie', label: 'onderdeel van', ring: 'processen' },
        { bron_id: 'pr4', doel_id: 'pr1', relatietype: 'proces_hierarchie', label: 'onderdeel van', ring: 'processen' },
        { bron_id: 'pr6', doel_id: 'pr5', relatietype: 'proces_hierarchie', label: 'onderdeel van', ring: 'processen' },
      ],
    })
    async function mountProces() {
      zetGraf(PROCES_GRAF())
      const { w } = await mountView()
      return w
    }

    it('(a+b) proces-knoop valt in de eigen proceslaan; de laan staat bovenaan', async () => {
      const w = await mountProces()
      expect(w.vm._laneVan({ element_type: 'proces', laag: 'business' })).toBe('processen')
      w.vm.toonLagen()
      await flushPromises()
      expect(w.vm.laneBanden[0].key).toBe('processen')
      const inst = w.vm.instanceProjectie.instances.find((i) => i.logischId === 'pr1')
      expect(inst.baan).toBe('processen')
      // (d) processen blijven tagloos (geen rol-instance-expansie).
      expect(inst.rollen).toEqual([])
      expect(inst.id).toBe('pr1') // identiteits-instance, geen expansie
    })

    it('(c) ring "Processen" default aan; uit → proces-knoop + vervult-lijn weg ("ring uit wint"), aan → terug', async () => {
      const w = await mountProces()
      expect(w.vm.ringAan.has('processen')).toBe(true) // default aan (niet in RING_DEFAULT_UIT)
      expect(getekendeIds(w)).toContain('pr1')
      expect(w.vm.zichtbareEdges.some((e) => e.ring === 'processen')).toBe(true)
      await w.find('[data-testid="lk-ring-processen"]').trigger('change') // ring UIT
      await flushPromises()
      expect(getekendeIds(w)).not.toContain('pr1') // alleen-via-processen-ring → knoop weg
      // LI037 — de HELE keten verdwijnt: ook deelprocessen, de gap-schakel en de hiërarchie-lijnen.
      expect(getekendeIds(w)).not.toContain('pr2')
      expect(getekendeIds(w)).not.toContain('pr4')
      expect(w.vm.zichtbareEdges.some((e) => e.relatietype === 'proces_hierarchie')).toBe(false)
      expect(w.vm.zichtbareEdges.some((e) => e.ring === 'processen')).toBe(false)
      await w.find('[data-testid="lk-ring-processen"]').trigger('change') // weer AAN
      await flushPromises()
      expect(getekendeIds(w)).toContain('pr1')
    })

    it('(e) proces zichtbaar in Overzicht én Lagen (geen weergave-conditie)', async () => {
      const w = await mountProces()
      expect(getekendeIds(w)).toContain('pr1') // Overzicht
      w.vm.toonLagen()
      await flushPromises()
      expect(getekendeIds(w)).toContain('pr1') // Lagen
      w.vm.toonOverzicht()
      await flushPromises()
      expect(getekendeIds(w)).toContain('pr1')
    })

    it('proces-knoop: afgeronde rechthoek + verloop-pijl-marker, type-regel "Proces", popup + doorklik', async () => {
      const w = await mountProces()
      const pr = w.vm.grafNodes.find((n) => n.id === 'pr1')
      const d = w.vm._nodeData(pr)
      // LI036 — proces = round-rectangle; het onderscheid met de component-rechthoek is de
      // verloop-pijl-marker in de gedeelde stijlbron (CY_STYLE-selector op element_type).
      expect(d.shape).toBe('round-rectangle')
      const marker = w.vm.CY_STYLE.find((r) => r.selector === 'node[element_type = "proces"]')
      expect(marker).toBeTruthy()
      expect(marker.style['background-image']).toContain('data:image/svg+xml')
      // Geen tweede type deelt de round-rectangle zónder onderscheid: alle andere vormen wijken af.
      const vormen = ['gebruikersgroep', 'contract'].map((et) => w.vm._vormVoorType({ element_type: et }))
      vormen.push(w.vm._vormVoorType({ element_type: 'partij', soort: 'organisatie' }))
      vormen.push(w.vm._vormVoorType({ element_type: 'partij', soort: 'persoon' }))
      vormen.push(w.vm._vormVoorType({ element_type: 'partij', soort: 'externe_partij' }))
      vormen.push(w.vm._vormVoorType({ element_type: 'database', laag: 'technology' }))
      expect(vormen).not.toContain('round-rectangle')
      expect(d.label).toContain('\nProces')
      await w.vm.openNodePopup('pr1')
      await flushPromises()
      expect(api.processen.haal).toHaveBeenCalledWith('pr1')
      expect(w.vm.popupKind).toBe('node')
      expect(w.find('[data-testid="lk-popup-titel"]').text()).toBe('Vergunningverlening')
      expect(w.find('[data-testid="lk-popup-velden"]').text()).toContain('Primair proces')
      expect(w.vm.popupActies.some((a) => a.label === 'Open proces →')).toBe(true)
    })

    // ── LI037 fase 2 — proceszone als boom + guards ──
    it('LI037 (boom) — rij = diepte, bomen gegroepeerd naast elkaar, distinct + deterministisch', async () => {
      const w = await mountProces()
      w.vm.toonLagen()
      await flushPromises()
      const pos = w.vm._swimlanePositions()
      // Rij = diepte: wortel boven, elk niveau een rij lager; gelijke diepte = gelijke rij.
      expect(pos.pr1.y).toBeLessThan(pos.pr2.y)
      expect(pos.pr2.y).toBeLessThan(pos.pr3.y)
      expect(pos.pr4.y).toBe(pos.pr2.y)
      expect(pos.pr5.y).toBe(pos.pr1.y)
      expect(pos.pr6.y).toBe(pos.pr2.y)
      // Groepering per boom: de Burgerzaken-boom (alfabetisch eerst) staat volledig links van de
      // Vergunningverlening-boom — geen overloop.
      const boomV = ['pr1', 'pr2', 'pr3', 'pr4'].map((id) => pos[id].x)
      const boomB = ['pr5', 'pr6'].map((id) => pos[id].x)
      expect(Math.max(...boomB)).toBeLessThan(Math.min(...boomV))
      // Distinct + deterministisch (twee aanroepen identiek).
      const ids = ['pr1', 'pr2', 'pr3', 'pr4', 'pr5', 'pr6']
      const sig = ids.map((id) => `${pos[id].x},${pos[id].y}`)
      expect(new Set(sig).size).toBe(ids.length)
      const pos2 = w.vm._swimlanePositions()
      expect(ids.map((id) => `${pos2[id].x},${pos2[id].y}`)).toEqual(sig)
      // De andere banen blijven het wrap-grid (a1/a2 in de componenten-baan, één rij).
      expect(pos.a1.y).toBe(pos.a2.y)
    })

    it('LI037 (cue) — "geen ondersteunend systeem": subboom-afgeleid, rand + popup, los van de gaps-toggle', async () => {
      const w = await mountProces()
      const node = (id) => w.vm.grafNodes.find((n) => n.id === id)
      expect(w.vm.toonRegistratiegaps).toBe(false) // de cue hangt hier bewust NIET aan
      expect(w.vm._nodeData(node('pr4')).procesGap).toBe(true) // Bezwaar behandelen: niets eronder
      expect(w.vm._nodeData(node('pr2')).procesGap).toBeUndefined() // eigen vervulling
      expect(w.vm._nodeData(node('pr1')).procesGap).toBeUndefined() // gedekt via zijn deelprocessen
      expect(w.vm._nodeData(node('pr5')).procesGap).toBeUndefined() // gedekt via pr6
      // Eigen rustige CY-randstijl (geen alarmkleur — border-kleur blijft data(border)).
      const stijl = w.vm.CY_STYLE.find((r) => r.selector === 'node[?procesGap]')
      expect(stijl).toBeTruthy()
      expect(stijl.style['border-style']).toBe('dashed')
      // De popup benoemt het gat in woorden; een gedekt proces niet.
      await w.vm.openNodePopup('pr4')
      await flushPromises()
      expect(w.find('[data-testid="lk-popup-geen-systeem"]').exists()).toBe(true)
      await w.vm.openNodePopup('pr2')
      await flushPromises()
      expect(w.find('[data-testid="lk-popup-geen-systeem"]').exists()).toBe(false)
    })

    it('LI037 (guard) — hiërarchie-lijnen tellen nooit als vervuller; de toggle voegt geen proces toe', async () => {
      const w = await mountProces()
      // pr1 draagt ALLEEN hiërarchie-edges (pr2/pr4 wijzen ernaar) → geen vervullers, actie inert.
      await w.vm.openNodePopup('pr1')
      await flushPromises()
      expect(w.vm.popupVervuldDoor).toEqual([])
      expect(w.vm.popupVervulActie.modus).toBe('geen')
      // pr2: alléén de échte component; de toggle voegt a1 toe en nooit een proces-id.
      await w.vm.openNodePopup('pr2')
      await flushPromises()
      expect(w.vm.popupVervuldDoor.map((c) => c.naam)).toEqual(['Zaaksysteem'])
      await w.find('[data-testid="lk-popup-vervul"]').trigger('click')
      await flushPromises()
      expect(w.vm.actieveSet.has('a1')).toBe(true)
      expect([...w.vm.actieveSet].some((id) => String(id).startsWith('pr'))).toBe(false)
    })

    // ── LI037 fase 3 — proces-ingang (één gedeeld handoff, ADR-034 besluit 4) ──
    // Eigen mount ZONDER de strategie-A-hele-landschap-laad (die zou de handoff-weergave overschrijven;
    // in de echte flow komt de gebruiker binnen via het handoff, niet via "toon het hele landschap").
    async function mountProcesHandoff() {
      zetGraf(PROCES_GRAF())
      const { w } = await mountView({ heleLandschap: false })
      return w
    }

    it('LI037 (handoff) — proces-variant opent in LAGEN met de herkomst benoemd; consume-once', async () => {
      neemKaartHandoff.mockReturnValueOnce({
        componentIds: ['a1'],
        weergave: 'lagen',
        procesIngang: { wortelId: 'pr1', wortelNaam: 'Vergunningverlening', herkomstId: 'pr3', herkomstNaam: 'Besluit vastleggen' },
      })
      const w = await mountProcesHandoff()
      expect(w.vm.weergave).toBe('lagen') // niet de praatplaat-dwang van ?center
      expect(w.vm.actieveSet.has('a1')).toBe(true)
      expect(w.vm.beginschermOpen).toBe(false)
      const marker = w.find('[data-testid="lk-proces-herkomst"]')
      expect(marker.text()).toContain('Proceslandschap: Vergunningverlening')
      expect(marker.text()).toContain('via Besluit vastleggen')
      // 3b/3d (herzien) — GEDIMD MET FOCUS: de herkomst-knoop is de actieve (oranje) selectie
      // (de bestaande enkelklik-mechaniek dimt al het niet-directe) en wordt gecentreerd.
      expect(w.vm.geselecteerdNodeId).toBe('pr3')
      expect(w.vm._selectieZonderDim).toBe(null) // dim ACTIEF (geen onderdrukking bij een deelproces)
      expect(w.vm._edgeGehighlight({ bron_id: 'a2', doel_id: 'pr3' })).toBe(true)
      expect(w.vm._centreerNaLayoutId).toBe('pr3') // one-shot; geconsumeerd in _naLayout (echte cy)
      // Wisbaar met × — selectie én dim-focus weg (plaat neutraal).
      await w.find('[data-testid="lk-proces-herkomst-wis"]').trigger('click')
      expect(w.find('[data-testid="lk-proces-herkomst"]').exists()).toBe(false)
      expect(w.vm.geselecteerdNodeId).toBe(null)
      // Consume-once: een volgende mount zonder handoff springt niet (default-mock → null).
      const w2 = await mountProcesHandoff()
      expect(w2.vm.weergave).toBe('overzicht')
      expect(w2.find('[data-testid="lk-proces-herkomst"]').exists()).toBe(false)
    })

    it('LI037 (handoff) — hoofdproces-ingang: boom in Lagen, ZONDER aparte deelproces-herkomst', async () => {
      neemKaartHandoff.mockReturnValueOnce({
        componentIds: ['a1', 'a2'],
        weergave: 'lagen',
        procesIngang: { wortelId: 'pr1', wortelNaam: 'Vergunningverlening', herkomstId: null, herkomstNaam: null },
      })
      const w = await mountProcesHandoff()
      expect(w.vm.weergave).toBe('lagen')
      const marker = w.find('[data-testid="lk-proces-herkomst"]')
      expect(marker.text()).toContain('Proceslandschap: Vergunningverlening')
      expect(marker.text()).not.toContain('via')
      // 3d (herzien) — hoofdproces-ingang: de wortel is de GESELECTEERDE (oranje) knoop en wordt
      // gecentreerd, maar ZONDER dim (de hele boom blijft zichtbaar): de zonder-dim-onderdrukking
      // staat op precies deze selectie.
      expect(w.vm.geselecteerdNodeId).toBe('pr1')
      expect(w.vm._selectieZonderDim).toBe('pr1') // selectie-highlight zonder dim (schone splitsing)
      expect(w.vm._centreerNaLayoutId).toBe('pr1')
      // Geen dim → geen "Toon hele landschap"-knop in de popup van de wortel (niets op te heffen).
      await w.vm.openNodePopup('pr1')
      await flushPromises()
      expect(w.find('[data-testid="lk-popup-toon-landschap"]').exists()).toBe(false)
      // Chip-× wist de ingang-selectie mee (levensduur = die van de chip).
      await w.find('[data-testid="lk-proces-herkomst-wis"]').trigger('click')
      expect(w.vm.geselecteerdNodeId).toBe(null)
      expect(w.vm._selectieZonderDim).toBe(null)
      // 3d — het blauwe accent bestaat niet meer: geen CY-laag en geen data-veld.
      expect(w.vm.CY_STYLE.some((r) => r.selector === 'node[?procesHerkomst]')).toBe(false)
      const node = (id) => w.vm.grafNodes.find((n) => n.id === id)
      expect('procesHerkomst' in w.vm._nodeData(node('pr1'))).toBe(false)
    })

    it('LI037-3b (weg terug) — "Toon hele landschap" in de herkomst-popup heft de dim op; accent + chip blijven', async () => {
      neemKaartHandoff.mockReturnValueOnce({
        componentIds: ['a1'],
        weergave: 'lagen',
        procesIngang: { wortelId: 'pr1', wortelNaam: 'Vergunningverlening', herkomstId: 'pr3', herkomstNaam: 'Besluit vastleggen' },
      })
      const w = await mountProcesHandoff()
      // De knop hoort alléén in de popup van de HERKOMST-knoop (niet bij een ander proces).
      await w.vm.openNodePopup('pr1')
      await flushPromises()
      expect(w.find('[data-testid="lk-popup-toon-landschap"]').exists()).toBe(false)
      await w.vm.openNodePopup('pr3')
      await flushPromises()
      const knop = w.find('[data-testid="lk-popup-toon-landschap"]')
      expect(knop.exists()).toBe(true)
      await knop.trigger('click')
      await flushPromises()
      // 3d — alléén de dim gaat weg: de herkomst blijft de geselecteerde (oranje) knoop tot de
      // gebruiker elders klikt; de chip blijft de herkomst benoemen.
      expect(w.vm.geselecteerdNodeId).toBe('pr3')
      expect(w.vm._selectieZonderDim).toBe('pr3') // dim onderdrukt voor precies deze selectie
      expect(w.find('[data-testid="lk-proces-herkomst"]').exists()).toBe(true)
      // Niets meer op te heffen → de knop is weg.
      expect(w.find('[data-testid="lk-popup-toon-landschap"]').exists()).toBe(false)
      // Een eigen klik elders = normale enkelklik-semantiek: selectie verspringt, dim weer normaal.
      w.vm.inspecteerNode('pr1')
      await flushPromises()
      expect(w.vm.geselecteerdNodeId).toBe('pr1')
      expect(w.vm._selectieZonderDim).toBe(null)
    })

    it('LI037-3d (combi) — gap-cue + oranje selectie op één knoop: selectie wint zolang hij staat, gap-info blijft in de popup', async () => {
      neemKaartHandoff.mockReturnValueOnce({
        componentIds: ['a1'],
        weergave: 'lagen',
        procesIngang: { wortelId: 'pr1', wortelNaam: 'Vergunningverlening', herkomstId: 'pr4', herkomstNaam: 'Bezwaar behandelen' },
      })
      const w = await mountProcesHandoff()
      const pr4 = w.vm.grafNodes.find((n) => n.id === 'pr4')
      // De gap-cue (fase 2) blijft in de data; de herkomst is de actieve selectie (dim-focus).
      expect(w.vm._nodeData(pr4).procesGap).toBe(true)
      expect(w.vm.geselecteerdNodeId).toBe('pr4')
      // Bestaande stijl-regel: zolang de knoop geselecteerd is wint hl-node (solid oranje) van de
      // gap-dash; verspringt de selectie, dan is de dashed gap-rand weer zichtbaar. De popup
      // benoemt het gat áltijd in woorden — de informatie raakt nooit zoek.
      const selectors = w.vm.CY_STYLE.map((r) => r.selector)
      expect(selectors.indexOf('node.hl-node')).toBeGreaterThan(selectors.indexOf('node[?procesGap]'))
      await w.vm.openNodePopup('pr4')
      await flushPromises()
      expect(w.find('[data-testid="lk-popup-geen-systeem"]').exists()).toBe(true)
    })

    it('LI037 (via proces) — beginscherm-keuze bouwt dezelfde payload en opent Lagen; "Begin opnieuw" wist de markering', async () => {
      api.processen.haal.mockImplementation(async (id) => ({
        pr4: { id: 'pr4', naam: 'Bezwaar behandelen', ouder_id: 'pr1' },
        pr1: { id: 'pr1', naam: 'Vergunningverlening', ouder_id: null },
      }[id]))
      api.processen.rollup.mockResolvedValue([{ component_id: 'a1' }, { component_id: 'a2' }])
      api.procesvervullingen.lijst.mockResolvedValue([{ component_id: 'a1' }])
      const w = await mountProces()
      await w.vm.openViaProces({ id: 'pr4' })
      await flushPromises()
      // Boom-vervullers (rollup ∪ wortel-eigen, dedup) als set; Lagen; herkomst = het deelproces.
      expect(api.processen.rollup).toHaveBeenCalledWith('pr1')
      expect(api.procesvervullingen.lijst).toHaveBeenCalledWith({ proces_id: 'pr1' })
      expect([...w.vm.actieveSet].sort()).toEqual(['a1', 'a2'])
      expect(w.vm.weergave).toBe('lagen')
      expect(w.find('[data-testid="lk-proces-herkomst"]').text()).toContain('via Bezwaar behandelen')
      expect(w.vm.beginschermOpen).toBe(false)
      // 3b — deelproces-keuze op het beginscherm opent óók gedimd-met-focus op de herkomst.
      expect(w.vm.geselecteerdNodeId).toBe('pr4')
      // "Begin opnieuw" = volledige reset, incl. de herkomstmarkering én de dim-focus.
      w.vm.wisSet()
      await flushPromises()
      expect(w.vm.procesIngang).toBe(null)
      expect(w.vm.geselecteerdNodeId).toBe(null)
    })

    it('LI037 (via proces) — boom zonder ondersteunende systemen: rustige melding, geen lege kaart', async () => {
      api.processen.haal.mockResolvedValue({ id: 'px', naam: 'Leeg proces', ouder_id: null })
      api.processen.rollup.mockResolvedValue([])
      api.procesvervullingen.lijst.mockResolvedValue([])
      const w = await mountProces()
      const setVoor = new Set(w.vm.actieveSet)
      await w.vm.openViaProces({ id: 'px' })
      await flushPromises()
      expect([...w.vm.actieveSet]).toEqual([...setVoor]) // set onaangeroerd
      expect(w.vm.weergave).toBe('overzicht') // geen weergavesprong
      expect(w.find('[data-testid="lk-proces-herkomst"]').exists()).toBe(false)
    })

    it('LI037 (popup) — hiërarchie-lijn → "Onderdeel van"; vervult-lijn → "Vervult" op het geregistreerde proces', async () => {
      const w = await mountProces()
      const hier = w.vm.grafEdges.find((e) => e.relatietype === 'proces_hierarchie' && e.bron_id === 'pr2')
      await w.vm.openEdgePopup(hier)
      await flushPromises()
      expect(w.vm.popupTitel).toBe('Onderdeel van')
      const velden = Object.fromEntries(w.vm.popupVelden.map((v) => [v.label, v.waarde]))
      expect(velden['Deelproces']).toBe('Aanvraag behandelen')
      expect(velden['Onderdeel van']).toBe('Vergunningverlening')
      const vervult = w.vm.grafEdges.find((e) => e.relatietype === 'procesvervulling' && e.bron_id === 'a1')
      await w.vm.openEdgePopup(vervult)
      await flushPromises()
      expect(w.vm.popupTitel).toBe('Vervult')
      const v2 = Object.fromEntries(w.vm.popupVelden.map((v) => [v.label, v.waarde]))
      expect(v2['Proces']).toBe('Aanvraag behandelen')
      expect(v2['Component']).toBe('Zaaksysteem')
    })
  })

  // ── LI036 slice 2 · stap 3 — aantal-badge + herkomst + "voeg vervullende componenten toe" ──
  describe('LI036 slice 2 stap 3 — badge/herkomst/set-actie', () => {
    const STAP3_GRAF = () => ({
      nodes: [
        { id: 'a1', naam: 'Zaaksysteem', element_type: 'applicatie', laag: 'application', lifecycle_status: 'concept', blokkades_open: 0 },
        { id: 'a2', naam: 'DMS', element_type: 'applicatie', laag: 'application', lifecycle_status: 'concept', blokkades_open: 0 },
        { id: 'pr1', naam: 'Vergunningverlening', element_type: 'proces', laag: 'business', archimate_element: 'business_process', blokkades_open: 0 },
        // Ongerelateerd aan pr1 (wel vervuller van pr2) — voor de ongedaan-maken-/per-proces-tests.
        { id: 'x-vrij', naam: 'Vrij Systeem', element_type: 'applicatie', laag: 'application', lifecycle_status: 'concept', blokkades_open: 0 },
        { id: 'pr2', naam: 'Burgerzaken', element_type: 'proces', laag: 'business', archimate_element: 'business_process', blokkades_open: 0 },
      ],
      edges: [
        { bron_id: 'a1', doel_id: 'a2', relatietype: 'flow', label: 'koppeling', ring: 'applicaties', richting: 'eenrichting', protocol: 'rest' },
        // LI037 fase-1-datavorm: de bundel staat op het GEREGISTREERDE proces; herkomst = de
        // functie-uitsplitsing van dat éne paar (geen herkomst uit andere processen meer).
        { bron_id: 'a1', doel_id: 'pr1', relatietype: 'procesvervulling', label: 'vervult', ring: 'processen', aantal: 2,
          herkomst: [
            { proces_id: 'pr1', proces_naam: 'Vergunningverlening', applicatiefunctie_label: 'Registreren' },
            { proces_id: 'pr1', proces_naam: 'Vergunningverlening', applicatiefunctie_label: 'Raadplegen' },
          ] },
        { bron_id: 'a2', doel_id: 'pr1', relatietype: 'procesvervulling', label: 'Archiveren', ring: 'processen', aantal: 1,
          herkomst: [{ proces_id: 'pr1', proces_naam: 'Vergunningverlening', applicatiefunctie_label: 'Archiveren' }] },
        { bron_id: 'x-vrij', doel_id: 'pr2', relatietype: 'procesvervulling', label: 'Registreren', ring: 'processen', aantal: 1,
          herkomst: [{ proces_id: 'pr2', proces_naam: 'Burgerzaken', applicatiefunctie_label: 'Registreren' }] },
      ],
    })
    async function mountStap3() {
      zetGraf(STAP3_GRAF())
      const { w } = await mountView()
      return w
    }

    it('(a) vervult-lijn aantal>1 → badge "N×" in het label (flow-patroon); aantal 1 → geen badge', async () => {
      const w = await mountStap3()
      const bundel = w.vm._edgeData({ bron_id: 'a1', doel_id: 'pr1', relatietype: 'procesvervulling', label: 'vervult', ring: 'processen', aantal: 3 }, 0)
      expect(bundel.label).toBe('vervult · 3×')
      const enkel = w.vm._edgeData({ bron_id: 'a2', doel_id: 'pr1', relatietype: 'procesvervulling', label: 'Archiveren', ring: 'processen', aantal: 1 }, 1)
      expect(enkel.label).toBe('Archiveren')
      // (d) geen regressie op de flow-label-opbouw.
      const flow = w.vm._edgeData({ bron_id: 'a1', doel_id: 'a2', relatietype: 'flow', label: 'koppeling', ring: 'applicaties', richting: 'eenrichting', protocol: 'rest', aantal: 1 }, 2)
      expect(flow.label).toBe('koppeling · REST · →')
    })

    it('(b) proces-popup: scanbare componentnamen; herkomst inklapbaar per component (dicht by default)', async () => {
      const w = await mountStap3()
      await w.vm.openNodePopup('pr1')
      await flushPromises()
      // Kop + namen scanbaar; géén herkomst-muur in de dl-velden.
      expect(w.find('[data-testid="lk-popup-vervuld"]').text()).toContain('Vervuld door: 2 componenten')
      expect(w.vm.popupVelden.some((v) => v.label === 'Vervuld door')).toBe(false)
      const namen = w.vm.popupVervuldDoor.map((c) => c.naam)
      expect(namen).toEqual(['DMS', 'Zaaksysteem'])
      // Herkomst per component (LI037: de functie-uitsplitsing van dít paar), achter een
      // <details> (standaard dicht).
      const zaak = w.find('[data-testid="lk-popup-vervuld-a1"]')
      expect(zaak.element.tagName).toBe('DETAILS')
      expect(zaak.element.open).toBe(false)
      const zaakData = w.vm.popupVervuldDoor.find((c) => c.id === 'a1')
      expect(zaakData.herkomst).toEqual([
        { label: 'Vergunningverlening', waarde: 'Registreren, Raadplegen' },
      ])
      // Uitklappen toont de herkomst-regels van díe component.
      zaak.element.open = true
      await flushPromises()
      expect(zaak.text()).toContain('Vergunningverlening · Registreren, Raadplegen')
    })

    it('(b3) herkomst None/leeg → alleen de componentnaam, geen uitklap', async () => {
      const g = STAP3_GRAF()
      g.edges[2].herkomst = null // DMS-edge zonder herkomst
      zetGraf(g)
      const { w } = await mountView()
      await w.vm.openNodePopup('pr1')
      await flushPromises()
      const dms = w.find('[data-testid="lk-popup-vervuld-a2"]')
      expect(dms.element.tagName).toBe('P') // platte naam, geen <details>
      expect(dms.text()).toBe('DMS')
    })

    it('(b2) vervult-lijn-popup toont de herkomst van díe bundel, gegroepeerd per deelproces', async () => {
      const w = await mountStap3()
      const edge = w.vm.grafEdges.find((e) => e.ring === 'processen' && e.bron_id === 'a1')
      await w.vm.openEdgePopup(edge)
      await flushPromises()
      const per = Object.fromEntries(w.vm.popupVelden.map((v) => [v.label, v.waarde]))
      expect(w.vm.popupTitel).toBe('Vervult')
      expect(per['Component']).toBe('Zaaksysteem')
      expect(per['Proces']).toBe('Vergunningverlening') // LI037 — de bundel staat op het geregistreerde proces
      expect(per['Koppelingen']).toBe('2')
      expect(per['Vergunningverlening']).toBe('Registreren, Raadplegen')
    })

    it('(c) vervul-toggle: toevoegen mét highlight → live om naar "− Verwijder"; alleen de groep eruit; weergave blijft', async () => {
      const w = await mountStap3()
      w.vm.toonLagen()
      await flushPromises()
      // Randgeval-default: a1 zat al (los van dit proces) in de set → telt mee in de groep.
      w.vm.voegComponentenToeAanSet([{ id: 'a1' }])
      // Plus een ongerelateerd set-lid dat NOOIT geraakt mag worden.
      w.vm.voegComponentenToeAanSet([{ id: 'x-vrij' }])
      await flushPromises()
      await w.vm.openNodePopup('pr1')
      await flushPromises()
      const knop = () => w.find('[data-testid="lk-popup-vervul"]')
      expect(knop().text()).toBe('+ Voeg vervullende componenten toe (1)') // alleen a2 ontbreekt nog
      await knop().trigger('click')
      await flushPromises()
      expect(w.vm.actieveSet.has('a1')).toBe(true)
      expect(w.vm.actieveSet.has('a2')).toBe(true)
      // Highlight van de verandering: het bestaande selectie-pad staat op het proces → het
      // vervul-web (incl. de toegevoegde knopen) licht op.
      expect(w.vm.geselecteerdNodeId).toBe('pr1')
      expect(w.vm._edgeGehighlight({ bron_id: 'a1', doel_id: 'pr1' })).toBe(true)
      // 2a — geen weergavesprong.
      expect(w.vm.weergave).toBe('lagen')
      // LIVE omgeklapt naar de verwijder-modus (zonder heropenen).
      expect(knop().text()).toBe('− Verwijder vervullende componenten')
      expect(knop().attributes('disabled')).toBeUndefined()
      // HERZIEN BESLUIT — verwijderen = ongedaan maken van déze knop: alléén a2 (door de knop
      // toegevoegd) gaat weg; a1 (zat er al vóór de klik) en x-vrij (ongerelateerd) blijven.
      await knop().trigger('click')
      await flushPromises()
      expect(w.vm.actieveSet.has('a1')).toBe(true)
      expect(w.vm.actieveSet.has('a2')).toBe(false)
      expect(w.vm.actieveSet.has('x-vrij')).toBe(true)
      expect(w.vm.weergave).toBe('lagen')
      // Toggle terug naar toevoegen, met de resterende telling (alleen a2 ontbreekt).
      expect(knop().text()).toBe('+ Voeg vervullende componenten toe (1)')
    })

    it('(c1b) gemeld geval: set={A} → +3 → verwijder → exact terug naar {A} (niet leeg)', async () => {
      const w = await mountStap3()
      w.vm.voegComponentenToeAanSet([{ id: 'a1' }]) // vertrekpunt (het "Zaaksysteem"-geval)
      await flushPromises()
      await w.vm.openNodePopup('pr1')
      await flushPromises()
      const knop = () => w.find('[data-testid="lk-popup-vervul"]')
      await knop().trigger('click') // voegt de ontbrekende vervullers toe
      await flushPromises()
      await knop().trigger('click') // ongedaan maken
      await flushPromises()
      expect([...w.vm.actieveSet]).toEqual(['a1']) // het vertrekpunt blijft — geen lege plaat
    })

    it('(c1c) alles zat er al vóór de knop → geen verwijder-modus (niets om ongedaan te maken)', async () => {
      const w = await mountStap3()
      w.vm.voegComponentenToeAanSet([{ id: 'a1' }, { id: 'a2' }]) // gebruiker had beide al
      await flushPromises()
      await w.vm.openNodePopup('pr1')
      await flushPromises()
      const knop = w.find('[data-testid="lk-popup-vervul"]')
      expect(knop.text()).toBe('+ Voeg vervullende componenten toe (0)')
      expect(knop.attributes('disabled')).toBeDefined()
      expect(knop.attributes('title')).toBe('Alle vervullende componenten staan al in beeld')
    })

    it('(c1d) handmatig één knop-toevoeging weghalen → telling/modus kloppen; daarna ongedaan-maken raakt alleen knop-toevoegingen', async () => {
      const w = await mountStap3()
      await w.vm.openNodePopup('pr1')
      await flushPromises()
      const knop = () => w.find('[data-testid="lk-popup-vervul"]')
      await knop().trigger('click') // voegt a1 + a2 toe (beide knop-toevoegingen)
      await flushPromises()
      w.vm.toggleSet('a2') // handmatig één toegevoegde weghalen
      await flushPromises()
      expect(knop().text()).toBe('+ Voeg vervullende componenten toe (1)') // terug naar toevoegen, juiste rest
      await knop().trigger('click') // a2 opnieuw via de knop
      await flushPromises()
      expect(knop().text()).toBe('− Verwijder vervullende componenten')
      await knop().trigger('click')
      await flushPromises()
      expect([...w.vm.actieveSet]).toEqual([]) // beide waren knop-toevoegingen → beide ongedaan
    })

    it('(c1e) per proces bijgehouden: X ongedaan maken laat de toevoeging van Y staan', async () => {
      const w = await mountStap3()
      await w.vm.openNodePopup('pr1')
      await flushPromises()
      const knop = () => w.find('[data-testid="lk-popup-vervul"]')
      await knop().trigger('click') // pr1 → a1 + a2 erbij
      await flushPromises()
      await w.vm.openNodePopup('pr2')
      await flushPromises()
      await knop().trigger('click') // pr2 → x-vrij erbij
      await flushPromises()
      expect(w.vm.actieveSet.has('x-vrij')).toBe(true)
      await w.vm.openNodePopup('pr1')
      await flushPromises()
      await knop().trigger('click') // pr1 ongedaan maken
      await flushPromises()
      expect(w.vm.actieveSet.has('a1')).toBe(false)
      expect(w.vm.actieveSet.has('a2')).toBe(false)
      expect(w.vm.actieveSet.has('x-vrij')).toBe(true) // pr2's toevoeging blijft
      await w.vm.openNodePopup('pr2')
      await flushPromises()
      expect(knop().text()).toBe('− Verwijder vervullende componenten') // pr2-administratie intact
    })

    it('(c2) toggle heen-en-terug herstelt de set-staat exact', async () => {
      const w = await mountStap3()
      await w.vm.openNodePopup('pr1')
      await flushPromises()
      const voor = [...w.vm.actieveSet].sort()
      await w.find('[data-testid="lk-popup-vervul"]').trigger('click') // toevoegen
      await flushPromises()
      await w.find('[data-testid="lk-popup-vervul"]').trigger('click') // verwijderen
      await flushPromises()
      expect([...w.vm.actieveSet].sort()).toEqual(voor)
    })

    it('(d) component-popup (niet-proces) toont géén herkomst-sectie en géén vervul-knop', async () => {
      const w = await mountStap3()
      await w.vm.openNodePopup('a1')
      await flushPromises()
      expect(w.find('[data-testid="lk-popup-vervuld"]').exists()).toBe(false)
      expect(w.find('[data-testid="lk-popup-vervul"]').exists()).toBe(false)
      expect(w.vm.popupVervuldDoor).toEqual([])
      expect(w.vm.popupVervulActie).toBe(null)
    })
  })

  // ── LI036 — organisatiebalk toont alleen in-beeld-organisaties (model i) ──
  describe('LI036 — organisatiebalk (model i)', () => {
    // rid = geladen door de subgraaf-discovery (eigenaar-/hoort-bij-keten) maar zónder zichtbare
    // relatie in deze selectie — het RID-geval. oA is wél in beeld (eigenaar-edge).
    const BALK_GRAF = () => ({
      nodes: [
        { id: 'a1', naam: 'Zaaksysteem', element_type: 'applicatie', laag: 'application', lifecycle_status: 'concept', blokkades_open: 0, eigenaar_organisatie_id: 'oA' },
        { id: 'a2', naam: 'DMS', element_type: 'applicatie', laag: 'application', lifecycle_status: 'concept', blokkades_open: 0 },
        { id: 'oA', naam: 'Gemeente Tiel', element_type: 'partij', laag: 'business', soort: 'organisatie', blokkades_open: 0 },
        { id: 'rid', naam: 'RID Rivierenland', element_type: 'partij', laag: 'business', soort: 'organisatie', blokkades_open: 0 },
      ],
      edges: [
        { bron_id: 'a1', doel_id: 'a2', relatietype: 'flow', label: 'koppeling', ring: 'applicaties' },
        { bron_id: 'oA', doel_id: 'a1', relatietype: 'eigenaar', label: 'is eigendom van', ring: 'eigenaar' },
      ],
    })
    async function mountBalk() {
      zetGraf(BALK_GRAF())
      const { w } = await mountView()
      return w
    }

    it('een geladen-maar-niet-getekende organisatie (RID-geval) staat NIET in de balk — Overzicht én Lagen', async () => {
      const w = await mountBalk()
      expect(w.find('[data-testid="lk-scope-org-oA"]').exists()).toBe(true) // in beeld → in de balk
      expect(w.find('[data-testid="lk-scope-org-rid"]').exists()).toBe(false) // geladen, niet in beeld
      expect(w.vm.organisatiesInBeeld.map((o) => o.id)).toEqual(['oA'])
      // De seed blijft over de VOLLE geladen lijst gaan (rid blijft aangevinkt-in-scope, alleen onzichtbaar).
      expect([...w.vm.scopeOrgs].sort()).toEqual(['oA', 'rid'])
      w.vm.toonLagen()
      await flushPromises()
      expect(w.find('[data-testid="lk-scope-org-oA"]').exists()).toBe(true)
      expect(w.find('[data-testid="lk-scope-org-rid"]').exists()).toBe(false) // cross-view identiek
    })

    it('model i — uitzetten om te focussen blijft omkeerbaar: uitgezette org blijft onaangevinkt in de balk', async () => {
      const w = await mountBalk()
      await w.find('[data-testid="lk-scope-org-oA"]').trigger('change') // oA uit
      await flushPromises()
      // De org-node verdwijnt van de plaat, maar blijft (onaangevinkt) in de balk staan.
      expect(getekendeIds(w)).not.toContain('oA')
      const cb = w.find('[data-testid="lk-scope-org-oA"]')
      expect(cb.exists()).toBe(true)
      expect(cb.element.checked).toBe(false)
      // Weer aanzetten via de balk herstelt de org op de plaat.
      await cb.trigger('change')
      await flushPromises()
      expect(getekendeIds(w)).toContain('oA')
    })

    it('lege balk (geen enkele organisatie in beeld) → korte hint i.p.v. kale ruimte', async () => {
      // Alleen rid geladen (irrelevant voor de selectie) → balk bestaat, lijst leeg → hint.
      const g = BALK_GRAF()
      g.nodes = g.nodes.filter((n) => n.id !== 'oA')
      g.edges = g.edges.filter((e) => e.bron_id !== 'oA')
      zetGraf(g)
      const { w } = await mountView()
      expect(w.find('[data-testid="lk-scopebalk"]').exists()).toBe(true)
      expect(w.vm.organisatiesInBeeld.length).toBe(0)
      expect(w.find('[data-testid="lk-scope-leeg"]').text()).toBe('geen organisatie in beeld')
    })

    it('de balk beweegt mee met de ringen: eigenaar-ring uit → org niet meer in beeld → uit de balk', async () => {
      const w = await mountBalk()
      expect(w.find('[data-testid="lk-scope-org-oA"]').exists()).toBe(true)
      await w.find('[data-testid="lk-ring-eigenaar"]').trigger('change') // enige relevantie-ring van oA uit
      await flushPromises()
      expect(w.find('[data-testid="lk-scope-org-oA"]').exists()).toBe(false) // "ring uit wint" werkt door
      expect(w.find('[data-testid="lk-scope-leeg"]').exists()).toBe(true)
    })
  })

  // ── LI036 — "ring uit wint van gaps": zichtbaar is wat de aanstaande ringen dragen ──
  describe('LI036 — ring uit wint van gaps', () => {
    const RING_GRAF = {
      nodes: [
        { id: 'a1', naam: 'App', element_type: 'applicatie', laag: 'application', lifecycle_status: 'concept', blokkades_open: 0 },
        { id: 'oX', naam: 'Alleen Beheer BV', element_type: 'partij', laag: 'business', soort: 'organisatie', blokkades_open: 0 },
        { id: 'oY', naam: 'Beheer en Eigenaar BV', element_type: 'partij', laag: 'business', soort: 'organisatie', blokkades_open: 0 },
        { id: 'gap1', naam: 'Losse DB', element_type: 'database', laag: 'technology', lifecycle_status: 'concept', blokkades_open: 0 },
        { id: 'los1', naam: 'Categorieloos object' }, // geen element_type → categorie 'overig' (geen ring)
      ],
      edges: [
        { bron_id: 'oX', doel_id: 'a1', relatietype: 'roltoewijzing', label: 'Technisch beheer', ring: 'rollen' },
        { bron_id: 'oY', doel_id: 'a1', relatietype: 'roltoewijzing', label: 'Functioneel beheer', ring: 'rollen' },
        { bron_id: 'oY', doel_id: 'a1', relatietype: 'eigenaar', label: 'is eigendom van', ring: 'eigenaar' },
      ],
    }
    async function mountRing() {
      zetGraf(RING_GRAF)
      const { w } = await mountView()
      await w.find('[data-testid="lk-registratiegaps"]').setValue(true) // gaps AAN in alle regeltests
      await flushPromises()
      return w
    }

    it('(a+b) ring uit haalt knopen weg die alléén via die ring in beeld waren — óók met gaps aan; een tweede aanstaande ring houdt de knoop vast', async () => {
      const w = await mountRing()
      expect(getekendeIds(w)).toContain('oX') // vooraf: rollen-ring aan → zichtbaar
      await w.find('[data-testid="lk-ring-rollen"]').trigger('change') // Rollen & beheer UIT
      await flushPromises()
      const ids = getekendeIds(w)
      expect(ids).not.toContain('oX') // alleen-via-rollen → weg (heeft relaties, dus géén echte gap)
      expect(ids).toContain('oY') // eigenaar-ring staat nog aan → blijft
      expect(ids).toContain('a1') // idem (endpoint van de eigenaar-edge)
    })

    it('(c) een échte gap (geen enkele relatie) volgt de ring van zijn categorie', async () => {
      const w = await mountRing()
      expect(getekendeIds(w)).toContain('gap1') // infrastructuur-ring aan → zichtbaar
      await w.find('[data-testid="lk-ring-infrastructuur"]').trigger('change')
      await flushPromises()
      expect(getekendeIds(w)).not.toContain('gap1') // categorie-ring uit → gap weg
    })

    it('(d) een categorieloze losse knoop ("overig", geen ring) blijft zichtbaar, ongeacht ringen', async () => {
      const w = await mountRing()
      expect(getekendeIds(w)).toContain('los1')
      for (const r of ['rollen', 'infrastructuur', 'applicaties', 'contracten']) {
        await w.find(`[data-testid="lk-ring-${r}"]`).trigger('change')
      }
      await flushPromises()
      expect(getekendeIds(w)).toContain('los1') // er is voor 'overig' niets uitgezet
    })

    it('(e) identiek gedrag op Lagen (één gedeelde regel)', async () => {
      const w = await mountRing()
      w.vm.toonLagen()
      await flushPromises()
      expect(getekendeIds(w)).toContain('oX')
      await w.find('[data-testid="lk-ring-rollen"]').trigger('change')
      await flushPromises()
      const ids = getekendeIds(w)
      expect(ids).not.toContain('oX') // ring uit wint, ook in de banen
      expect(ids).toContain('oY')
      expect(ids).toContain('gap1') // echte gap + toggle aan + infrastructuur-ring aan
      expect(ids).toContain('los1') // overig blijft
    })
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
      // LI036 organisatiebalk — de backend levert voor een eigenaar-org een eigenaar-edge; zonder
      // zo'n edge is een org terecht niet "in beeld" (en dus niet in de balk).
      { bron_id: 'oA', doel_id: 'appA', relatietype: 'eigenaar', label: 'is eigendom van', ring: 'eigenaar' },
      { bron_id: 'oB', doel_id: 'appB', relatietype: 'eigenaar', label: 'is eigendom van', ring: 'eigenaar' },
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

  it('ADR-040 F1 stap 2b — een set-wijziging herseedt de scope naar "alle aan" (init-semantiek A)', async () => {
    const { w } = await _mountScope()
    await w.find('[data-testid="lk-scope-org-oB"]').trigger('change') // oB bewust uit
    await flushPromises()
    expect([...w.vm.scopeOrgs].sort()).toEqual(['oA'])
    // Een set-wijziging (component toevoegen) herlaadt → de eenmalige seed zet alle aanwezige orgs weer
    // aan (geen naschuivende auto-settle; de uitvink gold binnen het vorige beeld).
    w.vm.toggleSet('appA')
    await flushPromises()
    expect([...w.vm.scopeOrgs].sort()).toEqual(['oA', 'oB'])
  })

  it('ADR-040 F1 stap 2b — scopebalk alleen op Overzicht; op de praatplaat is de scope inert', async () => {
    const { w } = await _mountScope()
    expect(w.find('[data-testid="lk-scopebalk"]').exists()).toBe(true) // Overzicht → balk aanwezig
    await w.find('[data-testid="lk-scope-org-oA"]').trigger('change') // oA uit (op Overzicht)
    await flushPromises()
    expect(_zichtbaar(w)).not.toContain('oA') // Overzicht: oA weggefilterd
    // Naar de praatplaat (centrum appA) zónder set-wijziging → balk weg + scope inert (geen stille
    // organisatie-verberging, ook al staat oA nog uitgevinkt).
    w.vm.toonPraatplaat('appA')
    await flushPromises()
    expect(w.vm.weergave).toBe('praatplaat')
    expect(w.find('[data-testid="lk-scopebalk"]').exists()).toBe(false) // praatplaat → balk verborgen
    expect(w.vm._inScope({ id: 'oA', element_type: 'partij', soort: 'organisatie' })).toBe(true) // inert
    // Terug naar Overzicht (geen set-wijziging) → balk weer zichtbaar, de uitvink is bewaard.
    w.vm.toonOverzicht()
    await flushPromises()
    expect(w.find('[data-testid="lk-scopebalk"]').exists()).toBe(true)
    expect([...w.vm.scopeOrgs].sort()).toEqual(['oB'])
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
    it('ADR-040 layout — Praatplaat = concentric (radiaal), Overzicht = grid (centrumloos)', async () => {
      const { w } = await mountView()
      await kies(w, 'a1') // praatplaat (ego)
      expect(w.vm.modus).toBe('ego')
      expect(w.vm._layout().name).toBe('concentric') // radiaal: één centrum + ringen
      w.vm.toonOverzicht() // overzicht (adapter → 'geheel')
      await flushPromises()
      expect(w.vm.modus).toBe('geheel')
      expect(w.vm._layout().name).toBe('grid') // centrumloos, gebalanceerd — geen ster (concentric weg voor Overzicht)
    })

    it('ADR-040 layout — beide layouts zijn niet-geanimeerd en tellen labelgrootte mee (deterministisch, geen samenval)', async () => {
      const { w } = await mountView()
      // Overzicht (geheel): grid, deterministisch, animate:false, avoidOverlap + labelgrootte meegeteld.
      const geheel = w.vm._layout()
      expect(geheel.name).toBe('grid')
      expect(geheel.animate).toBe(false)
      expect(geheel.avoidOverlap).toBe(true)
      expect(geheel.nodeDimensionsIncludeLabels).toBe(true)
      await kies(w, 'a1') // praatplaat (ego)
      const ego = w.vm._layout()
      expect(ego.name).toBe('concentric')
      expect(ego.animate).toBe(false)
      expect(ego.nodeDimensionsIncludeLabels).toBe(true)
      // Praatplaat-leesbaarheid: geen globale opblazing (spacingFactor 1.0) + slechts een kleine gap.
      expect(ego.spacingFactor).toBe(1.0)
      expect(ego.minNodeSpacing).toBeLessThanOrEqual(30)
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

  // ── LI033b — gebruikt-ring (organisatie gebruikt applicatie), spiegel van eigenaar ──
  describe('LI033b — gebruikt-ring', () => {
    const _gebruiktGraf = () => ({
      nodes: [
        { id: 'app1', naam: 'Financieel systeem', element_type: 'applicatie', laag: 'application', lifecycle_status: 'concept', blokkades_open: 0 },
        { id: 'org1', naam: 'Tiel', element_type: 'partij', laag: 'business', soort: 'organisatie', blokkades_open: 0 },
      ],
      edges: [{ bron_id: 'org1', doel_id: 'app1', relatietype: 'gebruikt', label: 'gebruikt', ring: 'gebruikt' }],
    })

    it('de ring "Gebruikt" heeft een checkbox en staat default aan', async () => {
      zetGraf(_gebruiktGraf())
      const { w } = await mountView()
      const cb = w.find('[data-testid="lk-ring-gebruikt"]')
      expect(cb.exists()).toBe(true)
      expect(cb.element.checked).toBe(true)
    })

    it('op Overzicht tekent de gebruikt-lijn (org → applicatie); ring uit → weg', async () => {
      zetGraf(_gebruiktGraf())
      const { w } = await mountView() // hele landschap → Overzicht
      const heeftGebruikt = () => w.vm.zichtbareEdges.some((e) => e.bron_id === 'org1' && e.doel_id === 'app1' && e.ring === 'gebruikt')
      expect(heeftGebruikt()).toBe(true)
      await w.find('[data-testid="lk-ring-gebruikt"]').trigger('change') // ring uit
      await flushPromises()
      expect(heeftGebruikt()).toBe(false)
    })

    it('op de Praatplaat is de gebruikende organisatie een kring-buur van de centrale applicatie', async () => {
      zetGraf(_gebruiktGraf())
      const { w } = await mountView()
      await kies(w, 'app1') // praatplaat centraal op app1
      expect(w.vm.modus).toBe('ego')
      const ids = w.vm.getekendeNodes.map((n) => n.id)
      expect(ids).toContain('app1')
      expect(ids).toContain('org1') // via de gebruikt-ring komt de gebruikende org als kring-buur mee
    })
  })

  // ── LI034 — versleepbare klik-popup (verving de sleep op het zijbalk-detailpaneel) ────────────
  describe('klik-popup draggable (LI034)', () => {
    it('slepen verplaatst de popup; wisSet reset naar standaard', async () => {
      const { w } = await mountView()
      expect(w.vm.popupPos).toEqual({ x: null, y: null })
      w.vm.onPopupMousedown({ clientX: 100, clientY: 80, target: { closest: () => null }, preventDefault() {} })
      expect(w.vm.popupDragging).toBe(true)
      w.vm.onPopupMousemove({ clientX: 140, clientY: 120 }) // offset (100,80) → pos (40,40)
      expect(w.vm.popupPos).toEqual({ x: 40, y: 40 })
      w.vm.onPopupMouseup()
      expect(w.vm.popupDragging).toBe(false)
      w.vm.wisSet()
      expect(w.vm.popupPos).toEqual({ x: null, y: null })
    })

    it('mousedown op een knop/link/input start geen drag (sluit/acties/flow-lijst blijven werken)', async () => {
      const { w } = await mountView()
      w.vm.onPopupMousedown({ target: { closest: (sel) => (sel.includes('button') ? {} : null) }, preventDefault() {} })
      expect(w.vm.popupDragging).toBe(false)
    })

    it('init vanuit DOM-positie: geen sprong naar de hoek bij de eerste beweging', async () => {
      const { w } = await mountView()
      // popup staat (CSS) op rect.left=1200; mousedown op x=800 (binnen de popup)
      w.vm.onPopupMousedown({
        clientX: 800, clientY: 100,
        target: { closest: () => null },
        currentTarget: { getBoundingClientRect: () => ({ left: 1200, top: 100 }) },
        preventDefault() {},
      })
      expect(w.vm.popupPos).toEqual({ x: 1200, y: 100 }) // geïnitialiseerd op de echte positie
      w.vm.onPopupMousemove({ clientX: 850, clientY: 100 }) // 50px naar rechts
      expect(w.vm.popupPos.x).toBe(1250) // schuift 50px, springt NIET naar de hoek
    })
  })

  // ── LI034 slice 2 — praatplaat-startstand: vier kernkringen aan, context-ringen uit ───────────
  describe('praatplaat ring-startstand (LI034 slice 2)', () => {
    const KERN = ['gebruikers', 'gebruikt', 'rollen', 'contracten', 'infrastructuur', 'applicaties']
    const CONTEXT = ['eigenaar', 'samenstelling', 'organisatiestructuur']

    it('bij het betreden van de praatplaat: kernkringen aan, context-ringen uit', async () => {
      const { w } = await mountView()
      // Overzicht-startstand vooraf: de context-ringen eigenaar/samenstelling staan aan (regressie-anker).
      expect(w.vm.ringAan.has('eigenaar')).toBe(true)
      expect(w.vm.ringAan.has('samenstelling')).toBe(true)
      // Praatplaat betreden.
      w.vm.toonPraatplaat('a1')
      await flushPromises()
      expect(w.vm.weergave).toBe('praatplaat')
      KERN.forEach((r) => expect(w.vm.ringAan.has(r)).toBe(true))
      CONTEXT.forEach((r) => expect(w.vm.ringAan.has(r)).toBe(false))
    })

    it('het Overzicht behoudt zijn bestaande startstand (alles behalve organisatiestructuur)', async () => {
      const { w } = await mountView()
      expect(w.vm.weergave).toBe('overzicht')
      // Alle ringen behalve de context-ring organisatiestructuur staan aan (ongewijzigd t.o.v. voorheen).
      expect(w.vm.ringAan.has('organisatiestructuur')).toBe(false)
      ;['eigenaar', 'samenstelling', 'gebruikt', 'gebruikers', 'rollen', 'contracten', 'infrastructuur', 'applicaties']
        .forEach((r) => expect(w.vm.ringAan.has(r)).toBe(true))
    })

    it('een handmatig aangezette context-ring blijft aan bij hercentreren (niet teruggeklapt)', async () => {
      const { w } = await mountView()
      w.vm.toonPraatplaat('a1') // betreden → kern-4
      await flushPromises()
      expect(w.vm.ringAan.has('eigenaar')).toBe(false)
      w.vm.toggleRing('eigenaar') // gebruiker zet 'Eigendom' handmatig aan
      expect(w.vm.ringAan.has('eigenaar')).toBe(true)
      w.vm.toonPraatplaat('a2') // hercentreren binnen de praatplaat → GEEN reset
      await flushPromises()
      expect(w.vm.weergave).toBe('praatplaat')
      expect(w.vm.ringAan.has('eigenaar')).toBe(true) // keuze behouden
    })

    it('deep-link ?center betreedt de praatplaat met de kern-4-startstand', async () => {
      const { w } = await mountView({ query: '?center=a1' })
      expect(w.vm.weergave).toBe('praatplaat')
      KERN.forEach((r) => expect(w.vm.ringAan.has(r)).toBe(true))
      CONTEXT.forEach((r) => expect(w.vm.ringAan.has(r)).toBe(false))
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
      w.vm.toonLagen()
      await flushPromises()
      // LI036 ring-uit-wint — losse nodes (d1/k1/p1) tonen via de gaps-toggle (categorie-ringen aan).
      await w.find('[data-testid="lk-registratiegaps"]').setValue(true)
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

  // ── LI034 — dim-op-klik (selectie): node + directe buren + incidente lijnen scherp, rest dimt ──
  describe('dim-op-klik (LI034)', () => {
    const _app = (id, naam) => ({ id, naam, element_type: 'applicatie', laag: 'application', lifecycle_status: 'concept', blokkades_open: 0 })
    it('selectie dimt alles behalve de node + directe buren + incidente lijnen; deselectie heft op', async () => {
      // Eigen cy-stub met inspecteerbare nodes én edges (source/target op edge.data()).
      const mkNode = (id) => { const c = new Set(); return { data: () => ({ id }), addClass: (x) => c.add(x), removeClass: (x) => c.delete(x), heeft: (x) => c.has(x) } }
      const mkEdge = (source, target) => { const c = new Set(); return { data: () => ({ source, target }), addClass: (x) => c.add(x), removeClass: (x) => c.delete(x), heeft: (x) => c.has(x) } }
      const nodes = { a1: mkNode('a1'), a2: mkNode('a2'), a3: mkNode('a3') }
      const e12 = mkEdge('a1', 'a2'); const e23 = mkEdge('a2', 'a3')
      const nColl = { forEach: (f) => Object.values(nodes).forEach(f), removeClass: (x) => Object.values(nodes).forEach((n) => n.removeClass(x)) }
      const eColl = { forEach: (f) => [e12, e23].forEach(f), removeClass: (x) => [e12, e23].forEach((e) => e.removeClass(x)) }
      const fakeCy = {
        on: vi.fn(), off: vi.fn(), elements: () => ({ remove: vi.fn(), unselect: vi.fn() }),
        getElementById: () => ({ length: 0, select: vi.fn() }), animate: vi.fn(), zoom: () => 1,
        pan: () => ({ x: 0, y: 0 }), add: vi.fn(), layout: () => ({ run: vi.fn() }),
        resize: vi.fn(), fit: vi.fn(), center: vi.fn(), destroy: vi.fn(), nodes: () => nColl, edges: () => eColl,
      }
      cytoscape.mockReturnValueOnce(fakeCy)
      zetGraf({
        nodes: [_app('a1', 'A1'), _app('a2', 'A2'), _app('a3', 'A3')],
        edges: [
          { bron_id: 'a1', doel_id: 'a2', relatietype: 'flow', label: 'koppeling', ring: 'applicaties' },
          { bron_id: 'a2', doel_id: 'a3', relatietype: 'flow', label: 'koppeling', ring: 'applicaties' },
        ],
      })
      const { w } = await mountView()

      // Selecteer a1: scherp = a1 (selectie) + a2 (directe buur); a3 dimt. Incidente lijn a1↔a2 scherp; a2↔a3 dimt.
      w.vm.inspecteerNode('a1')
      await flushPromises()
      expect(nodes.a1.heeft('lk-dim')).toBe(false)
      expect(nodes.a2.heeft('lk-dim')).toBe(false)
      expect(nodes.a3.heeft('lk-dim')).toBe(true)
      expect(e12.heeft('lk-dim')).toBe(false)
      expect(e23.heeft('lk-dim')).toBe(true)

      // Deselectie (popup sluiten) → dim volledig weg, terug naar de neutrale plaat.
      w.vm.sluitPopup()
      await flushPromises()
      expect(Object.values(nodes).every((n) => !n.heeft('lk-dim'))).toBe(true)
      expect([e12, e23].every((e) => !e.heeft('lk-dim'))).toBe(true)
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

  // ── LI034/ADR-041 — persoonlijke standaardkijk (kaart-kijkfilter) ─────────────────────────────
  describe('standaardkijk (LI034/ADR-041)', () => {
    it('_huidigeKijk bevat de kijk-variabelen en NIET de momentkeuze', async () => {
      const { w } = await mountView()
      const k = w.vm._huidigeKijk()
      ;['ringAan', 'fTypes', 'fLev', 'fHost', 'fLc', 'fRol', 'bivB', 'bivI', 'bivV', 'diepte',
        'kleurOpDomein', 'groepeerPerOrg', 'laneVolgorde', 'verbergLegeLanes', 'toonRegistratiegaps']
        .forEach((key) => expect(k).toHaveProperty(key))
      // Momentkeuze mag er NOOIT in zitten.
      ;['set', 'actieveSet', 'ego', 'egoStartId', 'weergave', 'zoek', 'sel', 'scopeOrgs', 'focus']
        .forEach((key) => expect(k[key]).toBeUndefined())
    })

    it('opslaan zet de sleutel kaart_kijkfilter met de kijk (niet de actieve set)', async () => {
      const { w } = await mountView()
      await w.find('[data-testid="lk-ring-organisatiestructuur"]').trigger('change') // ring AAN → onderscheidend
      await w.vm.slaKijkOp()
      await flushPromises()
      expect(api.voorkeuren.zet).toHaveBeenCalledTimes(1)
      const [sleutel, blob] = api.voorkeuren.zet.mock.calls[0]
      expect(sleutel).toBe('kaart_kijkfilter')
      expect(blob.ringAan).toContain('organisatiestructuur')
      expect(blob).not.toHaveProperty('actieveSet')
      expect(blob).not.toHaveProperty('set')
      // Status: opgeslagen = "Dit is je standaardkijk".
      expect(w.find('[data-testid="lk-standaardkijk-status"]').text()).toBe('Dit is je standaardkijk')
    })

    it('"Begin opnieuw" past de opgeslagen standaardkijk toe; actieve set blijft leeg', async () => {
      const { w } = await mountView()
      await w.find('[data-testid="lk-ring-organisatiestructuur"]').trigger('change') // AAN
      await w.vm.slaKijkOp(); await flushPromises()
      await w.find('[data-testid="lk-ring-organisatiestructuur"]').trigger('change') // weer UIT
      expect(w.vm.ringAan.has('organisatiestructuur')).toBe(false)
      w.vm.wisSet(); await flushPromises()
      expect(w.vm.ringAan.has('organisatiestructuur')).toBe(true) // standaardkijk terug
      expect([...w.vm.actieveSet]).toEqual([]) // momentkeuze ongemoeid
    })

    it('herroep verwijdert de standaard en zet de kale default terug', async () => {
      const { w } = await mountView()
      await w.find('[data-testid="lk-ring-organisatiestructuur"]').trigger('change') // AAN
      await w.vm.slaKijkOp(); await flushPromises()
      await w.vm.herroepKijk(); await flushPromises()
      expect(api.voorkeuren.herroep).toHaveBeenCalledWith('kaart_kijkfilter')
      expect(w.vm.ringAan.has('organisatiestructuur')).toBe(false) // kale default
      expect(w.find('[data-testid="lk-standaardkijk-herroep"]').exists()).toBe(false)
    })

    it('mount past de opgeslagen standaardkijk toe bij een verse start (geen lk-state)', async () => {
      api.voorkeuren.haalAlle.mockResolvedValueOnce([
        { voorkeur_sleutel: 'kaart_kijkfilter', waarde: { ringAan: ['applicaties'], kleurOpDomein: true }, updated_at: 'x' },
      ])
      const { w } = await mountView()
      expect(w.vm.ringAan.has('applicaties')).toBe(true)
      expect(w.vm.ringAan.has('eigenaar')).toBe(false) // niet in de opgeslagen set
      expect(w.vm.kleurOpDomein).toBe(true)
    })
  })

  // ── LI034 — reload: herladen behoudt het actieve werk ─────────────────────────────────────────
  describe('reload — herladen behoudt werk (LI034)', () => {
    it('_bewaarKaartState persisteert de ACTUELE in-sessie-set', async () => {
      const { w } = await mountView()
      w.vm.toggleSet('a1')
      await flushPromises()
      w.vm._bewaarKaartState()
      const s = JSON.parse(sessionStorage.getItem('lk-state') || 'null')
      expect(s.actieveSet).toContain('a1')
    })

    it('een beforeunload-event schrijft de actuele set naar lk-state', async () => {
      const { w } = await mountView()
      w.vm.toggleSet('a2')
      await flushPromises()
      sessionStorage.removeItem('lk-state')
      window.dispatchEvent(new Event('beforeunload'))
      const s = JSON.parse(sessionStorage.getItem('lk-state') || 'null')
      expect(s?.actieveSet).toContain('a2') // de nieuwst-gemounte component (deze) schrijft als laatste
    })

    it('"Begin opnieuw" (wisSet) wist lk-state → F5 hierna = beginscherm', async () => {
      const { w } = await mountView()
      w.vm._bewaarKaartState()
      expect(sessionStorage.getItem('lk-state')).toBeTruthy()
      w.vm.wisSet()
      expect(sessionStorage.getItem('lk-state')).toBeNull()
    })

    it('mount herstelt de in-sessie-set en dat wint van de standaardkijk (precedentie)', async () => {
      sessionStorage.setItem('lk-state', JSON.stringify({ actieveSet: ['a1'], ringAan: ['applicaties'] }))
      api.voorkeuren.haalAlle.mockResolvedValueOnce([
        { voorkeur_sleutel: 'kaart_kijkfilter', waarde: { ringAan: ['contracten'] }, updated_at: 'x' },
      ])
      const { w } = await mountView({ heleLandschap: false })
      expect([...w.vm.actieveSet]).toEqual(['a1']) // in-sessie werk hersteld
      expect(w.vm.ringAan.has('applicaties')).toBe(true) // uit lk-state
      expect(w.vm.ringAan.has('contracten')).toBe(false) // standaardkijk NIET toegepast (lk-state wint)
    })
  })

  // ── LI034 bug B — doorklik naar componentpagina gelijkgetrokken (popup ↔ zijpaneel) ───────────
  describe('bug B — doorklik gelijkgetrokken (LI034)', () => {
    it('applicatie: popup én zijpaneel geven beide de component-doorklik (geen regressie)', async () => {
      const { w } = await mountView() // GRAF: a1 applicatie (laag application)
      expect(w.vm._detailLink(w.vm.grafNodes.find((n) => n.id === 'a1'))?.label).toBe('Open component →')
      w.vm.inspecteerNode('a1'); await flushPromises()
      expect(w.find('[data-testid="lk-detail-open"]').exists()).toBe(true)
    })

    it('applicatielaag-component (componenttype ≠ applicatie): nu in BEIDE de doorklik', async () => {
      zetGraf({
        nodes: [
          { id: 'c1', naam: 'Maatwerk', element_type: 'maatwerkcomponent', laag: 'application', lifecycle_status: 'concept', blokkades_open: 0 },
        ],
        edges: [],
      })
      const { w } = await mountView()
      // popup-bron: component-detaillink
      expect(w.vm._detailLink(w.vm.grafNodes.find((n) => n.id === 'c1'))?.label).toBe('Open component →')
      // zijpaneel: dezelfde doorklik (voorheen ontbrak die bij de strikte isApplicatie)
      w.vm.inspecteerNode('c1'); await flushPromises()
      expect(w.find('[data-testid="lk-detail-open"]').exists()).toBe(true)
      expect(w.vm._heeftComponentDetail(w.vm.grafNodes.find((n) => n.id === 'c1'))).toBe(true)
    })

    it('technology-component (geen detailpagina): geen doorklik in BEIDE (geen dode link)', async () => {
      zetGraf({
        nodes: [
          { id: 'db', naam: 'DB', element_type: 'database', laag: 'technology', lifecycle_status: 'concept', blokkades_open: 0 },
        ],
        edges: [],
      })
      const { w } = await mountView()
      expect(w.vm._detailLink(w.vm.grafNodes.find((n) => n.id === 'db'))).toBeNull()
      w.vm.inspecteerNode('db'); await flushPromises()
      expect(w.find('[data-testid="lk-detail-open"]').exists()).toBe(false)
    })

    it('partij/contract: geen "Open component" (zijpaneel), wél hun eigen popup-doorklik', async () => {
      const { w } = await mountView()
      expect(w.vm._heeftComponentDetail({ element_type: 'partij', laag: 'business' })).toBe(false)
      expect(w.vm._heeftComponentDetail({ element_type: 'contract', laag: 'business' })).toBe(false)
      expect(w.vm._detailLink({ id: 'p', element_type: 'partij', laag: 'business' })?.label).toContain('partij')
      expect(w.vm._detailLink({ id: 'k', element_type: 'contract', laag: 'business' })?.label).toContain('contract')
    })
  })

  // ── LI034 bug A — relatie-loos set-lid tekenen op Overzicht (geen leeg canvas) ────────────────
  describe('bug A — relatie-loze set-component tekenen (LI034)', () => {
    const _los = (id, naam, et, laag) => ({ id, naam, element_type: et, laag, lifecycle_status: 'concept', blokkades_open: 0 })

    it('set van 1 relatie-loos component (Overzicht) → getekend + cue "geen relaties in beeld"', async () => {
      zetGraf({ nodes: [_los('db', 'Test Database', 'database', 'technology')], edges: [] })
      const { w } = await mountView({ heleLandschap: false })
      w.vm.voegComponentenToeAanSet([{ id: 'db', naam: 'Test Database', element_type: 'database' }])
      await flushPromises()
      expect(w.vm.weergave).toBe('overzicht')
      expect(w.vm.getekendeNodes.some((n) => n.id === 'db')).toBe(true) // getekend, niet leeg
      expect(w.vm.relatieLozeSetLeden.map((n) => n.id)).toEqual(['db'])
      expect(w.find('[data-testid="lk-geen-relaties"]').exists()).toBe(true)
      expect(w.find('[data-testid="lk-geen-relaties"]').text()).toContain('Test Database')
    })

    it('type-agnostisch: ook een relatie-loze APPLICATIE als set-lid wordt getekend + cue', async () => {
      zetGraf({ nodes: [_los('x', 'Losse App', 'applicatie', 'application')], edges: [] })
      const { w } = await mountView({ heleLandschap: false })
      w.vm.voegComponentenToeAanSet([{ id: 'x', naam: 'Losse App', element_type: 'applicatie' }])
      await flushPromises()
      expect(w.vm.getekendeNodes.some((n) => n.id === 'x')).toBe(true)
      expect(w.find('[data-testid="lk-geen-relaties"]').exists()).toBe(true)
    })

    it('regressie: een relatie-loze node die GEEN set-lid is blijft verborgen; nodes mét edges tekenen', async () => {
      zetGraf({
        nodes: [_los('a1', 'A1', 'applicatie', 'application'), _los('a2', 'A2', 'applicatie', 'application'), _los('los', 'Los', 'database', 'technology')],
        edges: [{ bron_id: 'a1', doel_id: 'a2', relatietype: 'flow', label: 'koppeling', ring: 'applicaties' }],
      })
      const { w } = await mountView() // hele landschap → actieveSet leeg (geen set-leden)
      const ids = w.vm.getekendeNodes.map((n) => n.id)
      expect(ids).toContain('a1') // heeft edge
      expect(ids).toContain('a2') // heeft edge
      expect(ids).not.toContain('los') // relatie-loos én geen set-lid → verborgen (registratiegat)
      expect(w.vm.relatieLozeSetLeden).toEqual([]) // geen cue zonder set-leden
    })

    it('praatplaat ongewijzigd: relatie-loos centrum wordt getekend (egoCentrum), geen Overzicht-cue', async () => {
      zetGraf({ nodes: [_los('x', 'Losse App', 'applicatie', 'application')], edges: [] })
      const { w } = await mountView({ heleLandschap: false })
      await kies(w, 'x') // praatplaat, centrum x
      expect(w.vm.modus).toBe('ego')
      expect(w.vm.getekendeNodes.some((n) => n.id === 'x')).toBe(true) // egoCentrum-uitzondering
      expect(w.vm.relatieLozeSetLeden).toEqual([]) // cue alleen op Overzicht
      expect(w.find('[data-testid="lk-geen-relaties"]').exists()).toBe(false)
    })
  })
})
