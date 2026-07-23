/** Tests — ChecklistConfigBeheer (tenant-beheer-view, ADR-022 W1).
 * Tenant-CRUD op `/checklistconfig`: vragen op `id`, met componenttype/actief +
 * categorie_nr/categorie_naam uit de respons; vraag aanmaken/(de)activeren met
 * "raakt N componenten"-aankondiging (window.confirm). */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'
import { useAuthStore } from '@/store/auth'

vi.mock('@/api', () => ({
  api: {
    checklistconfig: {
      lijst: vi.fn(),
      betekenissen: vi.fn(),
      impact: vi.fn(),
      maakVraag: vi.fn(),
      werkVraagBij: vi.fn(),
      zetAntwoordtype: vi.fn(),
      zetBetekenis: vi.fn(),
      zetActief: vi.fn(),
      voegOptieToe: vi.fn(),
      wijzigOptie: vi.fn(),
      deactiveerOptie: vi.fn(),
    },
    componenten: {
      opties: vi.fn(),
    },
  },
}))

import { api } from '@/api'
import ChecklistConfigBeheer from '@/views/ChecklistConfigBeheer.vue'

const VRAGEN = [
  {
    id: 'v1', componenttype: 'applicatie', code: '9.1', categorie_nr: 9, categorie_naam: 'Overig',
    vraag: 'V negen', prioriteit: 'midden', antwoordtype: 'geen', actief: true, betekenis: null, opties: [],
  },
  {
    id: 'v2', componenttype: 'applicatie', code: '2.1', categorie_nr: 2, categorie_naam: 'Hosting',
    vraag: 'Hosting', prioriteit: 'midden', antwoordtype: 'enkelvoudige_keuze', actief: true,
    betekenis: 'technische_plaatsing',
    opties: [{ id: 'o1', optie_sleutel: 'saas', label: 'SaaS', volgorde: 0, actief: true, afgeleid_bron: 'HostingModel' }],
  },
  {
    id: 'v3', componenttype: 'database', code: '1.3', categorie_nr: 1, categorie_naam: 'Eigenaar',
    vraag: 'Eigenaar', prioriteit: 'midden', antwoordtype: 'enkelvoudige_keuze', actief: true, betekenis: null,
    opties: [{ id: 'o2', optie_sleutel: 'bwb', label: 'BWB', volgorde: 0, actief: true, afgeleid_bron: null }],
  },
]

const BETEKENISSEN = [
  { optie_sleutel: 'technische_plaatsing', label: 'Technische plaatsing (waar draait dit op)', volgorde: 0 },
]

const TYPE_OPTIES = {
  componenttype: [
    { optie_sleutel: 'applicatie', label: 'Applicatie' },
    { optie_sleutel: 'database', label: 'Database' },
  ],
}

// ADR-022 W2 / LI050 — de view gate't bewerk-affordances op de beheerder-rol.
// Default beheerder, zodat de bestaande CRUD-tests het bewerkpad blijven oefenen;
// de rol-gating-tests mounten expliciet als viewer/medewerker.
async function mountView(rollen = ['beheerder']) {
  const pinia = createPinia()
  setActivePinia(pinia)
  useAuthStore().user = { roles: rollen }
  const wrapper = mount(ChecklistConfigBeheer, {
    global: { plugins: [pinia, [PrimeVue, { unstyled: true }], ToastService] },
  })
  await flushPromises()
  return wrapper
}

beforeEach(() => {
  vi.clearAllMocks()
  api.checklistconfig.lijst.mockResolvedValue(structuredClone(VRAGEN))
  api.checklistconfig.betekenissen.mockResolvedValue(structuredClone(BETEKENISSEN))
  api.componenten.opties.mockResolvedValue(structuredClone(TYPE_OPTIES))
  api.checklistconfig.impact.mockResolvedValue({ aantal_componenten: 4 })
})
afterEach(() => vi.restoreAllMocks())

