/** Tests — ContractConfigBeheer (platform-beheer contractcatalogus, ADR-020 fase E). */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'

vi.mock('@/api', () => ({
  api: { platformContractconfig: { lijst: vi.fn(), maak: vi.fn(), werkBij: vi.fn() } },
}))

import { api } from '@/api'
import { useAuthStore } from '@/store/auth'
import ContractConfigBeheer from '@/views/ContractConfigBeheer.vue'

const _opties = () => [
  { id: 1, dimensie: 'dekking', optie_sleutel: 'hosting', label: 'Hosting', volgorde: 0, actief: true },
  { id: 2, dimensie: 'dekking', optie_sleutel: 'oud_model', label: 'Oud model', volgorde: 1, actief: false },
  { id: 3, dimensie: 'kostenmodel', optie_sleutel: 'volume', label: 'Volume', volgorde: 0, actief: true },
  { id: 4, dimensie: 'relatie_rol', optie_sleutel: 'valt_onder', label: 'Valt onder', volgorde: 0, actief: true },
]

async function mountBeheer({ rollen = ['platformbeheerder'] } = {}) {
  const pinia = createPinia()
  const auth = useAuthStore(pinia)
  auth.user = { sub: 'p', email: 'b@platform.nl', roles: rollen }
  auth.sessionType = 'platform'
  const w = mount(ContractConfigBeheer, {
    attachTo: document.body,
    global: { plugins: [pinia, [PrimeVue, { unstyled: true }], ToastService], stubs: { teleport: true } },
  })
  await flushPromises()
  return w
}

beforeEach(() => {
  vi.clearAllMocks()
  api.platformContractconfig.lijst.mockResolvedValue(_opties())
})
afterEach(() => vi.restoreAllMocks())

describe('ContractConfigBeheer — render', () => {
  it('toont de drie dimensies met opties; gedeactiveerde rij onderscheiden', async () => {
    const w = await mountBeheer()
    expect(w.find('[data-testid="cat-sectie-dekking"]').exists()).toBe(true)
    expect(w.find('[data-testid="cat-sectie-kostenmodel"]').exists()).toBe(true)
    expect(w.find('[data-testid="cat-sectie-relatie_rol"]').exists()).toBe(true)
    expect(w.text()).toContain('Hosting')
    expect(w.text()).toContain('Volume')
    const inactief = w.find('[data-testid="cat-rij-2"]')
    expect(inactief.classes()).toContain('opacity-50')
    expect(w.find('[data-testid="cat-status-2"]').text()).toContain('Gedeactiveerd')
    expect(w.find('[data-testid="cat-status-1"]').text()).toContain('Actief')
  })

  it('biedt nergens een verwijder-affordance', async () => {
    const w = await mountBeheer()
    expect(w.findAll('[data-testid*="verwijder"]').length).toBe(0)
    expect(w.html()).not.toContain('Verwijderen')
    expect(api.platformContractconfig.verwijder).toBeUndefined()
  })
})

