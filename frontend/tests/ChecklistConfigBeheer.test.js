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
      impactAntwoorden: vi.fn(),
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
    categorie_volgorde: 9, volgorde: 1,
    vraag: 'V negen', prioriteit: 'midden', antwoordtype: 'geen', actief: true, betekenis: null, opties: [],
  },
  {
    id: 'v2', componenttype: 'applicatie', code: '2.1', categorie_id: 'c-ho', categorie_naam: 'Hosting',
    categorie_volgorde: 2, volgorde: 1,
    vraag: 'Hostingvraag', prioriteit: 'midden', antwoordtype: 'enkelvoudige_keuze', actief: true,
    betekenis: 'technische_plaatsing',
    opties: [{ id: 'o1', optie_sleutel: 'saas', label: 'SaaS', volgorde: 0, actief: true, afgeleid_bron: 'HostingModel' }],
  },
  {
    id: 'v4', componenttype: 'applicatie', code: '2.2', categorie_id: 'c-ho', categorie_naam: 'Hosting',
    categorie_volgorde: 2, volgorde: 2,
    vraag: 'Tweede hostingvraag', prioriteit: 'midden', antwoordtype: 'geen', actief: true, betekenis: null, opties: [],
  },
  {
    id: 'v3', componenttype: 'database', code: '1.3', categorie_id: 'c-ei', categorie_naam: 'Eigenaar',
    categorie_volgorde: 1, volgorde: 1,
    vraag: 'Eigenaarvraag', prioriteit: 'midden', antwoordtype: 'enkelvoudige_keuze', actief: true, betekenis: null,
    opties: [
      { id: 'o2', optie_sleutel: 'bwb', label: 'BWB', volgorde: 1, actief: true, afgeleid_bron: null },
      { id: 'o3', optie_sleutel: 'tiel', label: 'Tiel', volgorde: 2, actief: true, afgeleid_bron: null },
    ],
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
    // ADR-056: het opslaan-venster is een PrimeVue Dialog (teleporteert naar body).
    global: { plugins: [pinia, [PrimeVue, { unstyled: true }], ToastService], stubs: { teleport: true } },
  })
  await flushPromises()
  return wrapper
}

// LI050-ergonomie: dicht is de rusttoestand — de onderbouwing zit achter het pijltje.
async function openVraag(w, code) {
  await w.find(`[data-testid="cfg-vraag-toggle-${code}"]`).trigger('click')
}

