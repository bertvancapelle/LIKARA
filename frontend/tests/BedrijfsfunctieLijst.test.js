/** Tests — BedrijfsfunctieLijst (functieboom, ADR-043 gate 1a blok 2).
 *
 * Kern: de affordances spiegelen de backend-regels (LI032 picker-regel 1) —
 * modelinhoud kent géén bewerk-/verplaats-/verwijder-knop (422 MODELINHOUD_BESCHERMD),
 * een vervallen functie géén "+ Deelfunctie" (VERVALLEN_NIET_KOPPELBAAR) en tóónt de
 * rustige markering; eigen functies zijn wél volledig bewerkbaar. Het Diagram is de
 * gegeneraliseerde ProcesDiagram-bouwsteen met functie-taal (geen kaart-/detail-uitgang).
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'

vi.mock('@/api', () => ({
  api: {
    bedrijfsfuncties: { lijst: vi.fn(), maak: vi.fn(), werkBij: vi.fn(), verwijder: vi.fn() },
  },
}))

vi.mock('@/meldingen', () => ({ toastSucces: vi.fn() }))

// De Diagram-weergave mount ProcesDiagram (cytoscape); gemockt volgens het kaart-testpatroon.
vi.mock('@/composables/cytoscape', () => ({
  default: vi.fn(() => ({
    add: vi.fn(), layout: () => ({ run: vi.fn() }), fit: vi.fn(), resize: vi.fn(),
    destroy: vi.fn(), on: vi.fn(), zoom: () => 1,
    nodes: () => ({ updateStyle: vi.fn(), forEach: vi.fn(), removeClass: vi.fn() }),
    elements: () => ({ remove: vi.fn() }),
    getElementById: () => ({ length: 0, addClass: vi.fn() }),
  })),
}))

import { api } from '@/api'
import { toastSucces } from '@/meldingen'
import { useAuthStore } from '@/store/auth'
import BedrijfsfunctieLijst from '@modules/bwb_ontvlechting/frontend/views/BedrijfsfunctieLijst.vue'
import ProcesDiagram from '@modules/bwb_ontvlechting/frontend/views/ProcesDiagram.vue'

function maakRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/bedrijfsfuncties', name: 'bedrijfsfunctie-lijst', component: BedrijfsfunctieLijst },
    ],
  })
}

const _f = (id, naam, ouder_id = null, extra = {}) => ({
  id, naam, ouder_id,
  definitie: null, bron_model_id: null, bron_sleutel: null,
  bron_model_naam: null, bron_model_versie: null, vervallen: false,
  created_at: '2026-07-12T10:00:00Z', updated_at: '2026-07-12T10:00:00Z',
  ...extra,
})

// Geseede boom (gate-1a-vorm): Primair (model) → Dienstverlening (model) → Klantcontact
// (model); Besturend (model) → Regionale samenwerking (model, VERVALLEN); Datagedreven
// werken (EIGEN, onder Dienstverlening).
const _MODEL = { bron_model_id: 'rm1', bron_sleutel: 'x', bron_model_naam: 'GEMMA Bedrijfsfuncties', bron_model_versie: 'GEMMA 2 (2025)' }
const _boom = () => [
  _f('pr', 'Primair', null, { ..._MODEL, bron_sleutel: 'primair', definitie: 'Kernactiviteiten.' }),
  _f('dv', 'Dienstverlening', 'pr', { ..._MODEL, bron_sleutel: 'dienstverlening' }),
  _f('kc', 'Klantcontact', 'dv', { ..._MODEL, bron_sleutel: 'klantcontact' }),
  _f('bs', 'Besturend', null, { ..._MODEL, bron_sleutel: 'besturend' }),
  _f('rs', 'Regionale samenwerking', 'bs', { ..._MODEL, bron_sleutel: 'regionale_samenwerking', vervallen: true }),
  _f('ddw', 'Datagedreven werken', 'dv', { definitie: 'Eigen functie van de gemeente.' }),
]

async function mountLijst({ rollen = ['medewerker'] } = {}) {
  const router = maakRouter()
  await router.push('/bedrijfsfuncties')
  await router.isReady()
  const pinia = createPinia()
  const auth = useAuthStore(pinia)
  auth.user = { sub: 's', tenant_id: 't', email: 'a@b.nl', roles: rollen }
  const w = mount(BedrijfsfunctieLijst, { global: { plugins: [pinia, [PrimeVue, { unstyled: true }], ToastService, router], stubs: { teleport: true } } })
  await flushPromises()
  return w
}

beforeEach(() => {
  vi.clearAllMocks()
  sessionStorage.clear() // lijststaat (useLijstStaat) mag niet tussen tests lekken
  api.bedrijfsfuncties.lijst.mockResolvedValue({ items: _boom(), volgende_cursor: null })
})
afterEach(() => vi.restoreAllMocks())

describe('BedrijfsfunctieLijst — boomweergave', () => {
  it('toont wortels; deelfuncties pas na uitklappen', async () => {
    const w = await mountLijst()
    const boom = () => w.find('[data-testid="functies-boom"]').text()
    expect(boom()).toContain('Primair')
    expect(boom()).toContain('Besturend')
    expect(boom()).not.toContain('Dienstverlening') // ingeklapt
    await w.find('[data-testid="functie-toggle-pr"]').trigger('click')
    expect(boom()).toContain('Dienstverlening')
    expect(w.find('[data-testid="functie-toggle-pr"]').attributes('aria-expanded')).toBe('true')
  })

  it("haalt ALLE pagina's op voor de boom (keyset-lus)", async () => {
    api.bedrijfsfuncties.lijst
      .mockResolvedValueOnce({ items: [_boom()[0]], volgende_cursor: 'c1' })
      .mockResolvedValueOnce({ items: _boom().slice(1), volgende_cursor: null })
    const w = await mountLijst()
    expect(api.bedrijfsfuncties.lijst).toHaveBeenCalledTimes(2)
    expect(api.bedrijfsfuncties.lijst).toHaveBeenLastCalledWith({ limit: 100, after: 'c1' })
    expect(w.find('[data-testid="functies-boom"]').text()).toContain('Besturend')
  })

  it('zoeken filtert soepel en klapt de paden naar de treffers open', async () => {
    const w = await mountLijst()
    await w.find('[data-testid="filter-zoek"]').setValue('klantcon')
    const boom = w.find('[data-testid="functies-boom"]').text()
    expect(boom).toContain('Klantcontact') // pad opengeklapt
    expect(boom).toContain('Primair')
    expect(boom).not.toContain('Besturend') // geen treffer in die boom
  })
})

describe('BedrijfsfunctieLijst — modelinhoud vs. eigen (affordance spiegelt de backend)', () => {
  it('model-functie: herkomst ÉÉN keer boven de boom (uit de data), niet per rij; geen bewerk-affordance', async () => {
    const w = await mountLijst({ rollen: ['beheerder'] })
    // Punt 3 — informatie die overal hetzelfde is, is geen informatie: de herkomst
    // staat éénmaal boven de boom (data-gedreven, incl. de eigen-functies-zin) en
    // NIET meer op de rij.
    expect(w.find('[data-testid="functie-model-herkomst"]').text())
      .toBe('Uit GEMMA Bedrijfsfuncties, GEMMA 2 (2025). Eigen functies zijn gemarkeerd.')
    expect(w.find('[data-testid="functie-herkomst-pr"]').exists()).toBe(false)
    expect(w.find('[data-testid="functie-bewerk-pr"]').exists()).toBe(false)
    expect(w.find('[data-testid="functie-verplaats-pr"]').exists()).toBe(false)
    expect(w.find('[data-testid="functie-verwijder-pr"]').exists()).toBe(false)
    expect(w.find('[data-testid="functie-deelfunctie-pr"]').exists()).toBe(true)
  })

  it('eigen functie: "eigen"-badge + bewerk-/verplaats-knop (medewerker); verwijderen alléén beheerder', async () => {
    const w = await mountLijst({ rollen: ['medewerker'] })
    await w.find('[data-testid="functie-toggle-pr"]').trigger('click')
    await w.find('[data-testid="functie-toggle-dv"]').trigger('click')
    expect(w.find('[data-testid="functie-eigen-ddw"]').exists()).toBe(true)
    expect(w.find('[data-testid="functie-bewerk-ddw"]').exists()).toBe(true)
    expect(w.find('[data-testid="functie-verplaats-ddw"]').exists()).toBe(true)
    expect(w.find('[data-testid="functie-verwijder-ddw"]').exists()).toBe(false) // LI037-regel
    const w2 = await mountLijst({ rollen: ['beheerder'] })
    await w2.find('[data-testid="functie-toggle-pr"]').trigger('click')
    await w2.find('[data-testid="functie-toggle-dv"]').trigger('click')
    expect(w2.find('[data-testid="functie-verwijder-ddw"]').exists()).toBe(true)
  })

  it('viewer: alleen kijken — geen enkele mutatie-affordance', async () => {
    const w = await mountLijst({ rollen: ['viewer'] })
    expect(w.find('[data-testid="nieuwe-functie"]').exists()).toBe(false)
    expect(w.find('[data-testid="functie-deelfunctie-pr"]').exists()).toBe(false)
    expect(w.find('[data-testid="functie-diagram-pr"]').exists()).toBe(true) // lezen mag
  })

  it('vervallen functie: warning-tint + ⚠-icoon + tekst (nooit alléén kleur), geen "+ Deelfunctie"', async () => {
    const w = await mountLijst()
    await w.find('[data-testid="functie-toggle-bs"]').trigger('click')
    const badge = w.find('[data-testid="functie-vervallen-rs"]')
    expect(badge.text()).toContain('vervallen in het referentiemodel') // tekst
    expect(badge.text()).toContain('⚠') // icoon
    expect(badge.attributes('class')).toContain('--lk-color-warning') // warning-taal…
    expect(badge.attributes('class')).not.toContain('border-dashed') // …niet de gap-taal
    // De hele rij draagt de rustige waarschuwingstint (LI039 blok C).
    expect(w.find('[data-testid="functie-rij-rs"]').attributes('class')).toContain('--lk-color-warning')
    expect(w.find('[data-testid="functie-deelfunctie-rs"]').exists()).toBe(false)
    expect(w.find('[data-testid="functie-bewerk-rs"]').exists()).toBe(false)
  })

  it('C0 — rij-acties zijn rustig: rij draagt lk-rij, acties in de gedeelde RijActies-container', async () => {
    const w = await mountLijst({ rollen: ['beheerder'] })
    const rij = w.find('[data-testid="functie-rij-pr"]')
    expect(rij.attributes('class')).toContain('lk-rij') // hover/focus-within-contract (main.css)
    expect(rij.find('.lk-rij-acties').exists()).toBe(true)
    // De acties staan ín de container (verschijnen op de actieve rij / via focus).
    expect(rij.find('.lk-rij-acties [data-testid="functie-diagram-pr"]').exists()).toBe(true)
    // Het "eigen"-label is een eigenschap, geen actie: geen accent-knop-achtergrond.
    await w.find('[data-testid="functie-toggle-pr"]').trigger('click')
    await w.find('[data-testid="functie-toggle-dv"]').trigger('click')
    expect(w.find('[data-testid="functie-eigen-ddw"]').attributes('class')).not.toContain('--lk-color-accent')
  })

  it('UI-afronding v2 — drievorm + tweelaags rij: scan-laag (naam + afwijking) en lees-laag (volledige definitie)', async () => {
    const w = await mountLijst({ rollen: ['beheerder'] })
    // Punt 1 (v1, blijft) — doorklik (navigatie) vs. mutatie: de vorm vertelt het verschil.
    const doorklik = w.findComponent('[data-testid="functie-diagram-pr"]')
    expect(doorklik.props('text')).toBe(true)
    expect(doorklik.props('label')).toContain('→')
    expect(w.findComponent('[data-testid="functie-deelfunctie-pr"]').props('outlined')).toBe(true)
    await w.find('[data-testid="functie-toggle-pr"]').trigger('click')
    await w.find('[data-testid="functie-toggle-dv"]').trigger('click')
    expect(w.findComponent('[data-testid="functie-bewerk-ddw"]').props('outlined')).toBe(true)
    expect(w.findComponent('[data-testid="functie-verwijder-ddw"]').props('severity')).toBe('danger')
    // Punt 1 (v2) — tweelaags: naam in de scan-laag, de VOLLEDIGE definitie in de
    // lees-laag (twee-regel-clamp via de gedeelde klasse — géén één-regel-truncate,
    // geen tooltip, geen uitklap).
    const rij = w.find('[data-testid="functie-rij-pr"]')
    expect(rij.find('.lk-rij-kop [data-testid="functie-naam"]').exists()).toBe(true)
    const definitie = rij.find('[data-testid="functie-definitie-pr"]')
    expect(definitie.text()).toBe('Kernactiviteiten.') // volledige tekst in de DOM
    expect(definitie.attributes('class')).toContain('lk-rij-definitie')
    expect(definitie.attributes('class')).not.toContain('truncate')
    // Punt 2 (v2) — gereserveerde actiekolom: álle vijf beheerder-acties op een eigen
    // functie staan bínnen de RijActies-container (nooit een knop buiten beeld).
    const eigenRij = w.find('[data-testid="functie-rij-ddw"]')
    expect(eigenRij.findAll('.lk-rij-acties button').length).toBe(5)
    // De vervallen-badge hoort bij de naam (scan-laag).
    await w.find('[data-testid="functie-toggle-bs"]').trigger('click')
    const vervallenRij = w.find('[data-testid="functie-rij-rs"]')
    expect(vervallenRij.find('.lk-rij-kop [data-testid="functie-vervallen-rs"]').exists()).toBe(true)
  })
})

describe('BedrijfsfunctieLijst — toevoegen/bewerken (eigen functies)', () => {
  it('"Nieuwe functie" maakt een wortel; "+ Deelfunctie" vult de ouder voor', async () => {
    api.bedrijfsfuncties.maak.mockResolvedValue({ id: 'n1' })
    const w = await mountLijst()
    await w.find('[data-testid="nieuwe-functie"]').trigger('click')
    await w.find('[data-testid="functie-form-naam"]').setValue('Nieuw domein')
    await w.find('[data-testid="functie-dialog"] form').trigger('submit')
    await flushPromises()
    expect(api.bedrijfsfuncties.maak).toHaveBeenCalledWith({ naam: 'Nieuw domein', definitie: null, ouder_id: null })
    expect(toastSucces).toHaveBeenCalledWith(expect.anything(), 'Functie aangemaakt')

    await w.find('[data-testid="functie-deelfunctie-pr"]').trigger('click')
    expect(w.find('[data-testid="functie-dialog"]').text()).toContain('Primair')
    await w.find('[data-testid="functie-form-naam"]').setValue('Subsidieverlening')
    await w.find('[data-testid="functie-dialog"] form').trigger('submit')
    await flushPromises()
    expect(api.bedrijfsfuncties.maak).toHaveBeenLastCalledWith({ naam: 'Subsidieverlening', definitie: null, ouder_id: 'pr' })
  })

  it('bewerken van een eigen functie stuurt naam + definitie', async () => {
    api.bedrijfsfuncties.werkBij.mockResolvedValue({ id: 'ddw' })
    const w = await mountLijst()
    await w.find('[data-testid="functie-toggle-pr"]').trigger('click')
    await w.find('[data-testid="functie-toggle-dv"]').trigger('click')
    await w.find('[data-testid="functie-bewerk-ddw"]').trigger('click')
    await w.find('[data-testid="functie-form-naam"]').setValue('Datagedreven sturing')
    await w.find('[data-testid="functie-dialog"] form').trigger('submit')
    await flushPromises()
    expect(api.bedrijfsfuncties.werkBij).toHaveBeenCalledWith('ddw', { naam: 'Datagedreven sturing', definitie: 'Eigen functie van de gemeente.' })
    expect(toastSucces).toHaveBeenCalledWith(expect.anything(), 'Opgeslagen')
  })

  it('verwijderen: bevestigingsdialoog → api; 409 wordt een leesbare zin in de dialoog', async () => {
    api.bedrijfsfuncties.verwijder.mockRejectedValueOnce({ status: 409 })
    const w = await mountLijst({ rollen: ['beheerder'] })
    await w.find('[data-testid="functie-toggle-pr"]').trigger('click')
    await w.find('[data-testid="functie-toggle-dv"]').trigger('click')
    await w.find('[data-testid="functie-verwijder-ddw"]').trigger('click')
    await w.find('[data-testid="functie-verwijder-bevestig"]').trigger('click')
    await flushPromises()
    expect(api.bedrijfsfuncties.verwijder).toHaveBeenCalledWith('ddw')
    expect(w.find('[data-testid="functie-verwijder-fout"]').text()).toContain('onderliggende functies')
  })
})

describe('BedrijfsfunctieLijst — Diagram (gegeneraliseerde bouwsteen, functie-taal)', () => {
  it('schakelt naar het functie-diagram met functie-taal, vervallen via het EIGEN kanaal, zónder kaart-/detail-uitgang', async () => {
    const w = await mountLijst()
    await w.find('[data-testid="weergave-diagram"]').trigger('click')
    await flushPromises()
    expect(w.find('[data-testid="functie-diagram"]').exists()).toBe(true)
    expect(w.text()).toContain('Zoek een bedrijfsfunctie')
    const diagram = w.findComponent(ProcesDiagram)
    expect(diagram.props('metKaartUitgang')).toBe(false)
    expect(diagram.props('detailRoute')).toBe(null)
    expect(diagram.props('items').map((f) => f.id)).toContain('ddw')
    // LI039 blok C — vervallen loopt via het EIGEN kanaal; het gap-kanaal blijft vrij
    // voor de echte gap-cue (gate 3) — beide toestanden blijven zo uit elkaar te houden.
    expect(diagram.props('vervallenIds').has('rs')).toBe(true)
    expect(diagram.props('gapIds')).toBe(null)
    expect(diagram.props('teksten').vervallen).toBe('vervallen in het referentiemodel')
  })

  it('v3-regressie (bouwsteen) — de popup bestaat op INHOUD, óók zonder énige uitgang', async () => {
    // De popup-regressie ontstond doordat niemand hem in een test opende; dit mag
    // nooit meer stil wegvallen. Kale mount: geen detail-route, geen kaart, geen
    // open-label — en tóch een popup met de naam.
    const w = mount(ProcesDiagram, {
      props: {
        items: [_f('x1', 'Solo', null, { definitie: 'Definitie van Solo.' })],
        detailRoute: null,
        metKaartUitgang: false,
      },
      global: { plugins: [createPinia(), [PrimeVue, { unstyled: true }]] },
    })
    await flushPromises()
    w.vm.selecteer('x1')
    await flushPromises()
    expect(w.find('[data-testid="diagram-popup"]').exists()).toBe(true)
    expect(w.find('[data-testid="diagram-popup-naam"]').text()).toBe('Solo')
    expect(w.find('[data-testid="diagram-popup-open"]').exists()).toBe(false) // geen uitgangen — popup blijft
  })

  it('v3 — de functie-popup toont plek + DEFINITIE + vervallen; "Open functie →" landt op de Boom-rij', async () => {
    const w = await mountLijst()
    await w.find('[data-testid="weergave-diagram"]').trigger('click')
    await flushPromises()
    const diagram = w.findComponent(ProcesDiagram)
    // Klik = kijken: popup met naam, plek in woorden en de definitie (de kern).
    diagram.vm.selecteer('dv')
    await flushPromises()
    expect(w.find('[data-testid="diagram-popup-naam"]').text()).toBe('Dienstverlening')
    expect(w.find('[data-testid="diagram-popup-plek"]').text()).toContain('Primair')
    expect(w.find('[data-testid="functie-popup-definitie"]').exists()).toBe(false) // dv heeft geen definitie
    diagram.vm.selecteer('pr')
    await flushPromises()
    expect(w.find('[data-testid="functie-popup-definitie"]').text()).toBe('Kernactiviteiten.')
    // Vervallen functie: de bouwsteen-popup draagt de ⚠-markering (eigen kanaal).
    diagram.vm.selecteer('rs')
    await flushPromises()
    expect(w.find('[data-testid="diagram-popup-vervallen"]').text()).toContain('vervallen in het referentiemodel')
    // Uitgangen: "Toon hele functieboom" + "Open functie →" (géén kaart-uitgang).
    expect(w.find('[data-testid="diagram-popup-landschap"]').text()).toContain('Toon hele functieboom')
    expect(w.find('[data-testid="diagram-popup-kaart"]').exists()).toBe(false)
    const open = w.find('[data-testid="diagram-popup-open"]')
    expect(open.text()).toBe('Open functie →')
    await open.trigger('click')
    await flushPromises()
    // Landing: terug in de Boom, pad open (Besturend), rij aangestipt en in beeld.
    expect(w.find('[data-testid="functies-boom"]').exists()).toBe(true)
    expect(w.find('[data-testid="functie-rij-rs"]').exists()).toBe(true)
    expect(w.find('[data-testid="functie-rij-rs"]').attributes('class')).toContain('lk-aangestipt')
  })

  it('"Toon in functiebeeld" opent het Diagram met die functie als centrum', async () => {
    const w = await mountLijst()
    await w.find('[data-testid="functie-diagram-pr"]').trigger('click')
    await flushPromises()
    expect(w.find('[data-testid="functie-diagram"]').exists()).toBe(true)
    expect(w.findComponent(ProcesDiagram).props('initieelCentrumId')).toBe('pr')
  })

  it('blok B — aanmaak met actieve zoekterm: zoekterm wijkt ZICHTBAAR, rij aangestipt in beeld', async () => {
    api.bedrijfsfuncties.maak.mockResolvedValue({ id: 'n1' })
    const w = await mountLijst()
    await w.find('[data-testid="filter-zoek"]').setValue('klant')
    // De herlaad ná aanmaken levert de boom mét de nieuwe (niet-matchende) wortel.
    api.bedrijfsfuncties.lijst.mockResolvedValue({ items: [..._boom(), _f('n1', 'Zorgadministratie')], volgende_cursor: null })
    await w.find('[data-testid="nieuwe-functie"]').trigger('click')
    await w.find('[data-testid="functie-form-naam"]').setValue('Zorgadministratie')
    await w.find('[data-testid="functie-dialog"] form').trigger('submit')
    await flushPromises()
    // Zoekterm week — nooit stil: leesbare mededeling + de rij is zichtbaar én aangestipt.
    expect(w.find('[data-testid="filter-zoek"]').element.value).toBe('')
    expect(w.find('[data-testid="functie-wijk-melding"]').text()).toContain('Zoekterm opzij gezet')
    const rij = w.find('[data-testid="functie-rij-n1"]')
    expect(rij.exists()).toBe(true)
    expect(rij.attributes('class')).toContain('lk-aangestipt')
    // De melding hoort bij de geweken term en verdwijnt zodra de gebruiker weer typt.
    await w.find('[data-testid="filter-zoek"]').setValue('x')
    expect(w.find('[data-testid="functie-wijk-melding"]').exists()).toBe(false)
  })

  it('blok B — "+ Deelfunctie" onder een DICHTE ouder: het pad klapt open en de rij is zichtbaar', async () => {
    api.bedrijfsfuncties.maak.mockResolvedValue({ id: 'n2' })
    const w = await mountLijst()
    // Primair is dicht; de herlaad levert het nieuwe kind onder Primair.
    api.bedrijfsfuncties.lijst.mockResolvedValue({ items: [..._boom(), _f('n2', 'Subsidieverlening', 'pr')], volgende_cursor: null })
    await w.find('[data-testid="functie-deelfunctie-pr"]').trigger('click')
    await w.find('[data-testid="functie-form-naam"]').setValue('Subsidieverlening')
    await w.find('[data-testid="functie-dialog"] form').trigger('submit')
    await flushPromises()
    expect(w.find('[data-testid="functie-toggle-pr"]').attributes('aria-expanded')).toBe('true')
    expect(w.find('[data-testid="functie-rij-n2"]').exists()).toBe(true)
    expect(w.find('[data-testid="functie-rij-n2"]').attributes('class')).toContain('lk-aangestipt')
  })

  it('verplaats-doelen: vervallen functies en de eigen subboom zijn geen doel (picker spiegelt de backend)', async () => {
    const w = await mountLijst()
    await w.find('[data-testid="functie-toggle-pr"]').trigger('click')
    await w.find('[data-testid="functie-toggle-dv"]').trigger('click')
    await w.find('[data-testid="functie-verplaats-ddw"]').trigger('click')
    await flushPromises()
    const zs = w.findAllComponents({ name: 'ZoekSelect' }).find((c) => c.props('testid') === 'functie-verplaats-doel')
    const { items } = await zs.props('zoekFunctie')({})
    const ids = items.map((x) => x.id)
    expect(ids).not.toContain('rs') // vervallen — VERVALLEN_NIET_KOPPELBAAR vóóraf geweerd
    expect(ids).not.toContain('ddw') // zichzelf (subboom) — kring-preventie vóóraf
    expect(ids).toContain('bs')
  })
})
