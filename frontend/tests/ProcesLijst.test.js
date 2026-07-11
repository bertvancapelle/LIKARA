/** Tests — ProcesLijst (procesregister-boom, ADR-042 slice 4a). */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'

vi.mock('@/api', () => ({
  api: {
    // LI037 tree-view — rollup + procesvervullingen voeden de "geen ondersteunend systeem"-cue
    // (zelfde leespaden als de kaart-gap-cue).
    processen: { lijst: vi.fn(), maak: vi.fn(), werkBij: vi.fn(), verwijder: vi.fn(), rollup: vi.fn() },
    procesvervullingen: { lijst: vi.fn() },
  },
}))

// LI035 succes-standaard — helper gemockt zodat de succes-flow assertbaar is.
vi.mock('@/meldingen', () => ({ toastSucces: vi.fn() }))

// LI038 gate 1 — de Diagram-weergave mount ProcesDiagram (cytoscape); gemockt volgens het
// kaart-testpatroon zodat de schakelaar-test de echte child kan mounten.
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
import ProcesLijst from '@modules/bwb_ontvlechting/frontend/views/ProcesLijst.vue'
import ZoekSelect from '@modules/bwb_ontvlechting/frontend/views/ZoekSelect.vue'

function maakRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/processen', name: 'proces-lijst', component: ProcesLijst },
      { path: '/processen/:id', name: 'proces-detail', component: { template: '<div/>' } },
    ],
  })
}

const _p = (id, naam, ouder_id = null, toelichting = null) => ({
  id, naam, ouder_id, toelichting,
  created_at: '2026-07-01T10:00:00Z', updated_at: '2026-07-01T10:00:00Z',
})

// Geseede boom (fase-0-vorm, 3 niveaus): Vergunningverlening → Aanvraag behandelen → Besluit
// vastleggen; Burgerzaken → Verhuizing verwerken.
const _boom = () => [
  _p('vv', 'Vergunningverlening'),
  _p('ab', 'Aanvraag behandelen', 'vv'),
  _p('bv', 'Besluit vastleggen', 'ab'),
  _p('bz', 'Burgerzaken'),
  _p('verh', 'Verhuizing verwerken', 'bz'),
]

async function mountLijst({ rollen = ['medewerker'] } = {}) {
  const router = maakRouter()
  await router.push('/processen')
  await router.isReady()
  const pinia = createPinia()
  const auth = useAuthStore(pinia)
  auth.user = { sub: 's', tenant_id: 't', email: 'a@b.nl', roles: rollen }
  const w = mount(ProcesLijst, { global: { plugins: [pinia, [PrimeVue, { unstyled: true }], ToastService, router], stubs: { teleport: true } } })
  await flushPromises()
  return w
}

beforeEach(() => {
  vi.clearAllMocks()
  sessionStorage.clear() // lijststaat (useLijstStaat) mag niet tussen tests lekken
  api.processen.lijst.mockResolvedValue({ items: _boom(), volgende_cursor: null })
  // Default: beide bomen volledig gedekt (geen gap-tags) — de gap-test overschrijft dit.
  api.processen.rollup.mockImplementation(async (w) =>
    (w === 'vv' ? [{ proces_id: 'ab' }, { proces_id: 'bv' }] : w === 'bz' ? [{ proces_id: 'verh' }] : []))
  api.procesvervullingen.lijst.mockResolvedValue([{ component_id: 'c1' }])
})
afterEach(() => vi.restoreAllMocks())

