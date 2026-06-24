/** Tests — LandschapskaartView v3 (ADR-025, Cytoscape; drie modi + zoek/filter/set/detail). */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'

// Cytoscape gemockt (via de frontend-wrapper): de graaf-rendering is een side-effect;
// de panelen zijn de testbare laag.
vi.mock('@/composables/cytoscape', () => ({
  default: vi.fn(() => ({
    on: vi.fn(),
    elements: () => ({ remove: vi.fn(), unselect: vi.fn() }),
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
    landschapskaart: { haalGrafdata: vi.fn() },
    componenten: { opties: vi.fn() }, // LI019 1b — componenttype-catalogus voor het type-filter
    partijen: { lijst: vi.fn() }, // LI019 1b — leverancier-zoek (externe partijen)
  },
}))

import cytoscape from '@/composables/cytoscape'
import { api } from '@/api'
import LandschapskaartView from '@modules/bwb_ontvlechting/frontend/views/LandschapskaartView.vue'

const GRAF = () => ({
  nodes: [
    { id: 'a1', naam: 'Zaaksysteem', element_type: 'applicatie', laag: 'application', lifecycle_status: 'migratieklaar', domein: 'applicatie', hosting_model: 'saas', leverancier_naam: 'SaaS BV', leverancier_id: 'l1', blokkades_open: 0 },
    { id: 'a2', naam: 'Documentbeheer', element_type: 'applicatie', laag: 'application', lifecycle_status: 'geblokkeerd', domein: 'applicatie', hosting_model: 'on_premise', leverancier_naam: null, leverancier_id: null, blokkades_open: 1, plateau_naam: 'Plateau 2026', plateau_dispositie: 'Migreren' },
    { id: 'd1', naam: 'Klantdatabank', element_type: 'database', laag: 'technology', lifecycle_status: 'concept', domein: 'Database', hosting_model: 'on_premise', blokkades_open: 0 },
    { id: 'p1', naam: 'Org', element_type: 'partij', laag: 'business', soort: 'organisatie', blokkades_open: 0 },
    { id: 'k1', naam: 'Contract X', element_type: 'contract', laag: 'business', blokkades_open: 0 },
  ],
  edges: [{ bron_id: 'a1', doel_id: 'a2', relatietype: 'flow', label: 'koppeling', ring: 'applicaties', richting: 'eenrichting', protocol: 'rest' }],
})

async function mountView({ query = '' } = {}) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'home', component: { template: '<div/>' } },
      { path: '/landschapskaart', name: 'landschapskaart', component: { template: '<div/>' } },
      { path: '/applicaties/:id', name: 'applicatie-detail', component: { template: '<div/>' } },
    ],
  })
  await router.push(`/landschapskaart${query}`)
  await router.isReady()
  const pushSpy = vi.spyOn(router, 'push')
  const w = mount(LandschapskaartView, { global: { plugins: [router] } })
  await flushPromises()
  return { w, pushSpy }
}

beforeEach(() => {
  vi.clearAllMocks()
  sessionStorage.clear() // LI022 — voorkom dat bewaarde kaart-state tussen tests lekt
  api.landschapskaart.haalGrafdata.mockResolvedValue(GRAF())
  // LI019 1b — type-catalogus + leverancier-zoek defaults.
  api.componenten.opties.mockResolvedValue({
    componenttype: [
      { optie_sleutel: 'applicatie', label: 'Applicatie' },
      { optie_sleutel: 'database', label: 'Database' },
    ],
  })
  api.partijen.lijst.mockResolvedValue({ items: [{ id: 'l1', naam: 'SaaS BV', aard: 'externe_partij' }] })
})
afterEach(() => vi.restoreAllMocks())

