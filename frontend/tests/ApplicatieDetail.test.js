/** Tests — ApplicatieDetail (module-view via @modules). */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'

vi.mock('@/api', () => {
  const leeg = () => Promise.resolve({ items: [], volgende_cursor: null })
  return {
    api: {
      applicaties: {
        haal: vi.fn(),
        startInventarisatie: vi.fn(),
        verwijder: vi.fn(),
        lijst: vi.fn(leeg), // KoppelingSectie-pickers (bij dialog-open)
      },
      // ContractSectie laadt nu via component→contracten (CD054 padconsolidatie);
      // de Opbouw-tab (StructuurSectie) leest de structuurgraaf + catalogus-opties.
      componenten: {
        contracten: vi.fn(() => Promise.resolve([])),
        structuur: vi.fn(() => Promise.resolve({ draait_op: [], gebruikt_door: [] })),
        lijst: vi.fn(leeg), // StructuurSectie doel-picker (bij dialog-open)
        opties: vi.fn(() => Promise.resolve({ componenttype: [], structuurrelatie_type: [] })),
      },
      // Embedded child-secties laden bij mount hun lijst (default: leeg).
      datatypes: { lijst: vi.fn(leeg) },
      gebruikersgroepen: { lijst: vi.fn(leeg) },
      koppelingen: { lijst: vi.fn(leeg) },
      checklistscores: { lijst: vi.fn(leeg), opties: vi.fn(() => Promise.resolve({ score: [] })) },
      blokkades: { lijst: vi.fn(leeg) },
      checklistvragen: { lijst: vi.fn(() => Promise.resolve([])) },
      contracten: { lijst: vi.fn(leeg) },
      contractconfig: { opties: vi.fn(() => Promise.resolve({ dekking: [], kostenmodel: [], relatie_rol: [] })) },
    },
  }
})

import { api } from '@/api'
import { useAuthStore } from '@/store/auth'
import ApplicatieDetail from '@modules/bwb_ontvlechting/frontend/views/ApplicatieDetail.vue'
import ChecklistscoreSectie from '@modules/bwb_ontvlechting/frontend/views/ChecklistscoreSectie.vue'
import { LIFECYCLE_SEVERITY } from '@modules/bwb_ontvlechting/frontend/labels'

const _ID = 'app-1'

function _app(extra = {}) {
  return {
    id: _ID,
    naam: 'Zaaksysteem',
    beschrijving: null,
    hostingmodel: 'saas',
    eigenaar_organisatie: 'Gemeente Veldendam',
    eigenaar_naam: null,
    leverancier: null,
    migratiepad: 'herbouw',
    complexiteit: 'midden',
    prioriteit: 'hoog',
    lifecycle_status: 'concept',
    ...extra,
  }
}

async function mountDetail({ rollen = ['beheerder'], query = '' } = {}) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/applicaties', name: 'applicatie-lijst', component: { template: '<div/>' } },
      { path: '/applicaties/:id', name: 'applicatie-detail', component: ApplicatieDetail, props: true },
      { path: '/applicaties/:id/bewerken', name: 'applicatie-bewerken', component: { template: '<div/>' } },
      // ContractSectie (in het contracten-tabpaneel) rendert links naar contract-detail.
      { path: '/contracten/:id', name: 'contract-detail', component: { template: '<div/>' } },
    ],
  })
  await router.push(`/applicaties/${_ID}${query}`)
  await router.isReady()
  const pushSpy = vi.spyOn(router, 'push')

  const pinia = createPinia()
  const auth = useAuthStore(pinia)
  auth.user = { sub: 's', tenant_id: 't', email: 'a@b.nl', roles: rollen }

  const wrapper = mount(ApplicatieDetail, {
    props: { id: _ID },
    global: {
      plugins: [pinia, [PrimeVue, { unstyled: true }], ToastService, router],
      // Dialog teleporteert naar body; inline renderen zodat find() de inhoud ziet.
      stubs: { teleport: true },
    },
  })
  await flushPromises()
  return { wrapper, pushSpy }
}

beforeEach(() => vi.clearAllMocks())
afterEach(() => vi.restoreAllMocks())

