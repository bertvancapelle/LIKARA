/** Tests — ChecklistConfigBeheer (tenant-beheer-view, ADR-022 W1/W2/W3/W4, LI050).
 * Indeling: componenttype-keuze bovenaan · categorieën links (het filter) · vragen van de
 * geopende categorie rechts. Geen vraagcode op het scherm; code wordt door het systeem
 * toegekend. Rol-gating: iedereen leest, alleen de beheerder muteert. */
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
      categorieen: vi.fn(),
      maakCategorie: vi.fn(),
      wijzigCategorie: vi.fn(),
      verwijderCategorie: vi.fn(),
    },
    componenten: {
      opties: vi.fn(),
    },
  },
}))

import { api } from '@/api'
import ChecklistConfigBeheer from '@/views/ChecklistConfigBeheer.vue'

// LI050 (W3): de categorie is een eigen entiteit; (W4): de code is intern.
const CATEGORIEEN = [
  { id: 'c-ei', componenttype: 'database', naam: 'Eigenaar', volgorde: 1, aantal_vragen: 1 },
  { id: 'c-ho', componenttype: 'applicatie', naam: 'Hosting', volgorde: 2, aantal_vragen: 1 },
  { id: 'c-ov', componenttype: 'applicatie', naam: 'Overig', volgorde: 9, aantal_vragen: 1 },
]

