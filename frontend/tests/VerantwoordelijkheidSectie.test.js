/** Tests — VerantwoordelijkheidSectie (rol-toewijzing óp een object; ADR-024 slice 2b). */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'

vi.mock('@/api', () => ({
  api: {
    roltoewijzingen: { lijst: vi.fn(), rollen: vi.fn(), maak: vi.fn(), verwijder: vi.fn() },
    partijen: { lijst: vi.fn() },
  },
}))

import { api } from '@/api'
import { useAuthStore } from '@/store/auth'
import VerantwoordelijkheidSectie from '@modules/bwb_ontvlechting/frontend/views/VerantwoordelijkheidSectie.vue'

const OBJ = 'comp-1'

function maakRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/partijen/:id', name: 'partij-detail', component: { template: '<div/>' } }],
  })
}

async function mountSectie({ rollen = ['beheerder'] } = {}) {
  const router = maakRouter()
  await router.push('/partijen/p1')
  await router.isReady()
  const pinia = createPinia()
  const auth = useAuthStore(pinia)
  auth.user = { sub: 's', tenant_id: 't', email: 'a@b.nl', roles: rollen }
  const w = mount(VerantwoordelijkheidSectie, {
    props: { objectId: OBJ },
    attachTo: document.body,
    global: { plugins: [pinia, [PrimeVue, { unstyled: true }], ToastService, router], stubs: { teleport: true } },
  })
  await flushPromises()
  return w
}

async function kiesZoek(w, prefix, id) {
  await w.find(`[data-testid="${prefix}-input"]`).trigger('focus')
  await flushPromises()
  await w.find(`[data-testid="${prefix}-optie-${id}"]`).trigger('mousedown')
  await flushPromises()
}

const _rij = (over = {}) => ({
  toewijzing_id: 't1', rol: 'eigenaar', rol_label: 'Eigenaar',
  partij_id: 'p1', partij_naam: 'Jan de Vries', partij_aard: 'persoon', ...over,
})

beforeEach(() => {
  vi.clearAllMocks()
  api.roltoewijzingen.lijst.mockResolvedValue([_rij()])
  api.roltoewijzingen.rollen.mockResolvedValue([
    { optie_sleutel: 'functioneel_beheer', label: 'Functioneel beheer' },
    { optie_sleutel: 'eigenaar', label: 'Eigenaar' },
  ])
  api.partijen.lijst.mockResolvedValue({
    items: [
      { id: 'p1', naam: 'Jan de Vries', aard: 'persoon', afdeling_naam: 'Burgerzaken', organisatie_naam: 'Gemeente Tiel' },
      { id: 'p2', naam: 'Afdeling Inkoop', aard: 'organisatie_eenheid', organisatie_naam: 'Gemeente Tiel' },
    ],
    volgende_cursor: null,
  })
})
afterEach(() => vi.restoreAllMocks())

