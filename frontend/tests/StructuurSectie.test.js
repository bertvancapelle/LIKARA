/** Tests — StructuurSectie (de Opbouw-laag; ADR-021 Fase D / ADR-023 Fase C).
 *
 * Draait-op-relaties worden sinds de ADR-023-cutover via het unified relatiemodel
 * (`api.relaties`, assignment host→gehoste) gelegd — niet meer via de vervallen
 * `component-structuren`-CRUD. */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'

vi.mock('@/api', () => ({
  api: {
    componenten: { lijst: vi.fn(), structuur: vi.fn() },
    relaties: { maak: vi.fn(), werkBij: vi.fn(), verwijder: vi.fn() },
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

// ADR-023: de structuurgraaf wordt afgeleid uit assignment-relaties; `structuur_id`
// is de relatie-id (waarop werkBij/verwijder via `api.relaties` werken).
const _draaitOp = () => ({
  structuur_id: 's-1',
  component_id: 'db-1',
  naam: 'Oracle FIN-DB',
  componenttype: 'database',
  relatietype: 'assignment',
  relatietype_label: 'Assignment',
  omschrijving: null,
})
const _gebruiktDoor = () => ({
  structuur_id: 's-2',
  component_id: 'app-9',
  naam: 'Belastingsysteem',
  componenttype: 'applicatie',
  relatietype: 'assignment',
  relatietype_label: 'Assignment',
  omschrijving: null,
})

beforeEach(() => {
  vi.clearAllMocks()
  api.componenten.structuur.mockResolvedValue({ draait_op: [], gebruikt_door: [] })
  api.componenten.lijst.mockResolvedValue({
    items: [{ id: 'db-1', naam: 'Oracle FIN-DB' }],
    volgende_cursor: null,
  })
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('StructuurSectie', () => {
  it('rendert beide richtingen; elke buur linkt naar ComponentDetail (LI059)', async () => {
    api.componenten.structuur.mockResolvedValueOnce({
      draait_op: [_draaitOp()],
      gebruikt_door: [_gebruiktDoor()],
    })
    const w = await mountSectie()

    const draait = w.find('[data-testid="st-tabel-draait-op"]')
    expect(draait.text()).toContain('Oracle FIN-DB')

    const gebruikt = w.find('[data-testid="st-tabel-gebruikt-door"]')
    expect(gebruikt.text()).toContain('Belastingsysteem')

    // De buur (élk type) navigeert naar ComponentDetail (LI059).
    const appLink = gebruikt.find('a')
    expect(appLink.attributes('href')).toContain('/componenten/app-9')
    // De database-buur navigeert naar ComponentDetail.
    const dbLink = draait.find('a')
    expect(dbLink.attributes('href')).toContain('/componenten/db-1')
  })

  it('toevoegen: ZoekSelect-doel → relaties.maak (assignment, host→gehoste = bron→doel)', async () => {
    api.relaties.maak.mockResolvedValueOnce({})
    const w = await mountSectie()

    await w.find('[data-testid="st-toevoegen"]').trigger('click')
    await flushPromises()
    await kiesZoek(w, 'st-veld-doel', 'db-1')
    await w.find('[data-testid="st-form"]').trigger('submit')
    await flushPromises()

    // "Dit component draait op db-1": bron = de gekozen host (db-1), doel = dit component.
    expect(api.relaties.maak).toHaveBeenCalledWith({
      bron_id: 'db-1',
      doel_id: COMP,
      relatietype: 'assignment',
      omschrijving: null,
    })
  })

  it('toevoegen zonder doel valideert client-side (geen API-call)', async () => {
    const w = await mountSectie()
    await w.find('[data-testid="st-toevoegen"]').trigger('click')
    await flushPromises()
    await w.find('[data-testid="st-form"]').trigger('submit')
    await flushPromises()
    expect(api.relaties.maak).not.toHaveBeenCalled()
    expect(w.find('[data-testid="st-fout-doel"]').exists()).toBe(true)
  })

  it('wijzigen: alleen omschrijving → relaties.werkBij (endpoints/relatietype immutabel)', async () => {
    api.componenten.structuur.mockResolvedValueOnce({ draait_op: [_draaitOp()], gebruikt_door: [] })
    api.relaties.werkBij.mockResolvedValueOnce({})
    const w = await mountSectie()

    await w.find('[data-testid="st-bewerk-s-1"]').trigger('click')
    await flushPromises()
    await w.find('[data-testid="st-veld-omschrijving"]').setValue('Gedeelde database')
    await w.find('[data-testid="st-form"]').trigger('submit')
    await flushPromises()

    expect(api.relaties.werkBij).toHaveBeenCalledWith('s-1', { omschrijving: 'Gedeelde database' })
  })

  it('ontkoppelen via bevestigingsdialog → relaties.verwijder', async () => {
    api.componenten.structuur.mockResolvedValueOnce({ draait_op: [_draaitOp()], gebruikt_door: [] })
    api.relaties.verwijder.mockResolvedValueOnce({})
    const w = await mountSectie()

    await w.find('[data-testid="st-ontkoppel-s-1"]').trigger('click')
    await flushPromises()
    await w.find('[data-testid="st-ontkoppel-bevestig"]').trigger('click')
    await flushPromises()

    expect(api.relaties.verwijder).toHaveBeenCalledWith('s-1')
  })

  it.each([
    ['ZELFVERWIJZING', 422],
    ['RELATIE_BESTAAT', 409],
  ])('foutpad %s wordt afgevangen (geen sectie-refetch)', async (code, status) => {
    api.relaties.maak.mockRejectedValueOnce({ status, code, message: 'fout' })
    const w = await mountSectie()
    const refetchVoor = api.componenten.structuur.mock.calls.length

    await w.find('[data-testid="st-toevoegen"]').trigger('click')
    await flushPromises()
    await kiesZoek(w, 'st-veld-doel', 'db-1')
    await w.find('[data-testid="st-form"]').trigger('submit')
    await flushPromises()

    expect(api.relaties.maak).toHaveBeenCalled()
    // Mislukte mutatie → geen herlaad van de sectie (en nooit een engine-call; de
    // structuur voedt de engine niet, ADR-021).
    expect(api.componenten.structuur.mock.calls.length).toBe(refetchVoor)
  })

  it('zonder schrijfrol geen toevoeg-/rij-acties', async () => {
    api.componenten.structuur.mockResolvedValueOnce({ draait_op: [_draaitOp()], gebruikt_door: [] })
    const w = await mountSectie({ rollen: ['viewer'] })
    expect(w.find('[data-testid="st-toevoegen"]').exists()).toBe(false)
    expect(w.find('[data-testid="st-ontkoppel-s-1"]').exists()).toBe(false)
  })

  it('LI037 rol-gating: medewerker mag toevoegen/bewerken maar NIET ontkoppelen (VERWIJDEREN = beheerder)', async () => {
    api.componenten.structuur.mockResolvedValue({ draait_op: [_draaitOp()], gebruikt_door: [] })
    const m = await mountSectie({ rollen: ['medewerker'] })
    expect(m.find('[data-testid="st-toevoegen"]').exists()).toBe(true)
    expect(m.find('[data-testid="st-bewerk-s-1"]').exists()).toBe(true)
    expect(m.find('[data-testid="st-ontkoppel-s-1"]').exists()).toBe(false)
    const b = await mountSectie({ rollen: ['beheerder'] })
    expect(b.find('[data-testid="st-ontkoppel-s-1"]').exists()).toBe(true)
  })
})
