/**
 * Tests — ADR-023 Fase F (F-1): migratielaag-overzicht (read-only views).
 * api gemockt; memory-router voor de router-links; PrimeVue (unstyled) voor DataTable/Tag.
 * Gedekt: lijst rendert items, detail rendert kernvelden, plateau-leden (contractuele
 * bevestiging), gap-readiness (gevuld + lege noemer → "n.v.t."), wp-hiërarchie, del-keten.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'

vi.mock('@/api', () => ({
  api: {
    plateaus: { lijst: vi.fn(), haal: vi.fn(), leden: vi.fn() },
    gaps: { lijst: vi.fn(), haal: vi.fn(), leden: vi.fn() },
    workPackages: { lijst: vi.fn(), haal: vi.fn(), subboom: vi.fn() },
    deliverables: { lijst: vi.fn(), haal: vi.fn(), keten: vi.fn() },
  },
}))

import { api } from '@/api'
import PlateauLijstView from './PlateauLijstView.vue'
import PlateauDetailView from './PlateauDetailView.vue'
import GapLijstView from './GapLijstView.vue'
import GapDetailView from './GapDetailView.vue'
import WorkPackageLijstView from './WorkPackageLijstView.vue'
import WorkPackageDetailView from './WorkPackageDetailView.vue'
import DeliverableLijstView from './DeliverableLijstView.vue'
import DeliverableDetailView from './DeliverableDetailView.vue'

const STUB = { template: '<div/>' }

function maakRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'plateau-lijst', component: STUB },
      { path: '/p/:id', name: 'plateau-detail', component: STUB },
      { path: '/g', name: 'gap-lijst', component: STUB },
      { path: '/g/:id', name: 'gap-detail', component: STUB },
      { path: '/w', name: 'work-package-lijst', component: STUB },
      { path: '/w/:id', name: 'work-package-detail', component: STUB },
      { path: '/d', name: 'deliverable-lijst', component: STUB },
      { path: '/d/:id', name: 'deliverable-detail', component: STUB },
    ],
  })
}

async function mountView(View, props = {}) {
  const router = maakRouter()
  await router.push('/')
  await router.isReady()
  const wrapper = mount(View, {
    props,
    global: { plugins: [createPinia(), [PrimeVue, { unstyled: true }], ToastService, router] },
  })
  await flushPromises()
  return wrapper
}

afterEach(() => vi.clearAllMocks())

describe('F-1 lijst-views', () => {
  beforeEach(() => {
    api.plateaus.lijst.mockResolvedValue({ items: [{ id: 'p1', naam: 'Huidig', toelichting: null }], volgende_cursor: null })
    api.gaps.lijst.mockResolvedValue({ items: [{ id: 'g1', naam: 'Kloof A', toelichting: 'x' }], volgende_cursor: null })
    api.workPackages.lijst.mockResolvedValue({ items: [{ id: 'w1', naam: 'WP-1', bovenliggend_id: null, toelichting: null }], volgende_cursor: null })
    api.deliverables.lijst.mockResolvedValue({ items: [{ id: 'd1', naam: 'DB over', toelichting: null }], volgende_cursor: null })
  })

  it('plateau-lijst rendert items met detail-link', async () => {
    const w = await mountView(PlateauLijstView)
    expect(w.text()).toContain('Huidig')
    expect(w.find('[data-testid="plateau-link"]').attributes('href')).toContain('/p/p1')
  })
  it('gap-lijst rendert items', async () => {
    const w = await mountView(GapLijstView)
    expect(w.text()).toContain('Kloof A')
    expect(w.find('[data-testid="gap-link"]').attributes('href')).toContain('/g/g1')
  })
  it('werkpakket-lijst toont top-niveau/subpakket-indicatie', async () => {
    const w = await mountView(WorkPackageLijstView)
    expect(w.text()).toContain('WP-1')
    expect(w.find('[data-testid="wp-is-subpakket"]').text()).toContain('top-niveau')
  })
  it('deliverable-lijst rendert items', async () => {
    const w = await mountView(DeliverableLijstView)
    expect(w.text()).toContain('DB over')
  })
  it('lege lijst toont lege-staat', async () => {
    api.plateaus.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
    const w = await mountView(PlateauLijstView)
    expect(w.find('[data-testid="plateau-lijst-leeg"]').exists()).toBe(true)
  })
})

describe('F-1 plateau-detail', () => {
  it('rendert leden met dispositie-label + contractuele bevestiging (n.v.t. voor componenten)', async () => {
    api.plateaus.haal.mockResolvedValue({ id: 'p1', naam: 'Doel', toelichting: 'doelplateau' })
    api.plateaus.leden.mockResolvedValue([
      { id: 'l1', lid_element_type: 'component', dispositie: 'migreren', dispositie_label: 'Migreren', contractueel_bevestigd: false, bevestigd_aantal_gebruikers: null, bevestigd_door: null, bevestigd_op: null },
      { id: 'l2', lid_element_type: 'contract', dispositie: 'behouden', dispositie_label: 'Behouden', contractueel_bevestigd: true, bevestigd_aantal_gebruikers: 250, bevestigd_door: 'bert@x', bevestigd_op: '2026-06-15T10:00:00Z' },
    ])
    const w = await mountView(PlateauDetailView, { id: 'p1' })
    expect(w.find('[data-testid="plateau-naam"]').text()).toBe('Doel')
    expect(w.text()).toContain('Migreren')
    expect(w.text()).toContain('Behouden')
    expect(w.text()).toContain('Bevestigd')
    expect(w.text()).toContain('250')
  })
})

describe('F-1 gap-detail', () => {
  it('toont beide readiness-cijfers gescheiden; lege noemer als n.v.t.', async () => {
    api.gaps.haal.mockResolvedValue({
      id: 'g1', naam: 'Kloof A', toelichting: null,
      baseline_plateau_id: 'pb', doel_plateau_id: 'pd',
      readiness_technisch: { aantal_klaar: 1, aantal_totaal: 2, percentage: 50.0 },
      readiness_contractueel: { aantal_klaar: 0, aantal_totaal: 0, percentage: null },
    })
    api.gaps.leden.mockResolvedValue([{ id: 'm1', lid_element_type: 'component', naam: 'App X' }])
    api.plateaus.haal.mockImplementation((id) => Promise.resolve({ id, naam: id === 'pb' ? 'Baseline' : 'Doel' }))
    const w = await mountView(GapDetailView, { id: 'g1' })
    expect(w.find('[data-testid="gap-naam"]').text()).toBe('Kloof A')
    expect(w.find('[data-testid="gap-overgang"]').text()).toContain('Baseline')
    expect(w.find('[data-testid="gap-overgang"]').text()).toContain('Doel')
    expect(w.find('[data-testid="readiness-technisch"]').text()).toContain('1 van 2 (50%)')
    // Lege noemer: nette uitleg i.p.v. 0% (UX-A4-4-tekst).
    expect(w.find('[data-testid="readiness-contractueel"]').text()).toContain('Nog geen leden')
    expect(w.find('[data-testid="readiness-contractueel"]').text()).not.toContain('0%')
    expect(w.text()).toContain('App X')
  })
})

describe('F-1 werkpakket-detail', () => {
  it('toont ouder + subboom-hiërarchie', async () => {
    api.workPackages.haal.mockImplementation((id) =>
      Promise.resolve(
        id === 'w1'
          ? { id: 'w1', naam: 'WP-kind', toelichting: null, bovenliggend_id: 'w0' }
          : { id: 'w0', naam: 'WP-ouder', toelichting: null, bovenliggend_id: null },
      ),
    )
    api.workPackages.subboom.mockResolvedValue([
      { id: 'w2', naam: 'WP-sub', bovenliggend_id: 'w1', niveau: 1, pad: ['WP-kind', 'WP-sub'] },
    ])
    const w = await mountView(WorkPackageDetailView, { id: 'w1' })
    expect(w.find('[data-testid="wp-naam"]').text()).toBe('WP-kind')
    expect(w.find('[data-testid="wp-ouder-link"]').text()).toContain('WP-ouder')
    expect(w.text()).toContain('WP-sub')
    expect(w.text()).toContain('1 direct')
  })
})

describe('F-1 deliverable-detail', () => {
  it('toont de realisatieketen (werkpakketten + plateaus)', async () => {
    api.deliverables.haal.mockResolvedValue({ id: 'd1', naam: 'Overgezette DB', toelichting: null })
    api.deliverables.keten.mockResolvedValue({
      werkpakketten: [{ relatie_id: 'r1', element_id: 'w1', naam: 'WP-migratie' }],
      plateaus: [{ relatie_id: 'r2', element_id: 'p1', naam: 'Doelplateau' }],
    })
    const w = await mountView(DeliverableDetailView, { id: 'd1' })
    expect(w.find('[data-testid="del-naam"]').text()).toBe('Overgezette DB')
    expect(w.text()).toContain('WP-migratie')
    expect(w.text()).toContain('Doelplateau')
  })
})