describe('VerantwoordelijkheidSectie', () => {
  it('toont de toegewezen rollen (rol-label + partij + aard)', async () => {
    const w = await mountSectie()
    expect(w.find('[data-testid="vw-tabel"]').text()).toContain('Eigenaar')
    expect(w.find('[data-testid="vw-tabel"]').text()).toContain('Jan de Vries')
    expect(w.find('[data-testid="vw-tabel"]').text()).toContain('Persoon')
    expect(api.roltoewijzingen.lijst).toHaveBeenCalledWith({ object_id: OBJ })
  })

  it('rol-gating: viewer geen toevoeg-knop, geen verwijder-knop', async () => {
    const w = await mountSectie({ rollen: ['viewer'] })
    expect(w.find('[data-testid="vw-toevoegen"]').exists()).toBe(false)
    expect(w.find('[data-testid="vw-verwijder-t1"]').exists()).toBe(false)
  })

  it('LI040-regressie: elke picker-optie toont de NAAM als scanlaag + gedempte identiteit', async () => {
    // De lat van deze test is bewust "zichtbare tekst", niet "component rendert":
    // de partijpicker-bug (ontbrekende IdentiteitLabel-import → lege regels met alleen
    // een aard-hint) bleef onder de oude asserts volledig groen.
    const w = await mountSectie()
    await w.find('[data-testid="vw-toevoegen"]').trigger('click')
    await flushPromises()
    await w.find('[data-testid="vw-veld-partij-input"]').trigger('focus')
    await flushPromises()
    expect(w.find('[data-testid="vw-veld-partij-optie-p1"]').text())
      .toContain('Jan de Vries — Burgerzaken — Gemeente Tiel')
    expect(w.find('[data-testid="vw-veld-partij-optie-p2"]').text())
      .toContain('Afdeling Inkoop — Gemeente Tiel')
    // En nergens de faal-marker van de bouwsteen.
    expect(w.find('[data-testid="identiteit-naam-ontbreekt"]').exists()).toBe(false)
  })

  it('toewijzen vereist partij én rol (geen API-call zonder rol)', async () => {
    const w = await mountSectie()
    await w.find('[data-testid="vw-toevoegen"]').trigger('click')
    await flushPromises()
    await kiesZoek(w, 'vw-veld-partij', 'p2')
    await w.find('[data-testid="vw-form"]').trigger('submit')
    await flushPromises()
    expect(w.find('[data-testid="vw-fout-rol"]').exists()).toBe(true)
    expect(api.roltoewijzingen.maak).not.toHaveBeenCalled()
  })

  it('toewijzen met partij+rol → maak + refetch', async () => {
    api.roltoewijzingen.maak.mockResolvedValueOnce({ toewijzing_id: 't2' })
    const w = await mountSectie()
    const voor = api.roltoewijzingen.lijst.mock.calls.length
    await w.find('[data-testid="vw-toevoegen"]').trigger('click')
    await flushPromises()
    await kiesZoek(w, 'vw-veld-partij', 'p2')
    await w.find('[data-testid="vw-veld-rol"]').setValue('functioneel_beheer')
    await w.find('[data-testid="vw-form"]').trigger('submit')
    await flushPromises()
    expect(api.roltoewijzingen.maak).toHaveBeenCalledWith({
      partij_id: 'p2', object_id: OBJ, rol: 'functioneel_beheer',
    })
    expect(api.roltoewijzingen.lijst.mock.calls.length).toBe(voor + 1)
  })

  it('409 TOEWIJZING_BESTAAT: geen refetch', async () => {
    api.roltoewijzingen.maak.mockRejectedValueOnce({ status: 409, code: 'TOEWIJZING_BESTAAT', message: 'al toegewezen' })
    const w = await mountSectie()
    const voor = api.roltoewijzingen.lijst.mock.calls.length
    await w.find('[data-testid="vw-toevoegen"]').trigger('click')
    await flushPromises()
    await kiesZoek(w, 'vw-veld-partij', 'p2')
    await w.find('[data-testid="vw-veld-rol"]').setValue('eigenaar')
    await w.find('[data-testid="vw-form"]').trigger('submit')
    await flushPromises()
    expect(api.roltoewijzingen.maak).toHaveBeenCalledTimes(1)
    expect(api.roltoewijzingen.lijst.mock.calls.length).toBe(voor)
  })

  it('verwijderen via bevestiging → verwijder + refetch', async () => {
    api.roltoewijzingen.verwijder.mockResolvedValueOnce(null)
    const w = await mountSectie()
    const voor = api.roltoewijzingen.lijst.mock.calls.length
    await w.find('[data-testid="vw-verwijder-t1"]').trigger('click')
    await w.find('[data-testid="vw-verwijder-bevestig"]').trigger('click')
    await flushPromises()
    expect(api.roltoewijzingen.verwijder).toHaveBeenCalledWith('t1')
    expect(api.roltoewijzingen.lijst.mock.calls.length).toBe(voor + 1)
  })

  it('lege staat zonder toewijzingen', async () => {
    api.roltoewijzingen.lijst.mockResolvedValueOnce([])
    const w = await mountSectie()
    expect(w.find('[data-testid="vw-leeg"]').exists()).toBe(true)
  })
})
