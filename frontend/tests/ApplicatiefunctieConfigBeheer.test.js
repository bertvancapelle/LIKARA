/** Tests — ApplicatiefunctieConfigBeheer (platform-beheer applicatiefunctie-catalogus, ADR-042). */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'

vi.mock('@/api', () => ({
  api: { platformApplicatiefunctieconfig: { lijst: vi.fn(), maak: vi.fn(), werkBij: vi.fn() } },
}))

import { api } from '@/api'
import { useAuthStore } from '@/store/auth'
import ApplicatiefunctieConfigBeheer from '@/views/ApplicatiefunctieConfigBeheer.vue'

const _opties = () => [
  { id: 1, optie_sleutel: 'registreren', label: 'Registreren', volgorde: 0, actief: true },
  { id: 2, optie_sleutel: 'raadplegen', label: 'Raadplegen', volgorde: 1, actief: true },
  { id: 3, optie_sleutel: 'oud', label: 'Oud', volgorde: 9, actief: false },
]

async function mountBeheer({ rollen = ['platformbeheerder'] } = {}) {
  const pinia = createPinia()
  const auth = useAuthStore(pinia)
  auth.user = { sub: 'p', email: 'b@platform.nl', roles: rollen }
  auth.sessionType = 'platform'
  const w = mount(ApplicatiefunctieConfigBeheer, {
    attachTo: document.body,
    global: { plugins: [pinia, [PrimeVue, { unstyled: true }], ToastService], stubs: { teleport: true } },
  })
  await flushPromises()
  return w
}

beforeEach(() => {
  vi.clearAllMocks()
  api.platformApplicatiefunctieconfig.lijst.mockResolvedValue(_opties())
})
afterEach(() => vi.restoreAllMocks())

describe('ApplicatiefunctieConfigBeheer', () => {
  it('toont de opties; gedeactiveerde rij onderscheiden', async () => {
    const w = await mountBeheer()
    expect(w.find('[data-testid="af-sectie"]').exists()).toBe(true)
    expect(w.text()).toContain('Registreren')
    expect(w.find('[data-testid="af-rij-3"]').classes()).toContain('opacity-50')
    expect(w.find('[data-testid="af-status-3"]').text()).toContain('Gedeactiveerd')
  })

  it('GEEN systeem-sleutel: élke actieve optie heeft een deactiveer-knop (ADR-042 besluit 3)', async () => {
    const w = await mountBeheer()
    expect(w.find('[data-testid="af-deactiveer-1"]').exists()).toBe(true)
    expect(w.find('[data-testid="af-deactiveer-2"]').exists()).toBe(true)
    expect(w.text()).not.toContain('Systeem') // geen Systeem-Tag zoals bij componentrollen
  })

  it('optie toevoegen → api.maak met sleutel/label', async () => {
    api.platformApplicatiefunctieconfig.maak.mockResolvedValue(
      { id: 4, optie_sleutel: 'gegevens_ontvangen', label: 'Gegevens ontvangen', volgorde: 10, actief: true },
    )
    const w = await mountBeheer()
    await w.find('[data-testid="af-toevoegen"]').trigger('click')
    await w.find('[data-testid="af-add-sleutel"]').setValue('gegevens_ontvangen')
    await w.find('[data-testid="af-add-label"]').setValue('Gegevens ontvangen')
    await w.find('[data-testid="af-add-form"]').trigger('submit')
    await flushPromises()
    expect(api.platformApplicatiefunctieconfig.maak).toHaveBeenCalledWith({
      optie_sleutel: 'gegevens_ontvangen', label: 'Gegevens ontvangen',
    })
    expect(w.text()).toContain('Gegevens ontvangen')
  })

  it('sleutel-validatie: geen snake_case → veldfout, geen api-call', async () => {
    const w = await mountBeheer()
    await w.find('[data-testid="af-toevoegen"]').trigger('click')
    await w.find('[data-testid="af-add-sleutel"]').setValue('Foute Sleutel')
    await w.find('[data-testid="af-add-label"]').setValue('X')
    await w.find('[data-testid="af-add-form"]').trigger('submit')
    await flushPromises()
    expect(w.find('[data-testid="af-add-fout-optie_sleutel"]').exists()).toBe(true)
    expect(api.platformApplicatiefunctieconfig.maak).not.toHaveBeenCalled()
  })

  it('deactiveren vraagt bevestiging en zet actief=false', async () => {
    api.platformApplicatiefunctieconfig.werkBij.mockResolvedValue({ ..._opties()[0], actief: false })
    const w = await mountBeheer()
    await w.find('[data-testid="af-deactiveer-1"]').trigger('click')
    expect(w.find('[data-testid="af-deact-dialog"]').exists()).toBe(true)
    await w.find('[data-testid="af-deact-bevestig"]').trigger('click')
    await flushPromises()
    expect(api.platformApplicatiefunctieconfig.werkBij).toHaveBeenCalledWith(1, { actief: false })
  })

  it('reactiveren zet actief=true', async () => {
    api.platformApplicatiefunctieconfig.werkBij.mockResolvedValue({ ..._opties()[2], actief: true })
    const w = await mountBeheer()
    await w.find('[data-testid="af-reactiveer-3"]').trigger('click')
    await flushPromises()
    expect(api.platformApplicatiefunctieconfig.werkBij).toHaveBeenCalledWith(3, { actief: true })
  })

  it('rol-gating: platformoperator ziet de lijst maar geen beheer-affordances', async () => {
    const w = await mountBeheer({ rollen: ['platformoperator'] })
    expect(w.text()).toContain('Registreren')
    expect(w.find('[data-testid="af-toevoegen"]').exists()).toBe(false)
    expect(w.find('[data-testid="af-deactiveer-1"]').exists()).toBe(false)
  })
})
