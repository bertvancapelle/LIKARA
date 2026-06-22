/** Tests — ContractFormulier (mantel-conditioneel + filter; checkbox-sets; envelopes). */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'

vi.mock('@/api', () => ({
  api: {
    partijen: { lijst: vi.fn() },
    contractconfig: { opties: vi.fn() },
    contracten: { lijst: vi.fn(), maak: vi.fn(), haal: vi.fn(), werkBij: vi.fn() },
  },
}))

import { api } from '@/api'
import { useAuthStore } from '@/store/auth'
import ContractFormulier from '@modules/bwb_ontvlechting/frontend/views/ContractFormulier.vue'

function maakRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/contracten', name: 'contract-lijst', component: { template: '<div/>' } },
      { path: '/contracten/nieuw', name: 'contract-nieuw', component: ContractFormulier },
      { path: '/contracten/:id', name: 'contract-detail', component: { template: '<div/>' } },
    ],
  })
}

async function mountForm({ id = null } = {}) {
  const router = maakRouter()
  await router.push('/contracten/nieuw')
  await router.isReady()
  const pinia = createPinia()
  const auth = useAuthStore(pinia)
  auth.user = { sub: 's', tenant_id: 't', email: 'a@b.nl', roles: ['medewerker'] }
  const w = mount(ContractFormulier, {
    props: { id },
    global: { plugins: [pinia, [PrimeVue, { unstyled: true }], ToastService, router] },
  })
  await flushPromises()
  return { w, router }
}

// ZoekSelect-interactie: focus → zoek → klik resultaat (CD049).
async function kiesZoek(w, prefix, id) {
  await w.find(`[data-testid="${prefix}-input"]`).trigger('focus')
  await flushPromises()
  await w.find(`[data-testid="${prefix}-optie-${id}"]`).trigger('mousedown')
  await flushPromises()
}

async function vulBasis(w) {
  await kiesZoek(w, 'veld-leverancier', 'l1')
  await w.find('[data-testid="veld-contracttype"]').setValue('los_contract')
  await w.find('[data-testid="veld-contractnaam"]').setValue('Contract A')
  await flushPromises()
}

beforeEach(() => {
  vi.clearAllMocks()
  api.partijen.lijst.mockResolvedValue({ items: [{ id: 'l1', naam: 'Acme BV' }], volgende_cursor: null })
  api.contractconfig.opties.mockResolvedValue({
    dekking: [{ optie_sleutel: 'hosting', label: 'Hosting', volgorde: 0 }],
    kostenmodel: [{ optie_sleutel: 'volume', label: 'Volumemodel', volgorde: 0 }],
    relatie_rol: [],
  })
  api.contracten.lijst.mockResolvedValue({ items: [{ id: 'm1', contractnaam: 'Mantel X', leverancier_id: 'l1' }], volgende_cursor: null })
})
afterEach(() => vi.restoreAllMocks())

describe('ContractFormulier', () => {
  it('toont mantel-zoekveld alleen bij deelcontract en filtert server-side op leverancier+type', async () => {
    const { w } = await mountForm()
    expect(w.find('[data-testid="veld-mantelcontract-input"]').exists()).toBe(false)
    await kiesZoek(w, 'veld-leverancier', 'l1')
    await w.find('[data-testid="veld-contracttype"]').setValue('deelcontract')
    await flushPromises()
    expect(w.find('[data-testid="veld-mantelcontract-input"]').exists()).toBe(true)
    // focus de mantel-zoek → server-side zoek met type+leverancier als extraFilters
    await w.find('[data-testid="veld-mantelcontract-input"]').trigger('focus')
    await flushPromises()
    expect(api.contracten.lijst).toHaveBeenCalledWith(
      expect.objectContaining({ contracttype: 'mantelcontract', leverancier_id: 'l1', limit: 11 }),
    )
    // terug naar los_contract → mantel-veld verdwijnt
    await w.find('[data-testid="veld-contracttype"]').setValue('los_contract')
    await flushPromises()
    expect(w.find('[data-testid="veld-mantelcontract-input"]').exists()).toBe(false)
  })

  it('checkbox-groepen sturen een declaratieve set (dekking/kostenmodel)', async () => {
    api.contracten.maak.mockResolvedValueOnce({ id: 'c1' })
    const { w } = await mountForm()
    await vulBasis(w)
    await w.find('[data-testid="dekking-hosting"]').setValue(true)
    await w.find('[data-testid="kostenmodel-volume"]').setValue(true)
    await w.find('[data-testid="contract-form"]').trigger('submit')
    await flushPromises()
    const payload = api.contracten.maak.mock.calls[0][0]
    expect(payload.dekking).toEqual(['hosting'])
    expect(payload.kostenmodel).toEqual(['volume'])
    expect(payload.mantelcontract_id).toBeNull()
  })

  it('zet een 422-veldfout op het juiste veld', async () => {
    api.contracten.maak.mockRejectedValueOnce({
      status: 422,
      detail: [{ loc: ['body', 'contractnaam'], msg: 'Maximaal 255 tekens.' }],
    })
    const { w } = await mountForm()
    await vulBasis(w)
    await w.find('[data-testid="contract-form"]').trigger('submit')
    await flushPromises()
    expect(w.find('[data-testid="fout-contractnaam"]').text()).toContain('Maximaal 255')
  })

  it('toont de LEVERANCIER_MISMATCH-envelope', async () => {
    api.contracten.maak.mockRejectedValueOnce({
      status: 422,
      code: 'LEVERANCIER_MISMATCH',
      message: 'de leverancier wijkt af van de mantel',
    })
    const { w } = await mountForm()
    await vulBasis(w)
    await w.find('[data-testid="contract-form"]').trigger('submit')
    await flushPromises()
    const alert = w.find('[data-testid="register-fout"]')
    expect(alert.exists()).toBe(true)
    expect(alert.text()).toContain('de leverancier wijkt af')
  })
})
