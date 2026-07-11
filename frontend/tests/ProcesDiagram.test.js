/**
 * Tests — ProcesDiagram (LI038 gate 1, proces-only structuurbeeld).
 *
 * Cytoscape gemockt (kaart-testpatroon): getest worden de lege staat, de focus-set-bedrading
 * (zoek → centrum → keten/zusjes/subboom), de gap-cue-doorgifte en de proces-only borging
 * (de component is api-vrij: alles komt uit de props — er is géén '@/api'-mock nodig en er
 * kán dus ook geen component-/vervuller-fetch plaatsvinden).
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'
import { createPinia } from 'pinia'
import { useAuthStore } from '@/store/auth'

const _cyInstanties = []
vi.mock('@/composables/cytoscape', () => ({
  default: vi.fn(() => {
    const inst = {
      add: vi.fn(),
      layout: vi.fn(() => ({ run: vi.fn() })),
      fit: vi.fn(), resize: vi.fn(), destroy: vi.fn(), on: vi.fn(),
      zoom: () => 1,
      nodes: () => ({ updateStyle: vi.fn(), forEach: vi.fn(), removeClass: vi.fn() }),
      elements: () => ({ remove: vi.fn() }),
      getElementById: () => ({ length: 0, addClass: vi.fn() }),
    }
    _cyInstanties.push(inst)
    return inst
  }),
}))

import ProcesDiagram from '@modules/bwb_ontvlechting/frontend/views/ProcesDiagram.vue'

// Boom: Vergunningverlening → Aanvraag behandelen → Besluit vastleggen
//                           → Toezicht houden → Controle uitvoeren
// plus een losse tweede boom Burgerzaken → Verhuizing verwerken.
const _p = (id, naam, ouder_id = null) => ({ id, naam, ouder_id })
const PROCESSEN = [
  _p('vv', 'Vergunningverlening'),
  _p('ab', 'Aanvraag behandelen', 'vv'),
  _p('bv', 'Besluit vastleggen', 'ab'),
  _p('th', 'Toezicht houden', 'vv'),
  _p('cu', 'Controle uitvoeren', 'th'),
  _p('bz', 'Burgerzaken'),
  _p('verh', 'Verhuizing verwerken', 'bz'),
]

function mountDiagram(props = {}) {
  // Router voor de "Open proces →"-link in de popup (gate 2); pinia + auth voor de
  // kaart-affordance-gating (spiegel van ProcesDetail: alle vier tenant-rollen).
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: { template: '<div/>' } },
      { path: '/processen/:id', name: 'proces-detail', component: { template: '<div/>' } },
      { path: '/landschapskaart', name: 'landschapskaart', component: { template: '<div/>' } },
    ],
  })
  const pinia = createPinia()
  const auth = useAuthStore(pinia)
  auth.user = { sub: 's', tenant_id: 't', email: 'a@b.nl', roles: ['medewerker'] }
  return mount(ProcesDiagram, {
    props: { processen: PROCESSEN, gapIds: null, ...props },
    global: { plugins: [pinia, [PrimeVue, { unstyled: true }], ToastService, router], stubs: { teleport: true } },
  })
}

beforeEach(() => { _cyInstanties.length = 0 })
afterEach(() => vi.clearAllMocks())

describe('ProcesDiagram — leeg openen + focus-set', () => {
  it('opent leeg met de uitnodiging om te zoeken', async () => {
    const w = mountDiagram()
    await flushPromises()
    expect(w.find('[data-testid="diagram-leeg"]').text()).toContain('Zoek een proces om te beginnen.')
    // Geen elementen getekend op de lege staat.
    const cy = _cyInstanties[0]
    expect(cy.add).not.toHaveBeenCalled()
  })

  it('centrum kiezen toont keten (boven) + subboom (beneden) + zusjes (opzij), zonder andere bomen', async () => {
    const w = mountDiagram()
    await flushPromises()
    w.vm.kiesCentrum({ id: 'ab' })
    await flushPromises()
    // Keten: vv. Subboom: bv. Zusje: th — maar diens subboom (cu) niet; andere boom (bz) niet.
    expect(w.vm.zichtbareIds).toEqual(new Set(['ab', 'vv', 'bv', 'th']))
    expect(w.find('[data-testid="diagram-leeg"]').exists()).toBe(false)
    // De getekende elementen zijn exact de focus-set + de echte ouder→kind-lijnen daarbinnen.
    const cy = _cyInstanties[0]
    expect(cy.add).toHaveBeenCalled()
    const elementen = cy.add.mock.calls.at(-1)[0]
    const nodeIds = elementen.filter((e) => !e.data.source).map((e) => e.data.id)
    const edges = elementen.filter((e) => e.data.source).map((e) => `${e.data.source}>${e.data.target}`)
    expect(new Set(nodeIds)).toEqual(new Set(['ab', 'vv', 'bv', 'th']))
    expect(new Set(edges)).toEqual(new Set(['ab>vv', 'bv>ab', 'th>vv']))
  })

  it('wortel-centrum: geen valse ouder-lijn boven de wortel', async () => {
    const w = mountDiagram()
    await flushPromises()
    w.vm.kiesCentrum({ id: 'bz' })
    await flushPromises()
    expect(w.vm.zichtbareIds).toEqual(new Set(['bz', 'verh']))
    const cy = _cyInstanties[0]
    const elementen = cy.add.mock.calls.at(-1)[0]
    const edges = elementen.filter((e) => e.data.source).map((e) => `${e.data.source}>${e.data.target}`)
    // Alleen de echte kind→ouder-lijn; niets boven de wortel, geen stam naar de andere boom.
    expect(edges).toEqual(['verh>bz'])
  })

  it('geeft de gap-cue (procesGap) alleen mee aan processen in de gap-set', async () => {
    const w = mountDiagram({ gapIds: new Set(['th', 'cu']) })
    await flushPromises()
    w.vm.kiesCentrum({ id: 'ab' })
    await flushPromises()
    const cy = _cyInstanties[0]
    const elementen = cy.add.mock.calls.at(-1)[0]
    const perId = new Map(elementen.filter((e) => !e.data.source).map((e) => [e.data.id, e.data]))
    expect(perId.get('th').procesGap).toBe(true)
    expect(perId.get('ab').procesGap).toBeUndefined() // undefined, niet false (CY-selector-conventie)
    expect(perId.get('vv').procesGap).toBeUndefined()
  })

  // ── LI038 gate 1 v2 — gekozen proces = label, geen slot-op-de-keuze ─────────────────────────
  it('v2 — heropenen ná een keuze biedt de VOLLEDIGE lijst aan; het diagram blijft staan', async () => {
    const w = mountDiagram()
    await flushPromises()
    // Kies via het echte zoekveld (focus → optie-mousedown, zoals de gebruiker).
    const input = w.find('[data-testid="diagram-zoek-input"]')
    await input.trigger('focus')
    await flushPromises()
    await w.find('[data-testid="diagram-zoek-optie-ab"]').trigger('mousedown')
    await flushPromises()
    expect(w.vm.centrumId).toBe('ab')
    expect(input.element.value).toBe('Aanvraag behandelen — Vergunningverlening')
    // Heropenen: de input hield focus → klik (geen focus-event) → volledige set, geen filter.
    await input.trigger('click')
    await flushPromises()
    expect(w.findAll('[role="option"]').length).toBe(PROCESSEN.length)
    expect(w.vm.zichtbareIds).toEqual(new Set(['ab', 'vv', 'bv', 'th'])) // diagram ongewijzigd
  })

  it('v2 — typen vervangt en filtert vers; het centrum wijzigt pas bij een NIEUWE keuze', async () => {
    const w = mountDiagram()
    await flushPromises()
    const input = w.find('[data-testid="diagram-zoek-input"]')
    await input.trigger('focus')
    await flushPromises()
    await w.find('[data-testid="diagram-zoek-optie-ab"]').trigger('mousedown')
    await flushPromises()
    // Typen (vervangt de voorgevulde tekst) → vers filteren; het diagram blijft op 'ab'.
    vi.useFakeTimers()
    await input.setValue('burger')
    vi.advanceTimersByTime(300)
    vi.useRealTimers()
    await flushPromises()
    expect(w.vm.centrumId).toBe('ab') // focus/typen wisselt het beeld niet
    const opties = w.findAll('[role="option"]')
    expect(opties.length).toBe(1) // soepel gefilterd op het nieuwe fragment
    // Pas de nieuwe keuze wisselt het diagram.
    await w.find('[data-testid="diagram-zoek-optie-bz"]').trigger('mousedown')
    await flushPromises()
    expect(w.vm.centrumId).toBe('bz')
    expect(w.vm.zichtbareIds).toEqual(new Set(['bz', 'verh']))
  })

  it('v2 — het ×-wis-gebaar leegt het veld en toont de volledige lijst; het diagram blijft tot een nieuwe keuze', async () => {
    const w = mountDiagram()
    await flushPromises()
    const input = w.find('[data-testid="diagram-zoek-input"]')
    await input.trigger('focus')
    await flushPromises()
    await w.find('[data-testid="diagram-zoek-optie-ab"]').trigger('mousedown')
    await flushPromises()
    await w.find('[data-testid="diagram-zoek-wis"]').trigger('click')
    await flushPromises()
    expect(input.element.value).toBe('')
    expect(w.findAll('[role="option"]').length).toBe(PROCESSEN.length) // volledige lijst open
    expect(w.vm.centrumId).toBe('ab') // diagram staat nog — wisselt pas bij een nieuwe keuze
    expect(w.vm.zichtbareIds.size).toBe(4)
  })

  it('verdwijnt het centrum uit de set (bv. verwijderd), dan valt het beeld terug naar de lege staat', async () => {
    const w = mountDiagram()
    await flushPromises()
    w.vm.kiesCentrum({ id: 'verh' })
    await flushPromises()
    expect(w.vm.zichtbareIds.size).toBe(2)
    await w.setProps({ processen: PROCESSEN.filter((p) => p.id !== 'verh') })
    await flushPromises()
    expect(w.vm.zichtbareIds.size).toBe(0)
    expect(w.find('[data-testid="diagram-leeg"]').exists()).toBe(true)
  })
})

describe('ProcesDiagram — LI038 gate 2: enkele klik = kijken (selectie + popup)', () => {
  async function metCentrum(props = {}) {
    const w = mountDiagram(props)
    await flushPromises()
    w.vm.kiesCentrum({ id: 'ab' })
    await flushPromises()
    return w
  }

  it('klik selecteert (oranje via de cy-tap-wiring) en opent de popup met naam + klikbare plek', async () => {
    const w = await metCentrum()
    // De echte klik-bedrading: de bij cy geregistreerde tap-handlers aanroepen.
    const cy = _cyInstanties[0]
    const nodeTap = cy.on.mock.calls.find((c) => c[0] === 'tap' && c[1] === 'node')[2]
    nodeTap({ target: { id: () => 'bv' } })
    await flushPromises()
    expect(w.vm.geselecteerdId).toBe('bv')
    expect(w.find('[data-testid="diagram-popup-naam"]').text()).toBe('Besluit vastleggen')
    // Plek in woorden: de keten van wortel naar directe ouder, elk klikbaar.
    const plek = w.find('[data-testid="diagram-popup-plek"]')
    expect(plek.text()).toContain('onder')
    expect(plek.text()).toContain('Vergunningverlening')
    expect(plek.text()).toContain('Aanvraag behandelen')
    // Kijken ≠ navigeren: set/weergave onveranderd (focus blijft rond het centrum 'ab').
    expect(w.vm.zichtbareIds).toEqual(new Set(['ab', 'vv', 'bv', 'th']))
    // Pad-klik inspecteert die ouder (zelfde enkelklik-semantiek).
    await w.find('[data-testid="diagram-popup-pad-vv"]').trigger('click')
    expect(w.find('[data-testid="diagram-popup-naam"]').text()).toBe('Vergunningverlening')
    expect(w.find('[data-testid="diagram-popup-plek"]').text()).toBe('Hoofdproces')
  })

  it('klik naast een knoop (background-tap) sluit de popup en heft de selectie op', async () => {
    const w = await metCentrum()
    w.vm.selecteer('th')
    await flushPromises()
    expect(w.find('[data-testid="diagram-popup"]').exists()).toBe(true)
    const cy = _cyInstanties[0]
    const bgTap = cy.on.mock.calls.find((c) => c[0] === 'tap' && typeof c[1] === 'function')[1]
    bgTap({ target: cy }) // klik op het lege canvas: target === cy
    await flushPromises()
    expect(w.find('[data-testid="diagram-popup"]').exists()).toBe(false)
    expect(w.vm.geselecteerdId).toBe(null)
    bgTap({ target: { id: () => 'x' } }) // een knoop-tap bubbelt óók hierheen → mag NIET sluiten
    expect(w.vm.popupId).toBe(null) // (was al dicht; belangrijkste: geen crash/verkeerd pad)
  })

  it('gap-cue verschijnt alleen bij een ondersteuningsloze subboom (zelfde cue-taal)', async () => {
    const w = await metCentrum({ gapIds: new Set(['th']) })
    w.vm.selecteer('th')
    await flushPromises()
    expect(w.find('[data-testid="diagram-popup-gap"]').text()).toBe('geen ondersteunend systeem')
    w.vm.selecteer('ab')
    await flushPromises()
    expect(w.find('[data-testid="diagram-popup-gap"]').exists()).toBe(false)
  })

  it('"Toon hele processenlandschap" verbreedt BINNEN het beeld: alle bomen, geen kaart/route/emit', async () => {
    const w = await metCentrum()
    w.vm.selecteer('ab')
    await flushPromises()
    await w.find('[data-testid="diagram-popup-landschap"]').trigger('click')
    await flushPromises()
    expect(w.vm.zichtbareIds).toEqual(new Set(PROCESSEN.map((p) => p.id))) // álle bomen
    expect(w.emitted('bekijkOpKaart')).toBeUndefined() // géén kaart-doorschakeling
    expect(w.find('[data-testid="diagram-popup"]').exists()).toBe(true) // popup blijft (kijken)
    // Een nieuwe keuze zet het beeld terug op de focus rond dat centrum.
    w.vm.kiesCentrum({ id: 'bz' })
    await flushPromises()
    expect(w.vm.zichtbareIds).toEqual(new Set(['bz', 'verh']))
  })

  it('"Bekijk op de kaart →" emit het proces — de doorschakeling (api-werk) hoort bij de ouder', async () => {
    const w = await metCentrum()
    w.vm.selecteer('ab')
    await flushPromises()
    await w.find('[data-testid="diagram-popup-kaart"]').trigger('click')
    expect(w.emitted('bekijkOpKaart')).toHaveLength(1)
    expect(w.emitted('bekijkOpKaart')[0][0].id).toBe('ab')
  })

  it('"Open proces →" linkt naar het proces-detailscherm', async () => {
    const w = await metCentrum()
    w.vm.selecteer('bv')
    await flushPromises()
    expect(w.find('[data-testid="diagram-popup-open"]').attributes('href')).toContain('/processen/bv')
  })

  // ── LI038 gate 2 v2 — versleepbare popup (gedeelde useSleepbaar-bouwsteen) ──
  it('v2 — de popup is versleepbaar: drag muteert de positie zonder sprong (DOM-init)', async () => {
    const w = await metCentrum()
    w.vm.selecteer('ab')
    await flushPromises()
    expect(w.vm.popupPos).toEqual({ x: null, y: null }) // standaardplek (CSS)
    await w.find('[data-testid="diagram-popup"]').trigger('mousedown', { clientX: 700, clientY: 90 })
    expect(w.vm.popupSleept).toBe(true)
    expect(w.vm.popupPos.x).not.toBe(null) // geïnitialiseerd uit de DOM-positie, niet (0,0)-sprong
    const start = { ...w.vm.popupPos }
    document.dispatchEvent(new MouseEvent('mousemove', { clientX: 750, clientY: 130 }))
    expect(w.vm.popupPos).toEqual({ x: start.x + 50, y: start.y + 40 }) // relatief meegeschoven
    document.dispatchEvent(new MouseEvent('mouseup'))
    expect(w.vm.popupSleept).toBe(false)
    // Gesleept = viewport-positie op het paneel zelf.
    await flushPromises()
    expect(w.find('[data-testid="diagram-popup"]').attributes('style')).toContain('position: fixed')
  })

  it('v2 — de actieknoppen zijn geen sleep-greep (klik blijft klik)', async () => {
    const w = await metCentrum()
    w.vm.selecteer('ab')
    await flushPromises()
    await w.find('[data-testid="diagram-popup-landschap"]').trigger('mousedown', { clientX: 10, clientY: 10 })
    expect(w.vm.popupSleept).toBe(false)
    expect(w.vm.popupPos).toEqual({ x: null, y: null })
  })

  it('g3 — dubbelklik (cy-tap-wiring) zoomt in: alleen het proces + zijn subboom; enkele klik blijft direct kijken', async () => {
    const w = await metCentrum() // focus rond 'ab' = {ab, vv, bv, th}
    const cy = _cyInstanties[0]
    const nodeTap = cy.on.mock.calls.find((c) => c[0] === 'tap' && c[1] === 'node')[2]
    // Enkele klik: DIRECT popup (geen uitstel) en géén centrum-/scope-wissel.
    nodeTap({ target: { id: () => 'bv' } })
    await flushPromises()
    expect(w.find('[data-testid="diagram-popup"]').exists()).toBe(true) // meteen zichtbaar
    expect(w.vm.inzoomId).toBe(null)
    expect(w.vm.zichtbareIds).toEqual(new Set(['ab', 'vv', 'bv', 'th']))
    // Tweede tap binnen de drempel = dubbelklik → inzoom: het beeld perkt écht in.
    nodeTap({ target: { id: () => 'bv' } })
    await flushPromises()
    expect(w.vm.inzoomId).toBe('bv')
    expect(w.vm.centrumId).toBe('bv')
    expect(w.vm.geselecteerdId).toBe('bv') // oranje op het nieuwe centrum
    expect(w.vm.zichtbareIds).toEqual(new Set(['bv'])) // subboom-only (blad → alleen zichzelf)
    expect(w.find('[data-testid="diagram-popup"]').exists()).toBe(false) // navigeren, niet inspecteren
  })

  it('g3 — inzoom op een blad met 0 kinderen én 0 vervullers slaagt (geen weigering — het proces-only pad)', async () => {
    const w = await metCentrum()
    w.vm.zoomInOp('bv') // blad; het diagram is api-vrij, dus vervuller-calls zijn onmogelijk
    await flushPromises()
    expect(w.vm.zichtbareIds).toEqual(new Set(['bv']))
    expect(w.find('[data-testid="diagram-leeg"]').exists()).toBe(false) // nette, niet-lege stand
  })

  it('g3 — "← Terug" herstelt de vorige stand, ook over meerdere stappen (history)', async () => {
    const w = await metCentrum() // staat 2: focus rond ab (zaad = lege staat 1)
    expect(w.find('[data-testid="diagram-terug"]').exists()).toBe(true) // er is al een vorige (leeg)
    w.vm.zoomInOp('ab') // staat 3: inzoom ab = {ab, bv} (th hangt onder vv, niet onder ab)
    await flushPromises()
    expect(w.vm.zichtbareIds).toEqual(new Set(['ab', 'bv']))
    w.vm.zoomInOp('bv') // staat 4: inzoom bv = {bv}
    await flushPromises()
    expect(w.vm.zichtbareIds).toEqual(new Set(['bv']))
    await w.find('[data-testid="diagram-terug"]').trigger('click') // → staat 3
    expect(w.vm.inzoomId).toBe('ab')
    expect(w.vm.zichtbareIds).toEqual(new Set(['ab', 'bv']))
    await w.find('[data-testid="diagram-terug"]').trigger('click') // → staat 2
    await flushPromises()
    expect(w.vm.inzoomId).toBe(null)
    expect(w.vm.zichtbareIds).toEqual(new Set(['ab', 'vv', 'bv', 'th'])) // focus exact terug
  })

  it('g3 — "Toon in procesbeeld"-ingang (initieelCentrumId): neutraal open, oranje, géén inperking, verse history-wortel', async () => {
    const w = mountDiagram({ initieelCentrumId: 'ab' })
    await flushPromises()
    expect(w.vm.centrumId).toBe('ab')
    expect(w.vm.geselecteerdId).toBe('ab') // oranje "kijk hier"
    expect(w.vm.inzoomId).toBe(null) // neutraal — geen set-inperking
    expect(w.vm.zichtbareIds).toEqual(new Set(['ab', 'vv', 'bv', 'th'])) // volledige focus
    expect(w.find('[data-testid="diagram-terug"]').exists()).toBe(false) // ingang = history-wortel
    expect(w.emitted('centrumGewijzigd').at(-1)).toEqual(['ab']) // ouder blijft bij (plek behouden)
  })

  it('v2 — de positie reset bij sluiten en bij een nieuwe proceskeuze (geen onthouden drift)', async () => {
    const w = await metCentrum()
    w.vm.selecteer('ab')
    await flushPromises()
    await w.find('[data-testid="diagram-popup"]').trigger('mousedown', { clientX: 700, clientY: 90 })
    document.dispatchEvent(new MouseEvent('mousemove', { clientX: 760, clientY: 150 }))
    document.dispatchEvent(new MouseEvent('mouseup'))
    expect(w.vm.popupPos.x).not.toBe(null)
    w.vm.sluitPopup() // sluiten → standaardplek terug
    expect(w.vm.popupPos).toEqual({ x: null, y: null })
    // Opnieuw slepen, dan een nieuwe proceskeuze → ook terug naar de standaardplek.
    w.vm.selecteer('ab')
    await flushPromises()
    await w.find('[data-testid="diagram-popup"]').trigger('mousedown', { clientX: 700, clientY: 90 })
    document.dispatchEvent(new MouseEvent('mousemove', { clientX: 720, clientY: 100 }))
    document.dispatchEvent(new MouseEvent('mouseup'))
    expect(w.vm.popupPos.x).not.toBe(null)
    w.vm.kiesCentrum({ id: 'bz' })
    await flushPromises()
    expect(w.vm.popupPos).toEqual({ x: null, y: null })
  })
})
