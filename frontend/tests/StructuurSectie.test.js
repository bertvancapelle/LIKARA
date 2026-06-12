/** Tests — StructuurSectie (de Opbouw-laag; ADR-021 Fase D, CD054b). */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'

vi.mock('@/api', () => ({
  api: {
    componenten: { lijst: vi.fn(), structuur: vi.fn(), opties: vi.fn() },
    componentStructuren: { maak: vi.fn(), werkBij: vi.fn(), verwijder: vi.fn() },
  },
}))

import { api } from '@/api'
import { useAuthStore } from '@/store/auth'
import StructuurSectie from '@modules/bwb_ontvlechting/frontend/views/StructuurSectie.vue'

const COMP = 'comp-1'

function maakRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/componenten/:id', name: 'component-detail', component: { template: '<div/>' } },
      { path: '/applicaties/:id', name: 'applicatie-detail', component: { template: '<div/>' } },
    ],
  })
}

async function mountSectie({ rollen = ['beheerder'] } = {}) {
  const router = maakRouter()
  await router.push('/componenten/comp-1')
  await router.isReady()
  const pinia = createPinia()
  const auth = useAuthStore(pinia)
  auth.user = { sub: 's', tenant_id: 't', email: 'a@b.nl', roles: rollen }
  const w = mount(StructuurSectie, {
    props: { componentId: COMP },
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

const _draaitOp = () => ({
  structuur_id: 's-1',
  component_id: 'db-1',
  naam: 'Oracle FIN-DB',
  componenttype: 'database',
  relatietype: 'draait_op',
  relatietype_label: 'Draait op',
  omschrijving: null,
})
const _gebruiktDoor = () => ({
  structuur_id: 's-2',
  component_id: 'app-9',
  naam: 'Belastingsysteem',
  componenttype: 'applicatie',
  relatietype: 'draait_op',
  relatietype_label: 'Draait op',
  omschrijving: null,
})

beforeEach(() => {
  vi.clearAllMocks()
  api.componenten.structuur.mockResolvedValue({ draait_op: [], gebruikt_door: [] })
  api.componenten.opties.mockResolvedValue({
    componenttype: [],
    structuurrelatie_type: [{ optie_sleutel: 'draait_op', label: 'Draait op' }],
  })
  api.componenten.lijst.mockResolvedValue({
    items: [{ id: 'db-1', naam: 'Oracle FIN-DB' }],
    volgende_cursor: null,
  })
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('StructuurSectie', () => {
  it('rendert beide richtingen met labels; subtype-buur linkt naar ApplicatieDetail', async () => {
    api.componenten.structuur.mockResolvedValueOnce({
      draait_op: [_draaitOp()],
      gebruikt_door: [_gebruiktDoor()],
    })
    const w = await mountSectie()

    const draait = w.find('[data-testid="st-tabel-draait-op"]')
    expect(draait.text()).toContain('Oracle FIN-DB')
    expect(draait.text()).toContain('Draait op')

    const gebruikt = w.find('[data-testid="st-tabel-gebruikt-door"]')
    expect(gebruikt.text()).toContain('Belastingsysteem')

    // De applicatie-subtype-buur navigeert naar ApplicatieDetail.
    const appLink = gebruikt.find('a')
    expect(appLink.attributes('href')).toContain('/applicaties/app-9')
    // De database-buur navigeert naar ComponentDetail.
    const dbLink = draait.find('a')
    expect(dbLink.attributes('href')).toContain('/componenten/db-1')
  })

  it('toevoegen: ZoekSelect-doel + verplicht relatietype → componentStructuren.maak', async () => {
    api.componentStructuren.maak.mockResolvedValueOnce({})
    const w = await mountSectie()

    await w.find('[data-testid="st-toevoegen"]').trigger('click')
    await flushPromises()
    await kiesZoek(w, 'st-veld-doel', 'db-1')
    await w.find('[data-testid="st-veld-relatietype"]').setValue('draait_op')
    await w.find('[data-testid="st-form"]').trigger('submit')
    await flushPromises()

    expect(api.componentStructuren.maak).toHaveBeenCalledWith({
      component_id: COMP,
      op_component_id: 'db-1',
      relatietype: 'draait_op',
      omschrijving: null,
    })
  })

  it('toevoegen zonder relatietype valideert client-side (geen API-call)', async () => {
    const w = await mountSectie()
    await w.find('[data-testid="st-toevoegen"]').trigger('click')
    await flushPromises()
    await kiesZoek(w, 'st-veld-doel', 'db-1')
    await w.find('[data-testid="st-form"]').trigger('submit')
    await flushPromises()
    expect(api.componentStructuren.maak).not.toHaveBeenCalled()
    expect(w.find('[data-testid="st-fout-relatietype"]').exists()).toBe(true)
  })

  it('wijzigen: alleen relatietype/omschrijving → componentStructuren.werkBij', async () => {
    api.componenten.structuur.mockResolvedValueOnce({ draait_op: [_draaitOp()], gebruikt_door: [] })
    api.componentStructuren.werkBij.mockResolvedValueOnce({})
    const w = await mountSectie()

    await w.find('[data-testid="st-bewerk-s-1"]').trigger('click')
    await flushPromises()
    await w.find('[data-testid="st-veld-relatietype"]').setValue('draait_op')
    await w.find('[data-testid="st-form"]').trigger('submit')
    await flushPromises()

    expect(api.componentStructuren.werkBij).toHaveBeenCalledWith('s-1', {
      relatietype: 'draait_op',
      omschrijving: null,
    })
  })

  it('ontkoppelen via bevestigingsdialog → componentStructuren.verwijder', async () => {
    api.componenten.structuur.mockResolvedValueOnce({ draait_op: [_draaitOp()], gebruikt_door: [] })
    api.componentStructuren.verwijder.mockResolvedValueOnce({})
    const w = await mountSectie()

    await w.find('[data-testid="st-ontkoppel-s-1"]').trigger('click')
    await flushPromises()
    await w.find('[data-testid="st-ontkoppel-bevestig"]').trigger('click')
    await flushPromises()

    expect(api.componentStructuren.verwijder).toHaveBeenCalledWith('s-1')
  })

  it.each([
    ['ZELFVERWIJZING', 422],
    ['RELATIE_BESTAAT', 409],
    ['ONGELDIGE_OPTIE', 422],
  ])('foutpad %s wordt afgevangen (geen sectie-refetch)', async (code, status) => {
    api.componentStructuren.maak.mockRejectedValueOnce({ status, code, message: 'fout' })
    const w = await mountSectie()
    const refetchVoor = api.componenten.structuur.mock.calls.length

    await w.find('[data-testid="st-toevoegen"]').trigger('click')
    await flushPromises()
    await kiesZoek(w, 'st-veld-doel', 'db-1')
    await w.find('[data-testid="st-veld-relatietype"]').setValue('draait_op')
    await w.find('[data-testid="st-form"]').trigger('submit')
    await flushPromises()

    expect(api.componentStructuren.maak).toHaveBeenCalled()
    // Mislukte mutatie → geen herlaad van de sectie (en sowieso nooit een engine-call,
    // die de sectie niet importeert; de structuur voedt de engine niet, ADR-021).
    expect(api.componenten.structuur.mock.calls.length).toBe(refetchVoor)
  })

  it('zonder schrijfrol geen toevoeg-/rij-acties', async () => {
    api.componenten.structuur.mockResolvedValueOnce({ draait_op: [_draaitOp()], gebruikt_door: [] })
    const w = await mountSectie({ rollen: ['viewer'] })
    expect(w.find('[data-testid="st-toevoegen"]').exists()).toBe(false)
    expect(w.find('[data-testid="st-ontkoppel-s-1"]').exists()).toBe(false)
  })
})
