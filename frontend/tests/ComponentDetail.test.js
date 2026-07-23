/** Tests — ComponentDetail (detail + Opbouw + Contracten; ADR-021 Fase D, CD054b). */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'

vi.mock('@/api', () => ({
  api: {
    componenten: {
      haal: vi.fn(),
      structuur: vi.fn(),
      contracten: vi.fn(),
      opties: vi.fn(),
      verwijder: vi.fn(),
      startBeoordeling: vi.fn(),
    },
    relaties: { maak: vi.fn(), werkBij: vi.fn(), verwijder: vi.fn() },
    componentContracten: { maak: vi.fn(), werkBij: vi.fn(), verwijder: vi.fn() },
    contractconfig: { opties: vi.fn() },
    contracten: { lijst: vi.fn() },
    // ADR-022 Fase E — ChecklistscoreSectie doet bij mount API-calls; mocken zodat
    // de meegerenderde sectie de overige asserts niet laat klappen.
    checklistvragen: { lijst: vi.fn() },
    checklistscores: { lijst: vi.fn(), maak: vi.fn(), werkBij: vi.fn(), opties: vi.fn() },
    // F-1-vervolg — BlokkadeSectie (met herkomst-kolom) komt mee bij checklist_dragend.
    blokkades: { lijst: vi.fn(), opties: vi.fn(), werkBij: vi.fn() },
    // ADR-024 slice 2b — VerantwoordelijkheidSectie laadt bij mount lijst + rollen.
    roltoewijzingen: {
      lijst: vi.fn(() => Promise.resolve([])),
      rollen: vi.fn(() => Promise.resolve([])),
      maak: vi.fn(),
      verwijder: vi.fn(),
    },
    partijen: { lijst: vi.fn(() => Promise.resolve({ items: [] })) },
    // ADR-027 — MigratiegereedheidSectie haalt bij mount de klaarverklaring op.
    klaarverklaringen: {
      lijst: vi.fn(() => Promise.resolve([])),
      maak: vi.fn(),
      wijzigStatus: vi.fn(),
    },
    // ADR-035 — SignaleringBadge laadt bij mount (fail-soft).
    signalering: { badgeComponent: vi.fn(() => Promise.resolve({ kritiek: 0, aandacht: 0 })) },
    // ADR-043 gate 4 — ComponentBedrijfsfunctieSectie ("Waarvoor gebruiken we het") laadt bij mount.
    functievervullingen: {
      componentKoppelingen: vi.fn(() => Promise.resolve([])),
      maak: vi.fn(),
      verwijder: vi.fn(),
      zetOordeel: vi.fn(),
    },
    bedrijfsfuncties: {
      lijst: vi.fn(() => Promise.resolve({ items: [], volgende_cursor: null })),
      haal: vi.fn(),
    },
    // Slice 4c — de lat-leesbron (de aanduiding op de sectiekoppen).
    componentNormen: {
      definitie: vi.fn(() => Promise.resolve([])),
      // LI047 — het open-punten-tabblad laadt bij mount (drie lege blokken volstaan hier).
      openPunten: vi.fn(() => Promise.resolve({
        component_id: 'db-1',
        moet_nog: { aantal: 0, punten: [] },
        netjes: { aantal: 0, punten: [] },
        valt_op: { aantal: 0, punten: [] },
        klaarverklaring: null,
      })),
    },
  },
}))

// LI035 succes-standaard — helper gemockt zodat de succes-flow assertbaar is.
vi.mock('@/meldingen', () => ({ toastSucces: vi.fn() }))

import { api } from '@/api'
import { toastSucces } from '@/meldingen'
// LI048 — de ketentest loopt door de échte detail-ingang (niet gemockt), zoals de kaart en het
// open-punten-overzicht hem gebruiken: aanleiding → route → scherm → de regel die de mens leest.
import { detailRoute } from '@/detailIngang'
import ComponentDetail from '@modules/bwb_ontvlechting/frontend/views/ComponentDetail.vue'
import ChecklistscoreSectie from '@modules/bwb_ontvlechting/frontend/views/ChecklistscoreSectie.vue'
import { useAuthStore } from '@/store/auth'

const ID = 'db-1'

function maakRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/componenten/:id', name: 'component-detail', component: ComponentDetail, props: true },
      { path: '/componenten/:id/bewerken', name: 'component-bewerken', component: { template: '<div/>' } },
      { path: '/componenten', name: 'component-lijst', component: { template: '<div/>' } },
      { path: '/applicaties/:id', name: 'applicatie-detail', component: { template: '<div/>' } },
      { path: '/contracten/:id', name: 'contract-detail', component: { template: '<div/>' } },
      { path: '/landschapskaart', name: 'landschapskaart', component: { template: '<div/>' } },
      // ADR-042 4b — de processectie linkt naar proces-detail/-lijst; het
      // verantwoordelijk-blok/VerantwoordelijkheidSectie naar partij-detail.
      { path: '/processen', name: 'proces-lijst', component: { template: '<div/>' } },
      { path: '/processen/:id', name: 'proces-detail', component: { template: '<div/>' } },
      { path: '/partijen/:id', name: 'partij-detail', component: { template: '<div/>' } },
    ],
  })
}

async function mountDetail({ rollen = ['beheerder'], query = '' } = {}) {
  const router = maakRouter()
  await router.push(`/componenten/db-1${query}`)
  await router.isReady()
  const pinia = createPinia()
  const auth = useAuthStore(pinia)
  auth.user = { sub: 's', tenant_id: 't', email: 'a@b.nl', roles: rollen }
  const w = mount(ComponentDetail, {
    props: { id: ID },
    attachTo: document.body,
    global: { plugins: [pinia, [PrimeVue, { unstyled: true }], ToastService, router], stubs: { teleport: true } },
  })
  await flushPromises()
  return { w, router }
}

const _component = (over = {}) => ({
  id: ID,
  naam: 'Oracle FIN-DB',
  componenttype: 'database',
  componenttype_label: 'Database',
  hostingmodel: 'on_premise',
  eigenaar_organisatie: 'Gemeente Veldendam',
  eigenaar_naam: null,
  leverancier: 'Oracle',
  beschrijving: null,
  heeft_applicatie_subtype: false,
  checklist_dragend: false,
  // ADR-055 — de catalogus-vlag die het Gebruikersgroepen-tabblad gate't. De basis-fixture is een
  // database: daar wordt niet door mensen mee gewerkt, dus false (spiegelt de echte catalogus).
  ondersteunt_werk: false,
  lifecycle_status: null,
  // ADR-028 — componentclassificatie (rol + BIV, met labels).
  componentrol: 'interne_applicatie',
  rol_label: 'Interne applicatie',
  biv_beschikbaarheid: null,
  biv_beschikbaarheid_label: null,
  biv_integriteit: null,
  biv_integriteit_label: null,
  biv_vertrouwelijkheid: null,
  biv_vertrouwelijkheid_label: null,
  ...over,
})

