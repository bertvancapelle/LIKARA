/** Tests — NormBeheer (ADR-052 slice 4b): rol-gating (lezen iedereen, wijzigen beheerder),
 *  soort-indicator, en de impact-voorspelling vóór opslaan. */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'

vi.mock('@/api', () => ({
  api: {
    componentNormen: { definitie: vi.fn(), impact: vi.fn(), zetVerplicht: vi.fn() },
  },
}))

import { api } from '@/api'
import { useAuthStore } from '../store/auth'
import NormBeheer from './NormBeheer.vue'

const DEF = () => [
  { feit: 'eigenaar', verplicht: true, bewust_geen_mogelijk: false },
  { feit: 'koppelingen', verplicht: true, bewust_geen_mogelijk: true },
  { feit: 'gebruikersgroep', verplicht: false, bewust_geen_mogelijk: false },
]

async function mountView({ roles = ['beheerder'] } = {}) {
  const pinia = createPinia()
  const auth = useAuthStore(pinia)
  auth.user = { email: 'b@b.nl', roles }
  const w = mount(NormBeheer, {
    global: { plugins: [pinia, [PrimeVue, { unstyled: true }], ToastService], stubs: { teleport: true } },
  })
  await flushPromises()
  return w
}

beforeEach(() => {
  vi.clearAllMocks()
  api.componentNormen.definitie.mockResolvedValue(DEF())
})
afterEach(() => vi.restoreAllMocks())

describe('NormBeheer — rol-gating', () => {
  it('beheerder ziet de lat + toggle-knoppen (aan/uit volgt de stand)', async () => {
    const w = await mountView({ roles: ['beheerder'] })
    expect(w.find('[data-testid="norm-rij-eigenaar"]').exists()).toBe(true)
    expect(w.find('[data-testid="norm-verplicht-eigenaar"]').exists()).toBe(true)
    expect(w.find('[data-testid="norm-toggle-eigenaar"]').text()).toContain('Uitzetten') // verplicht → uitzetten
    expect(w.find('[data-testid="norm-toggle-gebruikersgroep"]').text()).toContain('Aanzetten') // niet verplicht
    expect(w.find('[data-testid="norm-readonly-hint"]').exists()).toBe(false)
  })

  it('medewerker ziet de lat read-only: geen toggles, wel de read-only-hint', async () => {
    const w = await mountView({ roles: ['medewerker'] })
    expect(w.find('[data-testid="norm-rij-eigenaar"]').exists()).toBe(true) // leesbaar
    expect(w.find('[data-testid="norm-toggle-eigenaar"]').exists()).toBe(false) // geen wijzig-affordance
    expect(w.find('[data-testid="norm-readonly-hint"]').exists()).toBe(true)
  })

  it('per feit de soort: relationeel ("bewust geen") vs eigen veld', async () => {
    const w = await mountView()
    expect(w.find('[data-testid="norm-soort-koppelingen"]').text()).toContain('bewust geen')
    expect(w.find('[data-testid="norm-soort-eigenaar"]').text()).toContain('eigen veld')
  })
})

describe('NormBeheer — impact vóór opslaan (besluit 3)', () => {
  it('aanzetten toont de impact en slaat pas op na bevestigen', async () => {
    api.componentNormen.impact.mockResolvedValue({
      feit: 'gebruikersgroep', verplicht_doel: true, componenten_geraakt: 40, klaarverklaringen_geraakt: 12,
    })
    api.componentNormen.zetVerplicht.mockResolvedValue({ feit: 'gebruikersgroep', verplicht: true })
    const w = await mountView({ roles: ['beheerder'] })
    await w.find('[data-testid="norm-toggle-gebruikersgroep"]').trigger('click')
    await flushPromises()
    expect(api.componentNormen.impact).toHaveBeenCalledWith('gebruikersgroep', true)
    const imp = w.find('[data-testid="norm-impact"]')
    expect(imp.text()).toContain('40')
    expect(imp.text()).toContain('12')
    expect(api.componentNormen.zetVerplicht).not.toHaveBeenCalled() // nog niet opgeslagen
    await w.find('[data-testid="norm-opslaan"]').trigger('click')
    await flushPromises()
    expect(api.componentNormen.zetVerplicht).toHaveBeenCalledWith('gebruikersgroep', true)
    expect(api.componentNormen.definitie).toHaveBeenCalledTimes(2) // herladen na opslaan
  })

  it('uitzetten toont "signalen vervallen" + "voldoen alsnog"', async () => {
    api.componentNormen.impact.mockResolvedValue({
      feit: 'eigenaar', verplicht_doel: false, componenten_geraakt: 3, klaarverklaringen_geraakt: 1, componenten_nu_compleet: 2,
    })
    const w = await mountView({ roles: ['beheerder'] })
    await w.find('[data-testid="norm-toggle-eigenaar"]').trigger('click')
    await flushPromises()
    expect(api.componentNormen.impact).toHaveBeenCalledWith('eigenaar', false)
    const imp = w.find('[data-testid="norm-impact"]')
    expect(imp.text()).toContain('vervallen')
    expect(imp.text()).toContain('2')
  })

  it('annuleren in de impact-dialog slaat niets op', async () => {
    api.componentNormen.impact.mockResolvedValue({ componenten_geraakt: 5, klaarverklaringen_geraakt: 0, verplicht_doel: true })
    const w = await mountView()
    await w.find('[data-testid="norm-toggle-gebruikersgroep"]').trigger('click')
    await flushPromises()
    await w.find('[data-testid="norm-annuleer"]').trigger('click')
    expect(api.componentNormen.zetVerplicht).not.toHaveBeenCalled()
  })
})
