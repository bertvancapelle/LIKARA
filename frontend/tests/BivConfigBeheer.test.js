/** Tests — BivConfigBeheer (platform-beheer BIV-schaal-catalogus, ADR-028). */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'

vi.mock('@/api', () => ({
  api: { platformBivschaalconfig: { lijst: vi.fn(), maak: vi.fn(), werkBij: vi.fn() } },
}))

import { api } from '@/api'
import { useAuthStore } from '@/store/auth'
import BivConfigBeheer from '@/views/BivConfigBeheer.vue'

const _opties = () => [
  { id: 3, optie_sleutel: 'hoog', label: 'Hoog', volgorde: 2, actief: true },
  { id: 1, optie_sleutel: 'laag', label: 'Laag', volgorde: 0, actief: true },
  { id: 2, optie_sleutel: 'midden', label: 'Midden', volgorde: 1, actief: true },
]

async function mountBeheer({ rollen = ['platformbeheerder'] } = {}) {
  const pinia = createPinia()
  const auth = useAuthStore(pinia)
  auth.user = { sub: 'p', email: 'b@platform.nl', roles: rollen }
  auth.sessionType = 'platform'
  const w = mount(BivConfigBeheer, {
    attachTo: document.body,
    global: { plugins: [pinia, [PrimeVue, { unstyled: true }], ToastService], stubs: { teleport: true } },
  })
  await flushPromises()
  return w
}

beforeEach(() => {
  vi.clearAllMocks()
  api.platformBivschaalconfig.lijst.mockResolvedValue(_opties())
})
afterEach(() => vi.restoreAllMocks())

describe('BivConfigBeheer', () => {
  it('toont de niveaus ORDINAAL op volgorde (laag → hoog), met de volgorde-kolom', async () => {
    const w = await mountBeheer()
    const rijen = w.findAll('[data-testid^="biv-rij-"]')
    // gesorteerd op volgorde: laag(0), midden(1), hoog(2)
    expect(rijen[0].text()).toContain('Laag')
    expect(rijen[1].text()).toContain('Midden')
    expect(rijen[2].text()).toContain('Hoog')
    expect(w.find('[data-testid="biv-volgorde-1"]').text()).toBe('0')
    expect(w.find('[data-testid="biv-volgorde-3"]').text()).toBe('2')
  })

  it('geen systeem-sleutel: elk niveau is deactiveerbaar', async () => {
    const w = await mountBeheer()
    expect(w.find('[data-testid="biv-deactiveer-1"]').exists()).toBe(true)
    expect(w.find('[data-testid="biv-deactiveer-3"]').exists()).toBe(true)
  })

  it('toevoegen van "Zeer hoog" met volgorde 3 komt ná Hoog', async () => {
    api.platformBivschaalconfig.maak.mockResolvedValue({ id: 4, optie_sleutel: 'zeer_hoog', label: 'Zeer hoog', volgorde: 3, actief: true })
    const w = await mountBeheer()
    await w.find('[data-testid="biv-toevoegen"]').trigger('click')
    await w.find('[data-testid="biv-add-sleutel"]').setValue('zeer_hoog')
    await w.find('[data-testid="biv-add-label"]').setValue('Zeer hoog')
    await w.find('[data-testid="biv-add-volgorde"]').setValue('3')
    await w.find('[data-testid="biv-add-form"]').trigger('submit')
    await flushPromises()
    expect(api.platformBivschaalconfig.maak).toHaveBeenCalledWith(expect.objectContaining({ optie_sleutel: 'zeer_hoog', label: 'Zeer hoog', volgorde: 3 }))
    const rijen = w.findAll('[data-testid^="biv-rij-"]')
    expect(rijen[rijen.length - 1].text()).toContain('Zeer hoog') // achteraan (hoogste)
  })

  it('label wijzigen roept werkBij', async () => {
    api.platformBivschaalconfig.werkBij.mockResolvedValue({ ..._opties()[1], label: 'Laag risico' })
    const w = await mountBeheer()
    await w.find('[data-testid="biv-bewerk-1"]').trigger('click')
    await w.find('[data-testid="biv-edit-label"]').setValue('Laag risico')
    await w.find('[data-testid="biv-edit-form"]').trigger('submit')
    await flushPromises()
    expect(api.platformBivschaalconfig.werkBij).toHaveBeenCalledWith(1, expect.objectContaining({ label: 'Laag risico' }))
  })

  it('een niet-beheerder ziet geen beheerknoppen', async () => {
    const w = await mountBeheer({ rollen: ['platformoperator'] })
    expect(w.find('[data-testid="biv-toevoegen"]').exists()).toBe(false)
    expect(w.find('[data-testid="biv-bewerk-1"]').exists()).toBe(false)
  })
})
