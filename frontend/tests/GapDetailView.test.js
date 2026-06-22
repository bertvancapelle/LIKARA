/** Tests — GapDetailView (migratielaag: wijzigen/verwijderen + leden + readiness; UX-A4-4). */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'

vi.mock('@/api', () => ({
  api: {
    gaps: {
      haal: vi.fn(), leden: vi.fn(), werkBij: vi.fn(), verwijder: vi.fn(),
      voegLid: vi.fn(), verwijderLid: vi.fn(),
    },
    plateaus: { haal: vi.fn(), lijst: vi.fn() },
    componenten: { lijst: vi.fn() },
    contracten: { lijst: vi.fn() },
  },
}))

import { api } from '@/api'
import { useAuthStore } from '@/store/auth'
import GapDetailView from '@/views/migratie/GapDetailView.vue'

const ID = 'g1'

function maakRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/migratie/gaps', name: 'gap-lijst', component: { template: '<div/>' } },
      { path: '/migratie/gaps/:id', name: 'gap-detail', component: GapDetailView, props: true },
      { path: '/migratie/plateaus/:id', name: 'plateau-detail', component: { template: '<div/>' } },
    ],
  })
}

async function mountDetail({ rollen = ['beheerder'] } = {}) {
  const router = maakRouter()
  await router.push(`/migratie/gaps/${ID}`)
  await router.isReady()
  const pinia = createPinia()
  const auth = useAuthStore(pinia)
  auth.user = { sub: 's', tenant_id: 't', email: 'a@b.nl', roles: rollen }
  const w = mount(GapDetailView, {
    props: { id: ID },
    attachTo: document.body,
    global: { plugins: [pinia, [PrimeVue, { unstyled: true }], ToastService, router], stubs: { teleport: true } },
  })
  await flushPromises()
  return { w, router }
}

async function kiesZoek(w, prefix, id) {
  await w.find(`[data-testid="${prefix}-input"]`).trigger('focus')
  await flushPromises()
  await w.find(`[data-testid="${prefix}-optie-${id}"]`).trigger('mousedown')
  await flushPromises()
}

const _gap = (over = {}) => ({
  id: ID, naam: 'Kloof A', toelichting: 'overgang', baseline_plateau_id: 'pb', doel_plateau_id: 'pd',
  readiness_technisch: { aantal_klaar: 3, aantal_totaal: 5, percentage: 60.0 },
  readiness_contractueel: { aantal_klaar: 0, aantal_totaal: 0, percentage: null },
  ...over,
})

beforeEach(() => {
  vi.clearAllMocks()
  api.gaps.haal.mockResolvedValue(_gap())
  api.gaps.leden.mockResolvedValue([{ id: 'rl1', gap_id: ID, lid_id: 'c1', lid_element_type: 'component', naam: 'Oracle FIN-DB' }])
  api.plateaus.haal.mockImplementation((id) => Promise.resolve({ id, naam: id === 'pb' ? 'Baseline' : 'Doel' }))
  api.plateaus.lijst.mockResolvedValue({
    items: [{ id: 'pb', naam: 'Baseline' }, { id: 'pd', naam: 'Doel' }, { id: 'pd2', naam: 'Eindplateau' }],
    volgende_cursor: null,
  })
  api.componenten.lijst.mockResolvedValue({ items: [{ id: 'c2', naam: 'Belastingsysteem' }], volgende_cursor: null })
  api.contracten.lijst.mockResolvedValue({ items: [{ id: 'k2', contractnaam: 'Licentie', leverancier_naam: 'Oracle BV' }], volgende_cursor: null })
})
afterEach(() => vi.restoreAllMocks())

describe('GapDetailView — render + readiness', () => {
  it('toont overgang, readiness (telling+percentage) en leden', async () => {
    const { w } = await mountDetail()
    expect(w.find('[data-testid="gap-overgang"]').text()).toContain('Baseline')
    expect(w.find('[data-testid="gap-overgang"]').text()).toContain('Doel')
    // Beide plateaus als klikbare router-link in de header-subtitel.
    expect(w.find('[data-testid="gap-baseline-link"]').text()).toContain('Baseline')
    expect(w.find('[data-testid="gap-doel-link"]').text()).toContain('Doel')
    expect(w.find('[data-testid="readiness-technisch"]').text()).toContain('3 van 5 (60%)')
    expect(w.find('[data-testid="readiness-contractueel"]').text()).toContain('Nog geen leden')
    expect(w.find('[data-testid="readiness-uitleg"]').text()).toContain('automatisch afgeleid')
    expect(w.find('[data-testid="gap-leden-tabel"]').text()).toContain('Oracle FIN-DB')
  })

  it('readiness is read-only: geen invoerveld/zet-knop', async () => {
    const { w } = await mountDetail()
    const blok = w.find('[data-testid="readiness-technisch"]')
    expect(blok.find('input').exists()).toBe(false)
    expect(blok.find('button').exists()).toBe(false)
  })

  it('viewer ziet geen beheer-acties', async () => {
    const { w } = await mountDetail({ rollen: ['viewer'] })
    expect(w.find('[data-testid="gap-bewerken"]').exists()).toBe(false)
    expect(w.find('[data-testid="gap-verwijderen"]').exists()).toBe(false)
    expect(w.find('[data-testid="gap-lid-koppelen"]').exists()).toBe(false)
    expect(w.find('[data-testid="gap-lid-ontkoppel-rl1"]').exists()).toBe(false)
  })
})

