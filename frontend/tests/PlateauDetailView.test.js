/** Tests — PlateauDetailView (migratielaag: wijzigen/verwijderen + ledenbeheer; UX-A4-1).
 * ADR-046 besluit 2: de dispositie is als bestemmingsveld afgebouwd — het koppel-formulier
 * vraagt géén dispositie meer; een historische waarde blijft read-only zichtbaar. */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'

vi.mock('@/api', () => ({
  api: {
    plateaus: {
      haal: vi.fn(), leden: vi.fn(), werkBij: vi.fn(), verwijder: vi.fn(),
      voegLid: vi.fn(), werkLid: vi.fn(), verwijderLid: vi.fn(),
    },
    componenten: { lijst: vi.fn() },
    contracten: { lijst: vi.fn() },
  },
}))

import { api } from '@/api'
import { useAuthStore } from '@/store/auth'
import PlateauDetailView from '@/views/migratie/PlateauDetailView.vue'

const ID = 'pl1'

function maakRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/migratie/plateaus', name: 'plateau-lijst', component: { template: '<div/>' } },
      { path: '/migratie/plateaus/:id', name: 'plateau-detail', component: PlateauDetailView, props: true },
    ],
  })
}

async function mountDetail({ rollen = ['beheerder'] } = {}) {
  const router = maakRouter()
  await router.push(`/migratie/plateaus/${ID}`)
  await router.isReady()
  const pinia = createPinia()
  const auth = useAuthStore(pinia)
  auth.user = { sub: 's', tenant_id: 't', email: 'a@b.nl', roles: rollen }
  const w = mount(PlateauDetailView, {
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

// ADR-046 — nieuwe leden dragen géén dispositie meer (null); de read exposeert het veld
// nog voor historische rijen (zie de historisch-test onderaan).
const _lidComp = () => ({
  id: 'rel1', plateau_id: ID, lid_id: 'c1', lid_element_type: 'component', lid_naam: 'Oracle FIN-DB',
  dispositie: null, dispositie_label: null, contractueel_bevestigd: false,
  bevestigd_aantal_gebruikers: null, bevestigd_door: null, bevestigd_op: null,
})

beforeEach(() => {
  vi.clearAllMocks()
  api.plateaus.haal.mockResolvedValue({ id: ID, naam: 'Huidig', toelichting: 'startbeeld' })
  api.plateaus.leden.mockResolvedValue([_lidComp()])
  api.componenten.lijst.mockResolvedValue({ items: [{ id: 'c2', naam: 'Belastingsysteem' }], volgende_cursor: null })
  api.contracten.lijst.mockResolvedValue({
    items: [{ id: 'k2', contractnaam: 'Oracle licentie', leverancier_naam: 'Oracle BV' }], volgende_cursor: null,
  })
})
afterEach(() => vi.restoreAllMocks())

describe('PlateauDetailView — render + rol-gating', () => {
  it('toont leden met naam en type; geen dispositie-kolom zonder historische waarden', async () => {
    const { w } = await mountDetail()
    const t = w.find('[data-testid="plateau-leden-tabel"]').text()
    expect(t).toContain('Oracle FIN-DB')
    expect(t).toContain('Component')
    // ADR-046 — geen dispositie-invoer of -kolom meer voor dispositieloze leden.
    expect(t).not.toContain('Dispositie')
    expect(w.find('[data-testid="plateau-bewerken"]').exists()).toBe(true)
    expect(w.find('[data-testid="lid-koppelen"]').exists()).toBe(true)
  })

  it('viewer ziet geen beheer-acties', async () => {
    const { w } = await mountDetail({ rollen: ['viewer'] })
    expect(w.find('[data-testid="plateau-bewerken"]').exists()).toBe(false)
    expect(w.find('[data-testid="plateau-verwijderen"]').exists()).toBe(false)
    expect(w.find('[data-testid="lid-koppelen"]').exists()).toBe(false)
    expect(w.find('[data-testid="lid-ontkoppel-rel1"]').exists()).toBe(false)
  })

  it('medewerker mag koppelen maar niet ontkoppelen (alleen beheerder)', async () => {
    const { w } = await mountDetail({ rollen: ['medewerker'] })
    expect(w.find('[data-testid="lid-koppelen"]').exists()).toBe(true)
    expect(w.find('[data-testid="plateau-verwijderen"]').exists()).toBe(false)
    expect(w.find('[data-testid="lid-ontkoppel-rel1"]').exists()).toBe(false)
  })

  it('een HISTORISCHE dispositie blijft read-only leesbaar (kolom verschijnt)', async () => {
    api.plateaus.leden.mockResolvedValue([
      { ..._lidComp(), dispositie: 'migreren', dispositie_label: 'Migreren' },
    ])
    const { w } = await mountDetail()
    const t = w.find('[data-testid="plateau-leden-tabel"]').text()
    expect(t).toContain('Dispositie (historisch)')
    const tag = w.find('[data-testid="lid-dispositie-rel1"]')
    expect(tag.exists()).toBe(true)
    expect(tag.text()).toContain('Migreren')
    // Read-only: geen select/inline-wijziging meer.
    expect(tag.element.tagName).not.toBe('SELECT')
  })
})

describe('PlateauDetailView — plateau wijzigen/verwijderen', () => {
  it('bewerken stuurt werkBij', async () => {
    api.plateaus.werkBij.mockResolvedValueOnce({ id: ID, naam: 'Huidig (2026)', toelichting: 'startbeeld' })
    const { w } = await mountDetail()
    await w.find('[data-testid="plateau-bewerken"]').trigger('click')
    await w.find('[data-testid="pe-naam"]').setValue('Huidig (2026)')
    await w.find('[data-testid="plateau-edit-form"]').trigger('submit')
    await flushPromises()
    expect(api.plateaus.werkBij).toHaveBeenCalledWith(ID, { naam: 'Huidig (2026)', toelichting: 'startbeeld' })
  })

  it('verwijderen navigeert naar de plateau-lijst', async () => {
    api.plateaus.verwijder.mockResolvedValueOnce(null)
    const { w, router } = await mountDetail()
    await w.find('[data-testid="plateau-verwijderen"]').trigger('click')
    await w.find('[data-testid="plateau-verwijder-bevestig"]').trigger('click')
    await flushPromises()
    expect(api.plateaus.verwijder).toHaveBeenCalledWith(ID)
    expect(router.currentRoute.value.name).toBe('plateau-lijst')
  })
})

describe('PlateauDetailView — leden koppelen/ontkoppelen', () => {
  it('koppelt een component-lid ZONDER dispositie (ADR-046; geen bevestigingsvelden)', async () => {
    api.plateaus.voegLid.mockResolvedValueOnce({ id: 'rel2' })
    const { w } = await mountDetail()
    await w.find('[data-testid="lid-koppelen"]').trigger('click')
    await flushPromises()
    expect(w.find('[data-testid="lk-bevestiging"]').exists()).toBe(false) // component → geen bevestiging
    expect(w.find('[data-testid="lk-dispositie"]').exists()).toBe(false) // ADR-046 — veld bestaat niet meer
    await kiesZoek(w, 'lk-veld-lid', 'c2')
    await w.find('[data-testid="lid-koppel-form"]').trigger('submit')
    await flushPromises()
    expect(api.plateaus.voegLid).toHaveBeenCalledWith(ID, { lid_id: 'c2' })
  })

  it('contract-lid toont de contractuele bevestiging en stuurt die mee (onveranderd)', async () => {
    api.plateaus.voegLid.mockResolvedValueOnce({ id: 'rel3' })
    const { w } = await mountDetail()
    await w.find('[data-testid="lid-koppelen"]').trigger('click')
    await flushPromises()
    await w.find('[data-testid="lk-type"]').setValue('contract')
    await flushPromises()
    expect(w.find('[data-testid="lk-bevestiging"]').exists()).toBe(true)
    await kiesZoek(w, 'lk-veld-lid', 'k2')
    await w.find('[data-testid="lk-bevestigd"]').setValue(true)
    await w.find('[data-testid="lk-aantal"]').setValue('250')
    await w.find('[data-testid="lid-koppel-form"]').trigger('submit')
    await flushPromises()
    expect(api.plateaus.voegLid).toHaveBeenCalledWith(ID, {
      lid_id: 'k2', contractueel_bevestigd: true, bevestigd_aantal_gebruikers: 250,
    })
  })

  it('koppelen vereist een lid (geen API-call zonder lid)', async () => {
    const { w } = await mountDetail()
    await w.find('[data-testid="lid-koppelen"]').trigger('click')
    await flushPromises()
    await w.find('[data-testid="lid-koppel-form"]').trigger('submit')
    await flushPromises()
    expect(w.find('[data-testid="lk-fout-lid"]').exists()).toBe(true)
    expect(api.plateaus.voegLid).not.toHaveBeenCalled()
  })

  it('ontkoppelen via bevestiging stuurt verwijderLid + refetch', async () => {
    api.plateaus.verwijderLid.mockResolvedValueOnce(null)
    const { w } = await mountDetail()
    const voor = api.plateaus.leden.mock.calls.length
    await w.find('[data-testid="lid-ontkoppel-rel1"]').trigger('click')
    await w.find('[data-testid="lid-ontkoppel-bevestig"]').trigger('click')
    await flushPromises()
    expect(api.plateaus.verwijderLid).toHaveBeenCalledWith(ID, 'rel1')
    expect(api.plateaus.leden.mock.calls.length).toBe(voor + 1)
  })

  it('leeg plateau toont een koppel-uitleg', async () => {
    api.plateaus.leden.mockResolvedValue([])
    const { w } = await mountDetail()
    const leeg = w.find('[data-testid="plateau-leden-leeg"]')
    expect(leeg.exists()).toBe(true)
    expect(leeg.text()).toContain('+ Lid koppelen')
  })
})
