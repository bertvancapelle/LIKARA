/** Tests — BedrijfsfunctieLijst (functieboom, ADR-043 gate 1a blok 2 + ADR-044 blok 2).
 *
 * Kern-gedrag (ADR-044 — plaatsingen, meervoudige plekken):
 * - een functie VERSCHIJNT op elke plek waar ze hoort (één rij per plaatsing/pad);
 * - "staat ook onder: …" op elke verschijning, klikbaar naar de andere plek;
 * - selectie/aanstip is FUNCTIE-breed (alle verschijningen lichten samen op);
 * - de uitklap-staat is PLEK-gebonden (openklappen hier laat de andere plek dicht);
 * - "Plaats ook onder…" / "Haal hier weg" via de plaatsings-endpoints; de laatste
 *   plaatsing weghalen maakt de functie een wortel (de zin zegt dat vooraf);
 * - modelinhoud kent GEEN plaatsings-affordances (422 MODELINHOUD_BESCHERMD vóóraf
 *   geweerd — LI032 picker-regel 1), en verder geen bewerk-/verwijder-knop;
 * - vervallen functies: rustige markering, geen "+ Deelfunctie".
 * Rij-testids zijn plek-gebonden (`functie-rij-<pad>` met '>' als scheider); voor een
 * wortel is de plek gelijk aan het functie-id.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'

vi.mock('@/api', () => ({
  api: {
    bedrijfsfuncties: {
      lijst: vi.fn(), maak: vi.fn(), werkBij: vi.fn(), verwijder: vi.fn(),
      plaats: vi.fn(), verwijderPlaatsing: vi.fn(),
    },
    // Gate 1b — referentiemodel inlezen (voorbeeld vóór bevestigen).
    referentiemodellen: { overzicht: vi.fn(), voorbeeld: vi.fn(), inlezen: vi.fn() },
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

// ADR-044 — rijen dragen `ouder_ids` (alle plaatsingen; leeg = wortel).
const _f = (id, naam, ouder_ids = [], extra = {}) => ({
  id, naam, ouder_ids,
  definitie: null, bron_model_id: null, bron_sleutel: null,
  bron_model_naam: null, bron_model_versie: null, vervallen: false,
  created_at: '2026-07-12T10:00:00Z', updated_at: '2026-07-12T10:00:00Z',
  ...extra,
})

// Geseede boom (ADR-044-vorm) mét het meervoud-geval:
//   Primair (model) → Dienstverlening → { Datagedreven werken (EIGEN), Klantcontact,
//                                          Toezicht (model, óók onder Besturend) → Handhaving }
//   Besturend (model) → { Regionale samenwerking (model, VERVALLEN), Toezicht (zelfde functie) }
const _MODEL = { bron_model_id: 'rm1', bron_sleutel: 'x', bron_model_naam: 'GEMMA Bedrijfsfuncties', bron_model_versie: 'release 1 juli 2026' }
const _boom = () => [
  _f('pr', 'Primair', [], { ..._MODEL, bron_sleutel: 'primair', definitie: 'Kernactiviteiten.' }),
  _f('dv', 'Dienstverlening', ['pr'], { ..._MODEL, bron_sleutel: 'dienstverlening' }),
  _f('kc', 'Klantcontact', ['dv'], { ..._MODEL, bron_sleutel: 'klantcontact' }),
  _f('bs', 'Besturend', [], { ..._MODEL, bron_sleutel: 'besturend' }),
  _f('rs', 'Regionale samenwerking', ['bs'], { ..._MODEL, bron_sleutel: 'regionale_samenwerking', vervallen: true }),
  // HET MEERVOUD-GEVAL — één functie, twee plekken (gelijkwaardig, geen kopie).
  _f('tz', 'Toezicht', ['dv', 'bs'], { ..._MODEL, bron_sleutel: 'toezicht' }),
  _f('hh', 'Handhaving', ['tz'], { ..._MODEL, bron_sleutel: 'handhaving' }),
  _f('ddw', 'Datagedreven werken', ['dv'], { definitie: 'Eigen functie van de gemeente.' }),
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
  // Het scherm haalt bij mount de model-status op (onvoltooid-signaal, best-effort).
  api.referentiemodellen.overzicht.mockResolvedValue([])
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

describe('BedrijfsfunctieLijst — ADR-044 meervoudige plekken', () => {
  // Beide ouders van Toezicht openklappen (dv-pad + bs-wortel).
  async function openBeidePlekken(w) {
    await w.find('[data-testid="functie-toggle-pr"]').trigger('click')
    await w.find('[data-testid="functie-toggle-pr>dv"]').trigger('click')
    await w.find('[data-testid="functie-toggle-bs"]').trigger('click')
  }

  it('een functie met twee plaatsingen verschijnt op BEIDE plekken — als dezelfde functie', async () => {
    const w = await mountLijst()
    await openBeidePlekken(w)
    expect(w.find('[data-testid="functie-rij-pr>dv>tz"]').exists()).toBe(true)
    expect(w.find('[data-testid="functie-rij-bs>tz"]').exists()).toBe(true)
    // Beide verschijningen vertellen dat ze óók elders staan (geen kopie-illusie).
    expect(w.find('[data-testid="functie-ookonder-pr>dv>tz"]').text()).toContain('Besturend')
    expect(w.find('[data-testid="functie-ookonder-bs>tz"]').text()).toContain('Dienstverlening')
    // Een functie met één plek draagt de regel niet (alleen wat afwijkt staat op de rij).
    expect(w.find('[data-testid="functie-ookonder-pr>dv>kc"]').exists()).toBe(false)
  })

  it('"staat ook onder"-klik toont de andere verschijning; de aanstip licht ALLE plekken op (functie-breed)', async () => {
    const w = await mountLijst()
    await w.find('[data-testid="functie-toggle-pr"]').trigger('click')
    await w.find('[data-testid="functie-toggle-pr>dv"]').trigger('click')
    // Besturend is nog dicht; de andere verschijning is dus niet zichtbaar.
    expect(w.find('[data-testid="functie-rij-bs>tz"]').exists()).toBe(false)
    await w.find('[data-testid="functie-ookonder-link-pr>dv>tz--bs"]').trigger('click')
    await flushPromises()
    // Pad opengeklapt → de andere plek is er, en BEIDE verschijningen zijn aangestipt.
    expect(w.find('[data-testid="functie-rij-bs>tz"]').exists()).toBe(true)
    expect(w.find('[data-testid="functie-rij-bs>tz"]').attributes('class')).toContain('lk-aangestipt')
    expect(w.find('[data-testid="functie-rij-pr>dv>tz"]').attributes('class')).toContain('lk-aangestipt')
  })

  it('uitklappen is PLEK-gebonden: Toezicht open onder de ene ouder laat de andere plek dicht', async () => {
    const w = await mountLijst()
    await openBeidePlekken(w)
    await w.find('[data-testid="functie-toggle-pr>dv>tz"]').trigger('click')
    // Handhaving verschijnt alléén onder het geopende pad.
    expect(w.find('[data-testid="functie-rij-pr>dv>tz>hh"]').exists()).toBe(true)
    expect(w.find('[data-testid="functie-rij-bs>tz>hh"]').exists()).toBe(false)
    expect(w.find('[data-testid="functie-toggle-bs>tz"]').attributes('aria-expanded')).toBe('false')
  })

  it('modelinhoud kent GEEN plaatsings-affordances (plekken komen uit de bron)', async () => {
    const w = await mountLijst({ rollen: ['beheerder'] })
    await openBeidePlekken(w)
    expect(w.find('[data-testid="functie-plaats-pr>dv>tz"]').exists()).toBe(false)
    expect(w.find('[data-testid="functie-haalweg-pr>dv>tz"]').exists()).toBe(false)
    expect(w.find('[data-testid="functie-plaats-pr"]').exists()).toBe(false)
  })

  it('"Plaats ook onder…": doelen spiegelen de backend; plaatsen roept het plaatsings-endpoint en toont de nieuwe plek', async () => {
    api.bedrijfsfuncties.plaats.mockResolvedValue(
      _f('ddw', 'Datagedreven werken', ['bs', 'dv'], { definitie: 'Eigen functie van de gemeente.' }),
    )
    const w = await mountLijst()
    await w.find('[data-testid="functie-toggle-pr"]').trigger('click')
    await w.find('[data-testid="functie-toggle-pr>dv"]').trigger('click')
    await w.find('[data-testid="functie-plaats-pr>dv>ddw"]').trigger('click')
    await flushPromises()
    // Picker-scope spiegelt de backend: geen huidige ouder (PLAATSING_BESTAAT), geen
    // zichzelf/subboom (kring), geen vervallen functie (VERVALLEN_NIET_KOPPELBAAR).
    const zs = w.findAllComponents({ name: 'ZoekSelect' }).find((c) => c.props('testid') === 'functie-plaats-doel')
    const { items } = await zs.props('zoekFunctie')({})
    const ids = items.map((x) => x.id)
    expect(ids).not.toContain('dv') // al een ouder
    expect(ids).not.toContain('ddw') // zichzelf
    expect(ids).not.toContain('rs') // vervallen
    expect(ids).toContain('bs')
    // Kiezen + bevestigen → POST /plaatsingen; de zin zegt "één en dezelfde functie".
    zs.vm.$emit('keuze', items.find((x) => x.id === 'bs'))
    await flushPromises()
    expect(w.find('[data-testid="functie-plaats-zin"]').text()).toContain('één en dezelfde functie')
    await w.find('[data-testid="functie-plaats-bevestig"]').trigger('click')
    await flushPromises()
    expect(api.bedrijfsfuncties.plaats).toHaveBeenCalledWith('ddw', { ouder_id: 'bs' })
    expect(toastSucces).toHaveBeenCalledWith(expect.anything(), 'Geplaatst')
    // De nieuwe verschijning is zichtbaar gemaakt (pad open) en de rij vertelt het meervoud.
    expect(w.find('[data-testid="functie-rij-bs>ddw"]').exists()).toBe(true)
    expect(w.find('[data-testid="functie-ookonder-pr>dv>ddw"]').text()).toContain('Besturend')
  })

  it('"Haal hier weg" (laatste plaatsing): de zin kondigt de wortel-landing aan; DELETE op de plaatsing', async () => {
    api.bedrijfsfuncties.verwijderPlaatsing.mockResolvedValue(
      _f('ddw', 'Datagedreven werken', [], { definitie: 'Eigen functie van de gemeente.' }),
    )
    const w = await mountLijst()
    await w.find('[data-testid="functie-toggle-pr"]').trigger('click')
    await w.find('[data-testid="functie-toggle-pr>dv"]').trigger('click')
    await w.find('[data-testid="functie-haalweg-pr>dv>ddw"]').trigger('click')
    // De regel leesbaar + het gevolg vooraf (geen verrassing: functie blijft, wordt wortel).
    const zin = w.find('[data-testid="functie-haalweg-zin"]').text()
    expect(zin).toContain('Datagedreven werken')
    expect(zin).toContain('Dienstverlening')
    expect(zin).toContain('hoogste niveau')
    await w.find('[data-testid="functie-haalweg-bevestig"]').trigger('click')
    await flushPromises()
    expect(api.bedrijfsfuncties.verwijderPlaatsing).toHaveBeenCalledWith('ddw', 'dv')
    expect(toastSucces).toHaveBeenCalledWith(expect.anything(), 'Hier weggehaald')
    // Zonder plaatsingen is de functie een wortel (plek = functie-id).
    expect(w.find('[data-testid="functie-rij-ddw"]').exists()).toBe(true)
  })

  it('"Haal hier weg" bij MEERDERE plekken: de zin benoemt waar de functie blijft staan', async () => {
    // Eigen functie met twee plekken (het gevolg-verschil met de wortel-variant).
    api.bedrijfsfuncties.lijst.mockResolvedValue({
      items: [..._boom(), _f('ee', 'Eigen dubbel', ['pr', 'bs'], {})], volgende_cursor: null,
    })
    const w = await mountLijst()
    await w.find('[data-testid="functie-toggle-pr"]').trigger('click')
    await w.find('[data-testid="functie-haalweg-pr>ee"]').trigger('click')
    const zin = w.find('[data-testid="functie-haalweg-zin"]').text()
    expect(zin).toContain('blijft ook staan onder: Besturend')
    expect(zin).not.toContain('hoogste niveau')
  })
})

describe('BedrijfsfunctieLijst — modelinhoud vs. eigen (affordance spiegelt de backend)', () => {
  it('model-functie: herkomst ÉÉN keer boven de boom (uit de data), niet per rij; geen bewerk-affordance', async () => {
    const w = await mountLijst({ rollen: ['beheerder'] })
    expect(w.find('[data-testid="functie-model-herkomst"]').text())
      .toBe('Uit GEMMA Bedrijfsfuncties, release 1 juli 2026. Eigen functies zijn gemarkeerd.')
    expect(w.find('[data-testid="functie-herkomst-pr"]').exists()).toBe(false)
    expect(w.find('[data-testid="functie-bewerk-pr"]').exists()).toBe(false)
    expect(w.find('[data-testid="functie-verwijder-pr"]').exists()).toBe(false)
    expect(w.find('[data-testid="functie-deelfunctie-pr"]').exists()).toBe(true)
  })

  it('eigen functie: "eigen"-badge + bewerk-/plaatsings-knoppen (medewerker); verwijderen alléén beheerder', async () => {
    const w = await mountLijst({ rollen: ['medewerker'] })
    await w.find('[data-testid="functie-toggle-pr"]').trigger('click')
    await w.find('[data-testid="functie-toggle-pr>dv"]').trigger('click')
    expect(w.find('[data-testid="functie-eigen-pr>dv>ddw"]').exists()).toBe(true)
    expect(w.find('[data-testid="functie-bewerk-pr>dv>ddw"]').exists()).toBe(true)
    expect(w.find('[data-testid="functie-plaats-pr>dv>ddw"]').exists()).toBe(true)
    expect(w.find('[data-testid="functie-haalweg-pr>dv>ddw"]').exists()).toBe(true)
    expect(w.find('[data-testid="functie-verwijder-pr>dv>ddw"]').exists()).toBe(false) // LI037-regel
    const w2 = await mountLijst({ rollen: ['beheerder'] })
    await w2.find('[data-testid="functie-toggle-pr"]').trigger('click')
    await w2.find('[data-testid="functie-toggle-pr>dv"]').trigger('click')
    expect(w2.find('[data-testid="functie-verwijder-pr>dv>ddw"]').exists()).toBe(true)
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
    const badge = w.find('[data-testid="functie-vervallen-bs>rs"]')
    expect(badge.text()).toContain('vervallen in het referentiemodel') // tekst
    expect(badge.text()).toContain('⚠') // icoon
    expect(badge.attributes('class')).toContain('--lk-color-warning') // warning-taal…
    expect(badge.attributes('class')).not.toContain('border-dashed') // …niet de gap-taal
    // De hele rij draagt de rustige waarschuwingstint (LI039 blok C).
    expect(w.find('[data-testid="functie-rij-bs>rs"]').attributes('class')).toContain('--lk-color-warning')
    expect(w.find('[data-testid="functie-deelfunctie-bs>rs"]').exists()).toBe(false)
    expect(w.find('[data-testid="functie-bewerk-bs>rs"]').exists()).toBe(false)
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
    await w.find('[data-testid="functie-toggle-pr>dv"]').trigger('click')
    expect(w.find('[data-testid="functie-eigen-pr>dv>ddw"]').attributes('class')).not.toContain('--lk-color-accent')
  })

  it('UI-afronding v2 — drievorm + tweelaags rij: scan-laag (naam + afwijking) en lees-laag (volledige definitie)', async () => {
    const w = await mountLijst({ rollen: ['beheerder'] })
    // Punt 1 (v1, blijft) — doorklik (navigatie) vs. mutatie: de vorm vertelt het verschil.
    const doorklik = w.findComponent('[data-testid="functie-diagram-pr"]')
    expect(doorklik.props('text')).toBe(true)
    expect(doorklik.props('label')).toContain('→')
    expect(w.findComponent('[data-testid="functie-deelfunctie-pr"]').props('outlined')).toBe(true)
    await w.find('[data-testid="functie-toggle-pr"]').trigger('click')
    await w.find('[data-testid="functie-toggle-pr>dv"]').trigger('click')
    expect(w.findComponent('[data-testid="functie-bewerk-pr>dv>ddw"]').props('outlined')).toBe(true)
    expect(w.findComponent('[data-testid="functie-plaats-pr>dv>ddw"]').props('outlined')).toBe(true)
    // Destructief draagt danger (LI037): de functie-verwijdering én het weghalen van
    // een plaatsing (dat verwijdert een registratie-feit).
    expect(w.findComponent('[data-testid="functie-haalweg-pr>dv>ddw"]').props('severity')).toBe('danger')
    expect(w.findComponent('[data-testid="functie-verwijder-pr>dv>ddw"]').props('severity')).toBe('danger')
    // Punt 1 (v2) — tweelaags: naam in de scan-laag, de VOLLEDIGE definitie in de lees-laag.
    const rij = w.find('[data-testid="functie-rij-pr"]')
    expect(rij.find('.lk-rij-kop [data-testid="functie-naam"]').exists()).toBe(true)
    const definitie = rij.find('[data-testid="functie-definitie-pr"]')
    expect(definitie.text()).toBe('Kernactiviteiten.') // volledige tekst in de DOM
    expect(definitie.attributes('class')).toContain('lk-rij-definitie')
    expect(definitie.attributes('class')).not.toContain('truncate')
    // Punt 2 (v2) — gereserveerde actiekolom: álle zes beheerder-acties op een eigen
    // functie-met-ouder staan bínnen de RijActies-container (nooit een knop buiten beeld).
    const eigenRij = w.find('[data-testid="functie-rij-pr>dv>ddw"]')
    expect(eigenRij.findAll('.lk-rij-acties button').length).toBe(6)
    // De vervallen-badge hoort bij de naam (scan-laag).
    await w.find('[data-testid="functie-toggle-bs"]').trigger('click')
    const vervallenRij = w.find('[data-testid="functie-rij-bs>rs"]')
    expect(vervallenRij.find('.lk-rij-kop [data-testid="functie-vervallen-bs>rs"]').exists()).toBe(true)
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

  it('bewerken van een eigen functie stuurt naam + definitie (GEEN plaatsings-velden)', async () => {
    api.bedrijfsfuncties.werkBij.mockResolvedValue({ id: 'ddw' })
    const w = await mountLijst()
    await w.find('[data-testid="functie-toggle-pr"]').trigger('click')
    await w.find('[data-testid="functie-toggle-pr>dv"]').trigger('click')
    await w.find('[data-testid="functie-bewerk-pr>dv>ddw"]').trigger('click')
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
    await w.find('[data-testid="functie-toggle-pr>dv"]').trigger('click')
    await w.find('[data-testid="functie-verwijder-pr>dv>ddw"]').trigger('click')
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
    const w = mount(ProcesDiagram, {
      props: {
        items: [_f('x1', 'Solo', [], { definitie: 'Definitie van Solo.' })],
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
    // ADR-044 — een functie op twee plekken: de popup benoemt het meervoud expliciet.
    diagram.vm.selecteer('tz')
    await flushPromises()
    const plek = w.find('[data-testid="diagram-popup-plek"]').text()
    expect(plek).toContain('staat onder')
    expect(plek).toContain('Dienstverlening')
    expect(plek).toContain('Besturend')
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
    expect(w.find('[data-testid="functie-rij-bs>rs"]').exists()).toBe(true)
    expect(w.find('[data-testid="functie-rij-bs>rs"]').attributes('class')).toContain('lk-aangestipt')
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
    api.bedrijfsfuncties.lijst.mockResolvedValue({ items: [..._boom(), _f('n2', 'Subsidieverlening', ['pr'])], volgende_cursor: null })
    await w.find('[data-testid="functie-deelfunctie-pr"]').trigger('click')
    await w.find('[data-testid="functie-form-naam"]').setValue('Subsidieverlening')
    await w.find('[data-testid="functie-dialog"] form').trigger('submit')
    await flushPromises()
    expect(w.find('[data-testid="functie-toggle-pr"]').attributes('aria-expanded')).toBe('true')
    expect(w.find('[data-testid="functie-rij-pr>n2"]').exists()).toBe(true)
    expect(w.find('[data-testid="functie-rij-pr>n2"]').attributes('class')).toContain('lk-aangestipt')
  })
})

// ── Gate 1b — referentiemodel inlezen: voorbeeld vóór bevestigen ─────────────────

const _AANBOD = (extra = {}) => [{
  model_sleutel: 'gemma_bedrijfsfuncties',
  label: 'GEMMA Bedrijfsfuncties',
  herkomst: 'VNG-Realisatie/GEMMA-Archi-repository — licentie EUPL',
  versie: 'release 1 juli 2026',
  beschikbaar: true,
  ingelezen: null,
  aantal_functies: 0,
  aantal_vervallen: 0,
  ...extra,
}]

const _PLAN = (extra = {}) => ({
  nieuw: Array.from({ length: 297 }, (_, i) => `Functie ${i + 1}`),
  bijgewerkt: [],
  vervallen: [],
  ongewijzigd: 0,
  plaatsingen_totaal: 302,
  plaatsingen_nieuw: 302,
  plaatsingen_vervallen: 0,
  overgeslagen: { BusinessObject: 507 },
  overgeslagen_totaal: 2455,
  ...extra,
})

describe('BedrijfsfunctieLijst — gate 1b: referentiemodel inlezen', () => {
  it('de inlees-affordance is beheerder-only (medewerker ziet geen knop)', async () => {
    const w1 = await mountLijst({ rollen: ['medewerker'] })
    expect(w1.find('[data-testid="model-inlezen"]').exists()).toBe(false)
    const w2 = await mountLijst({ rollen: ['beheerder'] })
    expect(w2.find('[data-testid="model-inlezen"]').exists()).toBe(true)
  })

  it('eerste inlees: openen → voorbeeld (dry-run, gebruikerstaal) → pas ná bevestigen landt het + boom herlaadt', async () => {
    api.referentiemodellen.overzicht.mockResolvedValue(_AANBOD())
    api.referentiemodellen.voorbeeld.mockResolvedValue(_PLAN())
    api.referentiemodellen.inlezen.mockResolvedValue({
      ..._PLAN(), model: { model_sleutel: 'gemma_bedrijfsfuncties', naam: 'GEMMA Bedrijfsfuncties', versie: 'release 1 juli 2026' },
    })
    const w = await mountLijst({ rollen: ['beheerder'] })
    const lijstCallsVoor = api.bedrijfsfuncties.lijst.mock.calls.length

    await w.find('[data-testid="model-inlezen"]').trigger('click')
    await flushPromises()
    // Eén model in het aanbod → direct het voorbeeld (dry-run) — niets geschreven.
    expect(api.referentiemodellen.voorbeeld).toHaveBeenCalledWith('gemma_bedrijfsfuncties')
    expect(api.referentiemodellen.inlezen).not.toHaveBeenCalled()
    const voorbeeld = w.find('[data-testid="inlees-voorbeeld"]').text()
    expect(voorbeeld).toContain('297 functies worden toegevoegd')
    expect(voorbeeld).toContain('302 plaatsingen')
    expect(voorbeeld).toContain('2455 elementen van andere typen worden overgeslagen')

    await w.find('[data-testid="inlees-bevestig"]').trigger('click')
    await flushPromises()
    expect(api.referentiemodellen.inlezen).toHaveBeenCalledWith('gemma_bedrijfsfuncties')
    expect(toastSucces).toHaveBeenCalledWith(expect.anything(), 'Ingelezen')
    // De boom herlaadt (de gebruiker ziet direct de nieuwe stand) + resultaat-staat.
    expect(api.bedrijfsfuncties.lijst.mock.calls.length).toBeGreaterThan(lijstCallsVoor)
    expect(w.find('[data-testid="inlees-resultaat"]').text()).toContain('GEMMA Bedrijfsfuncties')
  })

  it('herinlees: voorbeeld toont nieuw · bijgewerkt · vervallen — mét de vervallen functies bij naam (de werklijst)', async () => {
    api.referentiemodellen.overzicht.mockResolvedValue(
      _AANBOD({ ingelezen: { id: 'rm1', naam: 'GEMMA Bedrijfsfuncties', versie: 'v1', ingelezen_op: '2026-07-13T09:00:00Z' } }),
    )
    api.referentiemodellen.voorbeeld.mockResolvedValue(_PLAN({
      nieuw: ['A', 'B', 'C', 'D'],
      bijgewerkt: Array.from({ length: 12 }, (_, i) => `B${i}`),
      vervallen: [
        { naam: 'Regionale samenwerking', in_gebruik: true },
        { naam: 'Oude functie', in_gebruik: false },
        { naam: 'Derde functie', in_gebruik: false },
      ],
      ongewijzigd: 280,
      overgeslagen_totaal: 0,
      overgeslagen: {},
    }))
    const w = await mountLijst({ rollen: ['beheerder'] })
    await w.find('[data-testid="model-inlezen"]').trigger('click')
    await flushPromises()
    expect(w.find('[data-testid="inlees-eerder"]').exists()).toBe(true) // herinlees benoemd
    expect(w.find('[data-testid="inlees-voorbeeld"]').text()).toContain('4 nieuw · 12 bijgewerkt · 3 vervallen — waarvan 1 nog in gebruik')
    const lijst = w.find('[data-testid="inlees-vervallen-lijst"]').text()
    expect(lijst).toContain('Regionale samenwerking')
    expect(lijst).toContain('nog in gebruik')
  })

  it('geen wijzigingen: de bevestig-knop is uitgeschakeld ("al actueel")', async () => {
    api.referentiemodellen.overzicht.mockResolvedValue(_AANBOD())
    api.referentiemodellen.voorbeeld.mockResolvedValue(_PLAN({
      nieuw: [], plaatsingen_nieuw: 0, ongewijzigd: 297, overgeslagen: {}, overgeslagen_totaal: 0,
    }))
    const w = await mountLijst({ rollen: ['beheerder'] })
    await w.find('[data-testid="model-inlezen"]').trigger('click')
    await flushPromises()
    expect(w.find('[data-testid="inlees-voorbeeld"]').text()).toContain('al actueel')
    expect(w.find('[data-testid="inlees-bevestig"]').attributes('disabled')).toBeDefined()
  })

  it('lege staat: de beheerder krijgt de inlees-route; een medewerker een verwijzing (geen dode knop)', async () => {
    api.bedrijfsfuncties.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
    const w1 = await mountLijst({ rollen: ['beheerder'] })
    expect(w1.find('[data-testid="lijst-leeg-inlezen"]').exists()).toBe(true)
    const w2 = await mountLijst({ rollen: ['medewerker'] })
    expect(w2.find('[data-testid="lijst-leeg-inlezen"]').exists()).toBe(false)
    expect(w2.find('[data-testid="lijst-leeg"]').text()).toContain('beheerder')
  })
})

// ── B2 (browsercheck-bevinding) — een lege uitkomst is geen fout ─────────────────

describe('BedrijfsfunctieLijst — B2: aanbod-staten sluiten elkaar uit', () => {
  it('leeg aanbod (200, lege lijst) → rustige lege staat, GÉÉN foutmelding', async () => {
    api.referentiemodellen.overzicht.mockResolvedValue([])
    const w = await mountLijst({ rollen: ['beheerder'] })
    await w.find('[data-testid="model-inlezen"]').trigger('click')
    await flushPromises()
    expect(w.find('[data-testid="inlees-geen-aanbod"]').text()).toContain('nog geen referentiemodellen beschikbaar')
    expect(w.find('[data-testid="inlees-geen-aanbod"]').text()).toContain('platformbeheerder') // route naar de actie
    expect(w.find('[data-testid="inlees-fout"]').exists()).toBe(false) // geen alarmrood
    expect(w.find('[data-testid="inlees-sluiten"]').exists()).toBe(true)
  })

  it('gefaalde aanroep → foutmelding, GÉÉN "geen model beschikbaar" — nooit beide', async () => {
    const w = await mountLijst({ rollen: ['beheerder'] })
    api.referentiemodellen.overzicht.mockRejectedValue({ status: 500, message: 'kapot' })
    await w.find('[data-testid="model-inlezen"]').trigger('click')
    await flushPromises()
    expect(w.find('[data-testid="inlees-fout"]').exists()).toBe(true)
    expect(w.find('[data-testid="inlees-geen-aanbod"]').exists()).toBe(false)
  })

  it('een niet-beschikbaar model (geen bestand in de release) telt niet als aanbod', async () => {
    api.referentiemodellen.overzicht.mockResolvedValue(_AANBOD({ beschikbaar: false }))
    const w = await mountLijst({ rollen: ['beheerder'] })
    await w.find('[data-testid="model-inlezen"]').trigger('click')
    await flushPromises()
    expect(w.find('[data-testid="inlees-geen-aanbod"]').exists()).toBe(true)
    expect(w.find('[data-testid="inlees-fout"]').exists()).toBe(false)
  })
})

// ── Gate 1b-afronding — onvoltooide inlees: nooit stil ───────────────────────────

const _ONVOLTOOID = { id: 'rm1', naam: 'GEMMA Bedrijfsfuncties', versie: 'release 1 juli 2026', ingelezen_op: '2026-07-13T09:00:00Z', inlees_voltooid: false }
const _VOLTOOID = { ..._ONVOLTOOID, inlees_voltooid: true }

describe('BedrijfsfunctieLijst — onvoltooide inlees', () => {
  it('afgebroken inlees → waarschuwing voor iedereen; alléén de beheerder krijgt de herstart-actie', async () => {
    api.referentiemodellen.overzicht.mockResolvedValue(_AANBOD({ ingelezen: _ONVOLTOOID }))
    const w1 = await mountLijst({ rollen: ['medewerker'] })
    expect(w1.find('[data-testid="functie-inlees-onvoltooid"]').text()).toContain('niet afgerond')
    expect(w1.find('[data-testid="onvoltooid-hervat"]').exists()).toBe(false) // signaal zonder actie
    const w2 = await mountLijst({ rollen: ['beheerder'] })
    expect(w2.find('[data-testid="functie-inlees-onvoltooid"]').exists()).toBe(true)
    expect(w2.find('[data-testid="onvoltooid-hervat"]').exists()).toBe(true)
  })

  it('voltooide inlees → géén vals signaal', async () => {
    api.referentiemodellen.overzicht.mockResolvedValue(_AANBOD({ ingelezen: _VOLTOOID }))
    const w = await mountLijst({ rollen: ['beheerder'] })
    expect(w.find('[data-testid="functie-inlees-onvoltooid"]').exists()).toBe(false)
  })

  it('hervatten: afronden mag óók zonder wijzigingen; na afloop verdwijnt het signaal', async () => {
    // mount + openen zien de onvoltooide stand; ná het inlezen is hij voltooid.
    api.referentiemodellen.overzicht
      .mockResolvedValueOnce(_AANBOD({ ingelezen: _ONVOLTOOID }))  // mount
      .mockResolvedValueOnce(_AANBOD({ ingelezen: _ONVOLTOOID }))  // openInlezen
      .mockResolvedValueOnce(_AANBOD({ ingelezen: _VOLTOOID }))    // na inlezen
    // Het kritieke randgeval: alles staat er al (plan leeg) — alleen de afronding ontbreekt.
    api.referentiemodellen.voorbeeld.mockResolvedValue(_PLAN({
      nieuw: [], plaatsingen_nieuw: 0, ongewijzigd: 297, overgeslagen: {}, overgeslagen_totaal: 0,
    }))
    api.referentiemodellen.inlezen.mockResolvedValue({
      ..._PLAN({ nieuw: [], ongewijzigd: 297 }),
      model: { model_sleutel: 'gemma_bedrijfsfuncties', naam: 'GEMMA Bedrijfsfuncties', versie: 'release 1 juli 2026' },
    })
    const w = await mountLijst({ rollen: ['beheerder'] })
    await w.find('[data-testid="onvoltooid-hervat"]').trigger('click')
    await flushPromises()
    // In de dialog: onvoltooid benoemd; de voorbeeldzin zegt "afronding ontbreekt";
    // bevestigen is NIET uitgeschakeld ondanks 0 wijzigingen.
    expect(w.find('[data-testid="inlees-onvoltooid-melding"]').exists()).toBe(true)
    expect(w.find('[data-testid="inlees-voorbeeld"]').text()).toContain('afronding van de vorige inlees ontbreekt')
    expect(w.find('[data-testid="inlees-bevestig"]').attributes('disabled')).toBeUndefined()
    await w.find('[data-testid="inlees-bevestig"]').trigger('click')
    await flushPromises()
    expect(api.referentiemodellen.inlezen).toHaveBeenCalledWith('gemma_bedrijfsfuncties')
    expect(w.find('[data-testid="functie-inlees-onvoltooid"]').exists()).toBe(false) // signaal weg
  })
})