describe('ProcesLijst — boomweergave', () => {
  it('toont hoofdprocessen; deelprocessen pas na uitklappen', async () => {
    const w = await mountLijst()
    // Assert op de boom-container: de (i)-uitlegtekst noemt "Aanvraag behandelen" als voorbeeld.
    const boom = () => w.find('[data-testid="processen-boom"]').text()
    expect(boom()).toContain('Vergunningverlening')
    expect(boom()).toContain('Burgerzaken')
    expect(boom()).not.toContain('Aanvraag behandelen') // ingeklapt
    await w.find('[data-testid="proces-toggle-vv"]').trigger('click')
    expect(boom()).toContain('Aanvraag behandelen')
    expect(w.find('[data-testid="proces-toggle-vv"]').attributes('aria-expanded')).toBe('true')
  })

  it('haalt ALLE pagina\'s op voor de boom (keyset-lus)', async () => {
    api.processen.lijst
      .mockResolvedValueOnce({ items: [_p('vv', 'Vergunningverlening')], volgende_cursor: 'cur-1' })
      .mockResolvedValueOnce({ items: [_p('ab', 'Aanvraag behandelen', 'vv')], volgende_cursor: null })
    const w = await mountLijst()
    expect(api.processen.lijst).toHaveBeenCalledTimes(2)
    expect(api.processen.lijst).toHaveBeenLastCalledWith(expect.objectContaining({ after: 'cur-1' }))
    await w.find('[data-testid="proces-toggle-vv"]').trigger('click')
    expect(w.find('[data-testid="processen-boom"]').text()).toContain('Aanvraag behandelen')
  })

  it('zoeken filtert soepel (partieel, hoofdletter-ongevoelig) en klapt het pad naar de treffer open', async () => {
    const w = await mountLijst()
    await w.find('[data-testid="filter-zoek"]').setValue('  AANVRAAG ')
    const boom = w.find('[data-testid="processen-boom"]').text()
    expect(boom).toContain('Aanvraag behandelen') // treffer zichtbaar zonder handmatig uitklappen
    expect(boom).toContain('Vergunningverlening') // het pad ernaartoe blijft staan
    expect(boom).not.toContain('Burgerzaken') // niet-matchende tak verdwijnt
  })

  it('rij-link gaat naar de proces-detail-route', async () => {
    const w = await mountLijst()
    expect(w.find('[data-testid="proces-link"]').attributes('href')).toContain('/processen/')
  })

  it('nieuw top-level proces via de dialog → api.processen.maak zonder ouder', async () => {
    api.processen.maak.mockResolvedValue(_p('nieuw', 'Inkoop'))
    const w = await mountLijst()
    await w.find('[data-testid="nieuw-proces"]').trigger('click')
    await w.find('[data-testid="proces-naam"]').setValue('Inkoop')
    await w.find('[data-testid="proces-dialog-opslaan"]').trigger('submit')
    await flushPromises()
    expect(api.processen.maak).toHaveBeenCalledWith({ naam: 'Inkoop', toelichting: null })
    expect(toastSucces).toHaveBeenCalledWith(expect.anything(), 'Proces aangemaakt')
  })

  it('hernoemen opent voorgevuld en roept werkBij aan', async () => {
    api.processen.werkBij.mockResolvedValue(_p('vv', 'Vergunningen'))
    const w = await mountLijst()
    await w.find('[data-testid="proces-hernoem-vv"]').trigger('click')
    expect(w.find('[data-testid="proces-naam"]').element.value).toBe('Vergunningverlening')
    await w.find('[data-testid="proces-naam"]').setValue('Vergunningen')
    await w.find('[data-testid="proces-dialog-opslaan"]').trigger('submit')
    await flushPromises()
    expect(api.processen.werkBij).toHaveBeenCalledWith('vv', { naam: 'Vergunningen', toelichting: null })
    expect(toastSucces).toHaveBeenCalledWith(expect.anything(), 'Opgeslagen')
  })

  it('rol-gating: viewer ziet geen aanmaak-/hernoem-affordances', async () => {
    const w = await mountLijst({ rollen: ['viewer'] })
    expect(w.find('[data-testid="nieuw-proces"]').exists()).toBe(false)
    expect(w.find('[data-testid="proces-hernoem-vv"]').exists()).toBe(false)
    // LI037 gate 2 — verwijderen/verplaatsen zijn óók rol-gated.
    expect(w.find('[data-testid="proces-verwijder-vv"]').exists()).toBe(false)
    expect(w.find('[data-testid="proces-verplaats-vv"]').exists()).toBe(false)
  })

  it('LI037 rol-gating: medewerker mag aanmaken/hernoemen/verplaatsen maar NIET verwijderen (VERWIJDEREN = beheerder)', async () => {
    const w = await mountLijst({ rollen: ['medewerker'] })
    expect(w.find('[data-testid="nieuw-proces"]').exists()).toBe(true)
    expect(w.find('[data-testid="proces-hernoem-vv"]').exists()).toBe(true)
    expect(w.find('[data-testid="proces-verplaats-vv"]').exists()).toBe(true)
    expect(w.find('[data-testid="proces-verwijder-vv"]').exists()).toBe(false)
    const b = await mountLijst({ rollen: ['beheerder'] })
    expect(b.find('[data-testid="proces-verwijder-vv"]').exists()).toBe(true)
  })

  it('LI037 vorm: rij-acties zijn Buttons — Hernoemen/Verplaatsen secundair, Verwijderen danger', async () => {
    const w = await mountLijst({ rollen: ['beheerder'] })
    expect(w.findComponent('[data-testid="proces-hernoem-vv"]').props('severity')).toBe('secondary')
    expect(w.findComponent('[data-testid="proces-verplaats-vv"]').props('severity')).toBe('secondary')
    expect(w.findComponent('[data-testid="proces-verwijder-vv"]').props('severity')).toBe('danger')
  })

  // ── LI037 tree-view gate 2 — verwijderen + verhangen ──
  it('LI037-g2 (verwijderen) — bevestiging → endpoint; rij lokaal weg zonder herlaad-sprong', async () => {
    api.processen.verwijder.mockResolvedValue(null)
    const w = await mountLijst({ rollen: ['beheerder'] })
    await w.find('[data-testid="proces-toggle-bz"]').trigger('click')
    await w.find('[data-testid="proces-verwijder-verh"]').trigger('click')
    expect(w.find('[data-testid="proces-verwijder-omschrijving"]').text()).toContain('Verwijder "Verhuizing verwerken"?')
    await w.find('[data-testid="proces-verwijder-bevestig"]').trigger('click')
    await flushPromises()
    expect(api.processen.verwijder).toHaveBeenCalledWith('verh')
    expect(toastSucces).toHaveBeenCalledWith(expect.anything(), 'Verwijderd')
    expect(w.find('[data-testid="processen-boom"]').text()).not.toContain('Verhuizing verwerken')
    expect(api.processen.lijst).toHaveBeenCalledTimes(1) // lokaal bijgewerkt — geen herlaad
  })

  it('LI037-g2 (verwijderen, 409) — leesbare melding, boom onveranderd', async () => {
    api.processen.verwijder.mockRejectedValue({ status: 409, message: 'Dit proces heeft deelprocessen; verplaats of verwijder die eerst.' })
    const w = await mountLijst({ rollen: ['beheerder'] })
    await w.find('[data-testid="proces-verwijder-vv"]').trigger('click')
    await w.find('[data-testid="proces-verwijder-bevestig"]').trigger('click')
    await flushPromises()
    const fout = w.find('[data-testid="proces-verwijder-fout"]')
    expect(fout.exists()).toBe(true)
    expect(fout.text()).toContain('kan niet worden verwijderd omdat er nog onderliggende processen zijn')
    expect(w.find('[data-testid="processen-boom"]').text()).toContain('Vergunningverlening') // onveranderd
  })

  it('LI037-g2 (verhangen) — de picker sluit het proces zelf + zijn nazaten uit (kring-preventie vóóraf)', async () => {
    const w = await mountLijst()
    await w.find('[data-testid="proces-toggle-vv"]').trigger('click')
    await w.find('[data-testid="proces-verplaats-ab"]').trigger('click')
    const picker = w.findAllComponents(ZoekSelect).find((c) => c.props('testid') === 'proces-verplaats-doel')
    expect(picker).toBeTruthy()
    const r = await picker.props('zoekFunctie')({})
    const namen = r.items.map((x) => x.naam)
    expect(namen).not.toContain('Aanvraag behandelen') // zichzelf
    expect(namen).not.toContain('Besluit vastleggen') // nazaat → zou een kring maken
    expect(namen).toEqual(expect.arrayContaining(['Burgerzaken', 'Verhuizing verwerken', 'Vergunningverlening']))
    // Identiteitspatroon: treffer mét oudercontext.
    const verh = r.items.find((x) => x.id === 'verh')
    expect(picker.props('weergave')(verh)).toBe('Verhuizing verwerken — Burgerzaken')
  })

  it('LI037-g2 (verhangen mét kinderen) — bevestiging benoemt N; werkBij met het doel; nieuwe plek klapt open', async () => {
    api.processen.werkBij.mockResolvedValue(null)
    const w = await mountLijst()
    await w.find('[data-testid="proces-toggle-vv"]').trigger('click')
    await w.find('[data-testid="proces-verplaats-ab"]').trigger('click')
    const picker = w.findAllComponents(ZoekSelect).find((c) => c.props('testid') === 'proces-verplaats-doel')
    picker.vm.$emit('keuze', { id: 'bz', naam: 'Burgerzaken' })
    await flushPromises()
    // ab heeft 1 nazaat (bv) → de zin benoemt de meeverhuizende tak expliciet.
    expect(w.find('[data-testid="proces-verplaats-zin"]').text())
      .toBe('Verplaats "Aanvraag behandelen" en 1 onderliggend proces naar "Burgerzaken"?')
    await w.find('[data-testid="proces-verplaats-bevestig"]').trigger('click')
    await flushPromises()
    expect(api.processen.werkBij).toHaveBeenCalledWith('ab', { ouder_id: 'bz' })
    expect(toastSucces).toHaveBeenCalledWith(expect.anything(), 'Verplaatst')
    // De nieuwe plek is opengeklapt: ab staat nu zichtbaar onder Burgerzaken.
    expect(w.find('[data-testid="proces-rij-ab"]').exists()).toBe(true)
  })

  it('LI037-g2 (promoveren, zonder kinderen) — "Geen (maak hoofdproces)" → ouder_id null; korte zin', async () => {
    api.processen.werkBij.mockResolvedValue(null)
    const w = await mountLijst()
    await w.find('[data-testid="proces-toggle-vv"]').trigger('click')
    await w.find('[data-testid="proces-toggle-ab"]').trigger('click')
    await w.find('[data-testid="proces-verplaats-bv"]').trigger('click')
    await w.find('[data-testid="proces-verplaats-geen"]').trigger('click')
    const zin = w.find('[data-testid="proces-verplaats-zin"]').text()
    expect(zin).toBe('Verplaats "Besluit vastleggen" naar hoofdprocesniveau?')
    expect(zin).not.toContain('onderliggend')
    await w.find('[data-testid="proces-verplaats-bevestig"]').trigger('click')
    await flushPromises()
    expect(api.processen.werkBij).toHaveBeenCalledWith('bv', { ouder_id: null })
  })

  it('LI037-g2 (top-level) — "Geen (maak hoofdproces)" is uitgeschakeld voor een hoofdproces', async () => {
    const w = await mountLijst()
    await w.find('[data-testid="proces-verplaats-vv"]').trigger('click')
    const geen = w.find('[data-testid="proces-verplaats-geen"]')
    expect(geen.attributes('disabled')).toBeDefined()
    expect(geen.attributes('title')).toBe('Dit is al een hoofdproces')
    // Zonder keuze blijft Verplaatsen uit.
    expect(w.find('[data-testid="proces-verplaats-bevestig"]').attributes('disabled')).toBeDefined()
  })

  // ── LI037 tree-view gate 1 — verbindingslijnen + gap-cue ──
  it('LI037 (lijnen) — connectoren op elk niveau (3 diep), laatste kind sluit af, doorloop bij broers', async () => {
    // Extra broer onder vv → een dóórlopende guide-lijn op het diepere niveau.
    api.processen.lijst.mockResolvedValue({
      items: [..._boom(), _p('bez', 'Bezwaar behandelen', 'vv')],
      volgende_cursor: null,
    })
    const w = await mountLijst()
    await w.find('[data-testid="proces-toggle-vv"]').trigger('click')
    await w.find('[data-testid="proces-toggle-ab"]').trigger('click')
    // Wortels dragen géén elleboog; kinderen wél.
    expect(w.find('[data-testid="proces-lijn-vv"]').exists()).toBe(false)
    expect(w.find('[data-testid="proces-lijn-ab"]').exists()).toBe(true)
    expect(w.find('[data-testid="proces-lijn-bv"]').exists()).toBe(true)
    // "Aanvraag behandelen" is NIET het laatste kind (Bezwaar volgt) → de verticale lijn loopt
    // door (bottom-0); "Bezwaar behandelen" is het laatste kind → elleboog sluit af (bottom-1/2).
    expect(w.find('[data-testid="proces-lijn-ab"]').classes()).toContain('bottom-0')
    expect(w.find('[data-testid="proces-lijn-bez"]').classes()).toContain('bottom-1/2')
    // Gate 1c — laatste-kind-afsluiting (└): bez draagt ALLEEN elleboog + horizontale stub —
    // géén extra lijn onder de elleboog (dat was het T-stuk-defect).
    const bezLijnen = w.find('[data-testid="proces-rij-bez"]').findAll('[data-boomlijn]')
    expect(bezLijnen.length).toBe(2)
    // Niveau 3 (bv): doorlopende guide van het ab-broers-spoor + elleboog + horizontale stub = 3;
    // alle decoratief (aria-hidden).
    const bvLijnen = w.find('[data-testid="proces-rij-bv"]').findAll('[data-boomlijn]')
    expect(bvLijnen.length).toBe(3)
    expect(bvLijnen.every((s) => s.attributes('aria-hidden') === 'true')).toBe(true)
    // Gate 1c — naadloosheid: de doorloop-guide op bv's rij bestaat (de ab↔bez-lijn loopt hier
    // dóór — dat was het gat) en beslaat de VOLLE rijhoogte (inset-y-0). De exacte kolom-x is
    // een calc()-inline-stijl die happy-dom niet serialiseert → de pixel-uitlijning (guide op
    // kolom 0, elleboog op kolom 1) is een browsercheck-criterium (draaiboek stap 1–3).
    const bvGuide = bvLijnen.find((s) => s.classes().includes('inset-y-0'))
    expect(bvGuide).toBeTruthy()
    // Een opengeklapte ouder draagt de omlaag-stub naar zijn kinderen.
    const abLijnen = w.find('[data-testid="proces-rij-ab"]').findAll('[data-boomlijn]')
    expect(abLijnen.length).toBe(3) // elleboog + horizontale stub + omlaag-stub (open)
    // Gate 1c — bomen zijn onafhankelijk: een kind van de ándere wortel (Burgerzaken is niet de
    // laatste wortel) krijgt GEEN doorloop-guide van het wortel-niveau (wortels dragen geen kolom).
    await w.find('[data-testid="proces-toggle-bz"]').trigger('click')
    const verhLijnen = w.find('[data-testid="proces-rij-verh"]').findAll('[data-boomlijn]')
    expect(verhLijnen.length).toBe(2) // alleen elleboog + horizontale stub
    expect(w.find('[data-testid="proces-lijn-verh"]').classes()).toContain('bottom-1/2')
  })

  it('LI037 (gap-cue) — subboom-semantiek: dekking klimt naar de voorouders; ongedekte boom toont de tag', async () => {
    // Vergunningverlening-boom gedekt via het DIEPSTE proces (bv) — de klim dekt ab + vv mee;
    // de Burgerzaken-boom heeft niets → bz + verh dragen de cue.
    api.processen.rollup.mockImplementation(async (w) => (w === 'vv' ? [{ proces_id: 'bv' }] : []))
    api.procesvervullingen.lijst.mockResolvedValue([]) // geen wortel-eigen regels
    const w = await mountLijst()
    // Zelfde leespaden als de kaart: rollup + wortel-eigen regels, per wortel (geen N+1 per rij).
    expect(api.processen.rollup).toHaveBeenCalledWith('vv')
    expect(api.processen.rollup).toHaveBeenCalledWith('bz')
    expect(api.procesvervullingen.lijst).toHaveBeenCalledWith({ proces_id: 'vv' })
    expect(w.find('[data-testid="proces-gap-bz"]').exists()).toBe(true)
    expect(w.find('[data-testid="proces-gap-vv"]').exists()).toBe(false) // gedekt via de klim
    await w.find('[data-testid="proces-toggle-bz"]').trigger('click')
    expect(w.find('[data-testid="proces-gap-verh"]').exists()).toBe(true)
    await w.find('[data-testid="proces-toggle-vv"]').trigger('click')
    expect(w.find('[data-testid="proces-gap-ab"]').exists()).toBe(false)
    expect(w.find('[data-testid="proces-gap-bz"]').text()).toBe('geen ondersteunend systeem')
  })

  it('LI037 (zoeken + lijnen) — tijdens een actief filter kloppen de lijnen voor de zichtbare takken', async () => {
    const w = await mountLijst()
    await w.find('[data-testid="filter-zoek"]').setValue('besluit')
    const boom = w.find('[data-testid="processen-boom"]').text()
    expect(boom).toContain('Besluit vastleggen') // treffer, pad opengeklapt
    expect(boom).toContain('Aanvraag behandelen')
    expect(boom).not.toContain('Burgerzaken')
    // bv is het enige zichtbare kind van ab → laatste (elleboog sluit af); geen doorloop-guide
    // (ab is óók het laatste zichtbare kind van vv) → elleboog + stub = 2 lijn-elementen.
    expect(w.find('[data-testid="proces-lijn-bv"]').classes()).toContain('bottom-1/2')
    expect(w.find('[data-testid="proces-rij-bv"]').findAll('[data-boomlijn]').length).toBe(2)
  })
})

