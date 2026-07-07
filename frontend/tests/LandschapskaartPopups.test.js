/**
 * Tests — Landschapskaart popups + fullscreen (klik op koppeling/knoop, dubbelklik =
 * hercentreren, fullscreen-overlay met staat-behoud). Cytoscape gemockt; de popup-/
 * fullscreen-logica is via defineExpose aan te roepen en rendert in de DOM.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { createPinia, setActivePinia } from 'pinia'
import { useAuthStore } from '@/store/auth'

vi.mock('@/composables/cytoscape', () => ({
  default: vi.fn(() => ({
    on: vi.fn(),
    elements: () => ({ remove: vi.fn(), unselect: vi.fn() }),
    getElementById: () => ({ length: 0, select: vi.fn() }),
    animate: vi.fn(), zoom: () => 1, pan: () => ({ x: 0, y: 0 }),
    add: vi.fn(), layout: () => ({ run: vi.fn() }), resize: vi.fn(), fit: vi.fn(), destroy: vi.fn(),
  })),
}))
vi.mock('@/api', () => ({
  api: {
    landschapskaart: { haalGrafdata: vi.fn(), subgraaf: vi.fn() }, // Fase B — set-scoped subgraaf
    applicaties: { haal: vi.fn() },
    componenten: { haal: vi.fn() },
    contracten: { haal: vi.fn() },
    partijen: { haal: vi.fn() },
    relaties: { lijst: vi.fn() },
    impactViews: { lijst: vi.fn() }, // ADR-033 2c — view-lijst (hier leeg: geen startscherm)
  },
}))

import { api } from '@/api'
import LandschapskaartView from '@modules/bwb_ontvlechting/frontend/views/LandschapskaartView.vue'

const GRAF = () => ({
  nodes: [
    { id: 'a1', naam: 'Zaaksysteem', element_type: 'applicatie', laag: 'application', lifecycle_status: 'migratieklaar', domein: 'applicatie', hosting_model: 'saas', leverancier_naam: 'SaaS BV', blokkades_open: 0 },
    { id: 'a2', naam: 'Documentbeheer', element_type: 'applicatie', laag: 'application', lifecycle_status: 'geblokkeerd', domein: 'applicatie', hosting_model: 'on_premise', leverancier_naam: null, blokkades_open: 1 },
    { id: 'p1', naam: 'Gemeente X', element_type: 'partij', laag: 'business', soort: 'organisatie', blokkades_open: 0 },
    { id: 'k1', naam: 'Contract X', element_type: 'contract', laag: 'business', blokkades_open: 0 },
    { id: 'db1', naam: 'Oracle DB', element_type: 'database', laag: 'technology', lifecycle_status: 'concept', blokkades_open: 0 },
  ],
  edges: [{ bron_id: 'a1', doel_id: 'a2', relatietype: 'flow', label: 'koppeling', ring: 'applicaties', richting: 'eenrichting', protocol: 'api' }],
})

let wrappers = []
async function mountView() {
  const pinia = createPinia()
  setActivePinia(pinia)
  useAuthStore().user = { roles: ['medewerker'] }
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'home', component: { template: '<div/>' } },
      { path: '/landschapskaart', name: 'landschapskaart', component: { template: '<div/>' } },
      { path: '/applicaties/:id', name: 'applicatie-detail', component: { template: '<div/>' } },
      { path: '/componenten/:id', name: 'component-detail', component: { template: '<div/>' } },
      { path: '/partijen/:id', name: 'partij-detail', component: { template: '<div/>' } },
      { path: '/contracten/:id', name: 'contract-detail', component: { template: '<div/>' } },
    ],
  })
  await router.push('/landschapskaart')
  await router.isReady()
  const pushSpy = vi.spyOn(router, 'push')
  const w = mount(LandschapskaartView, { global: { plugins: [pinia, router] } })
  wrappers.push(w)
  await flushPromises()
  // Fase B — de kaart opent leeg; deze popup-suite test de graaf-interacties, dus laad eerst het
  // hele landschap (haalGrafdata). Set-mutaties (dubbelklik) lopen via de subgraaf-mock (zelfde GRAF).
  w.vm.toonHeleLandschap()
  await flushPromises()
  return { w, pushSpy }
}

beforeEach(() => {
  vi.clearAllMocks()
  sessionStorage.clear() // LI022 — voorkom dat bewaarde kaart-state tussen tests lekt
  api.landschapskaart.haalGrafdata.mockResolvedValue(GRAF())
  api.landschapskaart.subgraaf.mockResolvedValue(GRAF()) // Fase B — set-modus = zelfde graaf
  api.impactViews.lijst.mockResolvedValue([]) // geen views → geen startscherm in deze suite
})
afterEach(() => {
  wrappers.forEach((w) => w.unmount())
  wrappers = []
  vi.useRealTimers()
  vi.restoreAllMocks()
})

const veld = (w, label) => {
  const dts = w.findAll('[data-testid="lk-popup-velden"] dt')
  const dt = dts.find((d) => d.text() === label)
  return dt ? dt.element.nextElementSibling.textContent : null
}

describe('Landschapskaart — koppeling-popup (master-detail, ADR-023a Fase 4)', () => {
  const TWEE = () => ({ items: [
    { id: 'r1', bron_id: 'a1', doel_id: 'a2', naam: 'B-koppeling', kenmerken: { protocol: 'rest', richting: 'eenrichting', impact_bij_verbreking: 'hoog' }, omschrijving: 'desc B' },
    { id: 'r2', bron_id: 'a2', doel_id: 'a1', naam: 'A-koppeling', kenmerken: { protocol: 'soap', richting: 'tweerichting' }, omschrijving: null },
  ] })

  it('toont een master-detail (linker lijst + rechter detail); eerste rij (op naam) auto-geselecteerd', async () => {
    api.relaties.lijst.mockResolvedValue(TWEE())
    const { w } = await mountView()
    await w.vm.openEdgePopup({ bron_id: 'a1', doel_id: 'a2', ring: 'applicaties' })
    await flushPromises()
    expect(api.relaties.lijst).toHaveBeenCalledWith({ paar_bron_id: 'a1', paar_doel_id: 'a2', relatietype: 'flow' })
    expect(w.find('[data-testid="lk-popup-md"]').exists()).toBe(true)
    expect(w.find('[data-testid="lk-popup-lijst"]').exists()).toBe(true)
    expect(w.find('[data-testid="lk-popup-detail"]').exists()).toBe(true)
    expect(w.findAll('[data-testid^="lk-popup-flow-"]')).toHaveLength(2)
    // Gesorteerd op naam asc → 'A-koppeling' (r2) eerst en automatisch geselecteerd.
    expect(w.find('[data-testid="lk-popup-flow-r2"]').attributes('aria-selected')).toBe('true')
    expect(w.find('[data-testid="lk-popup-detail-naam"]').text()).toBe('A-koppeling')
    // Tegenpartij = doel van die flow (r2: a2→a1 → a1 = Zaaksysteem).
    expect(w.find('[data-testid="lk-popup-detail"]').text()).toContain('Zaaksysteem')
  })

  it('klik op een andere rij wisselt het detail-paneel', async () => {
    api.relaties.lijst.mockResolvedValue(TWEE())
    const { w } = await mountView()
    await w.vm.openEdgePopup({ bron_id: 'a1', doel_id: 'a2', ring: 'applicaties' })
    await flushPromises()
    await w.find('[data-testid="lk-popup-flow-r1"]').trigger('click')
    expect(w.find('[data-testid="lk-popup-detail-naam"]').text()).toBe('B-koppeling')
  })

  it('n=1: zelfde master-detail-layout (één rij + detail)', async () => {
    api.relaties.lijst.mockResolvedValue({ items: [
      { id: 'x', bron_id: 'a1', doel_id: 'a2', naam: 'Enige koppeling', kenmerken: { protocol: 'rest' }, omschrijving: null },
    ] })
    const { w } = await mountView()
    await w.vm.openEdgePopup({ bron_id: 'a1', doel_id: 'a2', ring: 'applicaties' })
    await flushPromises()
    expect(w.find('[data-testid="lk-popup-md"]').exists()).toBe(true)
    expect(w.findAll('[data-testid^="lk-popup-flow-"]')).toHaveLength(1)
    expect(w.find('[data-testid="lk-popup-detail-naam"]').text()).toBe('Enige koppeling')
  })

  it('edge-klik gebruikt paar_bron_id + paar_doel_id (niet gericht bron_id/doel_id)', async () => {
    api.relaties.lijst.mockResolvedValue({ items: [] })
    const { w } = await mountView()
    await w.vm.openEdgePopup({ bron_id: 'a2', doel_id: 'a1', ring: 'applicaties' })
    await flushPromises()
    const arg = api.relaties.lijst.mock.calls[0][0]
    expect(arg).toMatchObject({ paar_bron_id: 'a2', paar_doel_id: 'a1', relatietype: 'flow' })
    expect(arg.bron_id).toBeUndefined()
    expect(arg.doel_id).toBeUndefined()
  })

  it('403 op de relatie-fetch toont een nette melding (geen technische fout)', async () => {
    api.relaties.lijst.mockRejectedValue({ status: 403 })
    const { w } = await mountView()
    await w.vm.openEdgePopup({ bron_id: 'a1', doel_id: 'a2', ring: 'applicaties' })
    await flushPromises()
    expect(w.find('[data-testid="lk-popup-melding"]').exists()).toBe(true)
  })

  it('edge-label toont een aantal-badge bij ≥2 koppelingen, niet bij 1', async () => {
    const { w } = await mountView()
    const meer = w.vm._edgeData({ ring: 'applicaties', aantal: 3, richting: 'eenrichting', protocol: 'rest', bron_id: 'a1', doel_id: 'a2' }, 0)
    expect(meer.label).toContain('3×')
    const een = w.vm._edgeData({ ring: 'applicaties', aantal: 1, richting: 'eenrichting', protocol: 'rest', bron_id: 'a1', doel_id: 'a2' }, 0)
    expect(een.label).not.toContain('×')
  })
})

describe('Landschapskaart — knoop-popup (dispatch per soort)', () => {
  it('applicatie → /componenten met kern-velden (LI059)', async () => {
    api.componenten.haal.mockResolvedValue({ id: 'a1', naam: 'Zaaksysteem', lifecycle_status: 'migratieklaar', eigenaar_organisatie_naam: 'ICT', hostingmodel: 'saas', migratiepad: 'rehost', complexiteit: 'hoog', prioriteit: 'midden', beschrijving: 'Kernsysteem' })
    const { w } = await mountView()
    await w.vm.openNodePopup('a1')
    await flushPromises()
    expect(api.componenten.haal).toHaveBeenCalledWith('a1')
    expect(w.find('[data-testid="lk-popup-titel"]').text()).toBe('Zaaksysteem')
    expect(veld(w, 'Eigenaar-organisatie')).toBe('ICT')
    expect(veld(w, 'Migratiepad')).toBeTruthy()
    expect(veld(w, 'Beschrijving')).toBe('Kernsysteem')
    expect(w.find('[data-testid="lk-popup-actie"]').exists()).toBe(true) // Open applicatie →
  })

  it('contract → /contracten met looptijd + leverancier', async () => {
    api.contracten.haal.mockResolvedValue({ id: 'k1', contractnaam: 'Contract X', leverancier_naam: 'Acme', contracttype: 'raamcontract', begindatum: '2025-01-01', einddatum: '2027-12-31', omschrijving: 'DMS-licentie' })
    const { w } = await mountView()
    await w.vm.openNodePopup('k1')
    await flushPromises()
    expect(api.contracten.haal).toHaveBeenCalledWith('k1')
    expect(veld(w, 'Leverancier')).toBe('Acme')
    expect(veld(w, 'Looptijd')).toContain('2025-01-01')
    expect(veld(w, 'Omschrijving')).toBe('DMS-licentie')
  })

  it('partij → /partijen met alleen ingevulde contactvelden', async () => {
    api.partijen.haal.mockResolvedValue({ id: 'p1', naam: 'Gemeente X', aard: 'organisatie', plaats: 'Tiel', email: 'info@x.nl', telefoon: null, mobiel: null })
    const { w } = await mountView()
    await w.vm.openNodePopup('p1')
    await flushPromises()
    expect(api.partijen.haal).toHaveBeenCalledWith('p1')
    expect(veld(w, 'E-mail')).toBe('info@x.nl')
    expect(veld(w, 'Adres')).toBe('Tiel')
    expect(veld(w, 'Telefoon')).toBeNull() // leeg → geen regel
  })

  it('infra-component (database) → /componenten', async () => {
    api.componenten.haal.mockResolvedValue({ id: 'db1', naam: 'Oracle DB', componenttype_label: 'Database', lifecycle_status: 'concept', hostingmodel: 'on_premise', beschrijving: null })
    const { w } = await mountView()
    await w.vm.openNodePopup('db1')
    await flushPromises()
    expect(api.componenten.haal).toHaveBeenCalledWith('db1')
    expect(veld(w, 'Type')).toBe('Database')
    expect(w.find('[data-testid="lk-popup-actie"]').exists()).toBe(false) // geen applicatie-doorklik
  })

  it('partij-popup biedt doorklik naar het partij-detail (B2)', async () => {
    api.partijen.haal.mockResolvedValue({ id: 'p1', naam: 'Gemeente X', aard: 'organisatie' })
    const { w, pushSpy } = await mountView()
    await w.vm.openNodePopup('p1')
    await flushPromises()
    const actie = w.find('[data-testid="lk-popup-actie"]')
    expect(actie.exists()).toBe(true)
    await actie.trigger('click')
    expect(pushSpy).toHaveBeenCalledWith({ name: 'partij-detail', params: { id: 'p1' } })
  })

  it('edge-popup (rollen) biedt doorklik naar partij (bron) én component (doel) (B2)', async () => {
    const { w, pushSpy } = await mountView()
    await w.vm.openEdgePopup({ bron_id: 'p1', doel_id: 'a1', ring: 'rollen', label: 'Contractbeheer', relatietype: 'roltoewijzing' })
    await flushPromises()
    expect(w.find('[data-testid="lk-popup-actie"]').exists()).toBe(true) // partij (bron)
    expect(w.find('[data-testid="lk-popup-actie-1"]').exists()).toBe(true) // component (doel)
    await w.find('[data-testid="lk-popup-actie"]').trigger('click')
    expect(pushSpy).toHaveBeenCalledWith({ name: 'partij-detail', params: { id: 'p1' } })
  })

  it('ADR-033 1b — edge-popup (samenstelling) toont Geheel (bron) en Onderdeel (doel)', async () => {
    const { w } = await mountView()
    await w.vm.openEdgePopup({ bron_id: 'a1', doel_id: 'db1', ring: 'samenstelling', label: 'bestaat uit', relatietype: 'aggregation' })
    await flushPromises()
    expect(w.find('[data-testid="lk-popup-titel"]').text()).toBe('Samenstelling')
    expect(veld(w, 'Geheel')).toBe('Zaaksysteem') // bron = geheel
    expect(veld(w, 'Onderdeel')).toBe('Oracle DB') // doel = onderdeel
  })

  it('pre-fill toont meteen node-data terwijl de fetch nog loopt; 403 valt netjes terug', async () => {
    let los
    api.componenten.haal.mockReturnValue(new Promise((res) => { los = res }))
    const { w } = await mountView()
    w.vm.openNodePopup('a1') // niet awaiten: de fetch blijft hangen tot los()
    await flushPromises()
    // pre-fill zichtbaar vóór resolve (titel + node-velden)
    expect(w.find('[data-testid="lk-popup-titel"]').text()).toBe('Zaaksysteem')
    expect(w.find('[data-testid="lk-popup-laden"]').exists()).toBe(true)
    los({ id: 'a1', naam: 'Zaaksysteem', lifecycle_status: 'migratieklaar' })
    await flushPromises()
    expect(w.find('[data-testid="lk-popup-laden"]').exists()).toBe(false)
  })
})

describe('Landschapskaart — enkele vs. dubbele klik', () => {
  it('enkele klik opent (na drempel) de popup; dubbelklik hercentreert en opent GEEN popup', async () => {
    vi.useFakeTimers()
    api.componenten.haal.mockResolvedValue({ id: 'a1', naam: 'Zaaksysteem', lifecycle_status: 'migratieklaar' })
    const { w } = await mountView()

    // Dubbelklik: twee taps binnen de drempel → geen popup.
    w.vm.onNodeTap('a1')
    w.vm.onNodeTap('a1')
    vi.advanceTimersByTime(300)
    await flushPromises()
    expect(w.vm.popupOpen).toBe(false)

    // Enkele klik: één tap, drempel verstrijkt → popup opent.
    w.vm.onNodeTap('a1')
    vi.advanceTimersByTime(300)
    await flushPromises()
    expect(w.vm.popupOpen).toBe(true)
  })
})

describe('Landschapskaart — klik-popup samenvatting "wat raakt dit" (LI034)', () => {
  // Rijke graaf: één applicatie (a1) met een relatie in elke kern-kring.
  const RIJK = () => ({
    nodes: [
      { id: 'a1', naam: 'Zaaksysteem', element_type: 'applicatie', laag: 'application', lifecycle_status: 'migratieklaar', domein: 'applicatie', leverancier_naam: 'SaaS BV', blokkades_open: 0, eigenaar_organisatie_id: 'p1', gebruikt_door_organisaties: ['p1'] },
      { id: 'a2', naam: 'Documentbeheer', element_type: 'applicatie', laag: 'application', blokkades_open: 0 },
      { id: 'p1', naam: 'Gemeente Tiel', element_type: 'partij', laag: 'business', soort: 'organisatie', blokkades_open: 0 },
      { id: 'p2', naam: 'Beheer BV', element_type: 'partij', laag: 'business', soort: 'externe_partij', blokkades_open: 0 },
      { id: 'k1', naam: 'Contract X', element_type: 'contract', laag: 'business', blokkades_open: 0 },
      { id: 'srv1', naam: 'Server 1', element_type: 'database', laag: 'technology', blokkades_open: 0 },
    ],
    edges: [
      { bron_id: 'a1', doel_id: 'a2', relatietype: 'flow', label: 'koppeling', ring: 'applicaties' },
      { bron_id: 'p2', doel_id: 'a1', relatietype: 'roltoewijzing', label: 'Technisch beheer', ring: 'rollen' },
      { bron_id: 'a1', doel_id: 'k1', relatietype: 'association', label: 'valt onder', ring: 'contracten' },
      { bron_id: 'srv1', doel_id: 'a1', relatietype: 'assignment', label: 'draait op', ring: 'infrastructuur' },
    ],
  })
  const sam = (w, key) => {
    const el = w.find(`[data-testid="lk-popup-sam-${key}"]`)
    return el.exists() ? el.text() : null
  }

  it('toont per kring een leesbare regel, afgeleid uit de geladen graafdata', async () => {
    api.landschapskaart.haalGrafdata.mockResolvedValue(RIJK())
    api.componenten.haal.mockResolvedValue({ id: 'a1', naam: 'Zaaksysteem', lifecycle_status: 'migratieklaar' })
    const { w } = await mountView()
    await w.vm.openNodePopup('a1')
    await flushPromises()
    expect(w.find('[data-testid="lk-popup-samenvatting"]').exists()).toBe(true)
    expect(w.find('[data-testid="lk-popup-sub"]').text()).toContain('Migratieklaar') // type · status
    expect(sam(w, 'gebruikt')).toContain('Gemeente Tiel')
    expect(sam(w, 'beheer')).toContain('Beheer BV')
    expect(sam(w, 'beheer')).toContain('Technisch beheer')
    expect(sam(w, 'contract')).toContain('Contract X')
    expect(sam(w, 'contract')).toContain('SaaS BV') // leverancier uit node-metadata (slice-3-lijn komt later)
    expect(sam(w, 'eigenaar')).toContain('Gemeente Tiel')
    expect(sam(w, 'infra')).toContain('Server 1')
    expect(sam(w, 'koppel')).toContain('Documentbeheer')
  })

  it('benoemt ontbrekende relaties als leesbaar registratiegat (niet verbergen)', async () => {
    api.landschapskaart.haalGrafdata.mockResolvedValue({
      nodes: [{ id: 'x1', naam: 'Weesapplicatie', element_type: 'applicatie', laag: 'application', blokkades_open: 0 }],
      edges: [],
    })
    api.componenten.haal.mockResolvedValue({ id: 'x1', naam: 'Weesapplicatie' })
    const { w } = await mountView()
    await w.vm.openNodePopup('x1')
    await flushPromises()
    expect(sam(w, 'eigenaar')).toContain('nog geen eigenaar geregistreerd')
    expect(sam(w, 'contract')).toContain('geen contract gekoppeld')
    expect(sam(w, 'beheer')).toContain('geen beheerrol toegewezen')
    expect(sam(w, 'gebruikt')).toContain('nog geen gebruik geregistreerd')
    // gat-regel is als zodanig gemarkeerd (italic-klasse).
    expect(w.find('[data-testid="lk-popup-sam-eigenaar"]').classes()).toContain('italic')
  })

  it('een niet-applicatie-node (contract) krijgt géén kring-samenvatting', async () => {
    api.landschapskaart.haalGrafdata.mockResolvedValue(RIJK())
    api.contracten.haal.mockResolvedValue({ id: 'k1', contractnaam: 'Contract X' })
    const { w } = await mountView()
    await w.vm.openNodePopup('k1')
    await flushPromises()
    expect(w.find('[data-testid="lk-popup-samenvatting"]').exists()).toBe(false)
  })
})

describe('Landschapskaart — fullscreen-overlay', () => {
  it('toggelt fullscreen-classes en behoudt een open popup; Escape sluit', async () => {
    api.componenten.haal.mockResolvedValue({ id: 'a1', naam: 'Zaaksysteem' })
    const { w } = await mountView()
    await w.vm.openNodePopup('a1')
    await flushPromises()

    expect(w.find('[data-testid="lk-fullscreen-open"]').exists()).toBe(true)
    w.vm.toggleFullscreen()
    await flushPromises()
    expect(w.vm.fullscreen).toBe(true)
    expect(w.find('[data-testid="lk-wrapper"]').classes()).toContain('fixed')
    expect(w.find('[data-testid="lk-fullscreen-sluit"]').exists()).toBe(true)
    // staat-behoud: popup blijft open na de toggle.
    expect(w.find('[data-testid="lk-popup"]').exists()).toBe(true)

    // Escape sluit eerst de popup (niet de fullscreen).
    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
    await flushPromises()
    expect(w.vm.popupOpen).toBe(false)
    expect(w.vm.fullscreen).toBe(true)
    // tweede Escape sluit de fullscreen.
    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
    await flushPromises()
    expect(w.vm.fullscreen).toBe(false)
  })
})
