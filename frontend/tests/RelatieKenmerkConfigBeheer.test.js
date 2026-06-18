/** Tests — RelatieKenmerkConfigBeheer (platform-beheer relatie-kenmerk-catalogus, F-4). */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'

vi.mock('@/api', () => ({
  api: { platformRelatiekenmerkconfig: { lijst: vi.fn(), maak: vi.fn(), werkBij: vi.fn() } },
}))

import { api } from '@/api'
import { useAuthStore } from '@/store/auth'
import RelatieKenmerkConfigBeheer from '@/views/RelatieKenmerkConfigBeheer.vue'

const _opties = () => [
  { id: 1, dimensie: 'dispositie', optie_sleutel: 'behouden', label: 'Behouden', volgorde: 0, actief: true },
  { id: 2, dimensie: 'dispositie', optie_sleutel: 'migreren', label: 'Migreren', volgorde: 1, actief: true },
  { id: 3, dimensie: 'dispositie', optie_sleutel: 'oud', label: 'Oud', volgorde: 2, actief: false },
  { id: 4, dimensie: 'relatie_rol', optie_sleutel: 'valt_onder', label: 'Valt onder', volgorde: 0, actief: true },
  // ADR-024 slice 2b — beheerrol-dimensie (zelfde catalogus/endpoint).
  { id: 5, dimensie: 'beheerrol', optie_sleutel: 'functioneel_beheer', label: 'Functioneel beheer', volgorde: 0, actief: true },
  { id: 6, dimensie: 'beheerrol', optie_sleutel: 'eigenaar', label: 'Eigenaar', volgorde: 5, actief: true },
]

async function mountBeheer({ rollen = ['platformbeheerder'] } = {}) {
  const pinia = createPinia()
  const auth = useAuthStore(pinia)
  auth.user = { sub: 'p', email: 'b@platform.nl', roles: rollen }
  auth.sessionType = 'platform'
  const w = mount(RelatieKenmerkConfigBeheer, {
    attachTo: document.body,
    global: { plugins: [pinia, [PrimeVue, { unstyled: true }], ToastService], stubs: { teleport: true } },
  })
  await flushPromises()
  return w
}

beforeEach(() => {
  vi.clearAllMocks()
  api.platformRelatiekenmerkconfig.lijst.mockResolvedValue(_opties())
})
afterEach(() => vi.restoreAllMocks())

describe('RelatieKenmerkConfigBeheer — render', () => {
  it('toont beide dimensies; gedeactiveerde rij onderscheiden', async () => {
    const w = await mountBeheer()
    expect(w.find('[data-testid="rk-sectie-dispositie"]').exists()).toBe(true)
    expect(w.find('[data-testid="rk-sectie-relatie_rol"]').exists()).toBe(true)
    expect(w.text()).toContain('Migreren')
    expect(w.find('[data-testid="rk-rij-3"]').classes()).toContain('opacity-50')
    expect(w.find('[data-testid="rk-status-3"]').text()).toContain('Gedeactiveerd')
  })

  it('GEEN beschermde systeem-sleutel: élke actieve waarde heeft een deactiveer-knop', async () => {
    const w = await mountBeheer()
    expect(w.find('[data-testid="rk-deactiveer-1"]').exists()).toBe(true) // behouden
    expect(w.find('[data-testid="rk-deactiveer-2"]').exists()).toBe(true) // migreren
    expect(w.find('[data-testid="rk-deactiveer-4"]').exists()).toBe(true) // valt_onder
    // gedeactiveerde rij toont reactiveer i.p.v. deactiveer
    expect(w.find('[data-testid="rk-reactiveer-3"]').exists()).toBe(true)
  })

  it('toont de Beheerrollen-sectie (ADR-024 slice 2b) met de rollen en dezelfde acties', async () => {
    const w = await mountBeheer()
    const sectie = w.find('[data-testid="rk-sectie-beheerrol"]')
    expect(sectie.exists()).toBe(true)
    // gebruikerslabel-kop, geen datamodel-sleutel
    expect(w.find('#rk-kop-beheerrol').text()).toBe('Beheerrollen')
    // geseede rollen zichtbaar
    expect(sectie.text()).toContain('Functioneel beheer')
    expect(sectie.text()).toContain('Eigenaar')
    // identieke acties als de andere dimensies: toevoegen op de sectie + per-rij bewerken/deactiveren
    expect(w.find('[data-testid="rk-toevoegen-beheerrol"]').exists()).toBe(true)
    expect(w.find('[data-testid="rk-bewerk-5"]').exists()).toBe(true)
    expect(w.find('[data-testid="rk-deactiveer-5"]').exists()).toBe(true)
  })

  it('voegt een beheerrol toe met de juiste dimensie', async () => {
    api.platformRelatiekenmerkconfig.maak.mockResolvedValue({
      id: 10, dimensie: 'beheerrol', optie_sleutel: 'security_officer', label: 'Security officer', volgorde: 7, actief: true,
    })
    const w = await mountBeheer()
    await w.find('[data-testid="rk-toevoegen-beheerrol"]').trigger('click')
    await w.find('[data-testid="rk-add-sleutel"]').setValue('security_officer')
    await w.find('[data-testid="rk-add-label"]').setValue('Security officer')
    await w.find('[data-testid="rk-add-form"]').trigger('submit')
    await flushPromises()
    expect(api.platformRelatiekenmerkconfig.maak).toHaveBeenCalledWith(
      expect.objectContaining({ dimensie: 'beheerrol', optie_sleutel: 'security_officer', label: 'Security officer' }),
    )
  })

  it('verbergt beheer-acties zonder platformbeheerder-rol', async () => {
    const w = await mountBeheer({ rollen: ['platformoperator'] })
    expect(w.find('[data-testid="rk-toevoegen-dispositie"]').exists()).toBe(false)
    expect(w.find('[data-testid="rk-deactiveer-1"]').exists()).toBe(false)
    expect(w.find('[data-testid="rk-bewerk-1"]').exists()).toBe(false)
  })
})

describe('RelatieKenmerkConfigBeheer — acties', () => {
  it('voegt een optie toe via de dialog', async () => {
    api.platformRelatiekenmerkconfig.maak.mockResolvedValue({
      id: 9, dimensie: 'dispositie', optie_sleutel: 'herzien', label: 'Herzien', volgorde: 3, actief: true,
    })
    const w = await mountBeheer()
    await w.find('[data-testid="rk-toevoegen-dispositie"]').trigger('click')
    await w.find('[data-testid="rk-add-sleutel"]').setValue('herzien')
    await w.find('[data-testid="rk-add-label"]').setValue('Herzien')
    await w.find('[data-testid="rk-add-form"]').trigger('submit')
    await flushPromises()
    expect(api.platformRelatiekenmerkconfig.maak).toHaveBeenCalledWith(
      expect.objectContaining({ dimensie: 'dispositie', optie_sleutel: 'herzien', label: 'Herzien' }),
    )
  })

  it('deactiveert een optie (soft)', async () => {
    api.platformRelatiekenmerkconfig.werkBij.mockResolvedValue({
      id: 2, dimensie: 'dispositie', optie_sleutel: 'migreren', label: 'Migreren', volgorde: 1, actief: false,
    })
    const w = await mountBeheer()
    await w.find('[data-testid="rk-deactiveer-2"]').trigger('click')
    await w.find('[data-testid="rk-deact-bevestig"]').trigger('click')
    await flushPromises()
    expect(api.platformRelatiekenmerkconfig.werkBij).toHaveBeenCalledWith(2, { actief: false })
  })
})
