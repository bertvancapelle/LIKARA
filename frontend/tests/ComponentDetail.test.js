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
    componentNormen: { definitie: vi.fn(() => Promise.resolve([])) },
  },
}))

// LI035 succes-standaard — helper gemockt zodat de succes-flow assertbaar is.
vi.mock('@/meldingen', () => ({ toastSucces: vi.fn() }))

import { api } from '@/api'
import { toastSucces } from '@/meldingen'
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
      { id: 1, code: '3.2', categorie_nr: 3, categorie_naam: 'Data', vraag: 'a', prioriteit: 'hoog' },
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

  it('markeert de vraag uit de deep-link-query (blokkadelijst-doorklik, ADR-024-vervolg)', async () => {
    api.componenten.haal.mockResolvedValue(_component({ checklist_dragend: true }))
    api.checklistvragen.lijst.mockResolvedValue([
      { id: 1, code: '3.2', categorie_nr: 3, categorie_naam: 'Data', vraag: 'a', prioriteit: 'hoog' },
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
      { id: 1, code: '2.7', categorie_nr: 2, categorie_naam: 'Techniek', vraag: 'Gedeelde infra?', prioriteit: 'hoog' },
    ])
    api.blokkades.lijst.mockResolvedValue({
      items: [{
        id: 'b1', status: 'in_behandeling', toelichting: null, eigenaar: null,
        checklistvraag_id: 1, vraag_code: '2.7', vraag: 'Gedeelde infra?', score: 'deels',
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
      _component({ componenttype: 'applicatie', componenttype_label: 'Applicatie', heeft_applicatie_subtype: true }),
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