describe('ApplicatieDetail', () => {
  it('toont de applicatiegegevens en de lifecycle-status', async () => {
    api.applicaties.haal.mockResolvedValueOnce(_app())
    const { wrapper } = await mountDetail()
    expect(wrapper.text()).toContain('Zaaksysteem')
    expect(wrapper.text()).toContain('Gemeente Veldendam')
    expect(wrapper.find('[data-testid="detail-status"]').text()).toContain('Concept')
  })

  it('gate: Beheerder ziet bewerken + verwijderen + start (bij concept)', async () => {
    api.applicaties.haal.mockResolvedValueOnce(_app())
    const { wrapper } = await mountDetail({ rollen: ['beheerder'] })
    expect(wrapper.find('[data-testid="bewerken-knop"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="verwijder-knop"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="start-knop"]').exists()).toBe(true)
  })

  it('gate: Viewer ziet geen actieknoppen', async () => {
    api.applicaties.haal.mockResolvedValueOnce(_app())
    const { wrapper } = await mountDetail({ rollen: ['viewer'] })
    expect(wrapper.find('[data-testid="bewerken-knop"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="verwijder-knop"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="start-knop"]').exists()).toBe(false)
  })

  it('gate: Medewerker ziet geen verwijderen; start verdwijnt buiten concept', async () => {
    api.applicaties.haal.mockResolvedValueOnce(_app({ lifecycle_status: 'in_inventarisatie' }))
    const { wrapper } = await mountDetail({ rollen: ['medewerker'] })
    expect(wrapper.find('[data-testid="bewerken-knop"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="verwijder-knop"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="start-knop"]').exists()).toBe(false) // niet concept
  })

  it('start-inventarisatie roept de api aan en werkt de status bij', async () => {
    api.applicaties.haal.mockResolvedValueOnce(_app())
    api.applicaties.startInventarisatie.mockResolvedValueOnce(_app({ lifecycle_status: 'in_inventarisatie' }))
    const { wrapper } = await mountDetail({ rollen: ['medewerker'] })
    await wrapper.find('[data-testid="start-knop"]').trigger('click')
    await flushPromises()
    expect(api.applicaties.startInventarisatie).toHaveBeenCalledWith(_ID)
    expect(wrapper.find('[data-testid="detail-status"]').text()).toContain('In inventarisatie')
  })

  it('verwijderen verloopt via bevestiging en navigeert naar de lijst', async () => {
    api.applicaties.haal.mockResolvedValueOnce(_app())
    api.applicaties.verwijder.mockResolvedValueOnce(null)
    const { wrapper, pushSpy } = await mountDetail({ rollen: ['beheerder'] })

    await wrapper.find('[data-testid="verwijder-knop"]').trigger('click')
    await wrapper.find('[data-testid="verwijder-bevestig"]').trigger('click')
    await flushPromises()

    expect(api.applicaties.verwijder).toHaveBeenCalledWith(_ID)
    expect(pushSpy).toHaveBeenCalledWith({ name: 'applicatie-lijst' })
  })

  it('vangt een 403 bij verwijderen af zonder te navigeren', async () => {
    api.applicaties.haal.mockResolvedValueOnce(_app())
    const err = new Error('Onvoldoende rechten')
    err.status = 403
    api.applicaties.verwijder.mockRejectedValueOnce(err)
    const { wrapper, pushSpy } = await mountDetail({ rollen: ['beheerder'] })

    await wrapper.find('[data-testid="verwijder-knop"]').trigger('click')
    await wrapper.find('[data-testid="verwijder-bevestig"]').trigger('click')
    await flushPromises()

    expect(api.applicaties.verwijder).toHaveBeenCalled()
    expect(pushSpy).not.toHaveBeenCalledWith({ name: 'applicatie-lijst' })
  })

  // ── Lifecycle-indicator ─────────────────────────────────────────────────
  it('toont de backend-lifecycle als Tag; checklist_compleet is geen ruststatus', async () => {
    api.applicaties.haal.mockResolvedValueOnce(_app({ lifecycle_status: 'migratieklaar' }))
    const { wrapper } = await mountDetail()
    expect(wrapper.find('[data-testid="detail-status"]').text()).toContain('Migratieklaar')
    // checklist_compleet kent géén rust-severity (transient, ADR-013 B4)
    expect('checklist_compleet' in LIFECYCLE_SEVERITY).toBe(false)
  })

  it('checklist_compleet valt terug op humanize (geen crash/rustlabel)', async () => {
    api.applicaties.haal.mockResolvedValueOnce(_app({ lifecycle_status: 'checklist_compleet' }))
    const { wrapper } = await mountDetail()
    expect(wrapper.find('[data-testid="detail-status"]').text()).toContain('Checklist compleet')
  })

  // ── Coördinatie: na een score herladen lifecycle + blokkades ────────────
  it('herlaadt lifecycle (applicaties.haal) én blokkades na een score-mutatie', async () => {
    api.applicaties.haal.mockResolvedValue(_app())
    const { wrapper } = await mountDetail()
    const haalVoor = api.applicaties.haal.mock.calls.length
    const blokVoor = api.blokkades.lijst.mock.calls.length

    wrapper.findComponent(ChecklistscoreSectie).vm.$emit('gewijzigd')
    await flushPromises()

    expect(api.applicaties.haal.mock.calls.length).toBeGreaterThan(haalVoor)
    expect(api.blokkades.lijst.mock.calls.length).toBeGreaterThan(blokVoor)
  })
})