describe('LandschapskaartView v3', () => {
  it('rendert in Ego-modus en initialiseert Cytoscape', async () => {
    const { w } = await mountView()
    expect(cytoscape).toHaveBeenCalled()
    expect(w.find('[data-testid="lk-canvas"]').exists()).toBe(true)
    expect(w.find('[data-testid="lk-modus-ego"]').attributes('aria-pressed')).toBe('true')
    // resultatenlijst toont ALLEEN applicaties (a1, a2) — niet de partij/contract.
    expect(w.findAll('[data-testid^="lk-res-naam-"]').length).toBe(2)
    expect(w.find('[data-testid="lk-res-naam-p1"]').exists()).toBe(false)
    expect(w.find('[data-testid="lk-res-naam-k1"]').exists()).toBe(false)
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
    api.landschapskaart.haalGrafdata.mockResolvedValue({
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
    const { w } = await mountView()
    await w.find('[data-testid="lk-modus-geheel"]').trigger('click')
    await flushPromises()
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
    const { w } = await mountView() // ego-modus, centrum = a1 (hosting saas)
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

  it('LI019 1c — filterselects werken óók in Impact-modus', async () => {
    const { w } = await mountView()
    await w.find('[data-testid="lk-modus-impact"]').trigger('click')
    await flushPromises()
    await w.find('[data-testid="lk-filter-lifecycle-input"]').trigger('focus')
    await flushPromises()
    await w.find('[data-testid="lk-filter-lifecycle-optie-migratieklaar"]').trigger('mousedown')
    await flushPromises()
    const ids = w.vm.zichtbareNodes.map((n) => n.id)
    expect(ids).toContain('a1') // migratieklaar
    expect(ids).not.toContain('a2') // geblokkeerd — gefilterd, ook in impact-modus
  })

  it('LI019 1d — node→lane-toewijzing uit element_type/laag', async () => {
    const { w } = await mountView()
    const lane = w.vm._laneVan
    expect(lane({ element_type: 'applicatie', laag: 'application' })).toBe('componenten')
    expect(lane({ element_type: 'component', laag: 'application' })).toBe('componenten')
    expect(lane({ element_type: 'database', laag: 'technology' })).toBe('infrastructuur')
    expect(lane({ element_type: 'gebruikersgroep', laag: 'business' })).toBe('gebruikers')
    expect(lane({ element_type: 'partij', laag: 'business' })).toBe('rollen')
    expect(lane({ element_type: 'contract', laag: 'business' })).toBe('contracten')
    expect(lane({ element_type: 'onbekend' })).toBe('overig')
  })

  it('LI019 1d — layout-wisselaar schakelt tussen Radiaal en Swimlanes', async () => {
    const { w } = await mountView()
    // Default = Radiaal.
    expect(w.vm.layoutModus).toBe('radiaal')
    expect(w.find('[data-testid="lk-layout-radiaal"]').attributes('aria-pressed')).toBe('true')
    expect(w.find('[data-testid="lk-layout-swimlane"]').attributes('aria-pressed')).toBe('false')
    await w.find('[data-testid="lk-layout-swimlane"]').trigger('click')
    await flushPromises()
    expect(w.vm.layoutModus).toBe('swimlane')
    expect(w.find('[data-testid="lk-layout-swimlane"]').attributes('aria-pressed')).toBe('true')
  })

  it('LI019 1d — bewaarde layoutModus wordt hersteld uit sessionStorage', async () => {
    sessionStorage.setItem('lk-state', JSON.stringify({ layoutModus: 'swimlane' }))
    const { w } = await mountView()
    expect(w.vm.layoutModus).toBe('swimlane')
    expect(w.find('[data-testid="lk-layout-swimlane"]').attributes('aria-pressed')).toBe('true')
  })

  const SWIM_GRAF = {
    nodes: [
      { id: 'app', naam: 'App', element_type: 'applicatie', laag: 'application', lifecycle_status: 'concept', blokkades_open: 0 },
      { id: 'db', naam: 'DB', element_type: 'database', laag: 'technology', lifecycle_status: 'concept', blokkades_open: 0 },
    ],
    edges: [{ bron_id: 'app', doel_id: 'db', relatietype: 'assignment', label: 'draait op', ring: 'infrastructuur' }],
  }
  async function mountSwimlane() {
    api.landschapskaart.haalGrafdata.mockResolvedValue(SWIM_GRAF)
    const { w } = await mountView()
    await w.find('[data-testid="lk-modus-geheel"]').trigger('click')
    await flushPromises()
    await w.find('[data-testid="lk-layout-swimlane"]').trigger('click')
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

  it('LI019 1d-v3 — swimlane toont óók objecten zonder zichtbare relatie (bug 1)', async () => {
    // p1 (partij) en k1 (contract) hebben geen edges in de fixture → in radiaal verborgen,
    // in swimlane zichtbaar in hun lane.
    const { w } = await mountView()
    await w.find('[data-testid="lk-modus-geheel"]').trigger('click')
    await flushPromises()
    const radiaalIds = w.vm.getekendeNodes.map((n) => n.id)
    expect(radiaalIds).not.toContain('p1') // losse node → verborgen in radiaal
    await w.find('[data-testid="lk-layout-swimlane"]').trigger('click')
    await flushPromises()
    const swimlaneIds = w.vm.getekendeNodes.map((n) => n.id)
    expect(swimlaneIds).toContain('p1') // partij nu zichtbaar in de Rollen-lane
    expect(swimlaneIds).toContain('k1') // contract nu zichtbaar in de Contracten-lane
  })

  it('LI019 1d-v2 — lanevolgorde + verberg-lege hersteld uit sessionStorage', async () => {
    sessionStorage.setItem('lk-state', JSON.stringify({
      layoutModus: 'swimlane',
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
    const { w } = await mountView()
    await w.find('[data-testid="lk-modus-geheel"]').trigger('click')
    await flushPromises()
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

  it('toont de ring-checkboxes in ALLE modi (regressie LI018)', async () => {
    const RINGEN = ['lk-ring-applicaties', 'lk-ring-rollen', 'lk-ring-gebruikers', 'lk-ring-contracten', 'lk-ring-infrastructuur']
    const alleRingenZichtbaar = (w) => RINGEN.every((t) => w.find(`[data-testid="${t}"]`).exists())
    const { w } = await mountView()
    expect(alleRingenZichtbaar(w)).toBe(true) // ego
    await w.find('[data-testid="lk-modus-impact"]').trigger('click')
    await flushPromises()
    expect(alleRingenZichtbaar(w)).toBe(true) // impact
    await w.find('[data-testid="lk-modus-geheel"]').trigger('click')
    await flushPromises()
    expect(alleRingenZichtbaar(w)).toBe(true) // geheel
  })

  it('ring uitvinken verbergt ook de nodes van die ring (LI019 Fix 2)', async () => {
    api.landschapskaart.haalGrafdata.mockResolvedValue({
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
    await w.find('[data-testid="lk-modus-geheel"]').trigger('click')
    await flushPromises()
    expect(w.find('[data-testid="lk-zichtbaar-aantal"]').text()).toContain('3 nodes') // a1, a2, g1
    // ring 'gebruikers' uit → g1 (alleen via die ring verbonden) verdwijnt; apps blijven via de flow
    await w.find('[data-testid="lk-ring-gebruikers"]').trigger('change')
    await flushPromises()
    expect(w.find('[data-testid="lk-zichtbaar-aantal"]').text()).toContain('2 nodes')
  })

  it('zoekfilter vermindert de zichtbare resultaten', async () => {
    const { w } = await mountView()
    await w.find('[data-testid="lk-zoek"]').setValue('zaak')
    await flushPromises()
    expect(w.find('[data-testid="lk-res-naam-a1"]').exists()).toBe(true)
    expect(w.find('[data-testid="lk-res-naam-a2"]').exists()).toBe(false)
    expect(w.findAll('[data-testid^="lk-res-naam-"]').length).toBe(1)
  })

  it('Impact-modus telt set/raakvlakken/grensoverschrijdend', async () => {
    const { w } = await mountView()
    await w.find('[data-testid="lk-modus-impact"]').trigger('click')
    await flushPromises()
    expect(w.find('[data-testid="impact-samenvatting"]').text()).toBe('0 in set · 0 raakvlakken · 0 grensoverschrijdende koppelingen')
    await w.find('[data-testid="lk-res-set-a1"]').trigger('click') // a1 in de set
    await flushPromises()
    // flow a1→a2: a2 wordt raakvlak, koppeling grensoverschrijdend.
    expect(w.find('[data-testid="impact-samenvatting"]').text()).toBe('1 in set · 1 raakvlakken · 1 grensoverschrijdende koppelingen')
  })

  it('Geheel-model toont de verbonden nodes en vult de set met alle applicaties', async () => {
    const { w } = await mountView()
    await w.find('[data-testid="lk-modus-geheel"]').trigger('click')
    await flushPromises()
    // LI020 — losse nodes (p1/k1 zonder edges) zijn altijd verborgen; de 2 via de flow verbonden
    // applicaties blijven. De actieve set bevat alle applicaties.
    expect(w.find('[data-testid="lk-zichtbaar-aantal"]').text()).toContain('2 nodes')
    expect(w.find('[data-testid="lk-rechts"]').text()).toContain('Actieve set (2)')
  })

  it('partij-node wordt ego-centrum bij dubbelklik vanuit geheel-model (LI021)', async () => {
    api.landschapskaart.haalGrafdata.mockResolvedValue({
      nodes: [
        { id: 'a1', naam: 'App', element_type: 'applicatie', laag: 'application', lifecycle_status: 'concept', blokkades_open: 0 },
        { id: 'p1', naam: 'Provincie', element_type: 'partij', laag: 'business', soort: 'ketenpartner' },
      ],
      edges: [{ bron_id: 'p1', doel_id: 'a1', relatietype: 'roltoewijzing', label: 'Contractbeheer', ring: 'rollen' }],
    })
    const { w } = await mountView()
    await w.find('[data-testid="lk-modus-geheel"]').trigger('click')
    await flushPromises()
    // Dubbelklik op de partij-node (twee taps binnen de drempel) → ego met partij als centrum.
    w.vm.onNodeTap('p1'); w.vm.onNodeTap('p1')
    await flushPromises()
    expect(w.find('[data-testid="lk-modus-ego"]').attributes('aria-pressed')).toBe('true')
    // Detailpaneel toont de partij + zijn aard.
    expect(w.find('[data-testid="lk-detail-aard"]').exists()).toBe(true)
    expect(w.find('[data-testid="lk-detail-naam"]').text()).toBe('Provincie')
  })

  it('node-klik (resultaatrij) toont het detail-paneel', async () => {
    const { w } = await mountView()
    expect(w.find('[data-testid="lk-detail-leeg"]').exists()).toBe(true)
    await w.find('[data-testid="lk-res-naam-a2"]').trigger('click')
    await flushPromises()
    expect(w.find('[data-testid="lk-detail-naam"]').text()).toBe('Documentbeheer')
  })

  it('"Open applicatie →" navigeert naar het applicatie-detail', async () => {
    const { w, pushSpy } = await mountView()
    await w.find('[data-testid="lk-res-naam-a1"]').trigger('click')
    await flushPromises()
    await w.find('[data-testid="lk-detail-open"]').trigger('click')
    expect(pushSpy).toHaveBeenCalledWith({ name: 'applicatie-detail', params: { id: 'a1' } })
  })

  it('"Voeg alle gefilterde toe" vult de actieve set', async () => {
    const { w } = await mountView()
    await w.find('[data-testid="lk-voeg-alle"]').trigger('click')
    await flushPromises()
    // alleen de twee applicaties komen in de set (partij/contract zijn niet selecteerbaar).
    expect(w.find('[data-testid="lk-rechts"]').text()).toContain('Actieve set (2)')
  })

  it('Fix 3: klik op een actieve-set-item selecteert de node (detail-paneel)', async () => {
    const { w } = await mountView()
    await w.find('[data-testid="lk-res-set-a1"]').trigger('click') // a1 in de set
    await flushPromises()
    await w.find('[data-testid="lk-set-a1"]').find('button').trigger('click') // klik het set-item (naam)
    await flushPromises()
    expect(w.find('[data-testid="lk-detail-naam"]').text()).toBe('Zaaksysteem')
  })

  it('deep-link ?center=<id>&modus=ego zet de modus en de actieve set (ADR-025)', async () => {
    const { w } = await mountView({ query: '?center=a1&modus=ego' })
    expect(w.find('[data-testid="lk-modus-ego"]').attributes('aria-pressed')).toBe('true')
    // de center-applicatie staat in de actieve set en is het detail.
    expect(w.find('[data-testid="lk-rechts"]').text()).toContain('Actieve set (1)')
    expect(w.find('[data-testid="lk-detail-naam"]').text()).toBe('Zaaksysteem')
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
    await w.find('[data-testid="lk-res-naam-a2"]').trigger('click') // a2 zit op een plateau
    await flushPromises()
    const plateau = w.find('[data-testid="lk-detail-plateau"]')
    expect(plateau.exists()).toBe(true)
    expect(plateau.text()).toContain('Plateau 2026')
    expect(plateau.text()).toContain('Migreren')
    // a1 zit niet op een plateau → geen migratieplaatsing-regel.
    await w.find('[data-testid="lk-res-naam-a1"]').trigger('click')
    await flushPromises()
    expect(w.find('[data-testid="lk-detail-plateau"]').exists()).toBe(false)
  })

  it('toont het blokkade-icoon op een node met open blokkades', async () => {
    const { w } = await mountView()
    expect(w.find('[data-testid="lk-res-blok-a2"]').exists()).toBe(true)
    expect(w.find('[data-testid="lk-res-blok-a1"]').exists()).toBe(false)
  })
})