describe('ChecklistConfigBeheer', () => {
  it('laadt en toont de vragen + antwoordtype + componenttype', async () => {
    const w = await mountView()
    expect(w.find('[data-testid="cfg-vraag-9.1"]').exists()).toBe(true)
    expect(w.find('[data-testid="cfg-type-2.1"]').element.value).toBe('enkelvoudige_keuze')
    // Type-kolom toont het componenttype-label.
    expect(w.find('[data-testid="cfg-vraag-type-1.3"]').text()).toBe('Database')
  })

  it('filtert op categorie (uit categorie_nr van de respons)', async () => {
    const w = await mountView()
    await w.find('[data-testid="cfg-categorie-filter"]').setValue('1')
    expect(w.find('[data-testid="cfg-vraag-1.3"]').exists()).toBe(true)
    expect(w.find('[data-testid="cfg-vraag-9.1"]').exists()).toBe(false)
    expect(w.find('[data-testid="cfg-vraag-2.1"]').exists()).toBe(false)
  })

  it('zet antwoordtype op een geen-vraag (id-adressering)', async () => {
    api.checklistconfig.zetAntwoordtype.mockResolvedValue({
      ...VRAGEN[0], antwoordtype: 'getal',
    })
    const w = await mountView()
    await w.find('[data-testid="cfg-type-9.1"]').setValue('getal')
    await flushPromises()
    expect(api.checklistconfig.zetAntwoordtype).toHaveBeenCalledWith('v1', 'getal')
  })

  it('toont een 409 (CONFIGURATIE_CONFLICT) bij type-wisseling netjes', async () => {
    const err = new Error('Een reeds geconfigureerde vraag kan niet van antwoordtype wisselen.')
    err.status = 409
    err.code = 'CONFIGURATIE_CONFLICT'
    api.checklistconfig.zetAntwoordtype.mockRejectedValue(err)
    const w = await mountView()
    await w.find('[data-testid="cfg-type-1.3"]').setValue('meerkeuze')
    await flushPromises()
    expect(w.find('[data-testid="cfg-actie-fout"]').text()).toContain('niet van antwoordtype wisselen')
  })

  it('voegt een optie toe aan een vrije set (op vraag-id)', async () => {
    api.checklistconfig.voegOptieToe.mockResolvedValue({
      id: 'o9', optie_sleutel: 'tiel', label: 'Tiel', volgorde: 1, actief: true, afgeleid_bron: null,
    })
    const w = await mountView()
    await w.find('[data-testid="cfg-nieuw-sleutel-1.3"]').setValue('tiel')
    await w.find('[data-testid="cfg-nieuw-label-1.3"]').setValue('Tiel')
    await w.find('[data-testid="cfg-toevoegen-1.3"]').trigger('submit')
    await flushPromises()
    expect(api.checklistconfig.voegOptieToe).toHaveBeenCalledWith('v3', {
      optie_sleutel: 'tiel', label: 'Tiel', volgorde: 0,
    })
  })

  it('deactiveert een vrije optie (soft)', async () => {
    api.checklistconfig.deactiveerOptie.mockResolvedValue({
      id: 'o2', optie_sleutel: 'bwb', label: 'BWB', volgorde: 0, actief: false, afgeleid_bron: null,
    })
    const w = await mountView()
    await w.find('[data-testid="cfg-optie-deactiveren-o2"]').trigger('click')
    await flushPromises()
    expect(api.checklistconfig.deactiveerOptie).toHaveBeenCalledWith('o2')
  })

  it('afgeleide set: badge, label-only, geen toevoegen/deactiveren/volgorde', async () => {
    const w = await mountView()
    expect(w.find('[data-testid="cfg-afgeleid-2.1"]').exists()).toBe(true)
    expect(w.find('[data-testid="cfg-toevoegen-2.1"]').exists()).toBe(false) // geen toevoegen
    expect(w.find('[data-testid="cfg-optie-volgorde-o1"]').attributes('disabled')).toBeDefined()
    expect(w.find('[data-testid="cfg-optie-deactiveren-o1"]').exists()).toBe(false)
    expect(w.find('[data-testid="cfg-optie-label-o1"]').exists()).toBe(true) // label wél editbaar
  })

  it('voegt een nieuwe vraag toe na impact-aankondiging', async () => {
    const confirmSpy = vi.fn(() => true); window.confirm = confirmSpy
    api.checklistconfig.maakVraag.mockResolvedValue({
      id: 'v9', componenttype: 'applicatie', code: '1.4', categorie_nr: 1, categorie_naam: 'Eigenaar',
      vraag: 'Nieuwe vraag', prioriteit: 'midden', antwoordtype: 'geen', actief: true, opties: [],
    })
    const w = await mountView()
    await w.find('[data-testid="cfg-nieuwe-vraag-type"]').setValue('applicatie')
    await w.find('[data-testid="cfg-nieuwe-vraag-code"]').setValue('1.4')
    await w.find('[data-testid="cfg-nieuwe-vraag-tekst"]').setValue('Nieuwe vraag')
    await w.find('[data-testid="cfg-nieuwe-vraag-catnr"]').setValue('1')
    await w.find('[data-testid="cfg-nieuwe-vraag-catnaam"]').setValue('Eigenaar')
    await w.find('[data-testid="cfg-nieuwe-vraag"]').trigger('submit')
    await flushPromises()
    expect(api.checklistconfig.impact).toHaveBeenCalledWith('applicatie')
    expect(confirmSpy).toHaveBeenCalled()
    expect(api.checklistconfig.maakVraag).toHaveBeenCalledWith({
      componenttype: 'applicatie', code: '1.4', vraag: 'Nieuwe vraag',
      categorie_nr: 1, categorie_naam: 'Eigenaar',
    })
    expect(w.find('[data-testid="cfg-vraag-1.4"]').exists()).toBe(true)
  })

  it('toont een 409 CHECKLISTVRAAG_BESTAAT bij dubbele vraag netjes', async () => {
    window.confirm = vi.fn(() => true)
    const err = new Error('Deze checklistvraag bestaat al.')
    err.status = 409
    err.code = 'CHECKLISTVRAAG_BESTAAT'
    api.checklistconfig.maakVraag.mockRejectedValue(err)
    const w = await mountView()
    await w.find('[data-testid="cfg-nieuwe-vraag-type"]').setValue('applicatie')
    await w.find('[data-testid="cfg-nieuwe-vraag-code"]').setValue('9.1')
    await w.find('[data-testid="cfg-nieuwe-vraag-tekst"]').setValue('Dubbel')
    await w.find('[data-testid="cfg-nieuwe-vraag-catnr"]').setValue('9')
    await w.find('[data-testid="cfg-nieuwe-vraag-catnaam"]').setValue('Overig')
    await w.find('[data-testid="cfg-nieuwe-vraag"]').trigger('submit')
    await flushPromises()
    expect(w.find('[data-testid="cfg-actie-fout"]').text()).toContain('bestaat al')
  })

  it('(de)activeert een vraag na impact-aankondiging', async () => {
    window.confirm = vi.fn(() => true)
    api.checklistconfig.zetActief.mockResolvedValue({ ...VRAGEN[0], actief: false })
    const w = await mountView()
    expect(w.find('[data-testid="cfg-vraag-status-9.1"]').text()).toBe('actief')
    await w.find('[data-testid="cfg-vraag-actief-9.1"]').trigger('click')
    await flushPromises()
    expect(api.checklistconfig.impact).toHaveBeenCalledWith('applicatie')
    expect(api.checklistconfig.zetActief).toHaveBeenCalledWith('v1', false)
    expect(w.find('[data-testid="cfg-vraag-status-9.1"]').text()).toBe('gedeactiveerd')
  })

  it('(de)activeren wordt geannuleerd als de aankondiging wordt afgewezen', async () => {
    window.confirm = vi.fn(() => false)
    const w = await mountView()
    await w.find('[data-testid="cfg-vraag-actief-9.1"]').trigger('click')
    await flushPromises()
    expect(api.checklistconfig.zetActief).not.toHaveBeenCalled()
  })

  // ── ADR-023 Fase F (F-3): betekenis-toekenning ──────────────────────────────
  it('toont de betekenis-keuze + de huidige toekenning uit de respons', async () => {
    const w = await mountView()
    // v2 (code 2.1) draagt technische_plaatsing; v1 (9.1) geen.
    expect(w.find('[data-testid="cfg-betekenis-2.1"]').element.value).toBe('technische_plaatsing')
    expect(w.find('[data-testid="cfg-betekenis-9.1"]').element.value).toBe('')
    // De catalogus-optie is als keuze beschikbaar.
    expect(w.find('[data-testid="cfg-betekenis-9.1"]').text()).toContain('Technische plaatsing')
  })

  it('kent een betekenis toe (id-adressering)', async () => {
    api.checklistconfig.zetBetekenis.mockResolvedValue({ ...VRAGEN[0], betekenis: 'technische_plaatsing' })
    const w = await mountView()
    await w.find('[data-testid="cfg-betekenis-9.1"]').setValue('technische_plaatsing')
    await flushPromises()
    expect(api.checklistconfig.zetBetekenis).toHaveBeenCalledWith('v1', 'technische_plaatsing')
  })

  it('wist een betekenis (leeg = null)', async () => {
    api.checklistconfig.zetBetekenis.mockResolvedValue({ ...VRAGEN[1], betekenis: null })
    const w = await mountView()
    await w.find('[data-testid="cfg-betekenis-2.1"]').setValue('')
    await flushPromises()
    expect(api.checklistconfig.zetBetekenis).toHaveBeenCalledWith('v2', null)
  })

  it('toont een 409 (uniciteit) bij betekenis-toekenning netjes', async () => {
    const err = new Error('Een andere vraag van dit componenttype draagt deze betekenis al.')
    err.status = 409
    err.code = 'CONFIGURATIE_CONFLICT'
    api.checklistconfig.zetBetekenis.mockRejectedValue(err)
    const w = await mountView()
    await w.find('[data-testid="cfg-betekenis-9.1"]').setValue('technische_plaatsing')
    await flushPromises()
    expect(w.find('[data-testid="cfg-actie-fout"]').text()).toContain('draagt deze betekenis al')
  })
})