describe('ApplicatieDetail — categorie-tabs (CD022, #11)', () => {
  it('rendert de top-tablist met de 6 onderdelen en Overzicht als default', async () => {
    api.applicaties.haal.mockResolvedValue(_app())
    const { wrapper } = await mountDetail()
    expect(wrapper.find('[role="tablist"]').exists()).toBe(true)
    for (const k of ['overzicht', 'checklist', 'datatypes', 'gebruikersgroepen', 'koppelingen', 'blokkades']) {
      expect(wrapper.find(`[data-testid="detailtabs-tab-${k}"]`).exists()).toBe(true)
    }
    expect(wrapper.find('[data-testid="detailtabs-tab-overzicht"]').attributes('aria-selected')).toBe('true')
    // metadata staat in het Overzicht-panel
    expect(wrapper.find('[data-testid="panel-overzicht"]').text()).toContain('Gemeente Veldendam')
  })

  it('tab-klik wisselt de actieve tab (aria-selected verspringt)', async () => {
    api.applicaties.haal.mockResolvedValue(_app())
    const { wrapper } = await mountDetail()
    await wrapper.find('[data-testid="detailtabs-tab-datatypes"]').trigger('click')
    expect(wrapper.find('[data-testid="detailtabs-tab-datatypes"]').attributes('aria-selected')).toBe('true')
    expect(wrapper.find('[data-testid="detailtabs-tab-overzicht"]').attributes('aria-selected')).toBe('false')
  })

  it('toetsenbord: ArrowRight selecteert de volgende tab', async () => {
    api.applicaties.haal.mockResolvedValue(_app())
    const { wrapper } = await mountDetail()
    await wrapper.find('[data-testid="detailtabs-tab-overzicht"]').trigger('keydown', { key: 'ArrowRight' })
    expect(wrapper.find('[data-testid="detailtabs-tab-checklist"]').attributes('aria-selected')).toBe('true')
  })

  it('deep-link: ?tab=blokkades opent de Blokkades-tab', async () => {
    api.applicaties.haal.mockResolvedValue(_app())
    const { wrapper } = await mountDetail({ query: '?tab=blokkades' })
    expect(wrapper.find('[data-testid="detailtabs-tab-blokkades"]').attributes('aria-selected')).toBe('true')
  })

  it('checklist: categorie-sub-tabs uit de geladen vragen, eerste categorie default', async () => {
    api.applicaties.haal.mockResolvedValue(_app())
    api.checklistvragen.lijst.mockResolvedValue([
      { id: 1, code: '1.1', categorie_nr: 1, categorie_naam: 'Identiteit', vraag: 'a', prioriteit: 'hoog' },
      { id: 2, code: '2.1', categorie_nr: 2, categorie_naam: 'Data', vraag: 'b', prioriteit: 'hoog' },
    ])
    const { wrapper } = await mountDetail({ query: '?tab=checklist' })
    expect(wrapper.find('[data-testid="checklisttabs-tab-1"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="checklisttabs-tab-2"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="checklisttabs-tab-1"]').attributes('aria-selected')).toBe('true')
    // alleen categorie-1-vraag zichtbaar in het gedeelde score-panel
    expect(wrapper.find('[data-testid="cs-rij-1.1"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="cs-rij-2.1"]').exists()).toBe(false)
  })

  it('deep-link: ?tab=checklist&cat=2 opent de tweede categorie', async () => {
    api.applicaties.haal.mockResolvedValue(_app())
    api.checklistvragen.lijst.mockResolvedValue([
      { id: 1, code: '1.1', categorie_nr: 1, categorie_naam: 'Identiteit', vraag: 'a', prioriteit: 'hoog' },
      { id: 2, code: '2.1', categorie_nr: 2, categorie_naam: 'Data', vraag: 'b', prioriteit: 'hoog' },
    ])
    const { wrapper } = await mountDetail({ query: '?tab=checklist&cat=2' })
    expect(wrapper.find('[data-testid="checklisttabs-tab-2"]').attributes('aria-selected')).toBe('true')
    expect(wrapper.find('[data-testid="cs-rij-2.1"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="cs-rij-1.1"]').exists()).toBe(false)
  })
})