const VRAGEN = [
  {
    id: 'v1', componenttype: 'applicatie', code: '9.1', categorie_id: 'c-ov', categorie_naam: 'Overig',
    categorie_volgorde: 9,
    vraag: 'V negen', prioriteit: 'midden', antwoordtype: 'geen', actief: true, betekenis: null, opties: [],
  },
  {
    id: 'v2', componenttype: 'applicatie', code: '2.1', categorie_id: 'c-ho', categorie_naam: 'Hosting',
    categorie_volgorde: 2,
    vraag: 'Hostingvraag', prioriteit: 'midden', antwoordtype: 'enkelvoudige_keuze', actief: true,
    betekenis: 'technische_plaatsing',
    opties: [{ id: 'o1', optie_sleutel: 'saas', label: 'SaaS', volgorde: 0, actief: true, afgeleid_bron: 'HostingModel' }],
  },
  {
    id: 'v3', componenttype: 'database', code: '1.3', categorie_id: 'c-ei', categorie_naam: 'Eigenaar',
    categorie_volgorde: 1,
    vraag: 'Eigenaarvraag', prioriteit: 'midden', antwoordtype: 'enkelvoudige_keuze', actief: true, betekenis: null,
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

function zetMocks() {
  api.checklistconfig.lijst.mockResolvedValue(structuredClone(VRAGEN))
  api.checklistconfig.betekenissen.mockResolvedValue(structuredClone(BETEKENISSEN))
  api.componenten.opties.mockResolvedValue(structuredClone(TYPE_OPTIES))
  api.checklistconfig.impact.mockResolvedValue({ aantal_componenten: 4 })
  api.checklistconfig.categorieen.mockResolvedValue(structuredClone(CATEGORIEEN))
}

beforeEach(() => {
  vi.clearAllMocks()
  zetMocks()
})
afterEach(() => vi.restoreAllMocks())

describe('ChecklistConfigBeheer — indeling (LI050)', () => {
  it('opent op het eerste type; links alleen categorieën van dát type, rechts de geopende categorie', async () => {
    const w = await mountView()
    // Typekeuze default = applicatie (eerste type mét categorieën).
    expect(w.find('[data-testid="cfg-type-keuze"]').element.value).toBe('applicatie')
    // Linkerkolom: ALLEEN applicatie-categorieën — de borging-eis.
    const kolom = w.find('[data-testid="cfg-categorie-kolom"]').text()
    expect(kolom).toContain('Hosting')
    expect(kolom).toContain('Overig')
    expect(kolom).not.toContain('Eigenaar') // database-categorie hoort hier niet
    // Rechts: de eerste categorie (volgorde 2 = Hosting) staat open met haar vraag.
    expect(w.find('[data-testid="cfg-vraag-2.1"]').exists()).toBe(true)
    expect(w.find('[data-testid="cfg-vraag-9.1"]').exists()).toBe(false)
  })

  it('typewissel toont de categorieën en vragen van het andere type', async () => {
    const w = await mountView()
    await w.find('[data-testid="cfg-type-keuze"]').setValue('database')
    await flushPromises()
    const kolom = w.find('[data-testid="cfg-categorie-kolom"]').text()
    expect(kolom).toContain('Eigenaar')
    expect(kolom).not.toContain('Hosting')
    expect(w.find('[data-testid="cfg-vraag-1.3"]').exists()).toBe(true)
  })

  it('categorie kiezen in de kolom wisselt de vragen rechts', async () => {
    const w = await mountView()
    await w.find('[data-testid="cfg-cat-c-ov"]').trigger('click')
    expect(w.find('[data-testid="cfg-vraag-9.1"]').exists()).toBe(true)
    expect(w.find('[data-testid="cfg-vraag-2.1"]').exists()).toBe(false)
  })

  it('NERGENS staat een vraagcode op het scherm (zichtbare tekst, LI050 W4)', async () => {
    const w = await mountView()
    expect(w.text()).not.toContain('9.1')
    expect(w.text()).not.toContain('2.1')
    expect(w.text()).not.toContain('Code')
    await w.find('[data-testid="cfg-cat-c-ov"]').trigger('click')
    expect(w.text()).not.toContain('9.1')
  })

  it('lege categorie toont een regel mét route, geen kale leegte', async () => {
    api.checklistconfig.categorieen.mockResolvedValue([
      ...structuredClone(CATEGORIEEN),
      { id: 'c-leeg', componenttype: 'applicatie', naam: 'Leeg', volgorde: 1, aantal_vragen: 0 },
    ])
    const w = await mountView()
    // 'Leeg' heeft volgorde 1 → opent als eerste.
    expect(w.find('[data-testid="cfg-leeg"]').text()).toContain('nog geen vragen')
    expect(w.find('[data-testid="cfg-leeg"]').text()).toContain('Voeg hieronder de eerste vraag toe.')
  })
})

describe('ChecklistConfigBeheer — vraagbeheer', () => {
  it('zet antwoordtype op een geen-vraag (id-adressering)', async () => {
    api.checklistconfig.zetAntwoordtype.mockResolvedValue({ ...VRAGEN[0], antwoordtype: 'getal' })
    const w = await mountView()
    await w.find('[data-testid="cfg-cat-c-ov"]').trigger('click')
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
    await w.find('[data-testid="cfg-type-keuze"]').setValue('database')
    await flushPromises()
    await w.find('[data-testid="cfg-type-1.3"]').setValue('meerkeuze')
    await flushPromises()
    expect(w.find('[data-testid="cfg-actie-fout"]').text()).toContain('niet van antwoordtype wisselen')
  })

  it('voegt een optie toe aan een vrije set (op vraag-id)', async () => {
    api.checklistconfig.voegOptieToe.mockResolvedValue({
      id: 'o9', optie_sleutel: 'tiel', label: 'Tiel', volgorde: 1, actief: true, afgeleid_bron: null,
    })
    const w = await mountView()
    await w.find('[data-testid="cfg-type-keuze"]').setValue('database')
    await flushPromises()
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
    await w.find('[data-testid="cfg-type-keuze"]').setValue('database')
    await flushPromises()
    await w.find('[data-testid="cfg-optie-deactiveren-o2"]').trigger('click')
    await flushPromises()
    expect(api.checklistconfig.deactiveerOptie).toHaveBeenCalledWith('o2')
  })

  it('afgeleide set: badge, label-only, geen toevoegen/deactiveren/volgorde', async () => {
    const w = await mountView() // Hosting (2.1, afgeleide set) staat default open
    expect(w.find('[data-testid="cfg-afgeleid-2.1"]').exists()).toBe(true)
    expect(w.find('[data-testid="cfg-toevoegen-2.1"]').exists()).toBe(false)
    expect(w.find('[data-testid="cfg-optie-deactiveren-o1"]').exists()).toBe(false)
    expect(w.find('[data-testid="cfg-optie-volgorde-o1"]').attributes('disabled')).toBeDefined()
  })

  it('voegt een vraag toe ZONDER code: alleen tekst; het systeem kent de code toe (W4)', async () => {
    const confirmSpy = vi.fn(() => true); window.confirm = confirmSpy
    api.checklistconfig.maakVraag.mockResolvedValue({
      id: 'v9', componenttype: 'applicatie', code: '13', categorie_id: 'c-ho',
      categorie_naam: 'Hosting', categorie_volgorde: 2,
      vraag: 'Nieuwe vraag', prioriteit: 'midden', antwoordtype: 'geen', actief: true, opties: [],
    })
    const w = await mountView()
    // Er is géén code-invoerveld meer.
    expect(w.find('[data-testid="cfg-nieuwe-vraag-code"]').exists()).toBe(false)
    await w.find('[data-testid="cfg-nieuwe-vraag-tekst"]').setValue('Nieuwe vraag')
    await w.find('[data-testid="cfg-nieuwe-vraag"]').trigger('submit')
    await flushPromises()
    expect(confirmSpy).toHaveBeenCalled()
    // De payload draagt GEEN code — type en categorie komen uit de indeling.
    expect(api.checklistconfig.maakVraag).toHaveBeenCalledWith({
      componenttype: 'applicatie', vraag: 'Nieuwe vraag', categorie_id: 'c-ho',
    })
  })

  it('(de)activeert een vraag na impact-aankondiging op de vraagTEKST', async () => {
    const confirmSpy = vi.fn(() => true); window.confirm = confirmSpy
    api.checklistconfig.zetActief.mockResolvedValue({ ...VRAGEN[1], actief: false })
    const w = await mountView()
    await w.find('[data-testid="cfg-vraag-actief-2.1"]').trigger('click')
    await flushPromises()
    expect(api.checklistconfig.zetActief).toHaveBeenCalledWith('v2', false)
    // De aankondiging benoemt de vraag op zijn tekst, zonder code.
    expect(confirmSpy.mock.calls[0][0]).toContain('Hostingvraag')
    expect(confirmSpy.mock.calls[0][0]).not.toContain('2.1')
  })

  it('(de)activeren wordt geannuleerd als de aankondiging wordt afgewezen', async () => {
    window.confirm = vi.fn(() => false)
    const w = await mountView()
    await w.find('[data-testid="cfg-vraag-actief-2.1"]').trigger('click')
    await flushPromises()
    expect(api.checklistconfig.zetActief).not.toHaveBeenCalled()
  })

  it('kent een betekenis toe (id-adressering)', async () => {
    api.checklistconfig.zetBetekenis.mockResolvedValue({ ...VRAGEN[0], betekenis: 'technische_plaatsing' })
    const w = await mountView()
    await w.find('[data-testid="cfg-cat-c-ov"]').trigger('click')
    await w.find('[data-testid="cfg-betekenis-9.1"]').setValue('technische_plaatsing')
    await flushPromises()
    expect(api.checklistconfig.zetBetekenis).toHaveBeenCalledWith('v1', 'technische_plaatsing')
  })
})

describe('ChecklistConfigBeheer — categoriebeheer (LI050)', () => {
  it('voegt een categorie toe voor het gekozen type en opent hem', async () => {
    api.checklistconfig.maakCategorie.mockResolvedValue({
      id: 'c-nieuw', componenttype: 'applicatie', naam: 'Nieuw', volgorde: 5, aantal_vragen: 0,
    })
    const w = await mountView()
    await w.find('[data-testid="cfg-nieuwe-categorie-naam"]').setValue('Nieuw')
    await w.find('[data-testid="cfg-nieuwe-categorie"]').trigger('submit')
    await flushPromises()
    expect(api.checklistconfig.maakCategorie).toHaveBeenCalledWith({
      componenttype: 'applicatie', naam: 'Nieuw', volgorde: 0,
    })
  })

  it('hernoemt de geopende categorie in één handeling', async () => {
    api.checklistconfig.wijzigCategorie.mockResolvedValue({})
    const w = await mountView()
    await w.find('[data-testid="cfg-cat-open-naam"]').setValue('Hosting & infra')
    await w.find('[data-testid="cfg-cat-opslaan"]').trigger('click')
    await flushPromises()
    expect(api.checklistconfig.wijzigCategorie).toHaveBeenCalledWith('c-ho', { naam: 'Hosting & infra' })
  })

  it('wijzigt de volgorde vanuit de lijst', async () => {
    api.checklistconfig.wijzigCategorie.mockResolvedValue({})
    const w = await mountView()
    await w.find('[data-testid="cfg-cat-volgorde-c-ov"]').setValue('1')
    await w.find('[data-testid="cfg-cat-volgorde-c-ov"]').trigger('change')
    await flushPromises()
    expect(api.checklistconfig.wijzigCategorie).toHaveBeenCalledWith('c-ov', { volgorde: 1 })
  })

  it('verwijderen met vragen eronder toont de weigering mét telling (409)', async () => {
    window.confirm = vi.fn(() => true)
    const err = new Error('Er hangen nog 7 vragen onder deze categorie; verplaats of verwijder die eerst — een indeling met vragen verdwijnt nooit stil.')
    err.status = 409
    err.code = 'CATEGORIE_HEEFT_VRAGEN'
    api.checklistconfig.verwijderCategorie.mockRejectedValue(err)
    const w = await mountView()
    await w.find('[data-testid="cfg-cat-verwijderen"]').trigger('click')
    await flushPromises()
    expect(w.find('[data-testid="cfg-actie-fout"]').text()).toContain('7 vragen')
  })
})

describe('ChecklistConfigBeheer — rol-gating (ADR-022 W2 / LI050)', () => {
  it('niet-beheerder: zelfde indeling, géén bewerk-affordances, wél de uitlegzin', async () => {
    const w = await mountView(['medewerker'])
    expect(w.text()).toContain('De vragenlijst wordt bepaald door de beheerder van uw organisatie.')
    // Zelfde indeling: typekeuze + categorielijst + vragen leesbaar.
    expect(w.find('[data-testid="cfg-type-keuze"]').exists()).toBe(true)
    expect(w.find('[data-testid="cfg-categorie-kolom"]').text()).toContain('Hosting')
    expect(w.text()).toContain('Hostingvraag')
    expect(w.find('[data-testid="cfg-type-tekst-2.1"]').text()).toBe('Enkelvoudige keuze')
    // Geen enkele bewerk-affordance.
    expect(w.find('[data-testid="cfg-nieuwe-vraag"]').exists()).toBe(false)
    expect(w.find('[data-testid="cfg-nieuwe-categorie"]').exists()).toBe(false)
    expect(w.find('[data-testid="cfg-cat-opslaan"]').exists()).toBe(false)
    expect(w.find('[data-testid="cfg-cat-verwijderen"]').exists()).toBe(false)
    expect(w.find('[data-testid="cfg-cat-volgorde-c-ho"]').exists()).toBe(false)
    expect(w.find('[data-testid="cfg-vraag-actief-2.1"]').exists()).toBe(false)
    expect(w.text()).not.toContain('Deactiveren')
  })

  it('viewer: idem — leest, geen knoppen', async () => {
    const w = await mountView(['viewer'])
    expect(w.text()).toContain('De vragenlijst wordt bepaald door de beheerder van uw organisatie.')
    expect(w.find('[data-testid="cfg-nieuwe-vraag"]').exists()).toBe(false)
    expect(w.find('[data-testid="cfg-cat-c-ov"]').exists()).toBe(true) // navigeren mag
  })

  it('beheerder: bewerk-affordances aanwezig, uitlegzin afwezig', async () => {
    const w = await mountView(['beheerder'])
    expect(w.text()).not.toContain('De vragenlijst wordt bepaald door de beheerder van uw organisatie.')
    expect(w.find('[data-testid="cfg-nieuwe-vraag"]').exists()).toBe(true)
    expect(w.find('[data-testid="cfg-nieuwe-categorie"]').exists()).toBe(true)
    expect(w.find('[data-testid="cfg-vraag-actief-2.1"]').exists()).toBe(true)
  })
})
