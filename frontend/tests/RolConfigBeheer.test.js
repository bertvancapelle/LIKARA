/** Tests — RolConfigBeheer (platform-beheer componentrol-catalogus, ADR-028). */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'

vi.mock('@/api', () => ({
  api: { platformComponentrolconfig: { lijst: vi.fn(), maak: vi.fn(), werkBij: vi.fn() } },
}))

import { api } from '@/api'
import { useAuthStore } from '@/store/auth'
import RolConfigBeheer from '@/views/RolConfigBeheer.vue'

const _opties = () => [
  { id: 1, optie_sleutel: 'interne_applicatie', label: 'Interne applicatie', volgorde: 0, actief: true },
  { id: 2, optie_sleutel: 'externe_dataprovider', label: 'Externe dataprovider', volgorde: 2, actief: true },
  { id: 3, optie_sleutel: 'oud', label: 'Oud', volgorde: 9, actief: false },
]

async function mountBeheer({ rollen = ['platformbeheerder'] } = {}) {
  const pinia = createPinia()
  const auth = useAuthStore(pinia)
  auth.user = { sub: 'p', email: 'b@platform.nl', roles: rollen }
  auth.sessionType = 'platform'
  const w = mount(RolConfigBeheer, {
    attachTo: document.body,
    global: { plugins: [pinia, [PrimeVue, { unstyled: true }], ToastService], stubs: { teleport: true } },
  })
  await flushPromises()
  return w
}

beforeEach(() => {
  vi.clearAllMocks()
  api.platformComponentrolconfig.lijst.mockResolvedValue(_opties())
})
afterEach(() => vi.restoreAllMocks())

describe('RolConfigBeheer', () => {
  it('toont de rol-opties; gedeactiveerde rij onderscheiden', async () => {
    const w = await mountBeheer()
    expect(w.find('[data-testid="rol-sectie"]').exists()).toBe(true)
    expect(w.text()).toContain('Externe dataprovider')
    expect(w.find('[data-testid="rol-rij-3"]').classes()).toContain('opacity-50')
    expect(w.find('[data-testid="rol-status-3"]').text()).toContain('Gedeactiveerd')
  })

  it('interne_applicatie is beschermd: Systeem-Tag, geen deactiveer-knop; bewerken mag wel', async () => {
    const w = await mountBeheer()
    expect(w.find('[data-testid="rol-systeem-1"]').exists()).toBe(true)
    expect(w.find('[data-testid="rol-deactiveer-1"]').exists()).toBe(false)
    expect(w.find('[data-testid="rol-bewerk-1"]').exists()).toBe(true)
    // een gewone rol heeft wél een deactiveer-knop
    expect(w.find('[data-testid="rol-deactiveer-2"]').exists()).toBe(true)
  })

  it('toevoegen roept de API en voegt de rij toe', async () => {
    api.platformComponentrolconfig.maak.mockResolvedValue({ id: 4, optie_sleutel: 'koppelvlak', label: 'Koppelvlak', volgorde: 3, actief: true })
    const w = await mountBeheer()
    await w.find('[data-testid="rol-toevoegen"]').trigger('click')
    await w.find('[data-testid="rol-add-sleutel"]').setValue('koppelvlak')
    await w.find('[data-testid="rol-add-label"]').setValue('Koppelvlak')
    await w.find('[data-testid="rol-add-form"]').trigger('submit')
    await flushPromises()
    expect(api.platformComponentrolconfig.maak).toHaveBeenCalledWith(expect.objectContaining({ optie_sleutel: 'koppelvlak', label: 'Koppelvlak' }))
    expect(w.text()).toContain('Koppelvlak')
  })

  it('deactiveren van een gewone rol roept werkBij(actief:false)', async () => {
    api.platformComponentrolconfig.werkBij.mockResolvedValue({ ..._opties()[1], actief: false })
    const w = await mountBeheer()
    await w.find('[data-testid="rol-deactiveer-2"]').trigger('click')
    await w.find('[data-testid="rol-deact-bevestig"]').trigger('click')
    await flushPromises()
    expect(api.platformComponentrolconfig.werkBij).toHaveBeenCalledWith(2, { actief: false })
  })

  it('een niet-beheerder ziet geen toevoeg-/beheerknoppen', async () => {
    const w = await mountBeheer({ rollen: ['platformoperator'] })
    expect(w.find('[data-testid="rol-toevoegen"]').exists()).toBe(false)
    expect(w.find('[data-testid="rol-bewerk-1"]').exists()).toBe(false)
  })
})