describe('ApplicatieDetail — context-paneel categorie 8 (CD044 §5)', () => {
  const _vragen = [
    { id: 1, code: '1.1', categorie_nr: 1, categorie_naam: 'Identiteit', vraag: 'a', prioriteit: 'hoog' },
    { id: 8, code: '8.1', categorie_nr: 8, categorie_naam: 'Contractuele positie', vraag: 'c', prioriteit: 'hoog' },
  ]
  const _koppeling = {
    koppeling_id: 'k1', contract_id: 'c1', contractnaam: 'Mantel X', contracttype: 'mantelcontract',
    leverancier_id: 'l1', leverancier_naam: 'Acme BV', begindatum: '2026-01-01', einddatum: '2026-12-31',
    relatie_rol: 'valt_onder', relatie_rol_label: 'Valt onder / aanschaf',
  }

  it('is alleen zichtbaar op categorie-tab 8', async () => {
    api.applicaties.haal.mockResolvedValue(_app())
    api.checklistvragen.lijst.mockResolvedValue(_vragen)
    const op8 = await mountDetail({ query: '?tab=checklist&cat=8' })
    expect(op8.wrapper.find('[data-testid="context-paneel-cat8"]').exists()).toBe(true)
    const op1 = await mountDetail({ query: '?tab=checklist&cat=1' })
    expect(op1.wrapper.find('[data-testid="context-paneel-cat8"]').exists()).toBe(false)
  })

  it('toont de geregistreerde contracten incl. datums en is read-only', async () => {
    api.applicaties.haal.mockResolvedValue(_app())
    api.checklistvragen.lijst.mockResolvedValue(_vragen)
    api.componenten.contracten.mockResolvedValue([_koppeling])
    const { wrapper } = await mountDetail({ query: '?tab=checklist&cat=8' })
    const paneel = wrapper.find('[data-testid="context-paneel-cat8"]')
    expect(paneel.attributes('role')).toBe('complementary')
    const lijst = wrapper.find('[data-testid="context-paneel-lijst"]')
    expect(lijst.text()).toContain('Mantel X')
    expect(lijst.text()).toContain('Acme BV')
    expect(lijst.text()).toContain('2026-01-01')
    expect(lijst.text()).toContain('2026-12-31')
    // read-only: geen invoer/keuze/schrijf-knoppen in het paneel
    expect(paneel.findAll('input, select, button').length).toBe(0)
  })

  it('lege-staat: paneel met melding + link naar de Contracten-sectie', async () => {
    api.applicaties.haal.mockResolvedValue(_app())
    api.checklistvragen.lijst.mockResolvedValue(_vragen)
    api.componenten.contracten.mockResolvedValue([])
    const { wrapper } = await mountDetail({ query: '?tab=checklist&cat=8' })
    expect(wrapper.find('[data-testid="context-paneel-leeg"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="context-paneel-naar-sectie"]').exists()).toBe(true)
  })
})
