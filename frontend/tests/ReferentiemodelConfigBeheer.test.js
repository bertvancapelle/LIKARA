/** Tests — ReferentiemodelConfigBeheer (platform-beheer referentiemodel-aanbod, gate 1b §2.1).
 * Kern: GESLOTEN aanbod — geen toevoegen-affordance (nieuw model = release-curatie);
 * herkomst/versie zichtbaar (navolgbaar) en read-only; label/volgorde bewerkbaar;
 * soft-deactivate met bevestiging. Spiegel van ApplicatiefunctieConfigBeheer.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'

vi.mock('@/api', () => ({
  api: { platformReferentiemodelconfig: { lijst: vi.fn(), werkBij: vi.fn() } },
}))

import { api } from '@/api'
import { useAuthStore } from '@/store/auth'
import ReferentiemodelConfigBeheer from '@/views/ReferentiemodelConfigBeheer.vue'

const _opties = () => [
  {
    id: 1,
    optie_sleutel: 'gemma_bedrijfsfuncties',
    label: 'GEMMA Bedrijfsfuncties',
    herkomst: 'VNG-Realisatie/GEMMA-Archi-repository — licentie EUPL',
    versie: 'release 1 juli 2026',
    volgorde: 0,
    actief: true,
  },
  {
    id: 2,
    optie_sleutel: 'oud_model',
    label: 'Oud model',
    herkomst: 'bron X',
    versie: 'v1',
    volgorde: 1,
    actief: false,
  },
]

async function mountBeheer({ rollen = ['platformbeheerder'] } = {}) {
  const pinia = createPinia()
  const auth = useAuthStore(pinia)
  auth.user = { sub: 'p', email: 'b@platform.nl', roles: rollen }
  auth.sessionType = 'platform'
  const w = mount(ReferentiemodelConfigBeheer, {
    attachTo: document.body,
    global: { plugins: [pinia, [PrimeVue, { unstyled: true }], ToastService], stubs: { teleport: true } },
  })
  await flushPromises()
  return w
}

beforeEach(() => {
  vi.clearAllMocks()
  api.platformReferentiemodelconfig.lijst.mockResolvedValue(_opties())
})
afterEach(() => vi.restoreAllMocks())

describe('ReferentiemodelConfigBeheer', () => {
  it('toont het aanbod mét navolgbare herkomst en versie; gedeactiveerd onderscheiden', async () => {
    const w = await mountBeheer()
    expect(w.text()).toContain('GEMMA Bedrijfsfuncties')
    expect(w.text()).toContain('release 1 juli 2026')
    expect(w.text()).toContain('EUPL') // herkomst incl. licentie zichtbaar — "gecureerd"
    expect(w.find('[data-testid="rm-rij-2"]').classes()).toContain('opacity-50')
    expect(w.find('[data-testid="rm-status-2"]').text()).toContain('Gedeactiveerd')
  })

  it('GESLOTEN aanbod: er is geen toevoegen-affordance (nieuw model = release-curatie)', async () => {
    const w = await mountBeheer()
    expect(w.text()).not.toContain('Optie toevoegen')
    expect(w.find('button[data-testid$="toevoegen"]').exists()).toBe(false)
    // De uitleg benoemt waar nieuw aanbod wél vandaan komt.
    expect(w.text()).toContain('release')
  })

  it('bewerken: label/volgorde muteerbaar; sleutel/versie/herkomst read-only zichtbaar', async () => {
    api.platformReferentiemodelconfig.werkBij.mockResolvedValue({ ..._opties()[0], label: 'GEMMA (functies)' })
    const w = await mountBeheer()
    await w.find('[data-testid="rm-bewerk-1"]').trigger('click')
    expect(w.find('[data-testid="rm-edit-sleutel-readonly"]').text()).toBe('gemma_bedrijfsfuncties')
    await w.find('[data-testid="rm-edit-label"]').setValue('GEMMA (functies)')
    await w.find('[data-testid="rm-edit-form"]').trigger('submit')
    await flushPromises()
    expect(api.platformReferentiemodelconfig.werkBij).toHaveBeenCalledWith(1, {
      label: 'GEMMA (functies)', volgorde: 0,
    })
    expect(w.text()).toContain('GEMMA (functies)')
  })

  it('deactiveren vraagt bevestiging (mét "ingelezen blijft staan") en zet actief=false', async () => {
    api.platformReferentiemodelconfig.werkBij.mockResolvedValue({ ..._opties()[0], actief: false })
    const w = await mountBeheer()
    await w.find('[data-testid="rm-deactiveer-1"]').trigger('click')
    expect(w.find('[data-testid="rm-deact-dialog"]').exists()).toBe(true)
    expect(w.find('[data-testid="rm-deact-dialog"]').text()).toContain('blijft gewoon staan')
    await w.find('[data-testid="rm-deact-bevestig"]').trigger('click')
    await flushPromises()
    expect(api.platformReferentiemodelconfig.werkBij).toHaveBeenCalledWith(1, { actief: false })
  })

  it('platformoperator (alleen lezen): geen beheer-knoppen', async () => {
    const w = await mountBeheer({ rollen: ['platformoperator'] })
    expect(w.text()).toContain('GEMMA Bedrijfsfuncties')
    expect(w.find('[data-testid="rm-bewerk-1"]').exists()).toBe(false)
    expect(w.find('[data-testid="rm-deactiveer-1"]').exists()).toBe(false)
  })
})