describe('ProcesLijst — LI038 gate 1: weergave-schakelaar Boom | Diagram', () => {
  it('opent default in de Boom; de schakelaar toont beide opties', async () => {
    const w = await mountLijst()
    expect(w.find('[data-testid="processen-boom"]').exists()).toBe(true)
    expect(w.find('[data-testid="proces-diagram"]').exists()).toBe(false)
    expect(w.find('[data-testid="weergave-boom"]').attributes('aria-pressed')).toBe('true')
    expect(w.find('[data-testid="weergave-diagram"]').attributes('aria-pressed')).toBe('false')
  })

  it('wisselt naar het Diagram (proces-only, leeg openen) en terug naar de Boom', async () => {
    const w = await mountLijst()
    await w.find('[data-testid="weergave-diagram"]').trigger('click')
    expect(w.find('[data-testid="proces-diagram"]').exists()).toBe(true)
    expect(w.find('[data-testid="processen-boom"]').exists()).toBe(false)
    expect(w.find('[data-testid="filterbalk"]').exists()).toBe(false) // boom-zoek hoort bij de Boom
    expect(w.find('[data-testid="diagram-leeg"]').text()).toContain('Zoek een proces om te beginnen.')
    // Proces-only borging: de wissel veroorzaakt géén extra fetch (zelfde bron als de Boom)
    // en al helemaal geen component-/vervuller-calls buiten de bestaande gap-cue-afleiding.
    expect(api.processen.lijst).toHaveBeenCalledTimes(1)
    await w.find('[data-testid="weergave-boom"]').trigger('click')
    expect(w.find('[data-testid="processen-boom"]').exists()).toBe(true)
    expect(w.find('[data-testid="proces-diagram"]').exists()).toBe(false)
  })

  it('de weergave-keuze reist mee in de lijststaat (F5/terugnavigeren)', async () => {
    sessionStorage.setItem(
      'lijst-state:proces-lijst',
      JSON.stringify({ zoekterm: '', openTakken: [], weergave: 'diagram' }),
    )
    const w = await mountLijst()
    expect(w.find('[data-testid="proces-diagram"]').exists()).toBe(true)
    window.dispatchEvent(new Event('beforeunload'))
    const bewaard = JSON.parse(sessionStorage.getItem('lijst-state:proces-lijst'))
    expect(bewaard.weergave).toBe('diagram')
    w.unmount()
  })
})