describe('ChecklistConfigBeheer — rol-gating (ADR-022 W2 / LI050)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.checklistconfig.lijst.mockResolvedValue(structuredClone(VRAGEN))
    api.checklistconfig.betekenissen.mockResolvedValue(structuredClone(BETEKENISSEN))
    api.componenten.opties.mockResolvedValue(structuredClone(TYPE_OPTIES))
    api.checklistconfig.impact.mockResolvedValue({ aantal_componenten: 4 })
  })

  it('niet-beheerder: géén bewerk-affordances, wél de uitlegzin en de leesbare lijst', async () => {
    const w = await mountView(['medewerker'])
    // De uitlegzin — zichtbare tekst, geen "rendert".
    expect(w.text()).toContain('De vragenlijst wordt bepaald door de beheerder van uw organisatie.')
    // Alle bewerk-affordances zijn AFWEZIG (niet uitgegrijsd).
    expect(w.find('[data-testid="cfg-nieuwe-vraag"]').exists()).toBe(false)
    expect(w.find('[data-testid="cfg-vraag-actief-9.1"]').exists()).toBe(false)
    expect(w.find('[data-testid="cfg-type-9.1"]').exists()).toBe(false)
    expect(w.find('[data-testid="cfg-betekenis-9.1"]').exists()).toBe(false)
    expect(w.find('[data-testid="cfg-optie-opslaan-o2"]').exists()).toBe(false)
    expect(w.find('[data-testid="cfg-optie-deactiveren-o2"]').exists()).toBe(false)
    expect(w.find('[data-testid="cfg-toevoegen-1.3"]').exists()).toBe(false)
    expect(w.text()).not.toContain('Deactiveren')
    // De lijst blijft leesbaar: vraag, antwoordtype-als-tekst en optie-label zichtbaar.
    expect(w.text()).toContain('V negen')
    expect(w.find('[data-testid="cfg-type-tekst-9.1"]').text()).toBe('Geen')
    expect(w.text()).toContain('BWB')
  })

  it('viewer: zelfde leesbeeld als medewerker (geen knoppen, wél de zin)', async () => {
    const w = await mountView(['viewer'])
    expect(w.text()).toContain('De vragenlijst wordt bepaald door de beheerder van uw organisatie.')
    expect(w.find('[data-testid="cfg-nieuwe-vraag"]').exists()).toBe(false)
    expect(w.find('[data-testid="cfg-vraag-actief-9.1"]').exists()).toBe(false)
  })

  it('beheerder: bewerk-affordances aanwezig, uitlegzin afwezig', async () => {
    const w = await mountView(['beheerder'])
    expect(w.text()).not.toContain('De vragenlijst wordt bepaald door de beheerder van uw organisatie.')
    expect(w.find('[data-testid="cfg-nieuwe-vraag"]').exists()).toBe(true)
    expect(w.find('[data-testid="cfg-vraag-actief-9.1"]').exists()).toBe(true)
    expect(w.find('[data-testid="cfg-type-9.1"]').exists()).toBe(true)
    expect(w.find('[data-testid="cfg-optie-opslaan-o2"]').exists()).toBe(true)
  })
})