describe('ContractConfigBeheer — toevoegen', () => {
  it('weigert een sleutel die geen lowercase snake_case is (geen API-call)', async () => {
    const w = await mountBeheer()
    await w.find('[data-testid="cat-toevoegen-kostenmodel"]').trigger('click')
    await flushPromises()
    await w.find('[data-testid="cat-add-sleutel"]').setValue('Vaste Fee')
    await w.find('[data-testid="cat-add-label"]').setValue('Vaste fee')
    await w.find('[data-testid="cat-add-form"]').trigger('submit')
    expect(w.find('[data-testid="cat-add-fout-optie_sleutel"]').exists()).toBe(true)
    expect(api.platformContractconfig.maak).not.toHaveBeenCalled()
  })

  it('voegt toe met een geldige sleutel binnen de juiste dimensie', async () => {
    api.platformContractconfig.maak.mockResolvedValueOnce({ id: 9, dimensie: 'kostenmodel', optie_sleutel: 'vaste_fee', label: 'Vaste fee', volgorde: 1, actief: true })
    const w = await mountBeheer()
    await w.find('[data-testid="cat-toevoegen-kostenmodel"]').trigger('click')
    await flushPromises()
    await w.find('[data-testid="cat-add-sleutel"]').setValue('vaste_fee')
    await w.find('[data-testid="cat-add-label"]').setValue('Vaste fee')
    await w.find('[data-testid="cat-add-form"]').trigger('submit')
    await flushPromises()
    expect(api.platformContractconfig.maak).toHaveBeenCalledWith(
      expect.objectContaining({ dimensie: 'kostenmodel', optie_sleutel: 'vaste_fee', label: 'Vaste fee' }),
    )
  })

  it('toont een 409 CONFIGURATIE_CONFLICT in-form', async () => {
    api.platformContractconfig.maak.mockRejectedValueOnce({ status: 409, code: 'CONFIGURATIE_CONFLICT', message: 'sleutel bestaat al' })
    const w = await mountBeheer()
    await w.find('[data-testid="cat-toevoegen-dekking"]').trigger('click')
    await flushPromises()
    await w.find('[data-testid="cat-add-sleutel"]').setValue('hosting')
    await w.find('[data-testid="cat-add-label"]').setValue('Hosting 2')
    await w.find('[data-testid="cat-add-form"]').trigger('submit')
    await flushPromises()
    expect(w.find('[data-testid="cat-add-formfout"]').exists()).toBe(true)
  })
})

describe('ContractConfigBeheer — bewerken', () => {
  it('toont dimensie en sleutel read-only (niet bewerkbaar), label wél', async () => {
    const w = await mountBeheer()
    await w.find('[data-testid="cat-bewerk-1"]').trigger('click')
    await flushPromises()
    expect(w.find('[data-testid="cat-edit-sleutel-readonly"]').text()).toContain('hosting')
    expect(w.find('[data-testid="cat-edit-dimensie-readonly"]').text()).toContain('Dekking')
    expect(w.find('[data-testid="cat-edit-label"]').exists()).toBe(true)
    // geen invoerveld dat de sleutel/dimensie bewerkt
    expect(w.find('input[data-testid="cat-edit-sleutel"]').exists()).toBe(false)
    expect(w.find('input[data-testid="cat-edit-dimensie"]').exists()).toBe(false)
  })
})

describe('ContractConfigBeheer — deactiveren/reactiveren', () => {
  it('deactiveren toont de uitlegregel en roept werkBij met actief=false', async () => {
    api.platformContractconfig.werkBij.mockResolvedValueOnce({ ..._opties()[0], actief: false })
    const w = await mountBeheer()
    await w.find('[data-testid="cat-deactiveer-1"]').trigger('click')
    await flushPromises()
    expect(w.find('[data-testid="cat-deact-uitleg"]').text()).toContain('blijven leesbaar')
    await w.find('[data-testid="cat-deact-bevestig"]').trigger('click')
    await flushPromises()
    expect(api.platformContractconfig.werkBij).toHaveBeenCalledWith(1, { actief: false })
  })

  it('reactiveren roept werkBij met actief=true', async () => {
    api.platformContractconfig.werkBij.mockResolvedValueOnce({ ..._opties()[1], actief: true })
    const w = await mountBeheer()
    await w.find('[data-testid="cat-reactiveer-2"]').trigger('click')
    await flushPromises()
    expect(api.platformContractconfig.werkBij).toHaveBeenCalledWith(2, { actief: true })
  })
})

describe('ContractConfigBeheer — rol-gating', () => {
  it('platformoperator ziet alles read-only (geen schrijf-affordances)', async () => {
    const w = await mountBeheer({ rollen: ['platformoperator'] })
    expect(w.find('[data-testid="cat-toevoegen-dekking"]').exists()).toBe(false)
    expect(w.find('[data-testid="cat-bewerk-1"]').exists()).toBe(false)
    expect(w.find('[data-testid="cat-deactiveer-1"]').exists()).toBe(false)
    expect(w.find('[data-testid="cat-reactiveer-2"]').exists()).toBe(false)
    // de catalogus zelf is wél zichtbaar
    expect(w.find('[data-testid="cat-sectie-dekking"]').exists()).toBe(true)
    expect(w.text()).toContain('Hosting')
  })
})