describe('ProcesLijst — lijststaat behouden bij terugnavigeren (useLijstStaat)', () => {
  it('herstelt zoekterm + uitgeklapte takken uit de bewaarde staat', async () => {
    sessionStorage.setItem(
      'lijst-state:proces-lijst',
      JSON.stringify({ zoekterm: '', openTakken: ['bz'] }),
    )
    const w = await mountLijst()
    // De bz-tak staat hersteld open zonder klik; vv niet (assert op de boom-container —
    // de (i)-uitlegtekst noemt "Aanvraag behandelen" als voorbeeld).
    const boom = w.find('[data-testid="processen-boom"]').text()
    expect(boom).toContain('Verhuizing verwerken')
    expect(boom).not.toContain('Aanvraag behandelen')
  })

  it('bewaart de actuele staat op het beforeunload-pad (F5-gedrag) en pruned onbekende takken', async () => {
    sessionStorage.setItem(
      'lijst-state:proces-lijst',
      JSON.stringify({ zoekterm: '', openTakken: ['bz', 'weg-tak'] }),
    )
    const w = await mountLijst()
    await w.find('[data-testid="filter-zoek"]').setValue('burger')
    window.dispatchEvent(new Event('beforeunload'))
    const bewaard = JSON.parse(sessionStorage.getItem('lijst-state:proces-lijst'))
    expect(bewaard.zoekterm).toBe('burger')
    expect(bewaard.openTakken).toEqual(['bz']) // 'weg-tak' bestaat niet meer → stil geprund
    w.unmount()
  })
})