describe('GapDetailView — wijzigen/verwijderen', () => {
  it('bewerken stuurt werkBij incl. baseline/doel (voorgevuld)', async () => {
    api.gaps.werkBij.mockResolvedValueOnce(_gap({ naam: 'Kloof A (2026)' }))
    const { w } = await mountDetail()
    await w.find('[data-testid="gap-bewerken"]').trigger('click')
    await w.find('[data-testid="ge-naam"]').setValue('Kloof A (2026)')
    await w.find('[data-testid="gap-edit-form"]').trigger('submit')
    await flushPromises()
    expect(api.gaps.werkBij).toHaveBeenCalledWith(ID, {
      naam: 'Kloof A (2026)', toelichting: 'overgang', baseline_plateau_id: 'pb', doel_plateau_id: 'pd',
    })
  })

  it('baseline/doel zijn wijzigbaar: nieuw doel kiezen stuurt mee', async () => {
    api.gaps.werkBij.mockResolvedValueOnce(_gap({ doel_plateau_id: 'pd2' }))
    const { w } = await mountDetail()
    await w.find('[data-testid="gap-bewerken"]').trigger('click')
    await kiesZoek(w, 'ge-doel-zoek', 'pd2')
    await w.find('[data-testid="gap-edit-form"]').trigger('submit')
    await flushPromises()
    expect(api.gaps.werkBij).toHaveBeenCalledWith(
      ID,
      expect.objectContaining({ baseline_plateau_id: 'pb', doel_plateau_id: 'pd2' }),
    )
  })

  it('baseline == doel bij bewerken wordt client-side geweigerd', async () => {
    const { w } = await mountDetail()
    await w.find('[data-testid="gap-bewerken"]').trigger('click')
    await kiesZoek(w, 'ge-doel-zoek', 'pb') // doel := baseline
    await w.find('[data-testid="gap-edit-form"]').trigger('submit')
    await flushPromises()
    expect(w.find('[data-testid="ge-fout-doel"]').exists()).toBe(true)
    expect(api.gaps.werkBij).not.toHaveBeenCalled()
  })

  it('verwijderen navigeert naar de lijst', async () => {
    api.gaps.verwijder.mockResolvedValueOnce(null)
    const { w, router } = await mountDetail()
    await w.find('[data-testid="gap-verwijderen"]').trigger('click')
    await w.find('[data-testid="gap-verwijder-bevestig"]').trigger('click')
    await flushPromises()
    expect(api.gaps.verwijder).toHaveBeenCalledWith(ID)
    expect(router.currentRoute.value.name).toBe('gap-lijst')
  })
})

describe('GapDetailView — leden + readiness-rollup', () => {
  it('koppelt een component-lid en herlaadt readiness (gaps.haal opnieuw)', async () => {
    api.gaps.voegLid.mockResolvedValueOnce({ id: 'rl2' })
    const { w } = await mountDetail()
    const haalVoor = api.gaps.haal.mock.calls.length
    await w.find('[data-testid="gap-lid-koppelen"]').trigger('click')
    await kiesZoek(w, 'gap-lid-zoek', 'c2')
    await w.find('[data-testid="gap-lid-form"]').trigger('submit')
    await flushPromises()
    expect(api.gaps.voegLid).toHaveBeenCalledWith(ID, 'c2')
    expect(api.gaps.haal.mock.calls.length).toBe(haalVoor + 1) // readiness meebewogen
  })

  it('contract-lid koppelen via type-toggle', async () => {
    api.gaps.voegLid.mockResolvedValueOnce({ id: 'rl3' })
    const { w } = await mountDetail()
    await w.find('[data-testid="gap-lid-koppelen"]').trigger('click')
    await w.find('[data-testid="gl-type"]').setValue('contract')
    await flushPromises()
    await kiesZoek(w, 'gap-lid-zoek', 'k2')
    await w.find('[data-testid="gap-lid-form"]').trigger('submit')
    await flushPromises()
    expect(api.gaps.voegLid).toHaveBeenCalledWith(ID, 'k2')
  })

  it('koppelen vereist een keuze (geen API-call zonder lid)', async () => {
    const { w } = await mountDetail()
    await w.find('[data-testid="gap-lid-koppelen"]').trigger('click')
    await w.find('[data-testid="gap-lid-form"]').trigger('submit')
    await flushPromises()
    expect(w.find('[data-testid="gap-lid-fout"]').exists()).toBe(true)
    expect(api.gaps.voegLid).not.toHaveBeenCalled()
  })

  it('ontkoppelen stuurt verwijderLid en herlaadt readiness', async () => {
    api.gaps.verwijderLid.mockResolvedValueOnce(null)
    const { w } = await mountDetail()
    const haalVoor = api.gaps.haal.mock.calls.length
    await w.find('[data-testid="gap-lid-ontkoppel-rl1"]').trigger('click')
    await flushPromises()
    expect(api.gaps.verwijderLid).toHaveBeenCalledWith(ID, 'rl1')
    expect(api.gaps.haal.mock.calls.length).toBe(haalVoor + 1)
  })

  it('lege leden-lijst toont een koppel-uitleg', async () => {
    api.gaps.leden.mockResolvedValue([])
    const { w } = await mountDetail()
    const leeg = w.find('[data-testid="gap-leden-leeg"]')
    expect(leeg.exists()).toBe(true)
    expect(leeg.text()).toContain('+ Lid koppelen')
  })
})
