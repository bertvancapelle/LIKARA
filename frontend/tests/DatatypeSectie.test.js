/** Tests — DatatypeSectie (child-sectie via @modules). */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'

vi.mock('@/api', () => ({
  api: {
    datatypes: {
      lijst: vi.fn(),
      maak: vi.fn(),
      werkBij: vi.fn(),
      verwijder: vi.fn(),
      opties: vi.fn(),
    },
  },
}))

import DataTable from 'primevue/datatable'
import { api } from '@/api'
import { useAuthStore } from '@/store/auth'
import DatatypeSectie from '@modules/bwb_ontvlechting/frontend/views/DatatypeSectie.vue'

const APP = 'app-1'

function _dt(naamveld, id) {
  return { id, categorie: 'documenten', omschrijving: naamveld, omvang_indicatie: '10GB' }
}

async function mountSectie({ rollen = ['beheerder'] } = {}) {
  const pinia = createPinia()
  const auth = useAuthStore(pinia)
  auth.user = { sub: 's', tenant_id: 't', email: 'a@b.nl', roles: rollen }
  const wrapper = mount(DatatypeSectie, {
    props: { applicatieId: APP },
    attachTo: document.body, // nodig zodat .focus() document.activeElement zet
    global: {
      plugins: [pinia, [PrimeVue, { unstyled: true }], ToastService],
      stubs: { teleport: true },
    },
  })
  await flushPromises()
  return wrapper
}

beforeEach(() => {
  vi.clearAllMocks()
  api.datatypes.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
  api.datatypes.opties.mockResolvedValue({ categorie: ['documenten', 'email', 'binair'] })
})
afterEach(() => vi.restoreAllMocks())

describe('DatatypeSectie', () => {
  it('rendert de geladen datatypes (gescoopt op de applicatie)', async () => {
    api.datatypes.lijst.mockResolvedValueOnce({ items: [_dt('Zaakdocumenten', 'd1')], volgende_cursor: null })
    const w = await mountSectie()
    expect(api.datatypes.lijst).toHaveBeenCalledWith({ applicatie_id: APP, limit: 25, after: undefined })
    expect(w.text()).toContain('Zaakdocumenten')
  })

  it('"Meer laden" gebruikt de volgende_cursor en verdwijnt bij null', async () => {
    api.datatypes.lijst
      .mockResolvedValueOnce({ items: [_dt('A', 'd1')], volgende_cursor: 'c1' })
      .mockResolvedValueOnce({ items: [_dt('B', 'd2')], volgende_cursor: null })
    const w = await mountSectie()
    await w.find('[data-testid="dt-meer"]').trigger('click')
    await flushPromises()
    expect(api.datatypes.lijst).toHaveBeenLastCalledWith({ applicatie_id: APP, limit: 25, after: 'c1' })
    expect(w.find('[data-testid="dt-meer"]').exists()).toBe(false)
  })

  it('rol-gating: viewer ziet geen Toevoegen, medewerker wel', async () => {
    const viewer = await mountSectie({ rollen: ['viewer'] })
    expect(viewer.find('[data-testid="dt-toevoegen"]').exists()).toBe(false)
    const mede = await mountSectie({ rollen: ['medewerker'] })
    expect(mede.find('[data-testid="dt-toevoegen"]').exists()).toBe(true)
  })

  it('LI037 rol-gating: medewerker mag bewerken maar NIET verwijderen (VERWIJDEREN = beheerder)', async () => {
    api.datatypes.lijst.mockResolvedValue({ items: [_dt('Zaakdocumenten', 'd1')], volgende_cursor: null })
    const m = await mountSectie({ rollen: ['medewerker'] })
    expect(m.find('[data-testid="dt-bewerk-d1"]').exists()).toBe(true)
    expect(m.find('[data-testid="dt-verwijder-d1"]').exists()).toBe(false)
    const b = await mountSectie({ rollen: ['beheerder'] })
    expect(b.find('[data-testid="dt-verwijder-d1"]').exists()).toBe(true)
  })

  it('validatie blokkeert submit bij ontbrekende categorie', async () => {
    const w = await mountSectie()
    await w.find('[data-testid="dt-toevoegen"]').trigger('click')
    await flushPromises()
    await w.find('[data-testid="dt-form"]').trigger('submit')
    await flushPromises()
    expect(w.find('[data-testid="dt-fout-categorie"]').exists()).toBe(true)
    expect(api.datatypes.maak).not.toHaveBeenCalled()
  })

  it('focust het eerste veld bij openen van de Dialog', async () => {
    const w = await mountSectie()
    await w.find('[data-testid="dt-toevoegen"]').trigger('click')
    await flushPromises()
    await new Promise((r) => setTimeout(r, 0)) // focusEerste defert ná de focustrap
    expect(document.activeElement).toBe(w.find('[data-testid="dt-veld-categorie"]').element)
  })

  it('toont 422-veldfout in de Dialog op het juiste veld', async () => {
    const err = new Error('val')
    err.status = 422
    err.detail = [{ loc: ['body', 'omvang_indicatie'], msg: 'te lang' }]
    api.datatypes.maak.mockRejectedValueOnce(err)
    const w = await mountSectie()
    await w.find('[data-testid="dt-toevoegen"]').trigger('click')
    await flushPromises()
    await w.find('[data-testid="dt-veld-categorie"]').setValue('documenten')
    await w.find('[data-testid="dt-form"]').trigger('submit')
    await flushPromises()
    expect(w.find('[data-testid="dt-fout-omvang"]').text()).toContain('te lang')
  })

  it('ververst de lijst na een geslaagde aanmaak', async () => {
    api.datatypes.maak.mockResolvedValueOnce({ id: 'new' })
    const w = await mountSectie()
    const voor = api.datatypes.lijst.mock.calls.length
    await w.find('[data-testid="dt-toevoegen"]').trigger('click')
    await flushPromises()
    await w.find('[data-testid="dt-veld-categorie"]').setValue('documenten')
    await w.find('[data-testid="dt-form"]').trigger('submit')
    await flushPromises()
    expect(api.datatypes.maak).toHaveBeenCalledTimes(1)
    expect(api.datatypes.lijst.mock.calls.length).toBe(voor + 1) // refresh
  })
})

describe('DatatypeSectie — sortering (CD020)', () => {
  it('default-laad stuurt géén sort/order mee (backwards-compatible)', async () => {
    await mountSectie()
    expect(api.datatypes.lijst).toHaveBeenLastCalledWith({ applicatie_id: APP, limit: 25, after: undefined })
  })

  it('sorteerklik → refetch met sort/order + cursor-reset', async () => {
    api.datatypes.lijst.mockResolvedValueOnce({ items: [_dt('A', 'd1')], volgende_cursor: 'c1' })
    const w = await mountSectie()
    w.findComponent(DataTable).vm.$emit('sort', { sortField: 'omschrijving', sortOrder: -1 })
    await flushPromises()
    expect(api.datatypes.lijst).toHaveBeenLastCalledWith({
      applicatie_id: APP,
      limit: 25,
      after: undefined, // cursor-reset ondanks de eerdere volgende_cursor 'c1'
      sort: 'omschrijving',
      order: 'desc',
    })
  })

  it('vertaalt sortOrder 1 naar asc', async () => {
    const w = await mountSectie()
    w.findComponent(DataTable).vm.$emit('sort', { sortField: 'categorie', sortOrder: 1 })
    await flushPromises()
    expect(api.datatypes.lijst).toHaveBeenLastCalledWith(
      expect.objectContaining({ sort: 'categorie', order: 'asc' }),
    )
  })
})