beforeEach(() => {
  vi.clearAllMocks()
  api.componenten.haal.mockResolvedValue(_component())
  // LI047 — expliciet terugzetten: `clearAllMocks` wist aanroepen maar NIET de implementatie, dus
  // een respons uit een eerdere toets lekt anders door naar de volgende.
  api.componentNormen.openPunten.mockResolvedValue({
    component_id: ID,
    moet_nog: { aantal: 0, punten: [] },
    netjes: { aantal: 0, punten: [] },
    valt_op: { aantal: 0, punten: [] },
    klaarverklaring: null,
  })
  api.componenten.structuur.mockResolvedValue({
    draait_op: [],
    gebruikt_door: [
      {
        structuur_id: 's-1',
        component_id: 'app-9',
        naam: 'Belastingsysteem',
        componenttype: 'applicatie',
        relatietype: 'draait_op',
        relatietype_label: 'Draait op',
        omschrijving: null,
      },
    ],
  })
  api.componenten.contracten.mockResolvedValue([
    {
      koppeling_id: 'k-1',
      contract_id: 'c-1',
      contractnaam: 'Oracle licentie',
      contracttype: 'los_contract',
      leverancier_naam: 'Oracle',
      relatie_rol: 'valt_onder',
      relatie_rol_label: 'Valt onder',
      begindatum: null,
      einddatum: null,
    },
  ])
  api.componenten.opties.mockResolvedValue({ componenttype: [], structuurrelatie_type: [] })
  api.contractconfig.opties.mockResolvedValue({ relatie_rol: [] })
  // ChecklistscoreSectie mount-calls (alleen relevant bij checklist_dragend).
  api.checklistvragen.lijst.mockResolvedValue([])
  api.checklistscores.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
  api.checklistscores.opties.mockResolvedValue({ score: [] })
  // BlokkadeSectie mount-calls (alleen relevant bij checklist_dragend).
  api.blokkades.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
  api.blokkades.opties.mockResolvedValue({ status: ['open', 'in_behandeling', 'opgelost'] })
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('ComponentDetail', () => {
  it('toont velden + type-label en de Opbouw-sectie (beide richtingen)', async () => {
    const { w } = await mountDetail()
    expect(w.find('#detail-titel').text()).toContain('Oracle FIN-DB')
    expect(w.find('[data-testid="detail-type"]').text()).toContain('Database')
    // Opbouw (StructuurSectie-child): "Gebruikt door" toont Belastingsysteem.
    expect(w.find('[data-testid="st-tabel-gebruikt-door"]').text()).toContain('Belastingsysteem')
  })

  it('toont de Contracten-sectie (gegeneraliseerde ContractSectie) met de koppeling', async () => {
    const { w } = await mountDetail()
    expect(w.find('[data-testid="ct-tabel"]').text()).toContain('Oracle licentie')
    expect(api.componenten.contracten).toHaveBeenCalledWith(ID)
  })

  it('ADR-028: toont de rol en BIV — labels waar gezet, "Niet geclassificeerd" waar leeg', async () => {
    api.componenten.haal.mockResolvedValue(
      _component({
        rol_label: 'Externe dataprovider',
        biv_vertrouwelijkheid: 'hoog',
        biv_vertrouwelijkheid_label: 'Hoog',
      }),
    )
    const { w } = await mountDetail()
    expect(w.find('[data-testid="comp-rol"]').text()).toBe('Externe dataprovider')
    expect(w.find('[data-testid="comp-biv-v"]').text()).toBe('Hoog')
    // Leeg aspect toont expliciet "Niet geclassificeerd" (geen leeg vakje).
    expect(w.find('[data-testid="comp-biv-b"]').text()).toBe('Niet geclassificeerd')
    expect(w.find('[data-testid="comp-biv-i"]').text()).toBe('Niet geclassificeerd')
  })

  it('toont de Verantwoordelijkheden-sectie (ADR-024 slice 2b)', async () => {
    const { w } = await mountDetail()
    expect(w.find('[data-testid="vw-sectie"]').exists()).toBe(true)
    expect(api.roltoewijzingen.lijst).toHaveBeenCalledWith({ object_id: ID })
  })

  it('verwijderen met 409 IN_GEBRUIK wordt afgevangen (blijft op het detail)', async () => {
    api.componenten.verwijder.mockRejectedValueOnce({ status: 409, code: 'IN_GEBRUIK', message: 'In gebruik.' })
    const { w, router } = await mountDetail()
    await w.find('[data-testid="verwijder-knop"]').trigger('click')
    await flushPromises()
    await w.find('[data-testid="verwijder-bevestig"]').trigger('click')
    await flushPromises()
    expect(api.componenten.verwijder).toHaveBeenCalledWith(ID)
    expect(router.currentRoute.value.name).toBe('component-detail')
  })

  it('verwijderen lukt → navigeert naar de lijst', async () => {
    api.componenten.verwijder.mockResolvedValueOnce({})
    const { w, router } = await mountDetail()
    await w.find('[data-testid="verwijder-knop"]').trigger('click')
    await flushPromises()
    await w.find('[data-testid="verwijder-bevestig"]').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.name).toBe('component-lijst')
  })

  // ── ADR-022 Fase E: checklist alleen voor checklist-dragende typen ─────────
  it('toont de checklist-sectie bij checklist_dragend === true', async () => {
    api.componenten.haal.mockResolvedValue(_component({ checklist_dragend: true }))
    const { w } = await mountDetail()
    expect(w.find('[data-testid="cs-voortgang"]').exists()).toBe(true)
    // de vragenset wordt op het componenttype gescoped
    expect(api.checklistvragen.lijst).toHaveBeenCalledWith('database')
  })

  it('toont de checklist-sectie NIET bij checklist_dragend === false zónder profiel', async () => {
    const { w } = await mountDetail() // default checklist_dragend: false, lifecycle_status: null
    expect(w.find('[data-testid="cs-voortgang"]').exists()).toBe(false)
    expect(api.checklistvragen.lijst).not.toHaveBeenCalled()
  })

  it('ADR-027: gesloten type MÉT profiel toont de checklist read-only (banner + bewerkbaar=false)', async () => {
    // checklist_dragend=false maar lifecycle_status gezet ⇒ was dragend, nu gesloten → read-only tonen.
    api.componenten.haal.mockResolvedValue(_component({ checklist_dragend: false, lifecycle_status: 'in_inventarisatie' }))
    api.checklistvragen.lijst.mockResolvedValue([
      { id: 1, code: '3.2', categorie_id: 'c3', categorie_naam: 'Data', categorie_volgorde: 3, vraag: 'a', prioriteit: 'hoog' },
    ])
    const { w } = await mountDetail({ rollen: ['medewerker'] })
    expect(w.find('[data-testid="cs-voortgang"]').exists()).toBe(true)
    expect(w.findComponent(ChecklistscoreSectie).props('bewerkbaar')).toBe(false)
    expect(w.find('[data-testid="cs-gesloten"]').exists()).toBe(true)
  })

  // ── ADR-027 (DC015): migratiegereedheid-blok op ComponentDetail ────────────
  it('toont het migratiegereedheid-blok + klaarverklaar-knop bij checklist_dragend (medewerker)', async () => {
    api.componenten.haal.mockResolvedValue(_component({ checklist_dragend: true }))
    const { w } = await mountDetail({ rollen: ['medewerker'] })
    expect(w.find('[data-testid="mg-leesblok"]').exists()).toBe(true)
    expect(w.find('[data-testid="klaarverklaar-knop"]').exists()).toBe(true)
    expect(api.klaarverklaringen.lijst).toHaveBeenCalledWith({ component_id: ID })
  })

  it('toont het migratiegereedheid-blok NIET voor een kaal type zonder profiel', async () => {
    const { w } = await mountDetail() // checklist_dragend: false, lifecycle_status: null
    expect(w.find('[data-testid="mg-leesblok"]').exists()).toBe(false)
    expect(w.find('[data-testid="klaarverklaar-knop"]').exists()).toBe(false)
  })

  it('verbergt de klaarverklaar-knop voor een viewer (blok blijft read-only zichtbaar)', async () => {
    api.componenten.haal.mockResolvedValue(_component({ checklist_dragend: true }))
    const { w } = await mountDetail({ rollen: ['viewer'] })
    expect(w.find('[data-testid="mg-leesblok"]').exists()).toBe(true)
    expect(w.find('[data-testid="klaarverklaar-knop"]').exists()).toBe(false)
  })

  // ── LI046 — tab-aanleiding landt (de keten-variant mét vragen staat in detailIngang.flow.test.js) ──
  it('?tab=gebruik landt op de Gebruik-tab', async () => {
    const { w } = await mountDetail({ query: '?tab=gebruik' })
    expect(w.find('#detailtabs-panel-gebruik').isVisible()).toBe(true)
    expect(w.find('#detailtabs-panel-overzicht').isVisible()).toBe(false)
  })

  // ── LI046 slice 2 — veld-anker (?veld=): landen op het Overzicht bij het veld ──
  it('markeert het veld uit ?veld= in de checklist-markeer-taal, met bewerkknop ernaast', async () => {
    const { w } = await mountDetail({ query: '?veld=eigenaar' })
    const dt = w.find('#veld-eigenaar')
    expect(dt.exists()).toBe(true)
    expect(dt.classes().join(' ')).toContain('bg-[var(--lk-color-accent)]')
    const knop = w.find('[data-testid="veld-bewerk-knop"]')
    expect(knop.exists()).toBe(true)
  })

  it('de veld-markering is zichtbaar voor een viewer, maar zónder bewerkknop', async () => {
    const { w } = await mountDetail({ rollen: ['viewer'], query: '?veld=levensfase' })
    expect(w.find('#veld-levensfase').classes().join(' ')).toContain('bg-[var(--lk-color-accent)]')
    expect(w.find('[data-testid="veld-bewerk-knop"]').exists()).toBe(false)
  })

  it('de markering blijft staan tot "iets doen": bewerkknop opent de overlay en wist hem', async () => {
    const { w } = await mountDetail({ query: '?veld=bedoeling' })
    expect(w.find('#veld-bedoeling').classes().join(' ')).toContain('bg-[var(--lk-color-accent)]')
    await w.find('[data-testid="veld-bewerk-knop"]').trigger('click')
    await flushPromises()
    expect(w.find('#veld-bedoeling').classes().join(' ')).not.toContain('bg-[var(--lk-color-accent)]')
  })

  it('wegklikken (klik op het gemarkeerde veld) wist de markering ook', async () => {
    const { w } = await mountDetail({ query: '?veld=biv' })
    expect(w.find('#veld-biv').classes().join(' ')).toContain('bg-[var(--lk-color-accent)]')
    await w.find('[data-testid="comp-biv"]').trigger('click')
    expect(w.find('#veld-biv').classes().join(' ')).not.toContain('bg-[var(--lk-color-accent)]')
  })

  it('een onbekend ?veld= markeert niets en landt stil bovenaan (besluit 2)', async () => {
    const { w } = await mountDetail({ query: '?veld=onzin' })
    expect(w.find('[data-testid="veld-bewerk-knop"]').exists()).toBe(false)
    for (const veld of ['eigenaar', 'biv', 'levensfase', 'bedoeling', 'beschrijving']) {
      expect(w.find(`#veld-${veld}`).classes().join(' ')).not.toContain('bg-[var(--lk-color-accent)]')
    }
  })

  it('markeert de vraag uit de deep-link-query (blokkadelijst-doorklik, ADR-024-vervolg)', async () => {
    api.componenten.haal.mockResolvedValue(_component({ checklist_dragend: true }))
    api.checklistvragen.lijst.mockResolvedValue([
      { id: 1, code: '3.2', categorie_id: 'c3', categorie_naam: 'Data', categorie_volgorde: 3, vraag: 'a', prioriteit: 'hoog' },
    ])
    const { w } = await mountDetail({ query: '?markeer=3.2' })
    // route.query.markeer → markeerVraagCode → :markeer-code op de sectie (zelfde markeerpad).
    expect(w.findComponent(ChecklistscoreSectie).props('markeerCode')).toBe('3.2')
  })

  // ── F-1-vervolg: blokkades + herkomst-doorklik op ComponentDetail ──────────
  it('toont de blokkade-sectie alleen bij checklist_dragend === true', async () => {
    const { w: zonder } = await mountDetail() // checklist_dragend: false
    expect(zonder.find('[data-testid="bk-tabel"]').exists()).toBe(false)

    api.componenten.haal.mockResolvedValue(_component({ checklist_dragend: true }))
    const { w: met } = await mountDetail()
    expect(met.find('[data-testid="bk-tabel"]').exists()).toBe(true)
  })

  it('herkomst-doorklik markeert de checklist-vraag-rij op hetzelfde component', async () => {
    api.componenten.haal.mockResolvedValue(_component({ checklist_dragend: true }))
    api.checklistvragen.lijst.mockResolvedValue([
      { id: 1, code: '2.7', categorie_id: 'c2', categorie_naam: 'Techniek', categorie_volgorde: 2, vraag: 'Gedeelde infra?', prioriteit: 'hoog' },
    ])
    api.blokkades.lijst.mockResolvedValue({
      items: [{
        id: 'b1', status: 'in_behandeling', toelichting: null, eigenaar: null,
        checklistvraag_id: 1, vraag_code: '2.7', vraag: 'Gedeelde infra?', score: 'deels', categorie_id: 'c2',
      }],
      volgende_cursor: null,
    })
    const { w } = await mountDetail()
    expect(w.find('[data-testid="bk-herkomst-b1"]').exists()).toBe(true)
    await w.find('[data-testid="bk-herkomst-b1"]').trigger('click')
    await flushPromises()
    expect(w.find('[data-testid="cs-rij-2.7"]').classes()).toContain('bg-[var(--lk-color-accent)]')
  })

  // ── ADR-022 Fase E: "Start beoordeling" (concept → in_inventarisatie) ──────
  it('toont de Start-beoordeling-knop bij checklist_dragend:true + concept + bewerk-rechten', async () => {
    api.componenten.haal.mockResolvedValue(_component({ checklist_dragend: true, lifecycle_status: 'concept' }))
    const { w } = await mountDetail()
    expect(w.find('[data-testid="start-beoordeling-knop"]').exists()).toBe(true)
    // lifecycle-status-Tag wordt getoond zodra lifecycle_status gezet is
    expect(w.find('[data-testid="detail-status"]').text()).toContain('Concept')
  })

  it('verbergt de Start-beoordeling-knop bij een andere status dan concept', async () => {
    api.componenten.haal.mockResolvedValue(_component({ checklist_dragend: true, lifecycle_status: 'in_inventarisatie' }))
    const { w } = await mountDetail()
    expect(w.find('[data-testid="start-beoordeling-knop"]').exists()).toBe(false)
  })

  it('verbergt de Start-beoordeling-knop bij checklist_dragend:false', async () => {
    api.componenten.haal.mockResolvedValue(_component({ checklist_dragend: false, lifecycle_status: 'concept' }))
    const { w } = await mountDetail()
    expect(w.find('[data-testid="start-beoordeling-knop"]').exists()).toBe(false)
  })

  it('verbergt de Start-beoordeling-knop zonder bewerk-rechten', async () => {
    api.componenten.haal.mockResolvedValue(_component({ checklist_dragend: true, lifecycle_status: 'concept' }))
    const { w } = await mountDetail({ rollen: ['lezer'] })
    expect(w.find('[data-testid="start-beoordeling-knop"]').exists()).toBe(false)
  })

  it('klik op Start beoordeling roept de API aan en herlaadt', async () => {
    api.componenten.haal.mockResolvedValueOnce(_component({ checklist_dragend: true, lifecycle_status: 'concept' }))
    api.componenten.startBeoordeling.mockResolvedValueOnce(
      _component({ checklist_dragend: true, lifecycle_status: 'in_inventarisatie' }),
    )
    api.componenten.haal.mockResolvedValue(_component({ checklist_dragend: true, lifecycle_status: 'in_inventarisatie' }))
    const { w } = await mountDetail()
    await w.find('[data-testid="start-beoordeling-knop"]').trigger('click')
    await flushPromises()
    expect(api.componenten.startBeoordeling).toHaveBeenCalledWith(ID)
    // na herladen is de status gewijzigd → knop weg
    expect(w.find('[data-testid="start-beoordeling-knop"]').exists()).toBe(false)
  })

  it('applicatie-subtype: geen aparte-hint, wél bewerken/verwijderen + applicatie-tabs (LI059)', async () => {
    api.componenten.haal.mockResolvedValue(
      _component({ componenttype: 'applicatie', componenttype_label: 'Applicatie', heeft_applicatie_subtype: true, ondersteunt_werk: true }),
    )
    const { w } = await mountDetail()
    // De verwijzing naar een apart ApplicatieDetail bestaat niet meer.
    expect(w.find('[data-testid="detail-subtype-hint"]').exists()).toBe(false)
    // Beheer gebeurt hier: bewerken/verwijderen zijn beschikbaar (beheerder).
    expect(w.find('[data-testid="bewerken-knop"]').exists()).toBe(true)
    expect(w.find('[data-testid="verwijder-knop"]').exists()).toBe(true)
    // Applicatie-eigen tabs verschijnen (conditioneel op het subtype).
    const tabtekst = w.find('[data-testid="detailtabs"]').exists()
      ? w.find('[data-testid="detailtabs"]').text()
      : w.text()
    expect(tabtekst).toContain('Datatypes')
    expect(tabtekst).toContain('Gebruikersgroepen')
    expect(tabtekst).toContain('Koppelingen')
  })

  // ── ADR-055 — "wie gebruikt dit" hoort bij élk component waarmee mensen werken ──────────────
  const _tabtekst = (w) =>
    w.find('[data-testid="detailtabs"]').exists() ? w.find('[data-testid="detailtabs"]').text() : w.text()

  it('ADR-055: een fileshare krijgt Gebruikersgroepen — de verfijning hangt aan werk, niet aan het type applicatie', async () => {
    api.componenten.haal.mockResolvedValue(
      _component({ componenttype: 'fileshare', componenttype_label: 'Fileshare',
                   heeft_applicatie_subtype: false, ondersteunt_werk: true }),
    )
    const { w } = await mountDetail()
    const tabtekst = _tabtekst(w)
    // Dit is HET geval uit ADR-055: de gedeelde G-schijf waar een afdeling op werkt.
    expect(tabtekst).toContain('Gebruikersgroepen')
    // Datatypes blijft applicatie-eigen — de verbreding is gericht, niet alles-open.
    expect(tabtekst).not.toContain('Datatypes')
    // LI047 — Koppelingen is inmiddels wél component-breed (zie de eigen toets hieronder).
    expect(tabtekst).toContain('Koppelingen')
  })

  // ── LI047 snede 2 — de ingang in de kop ────────────────────────────────────────────────────
  const _openPunten = (moetNog = []) => ({
    component_id: ID,
    moet_nog: { aantal: moetNog.length, punten: moetNog.map((f) => ({ feit: f, route: null })) },
    netjes: { aantal: 0, punten: [] },
    valt_op: { aantal: 0, punten: [] },
    klaarverklaring: null,
  })

  it('LI048: het getal in het tablabel is exact het aantal regels in "Dit moet nog"', async () => {
    // Checklist-dragend, want alléén dan heeft Beoordeling twee onderdelen en dus een sub-rij
    // (regel 2). De basis-fixture is een database zónder checklist — daar is Open punten het
    // enige onderdeel en leidt de groepstab er direct naartoe.
    api.componenten.haal.mockResolvedValue(_component({ checklist_dragend: true }))
    api.componentNormen.openPunten.mockResolvedValue(_openPunten(['biv', 'contract', 'bedoeling']))
    const { w } = await mountDetail()
    // Eén bron: de groepstab, het sub-tabblad én de lijst lezen hetzelfde object. Een tabblad dat
    // "4" zegt terwijl het paneel drie regels toont, liegt zonder dat iemand het merkt. Dezelfde
    // waarheid op twee diepten is géén dubbeling — twee berekeningen zouden dat wél zijn.
    expect(w.find('[data-testid="detailtabs-tab-beoordeling"]').text()).toBe('Beoordeling (3)')
    await w.find('[data-testid="detailtabs-tab-beoordeling"]').trigger('click')
    await flushPromises()
    expect(w.find('[data-testid="subtabs-tab-open-punten"]').text()).toBe('Open punten (3)')
    expect(w.findAll('[data-testid="op-lijst-moet_nog"] > li')).toHaveLength(3)
  })

  it('LI048 besluit 3: bij nul dragen beide diepten wél een getal', async () => {
    // Herziet bewust de LI047-regel "een teller zwijgt bij nul" voor déze plek: "geen getal"
    // leest niet als nul maar als "dit telt niets" — en dat verschil is onzichtbaar.
    api.componenten.haal.mockResolvedValue(_component({ checklist_dragend: true }))
    api.componentNormen.openPunten.mockResolvedValue(_openPunten([]))
    const { w } = await mountDetail()
    expect(w.find('[data-testid="detailtabs-tab-beoordeling"]').text()).toBe('Beoordeling (0)')
    await w.find('[data-testid="detailtabs-tab-beoordeling"]').trigger('click')
    await flushPromises()
    expect(w.find('[data-testid="subtabs-tab-open-punten"]').text()).toBe('Open punten (0)')
  })

  it('LI048: de Open punten-knop in de detailkop bestaat niet meer — één ingang', async () => {
    api.componentNormen.openPunten.mockResolvedValue(_openPunten(['biv']))
    const { w } = await mountDetail()
    expect(w.find('[data-testid="open-punten-knop"]').exists()).toBe(false)
    expect(w.find('[data-testid="open-punten-teller"]').exists()).toBe(false)
    // In de kop staan alleen nog acties óp het component en wegwijzers naar buiten.
    expect(w.find('[data-testid="detail-kop-acties"]').text()).not.toContain('Open punten')
  })

  it('LI048: het tabblad opent het paneel en de plek leeft in het adres', async () => {
    api.componenten.haal.mockResolvedValue(_component({ checklist_dragend: true }))
    api.componentNormen.openPunten.mockResolvedValue(_openPunten(['biv']))
    const { w, router } = await mountDetail()
    await w.find('[data-testid="detailtabs-tab-beoordeling"]').trigger('click')
    await flushPromises()
    expect(w.find('[data-testid="open-punten-sectie"]').isVisible()).toBe(true)
    // Deelbaar en herstelbaar: het adres spreekt de ONDERDEEL-taal, niet de groep — zo blijft
    // elke bestaande link letterlijk werken (snede 2b).
    expect(router.currentRoute.value.query.tab).toBe('open-punten')
    // Een echt tabpaneel, gekoppeld aan het tabblad dat het opent — hier het SUB-tabblad, want
    // deze groep heeft er een (was `role="region"` toen het helemaal geen tab had).
    const paneel = w.find('[data-testid="panel-open-punten"]')
    expect(paneel.attributes('role')).toBe('tabpanel')
    expect(paneel.attributes('aria-labelledby')).toBe('subtabs-tab-open-punten')
  })

  it('LI047: het rode signaleringsbolletje is van het componentdetailscherm verdwenen', async () => {
    const { w } = await mountDetail()
    // Twee tellers die verschillende getallen roepen over hetzelfde component = een tweede
    // waarheid. Het bolletje telde anders (geen bewuste vaststelling, verantwoordelijke dubbel)
    // en klikte nergens heen.
    expect(w.find('[data-testid="signalering-badge"]').exists()).toBe(false)
    expect(api.signalering.badgeComponent).not.toHaveBeenCalled()
  })

  it('LI047: elk componenttype houdt Koppelingen — nu onder Samenhang', async () => {
    // De koppelingen zijn er echt — een koppelvlak dat naar een fileshare schrijft, applicaties
    // die op een databaseserver aansluiten. Zonder plek droeg het open-punten-overzicht een regel
    // die de gebruiker nooit kon wegwerken. De hergroepering (2b) mag dat niet ongedaan maken.
    for (const type of ['applicatie', 'database', 'fileshare', 'saas_dienst', 'server_compute',
                        'client_software', 'integratievoorziening', 'landelijke_voorziening']) {
      api.componenten.haal.mockResolvedValue(
        _component({ componenttype: type, componenttype_label: type,
                     heeft_applicatie_subtype: type === 'applicatie' }),
      )
      const { w } = await mountDetail()
      await w.find('[data-testid="detailtabs-tab-samenhang"]').trigger('click')
      await flushPromises()
      expect(w.find('[data-testid="subtabs-tab-koppelingen"]').exists(), `${type} mist Koppelingen`).toBe(true)
    }
  })

  // ── LI048 snede 2b — vijf groepen, nooit meer ───────────────────────────────────────────────
  // De TYPEN-matrix dekt alle acht componenttypen: elk met zijn eigen combinatie van
  // checklist-dragend / ondersteunt-werk / subtype, dus elk met een ander aantal onderdelen
  // per groep. Zo bewijst één matrix dat de indeling niet toevallig voor één type klopt.
  const TYPEN = [
    ['applicatie', true, true], ['database', true, false], ['server_compute', true, false],
    ['client_software', false, true], ['saas_dienst', false, true],
    ['integratievoorziening', true, false], ['fileshare', false, true],
    ['landelijke_voorziening', true, true],
  ]
  const _zetType = (type, dragend, werk) =>
    api.componenten.haal.mockResolvedValue(
      _component({ componenttype: type, componenttype_label: type,
                   heeft_applicatie_subtype: type === 'applicatie',
                   checklist_dragend: dragend, ondersteunt_werk: werk }),
    )
  const _hoofdrij = (w) => w.findAll('[role="tablist"]')[0].findAll('[role="tab"]')

  it('LI048 2b: de hoofdrij draagt NOOIT meer dan vijf tabbladen — op elk componenttype', async () => {
    // Dertien tabbladen liepen over naar een tweede regel; het gekozen tabblad hing dan los boven
    // een vlak dat pas onder regel twee begon. Vijf passen altijd. Deze toets valt om zodra
    // iemand er een zesde groep bij zet — precies de sluipweg terug naar de oude situatie.
    for (const [type, dragend, werk] of TYPEN) {
      _zetType(type, dragend, werk)
      const { w } = await mountDetail()
      const rij = _hoofdrij(w)
      expect(rij.length, `${type}: ${rij.length} tabbladen in de hoofdrij`).toBeLessThanOrEqual(5)
      expect(rij[0].attributes('id'), `${type}`).toBe('detailtabs-tab-overzicht')
      // En de kopknop uit snede 1 is overal weg — niet alleen bij het type dat je toevallig opende.
      expect(w.find('[data-testid="open-punten-knop"]').exists(), `${type} heeft nog de knop`).toBe(false)
    }
  })

  it('LI048 2b regel 1: een groep zonder beschikbare onderdelen verschijnt niet', async () => {
    // Geen tabblad dat naar niets leidt. Bewijs met een gemeten geval: een niet-checklist-dragend
    // type zónder werk-vlag mist zowel checklist als gebruikersgroepen als datatypes — de groepen
    // die daardoor leeg zouden vallen, staan er niet.
    _zetType('database', false, false)
    const { w } = await mountDetail()
    const ids = _hoofdrij(w).map((t) => t.attributes('id'))
    for (const id of ids) {
      await w.find(`[data-testid="${id}"]`).trigger('click')
      await flushPromises()
      // Elk groepstabblad leidt naar echte inhoud: er is altijd een zichtbaar paneel.
      expect(w.findAll('[role="tabpanel"]').filter((p) => p.isVisible()).length,
             `${id} leidt naar geen zichtbaar paneel`).toBeGreaterThan(0)
    }
  })

  it('LI048 2b regel 2: een groep met één onderdeel toont geen sub-rij', async () => {
    // Een keuzerij met één keuze is geen keuze. Twee echte gevallen:
    // (a) Overzicht heeft altijd precies één onderdeel;
    // (b) Beoordeling valt terug op alléén Open punten zodra het type geen checklist draagt.
    // NB: tel op de sub-rij zélf (`subtabs-*`), niet op alle `role="tablist"` — het open-punten-
    // paneel draagt zijn eigen blokken-rij, die altijd gemount is (`v-show`) en dus meetelt.
    _zetType('fileshare', false, true) // niet checklist-dragend
    const { w } = await mountDetail()
    const geenSubRij = (waar) =>
      expect(w.findAll('[data-testid^="subtabs-tab-"]').length, `${waar} toont een sub-rij`).toBe(0)
    geenSubRij('Overzicht')

    await w.find('[data-testid="detailtabs-tab-beoordeling"]').trigger('click')
    await flushPromises()
    geenSubRij('Beoordeling met één onderdeel')
    expect(w.find('[data-testid="open-punten-sectie"]').isVisible()).toBe(true)
    // Zónder sub-tabblad labelt het paneel naar het GROEPStabblad — nooit naar een id dat niet bestaat.
    expect(w.find('[data-testid="panel-open-punten"]').attributes('aria-labelledby'))
      .toBe('detailtabs-tab-beoordeling')
  })

  it('LI048 2b regel 4: een groep openen kiest het eerste beschikbare onderdeel', async () => {
    _zetType('applicatie', true, true)
    const { w, router } = await mountDetail()
    const EERSTE = {
      beoordeling: 'open-punten', 'wat-het-doet': 'bedrijfsfunctie',
      samenhang: 'koppelingen', afspraken: 'contracten',
    }
    for (const [groep, onderdeel] of Object.entries(EERSTE)) {
      await w.find(`[data-testid="detailtabs-tab-${groep}"]`).trigger('click')
      await flushPromises()
      expect(router.currentRoute.value.query.tab, `${groep} opent niet op ${onderdeel}`).toBe(onderdeel)
      expect(w.find(`[data-testid="subtabs-tab-${onderdeel}"]`).attributes('aria-selected')).toBe('true')
    }
  })

  // ── LI048 — de invariant: een tabrij draagt ALTIJD precies één keuze ───────────────────────
  // Dit is de vangrail onder besluit 1. Hij telt over ÉLKE tablist op het scherm (top,
  // checklist-categorieën, open-punten-blokken) en over elke bereikbare staat. Een toekomstige
  // uitzondering — een tweede `PLEKKEN_ZONDER_TAB`, een `activeTop` buiten `topTabs` — duwt hem
  // om, want dan zakt de telling naar 0. Tekst in een skill houdt dit niet tegen: in LI047 stond
  // de uitzondering netjes beschreven en wás ze precies de klacht.
  const _elkeRijHeeftEenKeuze = (w, waar) => {
    const rijen = w.findAll('[role="tablist"]')
    expect(rijen.length, `${waar}: geen enkele tabrij gevonden`).toBeGreaterThan(0)
    for (const rij of rijen) {
      const tabs = rij.findAll('[role="tab"]')
      if (!tabs.length) continue // een lege rij (categorieën nog niet geladen) is geen fout
      const gekozen = tabs.filter((t) => t.attributes('aria-selected') === 'true')
      expect(gekozen.length,
             `${waar}: ${gekozen.length} gekozen tabbladen in een rij van ${tabs.length}`).toBe(1)
      // De keuze is óók de enige die met Tab bereikbaar is (roving tabindex). Zonder match kreeg
      // ÉLKE tab `-1` en viel de hele rij uit de toetsenbordvolgorde — de a11y-fout onder LI047.
      expect(tabs.filter((t) => t.attributes('tabindex') === '0').length,
             `${waar}: rij niet bereikbaar met het toetsenbord`).toBe(1)
    }
  }

  it('LI048: elke tabrij heeft altijd precies één gekozen tabblad — in elke bereikbare staat', async () => {
    api.componenten.haal.mockResolvedValue(_component({ checklist_dragend: true, ondersteunt_werk: true }))
    api.componentNormen.openPunten.mockResolvedValue(_openPunten(['biv']))
    const { w } = await mountDetail()
    _elkeRijHeeftEenKeuze(w, 'bij binnenkomst')

    const ids = w.findAll('[role="tablist"]')[0].findAll('[role="tab"]').map((t) => t.attributes('id'))
    expect(ids.length).toBeGreaterThan(1)
    for (const id of ids) {
      await w.find(`[data-testid="${id}"]`).trigger('click')
      await flushPromises()
      _elkeRijHeeftEenKeuze(w, `na klik op ${id}`)
    }
  })

  it('LI048: ook na een deep-link houdt elke rij één keuze — ook bij een onzin-tab', async () => {
    for (const q of ['?tab=open-punten', '?tab=gebruik', '?tab=bestaat-niet', '?veld=eigenaar', '']) {
      api.componenten.haal.mockResolvedValue(_component({ ondersteunt_werk: true }))
      api.componentNormen.openPunten.mockResolvedValue(_openPunten(['biv']))
      const { w } = await mountDetail({ query: q })
      _elkeRijHeeftEenKeuze(w, `deep-link "${q}"`)
    }
  })

  // ── LI048 — de keten zoals de gebruiker hem loopt, niet de twee helften apart ──────────────
  it('LI048: van aanleiding tot geopend paneel — detailRoute → router → tabblad → lijst', async () => {
    // LI046-les: twee helften die apart groen zijn bewijzen de keten niet. Hier loopt de route
    // door dezelfde bouwsteen die de kaart en het open-punten-overzicht gebruiken (detailIngang),
    // door de router, tot de regel die de consultant leest.
    api.componenten.haal.mockResolvedValue(_component({ checklist_dragend: true }))
    api.componentNormen.openPunten.mockResolvedValue(_openPunten(['biv', 'contract']))
    const doel = detailRoute('component', ID, { tab: 'open-punten' })
    expect(doel).toEqual({ name: 'component-detail', params: { id: ID }, query: { tab: 'open-punten' } })

    const router = maakRouter()
    await router.push(doel)
    await router.isReady()
    const pinia = createPinia()
    const auth = useAuthStore(pinia)
    auth.user = { sub: 's', tenant_id: 't', email: 'a@b.nl', roles: ['beheerder'] }
    const w = mount(ComponentDetail, {
      props: { id: ID },
      attachTo: document.body,
      global: { plugins: [pinia, [PrimeVue, { unstyled: true }], ToastService, router], stubs: { teleport: true } },
    })
    await flushPromises()

    // BEIDE rijen staan goed: de groep is gekozen én het onderdeel erbinnen (snede 2b — een
    // bestaande link mag niet halverwege stranden op een groep zonder gekozen onderdeel).
    expect(w.find('[data-testid="detailtabs-tab-beoordeling"]').attributes('aria-selected')).toBe('true')
    expect(w.find('[data-testid="subtabs-tab-open-punten"]').attributes('aria-selected')).toBe('true')
    // … het paneel is zichtbaar en is een echt tabpaneel …
    expect(w.find('[data-testid="panel-open-punten"]').isVisible()).toBe(true)
    expect(w.find('[data-testid="panel-open-punten"]').attributes('role')).toBe('tabpanel')
    // … en de regels staan er echt, met het getal dat beide diepten beloven.
    expect(w.find('[data-testid="detailtabs-tab-beoordeling"]').text()).toBe('Beoordeling (2)')
    expect(w.find('[data-testid="subtabs-tab-open-punten"]').text()).toBe('Open punten (2)')
    expect(w.findAll('[data-testid="op-lijst-moet_nog"] > li')).toHaveLength(2)
  })

  it('LI048 2b: élke bestaande ?tab=-ingang landt nog op zijn inhoud, met beide rijen gezet', async () => {
    // De acht onderdeel-sleutels die van BUITEN kunnen komen, gemeten in de code:
    // kaart-aanleidingen (contracten · bedrijfsfunctie · gebruik), de blokkade-doorklik
    // (checklist), de backend-routes van het open-punten-overzicht (verantwoordelijkheden ·
    // gebruikersgroepen · koppelingen · contracten) en de gedeelde URL uit snede 1 (open-punten).
    // Hergroeperen mag er geen enkele stil laten sneuvelen — daarom de hele set, niet een greep.
    const INGANGEN = {
      'open-punten': 'beoordeling', checklist: 'beoordeling',
      bedrijfsfunctie: 'wat-het-doet', gebruik: 'wat-het-doet', gebruikersgroepen: 'wat-het-doet',
      koppelingen: 'samenhang',
      contracten: 'afspraken', verantwoordelijkheden: 'afspraken',
    }
    for (const [onderdeel, groep] of Object.entries(INGANGEN)) {
      _zetType('applicatie', true, true)
      api.componentNormen.openPunten.mockResolvedValue(_openPunten(['biv']))
      const { w } = await mountDetail({ query: `?tab=${onderdeel}` })
      expect(w.find(`[data-testid="detailtabs-tab-${groep}"]`).attributes('aria-selected'),
             `?tab=${onderdeel}: groep ${groep} niet gekozen`).toBe('true')
      expect(w.find(`[data-testid="subtabs-tab-${onderdeel}"]`).attributes('aria-selected'),
             `?tab=${onderdeel}: onderdeel niet gekozen`).toBe('true')
      expect(w.find(`#detailtabs-panel-${onderdeel}`).isVisible(),
             `?tab=${onderdeel}: paneel niet zichtbaar`).toBe(true)
    }
  })

  it('LI048: de terugweg loopt via de tabrij — Overzicht geeft weer een schone URL', async () => {
    api.componentNormen.openPunten.mockResolvedValue(_openPunten(['biv']))
    const { w, router } = await mountDetail({ query: '?tab=open-punten' })
    expect(w.find('[data-testid="panel-open-punten"]').isVisible()).toBe(true)
    await w.find('[data-testid="detailtabs-tab-overzicht"]').trigger('click')
    await flushPromises()
    expect(w.find('[data-testid="panel-open-punten"]').isVisible()).toBe(false)
    expect(router.currentRoute.value.query.tab).toBeUndefined() // Overzicht = schone URL
  })

  it('ADR-055: een database krijgt géén Gebruikersgroepen — daar draaien componenten op, dat is een koppeling', async () => {
    api.componenten.haal.mockResolvedValue(_component({ ondersteunt_werk: false }))
    const { w } = await mountDetail()
    expect(_tabtekst(w)).not.toContain('Gebruikersgroepen')
  })

  it('ADR-055: het paneel volgt de tabrij — geen paneel zonder tab', async () => {
    api.componenten.haal.mockResolvedValue(_component({ ondersteunt_werk: false }))
    const { w } = await mountDetail()
    expect(w.find('#detailtabs-panel-gebruikersgroepen').exists()).toBe(false)
  })

  // ADR-025 — "Bekijk op kaart".
  it('toont "Bekijk op kaart" met ARCHITECTUUR.LEZEN (tenant-rol)', async () => {
    const { w } = await mountDetail({ rollen: ['viewer'] })
    expect(w.find('[data-testid="bekijk-op-kaart-knop"]').exists()).toBe(true)
  })

  it('"Bekijk op kaart" navigeert naar de landschapskaart met ?center', async () => {
    const { w, router } = await mountDetail({ rollen: ['medewerker'] })
    const pushSpy = vi.spyOn(router, 'push')
    await w.find('[data-testid="bekijk-op-kaart-knop"]').trigger('click')
    expect(pushSpy).toHaveBeenCalledWith({ name: 'landschapskaart', query: { center: 'db-1' } })
  })

  it('"Bekijk op kaart" verborgen zonder tenant-rol (geen ARCHITECTUUR.LEZEN)', async () => {
    const { w } = await mountDetail({ rollen: [] })
    expect(w.find('[data-testid="bekijk-op-kaart-knop"]').exists()).toBe(false)
  })
})

describe('ComponentDetail — herzien Overzicht: de blokken (ADR-042 4b)', () => {
  it('toont de blokken: wat is dit / wie is verantwoordelijk (waarvoor = eigen tab)', async () => {
    const { w } = await mountDetail()
    expect(w.find('[data-testid="blok-wat-is-dit"]').exists()).toBe(true)
    expect(w.find('[data-testid="blok-verantwoordelijk"]').exists()).toBe(true)
    // Blok 1 draagt de compacte metadata (type + rol + BIV zitten erin).
    const wat = w.find('[data-testid="blok-wat-is-dit"]')
    expect(wat.text()).toContain('Database')
    expect(wat.find('[data-testid="comp-rol"]').exists()).toBe(true)
    expect(wat.find('[data-testid="comp-biv"]').exists()).toBe(true)
  })

  // ADR-043 gate 4 (G2) — "waarvoor gebruiken we het" is een EIGEN tab "Bedrijfsfunctie",
  // direct na Overzicht; de sectie leeft in dat panel (niet meer als blok onder Overzicht).
  it('toont een eigen tab "Bedrijfsfunctie" met de bedrijfsfunctie-sectie in het panel', async () => {
    const { w } = await mountDetail()
    const tabtekst = w.find('[data-testid="detailtabs"]').exists()
      ? w.find('[data-testid="detailtabs"]').text() : w.text()
    expect(tabtekst).toContain('Bedrijfsfunctie')
    const panel = w.find('#detailtabs-panel-bedrijfsfunctie')
    expect(panel.exists()).toBe(true)
    expect(panel.find('[data-testid="component-bedrijfsfunctie-sectie"]').exists()).toBe(true)
  })

  it('ADR-046: Levensfase en Bedoeling staan in dezelfde groep; het gat toont gedempt "nog niet vastgelegd"', async () => {
    // Zonder levensfase (de normale beginstand — geen default, geen alarm).
    const { w } = await mountDetail()
    const wat = w.find('[data-testid="blok-wat-is-dit"]')
    expect(wat.text()).toContain('Levensfase')
    expect(wat.text()).toContain('Bedoeling')
    expect(wat.text()).not.toContain('Migratiepad') // UI-label is 'Bedoeling' (ADR-046)
    const leeg = wat.find('[data-testid="levensfase-leeg"]')
    expect(leeg.exists()).toBe(true)
    expect(leeg.text()).toBe('nog niet vastgelegd')
    // Gedempt (muted token) — géén rood: leeg ≠ fout.
    expect(leeg.classes().join(' ')).toContain('text-muted')
    // LI040 — één leegte-taal: de bedoeling zonder waarde toont IDENTIEK gedempt
    // "nog niet vastgelegd" (nooit meer 'Onbekend').
    const padLeeg = wat.find('[data-testid="bedoeling-leeg"]')
    expect(padLeeg.exists()).toBe(true)
    expect(padLeeg.text()).toBe('nog niet vastgelegd')
    expect(padLeeg.classes().join(' ')).toContain('text-muted')
    expect(wat.text()).not.toContain('Onbekend')
    // LI040 — ook de oordelen zonder waarde: gedempt, en nergens een verzonnen 'Midden'.
    for (const veld of ['complexiteit-leeg', 'prioriteit-leeg']) {
      const el = wat.find(`[data-testid="${veld}"]`)
      expect(el.exists()).toBe(true)
      expect(el.text()).toBe('nog niet vastgelegd')
      expect(el.classes().join(' ')).toContain('text-muted')
    }
    expect(wat.text()).not.toContain('Midden')
  })

  it('ADR-046: een gezette levensfase toont het label (zichtbare tekst, niet alleen "rendert")', async () => {
    api.componenten.haal.mockResolvedValue(_component({ levensfase: 'uitfaseren', migratiepad: 'vervangen' }))
    const { w } = await mountDetail()
    expect(w.find('[data-testid="comp-levensfase"]').text()).toBe('Uitfaseren')
    expect(w.find('[data-testid="comp-bedoeling"]').text()).toBe('Vervangen')
  })

  it('sleutelrollen: gevulde product owner/proceseigenaar tonen namen; gaten rustig "nog niet geregistreerd"', async () => {
    api.roltoewijzingen.lijst.mockResolvedValue([
      { toewijzing_id: 't1', rol: 'product_owner', rol_label: 'Product owner', partij_id: 'p1', partij_naam: 'J. de Vries' },
      { toewijzing_id: 't2', rol: 'product_owner', rol_label: 'Product owner', partij_id: 'p2', partij_naam: 'P. van Dijk' },
      { toewijzing_id: 't3', rol: 'technisch_beheer', rol_label: 'Technisch beheer', partij_id: 'p3', partij_naam: 'X' },
    ])
    const { w } = await mountDetail()
    expect(w.find('[data-testid="sleutelrol-product-owner"]').text()).toContain('J. de Vries, P. van Dijk')
    expect(w.find('[data-testid="sleutelrol-proceseigenaar"]').text()).toContain('nog niet geregistreerd')
  })

  it('"Alle verantwoordelijkheden →" opent het bestaande tabblad (tonen hier, registreren daar)', async () => {
    const { w } = await mountDetail()
    // In het blok zelf géén toewijzen-affordance.
    expect(w.find('[data-testid="blok-verantwoordelijk"]').text()).not.toContain('Toevoegen')
    await w.find('[data-testid="alle-verantwoordelijkheden"]').trigger('click')
    await flushPromises()
    expect(w.find('#detailtabs-panel-verantwoordelijkheden').isVisible()).toBe(true)
  })

  it('Bewerken opent de overlay boven het detail (geen route-navigatie meer)', async () => {
    const { w, router } = await mountDetail()
    const routeVoor = router.currentRoute.value.fullPath
    await w.find('[data-testid="bewerken-knop"]').trigger('click')
    await flushPromises()
    expect(w.find('[data-testid="component-form-overlay"]').exists()).toBe(true)
    expect(router.currentRoute.value.fullPath).toBe(routeVoor) // detail blijft eronder
    expect(w.find('[data-testid="veld-naam"]').element.value).toBe('Oracle FIN-DB') // voorgevuld
  })

  it('deep-link ?bewerk=1 (de oude bewerken-route) opent de overlay direct', async () => {
    const { w } = await mountDetail({ query: '?bewerk=1' })
    expect(w.find('[data-testid="component-form-overlay"]').exists()).toBe(true)
  })
})

// LI035 succes-standaard — ook de regel-acties van ComponentBedrijfsfunctieSectie geven
// de korte bevestiging (ADR-043 gate 4; zie meldingen.js).
describe('ComponentBedrijfsfunctieSectie — succes-terugkoppeling', () => {
  it('een koppeling weghalen geeft een korte succes-toast', async () => {
    api.functievervullingen.componentKoppelingen.mockResolvedValue([{
      vervulling_id: 'fv1', herkomst: 'grof', functie_id: 'f1', functie_naam: 'Vergunningverlening',
      ouder_functie_id: null, ouder_naam: null, oordeel: null,
      grof_totaal_plekken: 1, grof_geldt_op: 1, verdrongen_op: 0,
    }])
    api.functievervullingen.verwijder.mockResolvedValue(undefined)
    const { w } = await mountDetail()
    await w.find('[data-testid="cbf-verwijder-fv1"]').trigger('click')
    await w.find('[data-testid="cbf-verwijder-bevestig"]').trigger('click')
    await flushPromises()
    expect(api.functievervullingen.verwijder).toHaveBeenCalledWith('fv1')
    expect(toastSucces).toHaveBeenCalledWith(expect.anything(), 'Koppeling weggehaald')
  })
})

describe('ComponentDetail — één aanduiding per feit (slice 4c besluit 21)', () => {
  it('elk genormeerd sectie-feit toont precies één aanduiding op zijn sectiekop', async () => {
    api.componentNormen.definitie.mockResolvedValue([
      { feit: 'contract', verplicht: true, bewust_geen_mogelijk: true },
      { feit: 'verantwoordelijke', verplicht: true, bewust_geen_mogelijk: false },
      { feit: 'koppelingen', verplicht: false, bewust_geen_mogelijk: true },
    ])
    const { w } = await mountDetail()
    expect(w.find('[data-testid="uitleg-contract-lat"]').exists()).toBe(true)
    expect(w.find('[data-testid="uitleg-verantwoordelijke-lat"]').exists()).toBe(true)
    // Tellende borging: #aanduidingen == #genormeerde feiten op dit scherm (contract + verantwoordelijke = 2).
    expect(w.findAll('[data-norm-lat]').length).toBe(2)
  })
})

describe('ComponentDetail — LI048: wegwijzers zijn een teken, handelingen een woord', () => {
  it('"Bekijk op kaart" draagt het kaartteken met een uitgesproken naam', async () => {
    const { w } = await mountDetail()
    const knop = w.get('[data-testid="bekijk-op-kaart-knop"]')
    expect(knop.find('svg[data-icoon="kaart"]').exists()).toBe(true)
    expect(knop.attributes('aria-label')).toBe('Bekijk op kaart')
    expect(knop.attributes('title')).toBe('Bekijk op kaart')
    // Geen zichtbaar woord meer — dát is de ruimtewinst.
    expect(knop.text().trim()).toBe('')
  })

  it('DE REGEL: elke handeling in de kop draagt een zichtbaar woord', async () => {
    // Dit is de regel, niet het geval. Wie er later "voor de consistentie" een teken van maakt,
    // laat deze toets omvallen — en dat is de bedoeling: een handeling verandert iets, en moet
    // in één blik te lezen zijn, ook door iemand die het scherm voor het eerst ziet. Een tooltip
    // verschijnt pas als je met de muis blijft hangen, en op een tablet nooit.
    const { w } = await mountDetail()
    const HANDELINGEN = [
      'bewerk-knop',
      'verwijder-knop',
      'klaarverklaar-knop',
    ]
    for (const testid of HANDELINGEN) {
      const knop = w.find(`[data-testid="${testid}"]`)
      if (!knop.exists()) continue          // niet elke statusovergang is altijd zichtbaar
      expect(knop.text().trim().length, testid).toBeGreaterThan(0)
      expect(knop.find('svg').exists(), `${testid} hoort geen teken te dragen`).toBe(false)
    }
  })

  it('de tekens houden dezelfde hoogte als de woordknoppen', async () => {
    // Loopt dit uit de pas, dan valt de rij visueel uiteen — het probleem van de lijstkop eerder
    // deze sessie. Het teken schaalt op `1em`, dus het erft de regelhoogte van de knop; er staat
    // nergens een eigen pixelmaat die daarvan af kan wijken.
    const { w } = await mountDetail()
    for (const naam of ['kaart', 'geschiedenis']) {
      const svg = w.find(`svg[data-icoon="${naam}"]`)
      if (!svg.exists()) continue
      expect(svg.attributes('height')).toBe('1em')
      expect(svg.attributes('width')).toBe('1em')
    }
    // Beide knoppen komen uit hetzelfde Button-preset als de woordknoppen: dezelfde padding,
    // dezelfde regelhoogte. Zou een van beide een eigen `class` met hoogte krijgen, dan is dat
    // hier zichtbaar.
    const kaart = w.get('[data-testid="bekijk-op-kaart-knop"]')
    const bewerk = w.find('[data-testid="bewerk-knop"]')
    if (bewerk.exists()) {
      expect(kaart.classes().join(' ')).not.toMatch(/\bh-\[|\bheight/)
      expect(bewerk.classes().join(' ')).not.toMatch(/\bh-\[|\bheight/)
    }
  })

  it('de volgorde van de knoppen is onveranderd', async () => {
    // De wijziging gaat over de VORM van twee knoppen, niet over hun plaats.
    const { w } = await mountDetail()
    const html = w.html()
    const pos = (t) => html.indexOf(`data-testid="${t}"`)
    expect(pos('bekijk-op-kaart-knop')).toBeGreaterThan(pos('bewerk-knop'))
    expect(pos('oh-knop')).toBeGreaterThan(pos('bekijk-op-kaart-knop'))
    expect(pos('verwijder-knop')).toBeGreaterThan(pos('oh-knop'))
  })
})
