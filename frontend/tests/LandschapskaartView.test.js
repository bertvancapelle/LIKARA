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
vi.mock('@/api', () => ({ api: { landschapskaart: { haalGrafdata: vi.fn() } } }))

import cytoscape from '@/composables/cytoscape'
import { api } from '@/api'
import LandschapskaartView from '@modules/bwb_ontvlechting/frontend/views/LandschapskaartView.vue'

const GRAF = () => ({
  nodes: [
    { id: 'a1', naam: 'Zaaksysteem', element_type: 'applicatie', laag: 'application', lifecycle_status: 'migratieklaar', domein: 'applicatie', hosting_model: 'saas', leverancier_naam: 'SaaS BV', blokkades_open: 0 },
    { id: 'a2', naam: 'Documentbeheer', element_type: 'applicatie', laag: 'application', lifecycle_status: 'geblokkeerd', domein: 'applicatie', hosting_model: 'on_premise', leverancier_naam: null, blokkades_open: 1, plateau_naam: 'Plateau 2026', plateau_dispositie: 'Migreren' },
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
  api.landschapskaart.haalGrafdata.mockResolvedValue(GRAF())
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
