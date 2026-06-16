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
  },
}))

import { api } from '@/api'
import ComponentDetail from '@modules/bwb_ontvlechting/frontend/views/ComponentDetail.vue'
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
    ],
  })
}

async function mountDetail({ rollen = ['beheerder'] } = {}) {
  const router = maakRouter()
  await router.push('/componenten/db-1')
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

  it('toont de checklist-sectie NIET bij checklist_dragend === false', async () => {
    const { w } = await mountDetail() // default checklist_dragend: false
    expect(w.find('[data-testid="cs-voortgang"]').exists()).toBe(false)
    expect(api.checklistvragen.lijst).not.toHaveBeenCalled()
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
    expect(w.find('[data-testid="cs-rij-2.7"]').classes()).toContain('bg-[var(--cd-color-accent)]')
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

  it('applicatie-subtype: hint naar ApplicatieDetail, geen bewerk-/verwijderknop', async () => {
    api.componenten.haal.mockResolvedValue(
      _component({ componenttype: 'applicatie', componenttype_label: 'Applicatie', heeft_applicatie_subtype: true }),
    )
    const { w } = await mountDetail()
    expect(w.find('[data-testid="detail-subtype-hint"]').exists()).toBe(true)
    expect(w.find('[data-testid="bewerken-knop"]').exists()).toBe(false)
    expect(w.find('[data-testid="verwijder-knop"]').exists()).toBe(false)
  })
})