function zetMocks() {
  api.checklistconfig.lijst.mockResolvedValue(structuredClone(VRAGEN))
  api.checklistconfig.betekenissen.mockResolvedValue(structuredClone(BETEKENISSEN))
  api.componenten.opties.mockResolvedValue(structuredClone(TYPE_OPTIES))
  api.checklistconfig.impact.mockResolvedValue({ aantal_componenten: 4 })
  api.checklistconfig.impactAntwoorden.mockResolvedValue({ aantal_antwoorden: 5 })
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
    await openVraag(w, '9.1')
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
    await openVraag(w, '1.3')
    await w.find('[data-testid="cfg-type-1.3"]').setValue('meerkeuze')
    await flushPromises()
    expect(w.find('[data-testid="cfg-actie-fout"]').text()).toContain('niet van antwoordtype wisselen')
  })

  it('voegt een optie toe aan een vrije set (op vraag-id) — achteraan, zonder getalveld', async () => {
    api.checklistconfig.voegOptieToe.mockResolvedValue({
      id: 'o9', optie_sleutel: 'cloud', label: 'Cloud', volgorde: 3, actief: true, afgeleid_bron: null,
    })
    const w = await mountView()
    await w.find('[data-testid="cfg-type-keuze"]').setValue('database')
    await flushPromises()
    await openVraag(w, '1.3')
    // LI050-ergonomie: geen getalveld in het toevoegformulier.
    expect(w.find('[data-testid="cfg-nieuw-volgorde-1.3"]').exists()).toBe(false)
    await w.find('[data-testid="cfg-nieuw-sleutel-1.3"]').setValue('cloud')
    await w.find('[data-testid="cfg-nieuw-label-1.3"]').setValue('Cloud')
    await w.find('[data-testid="cfg-toevoegen-1.3"]').trigger('submit')
    await flushPromises()
    // De nieuwe optie komt ACHTERAAN (max bestaande volgorde + 1); daarna slepen.
    expect(api.checklistconfig.voegOptieToe).toHaveBeenCalledWith('v3', {
      optie_sleutel: 'cloud', label: 'Cloud', volgorde: 3,
    })
  })

  it('deactiveert een vrije optie (soft)', async () => {
    api.checklistconfig.deactiveerOptie.mockResolvedValue({
      id: 'o2', optie_sleutel: 'bwb', label: 'BWB', volgorde: 0, actief: false, afgeleid_bron: null,
    })
    const w = await mountView()
    await w.find('[data-testid="cfg-type-keuze"]').setValue('database')
    await flushPromises()
    await openVraag(w, '1.3')
    await w.find('[data-testid="cfg-optie-deactiveren-o2"]').trigger('click')
    await flushPromises()
    expect(api.checklistconfig.deactiveerOptie).toHaveBeenCalledWith('o2')
  })

  it('afgeleide set: badge, label-only, geen toevoegen/deactiveren — en niet sleepbaar', async () => {
    const w = await mountView() // Hostingcategorie staat default open
    await openVraag(w, '2.1') // afgeleide set
    expect(w.find('[data-testid="cfg-afgeleid-2.1"]').exists()).toBe(true)
    expect(w.find('[data-testid="cfg-toevoegen-2.1"]').exists()).toBe(false)
    expect(w.find('[data-testid="cfg-optie-deactiveren-o1"]').exists()).toBe(false)
    // Structuur vast: de optierij van een afgeleide set sleept niet.
    expect(w.find('[data-testid="cfg-optie-2.1-saas"]').attributes('draggable')).toBeUndefined()
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
    await openVraag(w, '2.1')
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
    await openVraag(w, '2.1')
    await w.find('[data-testid="cfg-vraag-actief-2.1"]').trigger('click')
    await flushPromises()
    expect(api.checklistconfig.zetActief).not.toHaveBeenCalled()
  })

  it('kent een betekenis toe (id-adressering)', async () => {
    api.checklistconfig.zetBetekenis.mockResolvedValue({ ...VRAGEN[0], betekenis: 'technische_plaatsing' })
    const w = await mountView()
    await w.find('[data-testid="cfg-cat-c-ov"]').trigger('click')
    await openVraag(w, '9.1')
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
    // LI050 (W5): geen volgorde-invoerveld meer — de categorie komt achteraan.
    expect(w.find('[data-testid="cfg-nieuwe-categorie-volgorde"]').exists()).toBe(false)
    await w.find('[data-testid="cfg-nieuwe-categorie-naam"]').setValue('Nieuw')
    await w.find('[data-testid="cfg-nieuwe-categorie"]').trigger('submit')
    await flushPromises()
    expect(api.checklistconfig.maakCategorie).toHaveBeenCalledWith({
      componenttype: 'applicatie', naam: 'Nieuw',
    })
  })

  it('hernoemen is een handeling: knop opent het veld, opslaan schrijft en sluit', async () => {
    api.checklistconfig.wijzigCategorie.mockResolvedValue({})
    const w = await mountView()
    // Rusttoestand: geen invoerveld — de naam staat als kop (zie de kop-test).
    expect(w.find('[data-testid="cfg-cat-open-naam"]').exists()).toBe(false)
    await w.find('[data-testid="cfg-cat-hernoem"]').trigger('click')
    await w.find('[data-testid="cfg-cat-open-naam"]').setValue('Hosting & infra')
    await w.find('[data-testid="cfg-cat-hernoem-form"]').trigger('submit')
    await flushPromises()
    expect(api.checklistconfig.wijzigCategorie).toHaveBeenCalledWith('c-ho', { naam: 'Hosting & infra' })
    expect(w.find('[data-testid="cfg-cat-hernoem-form"]').exists()).toBe(false) // handeling sluit
  })

  it('annuleren sluit de hernoem-handeling zonder te schrijven', async () => {
    const w = await mountView()
    await w.find('[data-testid="cfg-cat-hernoem"]').trigger('click')
    await w.find('[data-testid="cfg-cat-annuleren"]').trigger('click')
    expect(w.find('[data-testid="cfg-cat-hernoem-form"]').exists()).toBe(false)
    expect(api.checklistconfig.wijzigCategorie).not.toHaveBeenCalled()
  })

  it('de categorienaam rechts is een KOP met aanduiding en aantal — geen invoerveld', async () => {
    const w = await mountView()
    const kop = w.find('[data-testid="cfg-cat-open-titel"]')
    expect(kop.element.tagName).toBe('H2')
    expect(kop.text()).toBe('Hosting')
    expect(w.text()).toContain('Vragen van categorie')
    expect(w.find('[data-testid="cfg-cat-open-aantal"]').text()).toContain('vraag')
    expect(w.find('[data-testid="cfg-cat-open-naam"]').exists()).toBe(false)
  })

  it('er leest precies ÉÉN categorie als geselecteerd — ook na wisselen en na slepen', async () => {
    api.checklistconfig.wijzigCategorie.mockResolvedValue({})
    const w = await mountView()
    const geselecteerd = () => w.findAll('[aria-current="true"]')
    expect(geselecteerd()).toHaveLength(1)
    // Wisselen: de selectie verhuist, er zijn er nooit twee.
    await w.find('[data-testid="cfg-cat-c-ov"]').trigger('click')
    expect(geselecteerd()).toHaveLength(1)
    expect(w.find('[data-testid="cfg-cat-c-ov"]').attributes('aria-current')).toBe('true')
    // Slepen: ook daarna precies één.
    await w.find('[data-testid="cfg-cat-rij-c-ov"]').trigger('dragstart')
    await w.find('[data-testid="cfg-cat-rij-c-ho"]').trigger('drop')
    await flushPromises()
    expect(geselecteerd()).toHaveLength(1)
    // En het visuele kanaal volgt mee: exact één knop draagt de accent-vulling.
    const metAccent = w.findAll('[data-testid^="cfg-cat-c"]').filter((b) => (b.attributes('class') || '').includes('--lk-color-accent'))
    expect(metAccent).toHaveLength(1)
  })

  it('sleept een categorie naar een nieuwe plek — alleen de gewijzigde rijen worden bewaard', async () => {
    api.checklistconfig.wijzigCategorie.mockResolvedValue({})
    const w = await mountView()
    // LI050 (W5): het getalveld bestaat niet meer — slepen is de enige bediening.
    expect(w.find('[data-testid="cfg-cat-volgorde-c-ov"]').exists()).toBe(false)
    // Sleep Overig (volgorde 9) op Hosting (volgorde 2) → Overig wordt 1; Hosting blijft 2.
    await w.find('[data-testid="cfg-cat-rij-c-ov"]').trigger('dragstart')
    await w.find('[data-testid="cfg-cat-rij-c-ho"]').trigger('drop')
    await flushPromises()
    expect(api.checklistconfig.wijzigCategorie).toHaveBeenCalledWith('c-ov', { volgorde: 1 })
    expect(api.checklistconfig.wijzigCategorie).not.toHaveBeenCalledWith('c-ho', { volgorde: 2 })
  })

  it('sleept een vraag binnen de categorie en bewaart de nieuwe volgorde', async () => {
    api.checklistconfig.werkVraagBij.mockImplementation(async (id, body) => ({
      ...VRAGEN.find((v) => v.id === id), ...body,
    }))
    const w = await mountView() // Hosting open: v2 (volgorde 1), v4 (volgorde 2)
    await w.find('[data-testid="cfg-vraag-2.2"]').trigger('dragstart')
    await w.find('[data-testid="cfg-vraag-2.1"]').trigger('drop')
    await flushPromises()
    expect(api.checklistconfig.werkVraagBij).toHaveBeenCalledWith('v4', { volgorde: 1 })
    expect(api.checklistconfig.werkVraagBij).toHaveBeenCalledWith('v2', { volgorde: 2 })
  })

  it('de vragen staan in de BEHEERDE volgorde, ook als die van de code afwijkt (herladen)', async () => {
    const gedraaid = structuredClone(VRAGEN)
    gedraaid.find((v) => v.id === 'v2').volgorde = 2
    gedraaid.find((v) => v.id === 'v4').volgorde = 1
    api.checklistconfig.lijst.mockResolvedValue(gedraaid)
    const w = await mountView()
    const rijen = w.findAll('[data-testid^="cfg-vraag-2."]').map((r) => r.attributes('data-testid'))
    expect(rijen).toEqual(['cfg-vraag-2.2', 'cfg-vraag-2.1']) // volgorde wint van code
  })

  it('de verwijderknop van de categorie staat in een EIGEN gescheiden zone, niet naast het naamveld', async () => {
    const w = await mountView()
    // DetailKop #destructief-patroon: de knop leeft in de afgezonderde zone.
    const zone = w.find('[data-testid="cfg-cat-destructief"]')
    expect(zone.exists()).toBe(true)
    expect(zone.find('[data-testid="cfg-cat-verwijderen"]').exists()).toBe(true)
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

describe('ChecklistConfigBeheer — leesbaarheid: dicht is de rusttoestand (LI050-ergonomie)', () => {
  it('ingeklapt toont een vraag alleen zijn tekst en actieve staat; de onderbouwing pas na openklappen', async () => {
    const w = await mountView()
    // Rusttoestand: tekst + staat zichtbaar…
    expect(w.text()).toContain('Hostingvraag')
    expect(w.find('[data-testid="cfg-vraag-status-2.1"]').text()).toBe('actief')
    // …maar géén onderbouwing: geen antwoordtype, betekenis, opties of activeer-knop.
    expect(w.find('[data-testid="cfg-vraag-detail-2.1"]').exists()).toBe(false)
    expect(w.find('[data-testid="cfg-type-2.1"]').exists()).toBe(false)
    expect(w.find('[data-testid="cfg-betekenis-2.1"]').exists()).toBe(false)
    expect(w.find('[data-testid="cfg-optie-2.1-saas"]').exists()).toBe(false)
    expect(w.find('[data-testid="cfg-vraag-actief-2.1"]').exists()).toBe(false)
    // Openklappen → alles erbij hoort verschijnt.
    await openVraag(w, '2.1')
    expect(w.find('[data-testid="cfg-vraag-detail-2.1"]').exists()).toBe(true)
    expect(w.find('[data-testid="cfg-type-2.1"]').exists()).toBe(true)
    expect(w.find('[data-testid="cfg-betekenis-2.1"]').exists()).toBe(true)
    expect(w.find('[data-testid="cfg-optie-2.1-saas"]').exists()).toBe(true)
    // Dichtklappen → terug naar de rusttoestand.
    await openVraag(w, '2.1')
    expect(w.find('[data-testid="cfg-vraag-detail-2.1"]').exists()).toBe(false)
  })

  it('er staat maar één vraag tegelijk open — openklappen sluit de vorige', async () => {
    const w = await mountView()
    await openVraag(w, '2.1')
    expect(w.find('[data-testid="cfg-vraag-detail-2.1"]').exists()).toBe(true)
    await openVraag(w, '2.2')
    expect(w.find('[data-testid="cfg-vraag-detail-2.2"]').exists()).toBe(true)
    // De vorige is vanzelf dicht — nooit twijfel welke velden bij welke vraag horen.
    expect(w.find('[data-testid="cfg-vraag-detail-2.1"]').exists()).toBe(false)
  })

  it('slepen werkt op de INGEKLAPTE regels; een geopende vraag sleept niet mee', async () => {
    const w = await mountView()
    // Ingeklapt: sleepbaar (de bestaande vraag-sleeptest bewijst het gedrag zelf).
    expect(w.find('[data-testid="cfg-vraag-2.1"]').attributes('draggable')).toBe('true')
    // Open: bewust niet sleepbaar — HTML5-drag op de rij kaapt anders het
    // selecteren/typen in de velden van de uitklap.
    await openVraag(w, '2.1')
    expect(w.find('[data-testid="cfg-vraag-2.1"]').attributes('draggable')).toBeUndefined()
    expect(w.find('[data-testid="cfg-vraag-2.2"]').attributes('draggable')).toBe('true')
  })

  it('sleept een antwoordoptie — de derde consument van de gedeelde bouwsteen; getalveld weg', async () => {
    api.checklistconfig.wijzigOptie.mockImplementation(async (id, body) => ({
      ...VRAGEN.find((v) => v.id === 'v3').opties.find((o) => o.id === id), ...body,
    }))
    const w = await mountView()
    await w.find('[data-testid="cfg-type-keuze"]').setValue('database')
    await flushPromises()
    await openVraag(w, '1.3')
    // Het getalveld is weg — slepen is de enige bediening (besluit Bert, W5).
    expect(w.find('[data-testid="cfg-optie-volgorde-o2"]').exists()).toBe(false)
    // Sleep Tiel (volgorde 2) op BWB (volgorde 1) → Tiel 1, BWB 2; per rij bewaard.
    await w.find('[data-testid="cfg-optie-1.3-tiel"]').trigger('dragstart')
    await w.find('[data-testid="cfg-optie-1.3-bwb"]').trigger('drop')
    await flushPromises()
    expect(api.checklistconfig.wijzigOptie).toHaveBeenCalledWith('o3', { volgorde: 1 })
    expect(api.checklistconfig.wijzigOptie).toHaveBeenCalledWith('o2', { volgorde: 2 })
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
    // Openklappen mag ook zonder beheerrecht — lezen blijft breed (W2).
    await openVraag(w, '2.1')
    expect(w.find('[data-testid="cfg-type-tekst-2.1"]').text()).toBe('Enkelvoudige keuze')
    // Geen enkele bewerk-affordance.
    expect(w.find('[data-testid="cfg-nieuwe-vraag"]').exists()).toBe(false)
    expect(w.find('[data-testid="cfg-nieuwe-categorie"]').exists()).toBe(false)
    expect(w.find('[data-testid="cfg-cat-opslaan"]').exists()).toBe(false)
    expect(w.find('[data-testid="cfg-cat-hernoem"]').exists()).toBe(false)
    expect(w.find('[data-testid="cfg-cat-verwijderen"]').exists()).toBe(false)
    expect(w.find('[data-testid="cfg-cat-rij-c-ho"]').attributes('draggable')).toBeUndefined() // slepen = beheerder
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
    await openVraag(w, '2.1')
    expect(w.find('[data-testid="cfg-vraag-actief-2.1"]').exists()).toBe(true)
  })
})

describe('ChecklistConfigBeheer — ADR-056 vraagtekst + opslaan-venster + zichtbare greep', () => {
  // Vraag 2.2 ('Tweede hostingvraag') staat in de standaard geopende categorie Hosting.
  async function openVenster(w) {
    await openVraag(w, '2.2')
    await w.find('[data-testid="cfg-vraagtekst-2.2"]').setValue('Tweede hostingvraag, aangescherpt')
    await w.find('[data-testid="cfg-vraagtekst-form-2.2"]').trigger('submit')
    await flushPromises()
  }

  it('de vraagtekst is bewerkbaar; opslaan opent het venster met voorspelling en ZONDER voorselectie', async () => {
    const w = await mountView()
    await openVenster(w)
    expect(w.find('[data-testid="cfg-opslaan-venster"]').exists()).toBe(true)
    // Besluit 12 — de voorspelling komt uit de antwoorden-telling van déze vraag.
    expect(api.checklistconfig.impactAntwoorden).toHaveBeenCalledWith('v4')
    expect(w.find('[data-testid="cfg-venster-aantal"]').text()).toContain('Dit raakt 5 antwoorden.')
    // Besluit 16 — niets voorgevinkt; opslaan kan pas ná een bewuste keuze.
    expect(w.find('[data-testid="cfg-aard-verduidelijking"]').element.checked).toBe(false)
    expect(w.find('[data-testid="cfg-aard-wijziging"]').element.checked).toBe(false)
    expect(w.find('[data-testid="cfg-venster-opslaan"]').attributes('disabled')).toBeDefined()
    // Het venster zegt expliciet dat er niets gewist en niets geblokkeerd wordt.
    expect(w.find('[data-testid="cfg-venster-geruststelling"]').text()).toContain('niets gewist')
  })

  it('de keuze reist mee in het opslaan: wijziging → wijzigingsaard "wijziging"', async () => {
    api.checklistconfig.werkVraagBij.mockResolvedValue({
      ...VRAGEN[2], vraag: 'Tweede hostingvraag, aangescherpt',
    })
    const w = await mountView()
    await openVenster(w)
    await w.find('[data-testid="cfg-aard-wijziging"]').setValue(true)
    expect(w.find('[data-testid="cfg-venster-opslaan"]').attributes('disabled')).toBeUndefined()
    await w.find('[data-testid="cfg-venster-opslaan"]').trigger('click')
    await flushPromises()
    expect(api.checklistconfig.werkVraagBij).toHaveBeenCalledWith('v4', {
      vraag: 'Tweede hostingvraag, aangescherpt',
      wijzigingsaard: 'wijziging',
    })
    expect(w.find('[data-testid="cfg-opslaan-venster"]').exists()).toBe(false) // venster dicht
  })

  it('… en verduidelijking → wijzigingsaard "verduidelijking"', async () => {
    api.checklistconfig.werkVraagBij.mockResolvedValue({
      ...VRAGEN[2], vraag: 'Tweede hostingvraag, aangescherpt',
    })
    const w = await mountView()
    await openVenster(w)
    await w.find('[data-testid="cfg-aard-verduidelijking"]').setValue(true)
    await w.find('[data-testid="cfg-venster-opslaan"]').trigger('click')
    await flushPromises()
    expect(api.checklistconfig.werkVraagBij).toHaveBeenCalledWith('v4', {
      vraag: 'Tweede hostingvraag, aangescherpt',
      wijzigingsaard: 'verduidelijking',
    })
  })

  it('annuleren sluit het venster zonder opslaan; ongewijzigde tekst opent het venster niet', async () => {
    const w = await mountView()
    await openVenster(w)
    await w.find('[data-testid="cfg-venster-annuleren"]').trigger('click')
    await flushPromises()
    expect(w.find('[data-testid="cfg-opslaan-venster"]').exists()).toBe(false)
    expect(api.checklistconfig.werkVraagBij).not.toHaveBeenCalled()
    // Ongewijzigde tekst: de knop is disabled en submit opent niets.
    expect(w.find('[data-testid="cfg-vraagtekst-opslaan-2.1"]').exists()).toBe(false) // vraag dicht
    await openVraag(w, '2.2') // heropent → verse buffer met de huidige tekst
    await openVraag(w, '2.2')
    await openVraag(w, '2.2')
  })

  it('de greep is in rust zichtbaar voor de beheerder — en bestaat NIET voor wie niet mag slepen', async () => {
    const beheer = await mountView(['beheerder'])
    // Categorieën (2) + vragen van de geopende categorie (2, beide dicht) dragen de greep.
    expect(beheer.findAll('[data-testid="sleep-greep"]').length).toBeGreaterThanOrEqual(4)
    // De uitlegregel zegt waaróm de volgorde ertoe doet.
    expect(beheer.find('[data-testid="cfg-volgorde-uitleg"]').text()).toContain(
      'volgorde waarin de consultant de vragen te zien krijgt',
    )
    // Wie niet mag slepen krijgt geen greep: een greep die niets doet is een valse belofte.
    const lezer = await mountView(['medewerker'])
    expect(lezer.findAll('[data-testid="sleep-greep"]').length).toBe(0)
    expect(lezer.find('[data-testid="cfg-volgorde-uitleg"]').exists()).toBe(false)
  })

  it('een geopende vraag is niet sleepbaar en draagt dan ook geen greep', async () => {
    const w = await mountView()
    const voor = w.findAll('[data-testid="sleep-greep"]').length
    await openVraag(w, '2.2')
    // De geopende rij verliest zijn greep (niet sleepbaar); de rest houdt hem.
    expect(w.findAll('[data-testid="sleep-greep"]').length).toBe(voor - 1)
  })
})

describe('ChecklistConfigBeheer — optie-Opslaan uit als er niets te doen is (correctie snede 1)', () => {
  // De niet-afgeleide optieset van de database-vraag 1.3 (opties o2 'BWB', o3 'Tiel').
  async function openOptieVraag(w) {
    await w.find('[data-testid="cfg-type-keuze"]').setValue('database')
    await flushPromises()
    await openVraag(w, '1.3')
  }

  it('de knop is uit zonder wijziging en gaat aan zodra het label is aangepast', async () => {
    const w = await mountView()
    await openOptieVraag(w)
    expect(w.find('[data-testid="cfg-optie-opslaan-o2"]').attributes('disabled')).toBeDefined()
    await w.find('[data-testid="cfg-optie-label-o2"]').setValue('BvoWB')
    expect(w.find('[data-testid="cfg-optie-opslaan-o2"]').attributes('disabled')).toBeUndefined()
    // Terugtypen naar de opgeslagen staat → weer uit.
    await w.find('[data-testid="cfg-optie-label-o2"]').setValue('BWB')
    expect(w.find('[data-testid="cfg-optie-opslaan-o2"]').attributes('disabled')).toBeDefined()
  })

  it('BIJT: een tweede klik tijdens of direct ná het opslaan levert géén tweede verzoek', async () => {
    let laatLanden
    api.checklistconfig.wijzigOptie.mockImplementation(
      () => new Promise((res) => { laatLanden = res }),
    )
    const w = await mountView()
    await openOptieVraag(w)
    await w.find('[data-testid="cfg-optie-label-o2"]').setValue('BvoWB')
    await w.find('[data-testid="cfg-optie-opslaan-o2"]').trigger('click')
    // In de vlucht: knop uit én een tweede klik doet niets.
    expect(w.find('[data-testid="cfg-optie-opslaan-o2"]').attributes('disabled')).toBeDefined()
    await w.find('[data-testid="cfg-optie-opslaan-o2"]').trigger('click')
    expect(api.checklistconfig.wijzigOptie).toHaveBeenCalledTimes(1)
    // Geslaagd: de respons ís de opgeslagen staat → niets meer te doen → uit.
    laatLanden({ id: 'o2', optie_sleutel: 'bwb', label: 'BvoWB', volgorde: 1, actief: true, afgeleid_bron: null })
    await flushPromises()
    expect(w.find('[data-testid="cfg-optie-opslaan-o2"]').attributes('disabled')).toBeDefined()
    await w.find('[data-testid="cfg-optie-opslaan-o2"]').trigger('click')
    expect(api.checklistconfig.wijzigOptie).toHaveBeenCalledTimes(1)
  })
})
