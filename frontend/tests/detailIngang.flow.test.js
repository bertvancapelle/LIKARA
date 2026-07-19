/**
 * LI046 — gebruikersflow-tests van de gedeelde detail-ingang: kaart → lijn-popup →
 * doorklik → landing op de ÉCHTE ComponentDetail, op een component MÉT checklistvragen.
 * De les (herstel-opdracht): de suite toetste consequent lege componenten en twee losse
 * helften; de wipe-race (terugschrijf vs. aanleiding) was alleen zichtbaar in de keten
 * mét vragen. Deze tests zijn de permanente borging — niet verzwakken, niet "opschonen"
 * tot ze weer synchroon klikken.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import { createPinia, setActivePinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'
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
    landschapskaart: { haalGrafdata: vi.fn(), subgraaf: vi.fn() },
    impactViews: { lijst: vi.fn(() => Promise.resolve([])) },
    organisatiegebruik: { lijstVoorApplicatie: vi.fn(() => Promise.resolve([])) },
    applicaties: { haal: vi.fn() },
    componenten: {
      haal: vi.fn(), structuur: vi.fn(), contracten: vi.fn(), opties: vi.fn(),
      verwijder: vi.fn(), startBeoordeling: vi.fn(),
    },
    relaties: { lijst: vi.fn(), maak: vi.fn(), werkBij: vi.fn(), verwijder: vi.fn() },
    componentContracten: { maak: vi.fn(), werkBij: vi.fn(), verwijder: vi.fn() },
    contractconfig: { opties: vi.fn(() => Promise.resolve({ relatie_rol: [] })) },
    contracten: { lijst: vi.fn(() => Promise.resolve({ items: [], volgende_cursor: null })) },
    checklistvragen: { lijst: vi.fn(() => Promise.resolve([])) },
    checklistscores: {
      lijst: vi.fn(() => Promise.resolve({ items: [], volgende_cursor: null })),
      maak: vi.fn(), werkBij: vi.fn(), opties: vi.fn(() => Promise.resolve({ score: [] })),
    },
    blokkades: {
      lijst: vi.fn(() => Promise.resolve({ items: [], volgende_cursor: null })),
      opties: vi.fn(() => Promise.resolve({ status: [] })), werkBij: vi.fn(),
    },
    roltoewijzingen: {
      lijst: vi.fn(() => Promise.resolve([])), rollen: vi.fn(() => Promise.resolve([])),
      maak: vi.fn(), verwijder: vi.fn(),
    },
    partijen: { lijst: vi.fn(() => Promise.resolve({ items: [] })) },
    klaarverklaringen: { lijst: vi.fn(() => Promise.resolve([])), maak: vi.fn(), wijzigStatus: vi.fn() },
    signalering: { badgeComponent: vi.fn(() => Promise.resolve({ kritiek: 0, aandacht: 0 })) },
    functievervullingen: {
      componentKoppelingen: vi.fn(() => Promise.resolve([])), maak: vi.fn(),
      verwijder: vi.fn(), zetOordeel: vi.fn(),
    },
    bedrijfsfuncties: { lijst: vi.fn(() => Promise.resolve({ items: [], volgende_cursor: null })), haal: vi.fn() },
    componentNormen: { definitie: vi.fn(() => Promise.resolve([])) },
  },
}))

import { api } from '@/api'
import LandschapskaartView from '@modules/bwb_ontvlechting/frontend/views/LandschapskaartView.vue'
import ComponentDetail from '@modules/bwb_ontvlechting/frontend/views/ComponentDetail.vue'

const GRAF = () => ({
  nodes: [
    { id: 'a1', naam: 'Sociaal domein suite', element_type: 'applicatie', laag: 'application', lifecycle_status: 'concept', blokkades_open: 0 },
    { id: 'p1', naam: 'Gemeente West Betuwe', element_type: 'partij', laag: 'business', soort: 'organisatie', blokkades_open: 0 },
    { id: 'k1', naam: 'Suite-contract', element_type: 'contract', laag: 'business', blokkades_open: 0 },
    { id: 'plek:f1', naam: 'Inkomensondersteuning', element_type: 'bedrijfsfunctie', laag: 'business', blokkades_open: 0 },
  ],
  edges: [
    { bron_id: 'p1', doel_id: 'a1', relatietype: 'gebruikt', label: 'gebruikt', ring: 'gebruikt' },
    { bron_id: 'p1', doel_id: 'a1', relatietype: 'eigenaar', label: 'is eigendom van', ring: 'eigenaar' },
    { bron_id: 'a1', doel_id: 'k1', relatietype: 'association', label: 'valt onder', ring: 'contracten' },
    { bron_id: 'a1', doel_id: 'plek:f1', relatietype: 'functievervulling', label: 'ondersteunt', ring: 'bedrijfsfuncties' },
  ],
})

let wrappers = []
afterEach(() => { wrappers.forEach((w) => w.unmount()); wrappers = []; vi.restoreAllMocks() })

beforeEach(() => {
  vi.clearAllMocks()
  sessionStorage.clear()
  api.landschapskaart.haalGrafdata.mockResolvedValue(GRAF())
  api.landschapskaart.subgraaf.mockResolvedValue(GRAF())
  api.organisatiegebruik.lijstVoorApplicatie.mockResolvedValue([
    { id: 'g1', organisatie_id: 'p1', applicatie_id: 'a1', heeft_verfijning: false, afdelingen: [] },
  ])
  api.componenten.haal.mockResolvedValue({
    id: 'a1', naam: 'Sociaal domein suite', componenttype: 'applicatie', componenttype_label: 'Applicatie',
    hostingmodel: 'saas', beschrijving: null, heeft_applicatie_subtype: true, checklist_dragend: true,
    lifecycle_status: 'concept', componentrol: 'interne_applicatie', rol_label: 'Interne applicatie',
    biv_beschikbaarheid: null, biv_beschikbaarheid_label: null, biv_integriteit: null,
    biv_integriteit_label: null, biv_vertrouwelijkheid: null, biv_vertrouwelijkheid_label: null,
  })
  // Werkelijkheids-nabootsing 2: het echte component is checklist-dragend MET vragen —
  // de categorie-tabs vullen zich async en triggeren de URL-terugschrijf-keten.
  api.checklistvragen.lijst.mockResolvedValue([
    { id: 1, code: '1.1', categorie_nr: 1, categorie_naam: 'Algemeen', vraag: 'a', prioriteit: 'hoog' },
    { id: 2, code: '2.1', categorie_nr: 2, categorie_naam: 'Hosting', vraag: 'b', prioriteit: 'hoog' },
  ])
  api.componenten.structuur.mockResolvedValue({ draait_op: [], gebruikt_door: [] })
  api.componenten.contracten.mockResolvedValue([])
  api.componenten.opties.mockResolvedValue({ componenttype: [], structuurrelatie_type: [] })
})

async function mountFlow() {
    const pinia = createPinia()
    setActivePinia(pinia)
    useAuthStore().user = { sub: 's', tenant_id: 't', email: 'a@b.nl', roles: ['medewerker'] }
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/', name: 'home', component: { template: '<div/>' } },
        { path: '/landschapskaart', name: 'landschapskaart', component: LandschapskaartView },
        { path: '/componenten/:id', name: 'component-detail', component: ComponentDetail, props: true },
        { path: '/componenten', name: 'component-lijst', component: { template: '<div/>' } },
        { path: '/componenten/:id/bewerken', name: 'component-bewerken', component: { template: '<div/>' } },
        { path: '/applicaties/:id', name: 'applicatie-detail', component: { template: '<div/>' } },
        { path: '/contracten/:id', name: 'contract-detail', component: { template: '<div/>' } },
        { path: '/partijen/:id', name: 'partij-detail', component: { template: '<div/>' } },
        { path: '/processen', name: 'proces-lijst', component: { template: '<div/>' } },
        { path: '/processen/:id', name: 'proces-detail', component: { template: '<div/>' } },
        { path: '/bedrijfsfuncties', name: 'bedrijfsfunctie-lijst', component: { template: '<div/>' } },
      ],
    })
    await router.push('/landschapskaart')
    await router.isReady()
    const w = mount({ template: '<router-view />' }, {
      attachTo: document.body,
      global: { plugins: [pinia, [PrimeVue, { unstyled: true }], ToastService, router], stubs: { teleport: true } },
    })
    wrappers.push(w)
    await flushPromises()
    const kaart = w.findComponent(LandschapskaartView)
    kaart.vm.toonHeleLandschap()
    await flushPromises()
    return { w, kaart, router }
}

describe('LI046 — gebruikersflow: kaart → lijn → doorklik → landing (component mét vragen)', () => {
  it('gebruikt-lijn: de klik landt de echte ComponentDetail op de Gebruik-tab', async () => {
    const { w, kaart, router } = await mountFlow()
    await kaart.vm.openEdgePopup({ bron_id: 'p1', doel_id: 'a1', ring: 'gebruikt', label: 'gebruikt', relatietype: 'gebruikt' })
    await flushPromises()

    // Stap 1 (herstel-opdracht): boots de WERKELIJKHEID na — wacht tot de stand geladen
    // én zichtbaar is ("Stand" staat in de popup), en klik DAARNA pas. Bert klikt immers
    // nadat hij de stand gelezen heeft; een klik vóór de async stand-laad is de test-luwe
    // variant die het verschil met de browser kan maskeren.
    expect(w.find('[data-testid="lk-popup-velden"]').text()).toContain('Stand')
    expect(w.find('[data-testid="lk-popup-velden"]').text()).toContain('Op organisatieniveau')

    // Diagnose-splitser: droeg de PUSH de aanleiding (popup-kant ok) of niet?
    const pushSpy = vi.spyOn(router, 'push')

    // De gebruiker klikt "Open Sociaal domein suite →" (tweede actie = doel).
    await w.find('[data-testid="lk-popup-actie-1"]').trigger('click')
    expect(pushSpy).toHaveBeenCalledWith({ name: 'component-detail', params: { id: 'a1' }, query: { tab: 'gebruik' } })
    await flushPromises()
    await flushPromises()

    // Waar is hij geland?
    expect(router.currentRoute.value.name).toBe('component-detail')
    expect(router.currentRoute.value.query).toEqual({ tab: 'gebruik' })
    const detail = w.findComponent(ComponentDetail)
    expect(detail.exists()).toBe(true)
    expect(detail.find('#detailtabs-panel-gebruik').isVisible()).toBe(true)
    expect(detail.find('#detailtabs-panel-overzicht').isVisible()).toBe(false)
  })

  it('eigenaar-lijn: de klik landt op het Overzicht met het eigenaar-veld gemarkeerd', async () => {
    const { w, kaart, router } = await mountFlow()
    await kaart.vm.openEdgePopup({ bron_id: 'p1', doel_id: 'a1', ring: 'eigenaar', label: 'is eigendom van', relatietype: 'eigenaar' })
    await flushPromises()
    await w.find('[data-testid="lk-popup-actie-1"]').trigger('click')
    await flushPromises()
    await flushPromises()
    expect(router.currentRoute.value.query).toEqual({ veld: 'eigenaar' })
    const detail = w.findComponent(ComponentDetail)
    expect(detail.find('#detailtabs-panel-overzicht').isVisible()).toBe(true)
    expect(detail.find('#veld-eigenaar').classes().join(' ')).toContain('bg-[var(--lk-color-accent)]')
  })

  it('valt-onder-contract-lijn: de klik op het component landt op de Contracten-tab', async () => {
    const { w, kaart, router } = await mountFlow()
    await kaart.vm.openEdgePopup({ bron_id: 'a1', doel_id: 'k1', ring: 'contracten', label: 'valt onder', relatietype: 'association' })
    await flushPromises()
    // actie-0 = bron (het component); actie-1 = het contract (kaal).
    await w.find('[data-testid="lk-popup-actie"]').trigger('click')
    await flushPromises()
    await flushPromises()
    expect(router.currentRoute.value.query).toEqual({ tab: 'contracten' })
    const detail = w.findComponent(ComponentDetail)
    expect(detail.find('#detailtabs-panel-contracten').isVisible()).toBe(true)
  })

  it('ondersteunt-lijn: de klik op het systeem landt op de Bedrijfsfunctie-tab', async () => {
    const { w, kaart, router } = await mountFlow()
    await kaart.vm.openEdgePopup({ bron_id: 'a1', doel_id: 'plek:f1', ring: 'bedrijfsfuncties', label: 'ondersteunt', relatietype: 'functievervulling' })
    await flushPromises()
    await w.find('[data-testid="lk-popup-actie"]').trigger('click')
    await flushPromises()
    await flushPromises()
    expect(router.currentRoute.value.query).toEqual({ tab: 'bedrijfsfunctie' })
    const detail = w.findComponent(ComponentDetail)
    expect(detail.find('#detailtabs-panel-bedrijfsfunctie').isVisible()).toBe(true)
  })

  // Stap 3.3 — "toeval is geen borging": de blokkade-doorklik-vorm (tab+cat+markeer) én het
  // veld-anker bewezen veilig op een component MÉT vragen (de wipe-race-conditie actief).
  it('?tab=checklist&cat=1&markeer=1.1 overleeft de landing op een component met vragen', async () => {
    const { w, router } = await mountFlow()
    await router.push({ name: 'component-detail', params: { id: 'a1' }, query: { tab: 'checklist', cat: '1', markeer: '1.1' } })
    await flushPromises()
    await flushPromises()
    expect(router.currentRoute.value.query).toEqual({ tab: 'checklist', cat: '1', markeer: '1.1' })
    const detail = w.findComponent(ComponentDetail)
    expect(detail.find('#detailtabs-panel-checklist').isVisible()).toBe(true)
  })

  it('?veld=levensfase overleeft de landing op een component met vragen', async () => {
    const { w, router } = await mountFlow()
    await router.push({ name: 'component-detail', params: { id: 'a1' }, query: { veld: 'levensfase' } })
    await flushPromises()
    await flushPromises()
    expect(router.currentRoute.value.query).toEqual({ veld: 'levensfase' })
    const detail = w.findComponent(ComponentDetail)
    expect(detail.find('#veld-levensfase').classes().join(' ')).toContain('bg-[var(--lk-color-accent)]')
  })
})
