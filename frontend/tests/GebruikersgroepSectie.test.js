/** Tests — GebruikersgroepSectie (child-sectie via @modules). */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'

vi.mock('@/api', () => ({
  api: {
    gebruikersgroepen: {
      lijst: vi.fn(),
      maak: vi.fn(),
      werkBij: vi.fn(),
      verwijder: vi.fn(),
    },
    // UX-B6-a — ZoekSelect voor de organisatie-keuze (partijen, aard_in organisatie+burger).
    partijen: { lijst: vi.fn(), haal: vi.fn() },
  },
}))

import { createRouter, createMemoryHistory } from 'vue-router'

import { api } from '@/api'
import { useAuthStore } from '@/store/auth'
import GebruikersgroepSectie from '@modules/bwb_ontvlechting/frontend/views/GebruikersgroepSectie.vue'

const APP = 'app-1'
const STUB = { template: '<div/>' }

async function mountSectie({ rollen = ['beheerder'] } = {}) {
  const pinia = createPinia()
  const auth = useAuthStore(pinia)
  auth.user = { sub: 's', tenant_id: 't', email: 'a@b.nl', roles: rollen }
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'home', component: STUB },
      { path: '/partijen/:id', name: 'partij-detail', component: STUB },
    ],
  })
  await router.push('/')
  await router.isReady()
  const wrapper = mount(GebruikersgroepSectie, {
    props: { applicatieId: APP },
    attachTo: document.body,
    global: { plugins: [pinia, [PrimeVue, { unstyled: true }], ToastService, router], stubs: { teleport: true } },
  })
  await flushPromises()
  return wrapper
}

beforeEach(() => {
  vi.clearAllMocks()
  api.gebruikersgroepen.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
  api.partijen.lijst.mockResolvedValue({ items: [{ id: 'org-1', naam: 'Gemeente Tiel', aard: 'organisatie' }], volgende_cursor: null })
  api.partijen.haal.mockResolvedValue({ id: 'org-1', naam: 'Gemeente Tiel', aard: 'organisatie' })
})
afterEach(() => vi.restoreAllMocks())

describe('GebruikersgroepSectie', () => {
  it('rendert de gebruikersgroepen; de organisatie is doorklikbaar naar de partij', async () => {
    api.gebruikersgroepen.lijst.mockResolvedValueOnce({
      items: [{ id: 'g1', organisatie_id: 'org-1', organisatie_naam: 'Gemeente Tiel', afdeling: 'Burgerzaken', aantal_gebruikers: 12 }],
      volgende_cursor: null,
    })
    const w = await mountSectie()
    expect(api.gebruikersgroepen.lijst).toHaveBeenCalledWith({ applicatie_id: APP, limit: 25, after: undefined })
    expect(w.text()).toContain('Gemeente Tiel')
    const link = w.find('[data-testid="gg-org-link-g1"]')
    expect(link.exists()).toBe(true)
    expect(link.attributes('href')).toContain('/partijen/org-1')
  })

  it('toont een streepje wanneer er geen organisatie gekoppeld is', async () => {
    api.gebruikersgroepen.lijst.mockResolvedValueOnce({
      items: [{ id: 'g2', organisatie_id: null, organisatie_naam: null, afdeling: null, aantal_gebruikers: null }],
      volgende_cursor: null,
    })
    const w = await mountSectie()
    expect(w.find('[data-testid="gg-org-link-g2"]').exists()).toBe(false)
  })

  it('rol-gating: viewer geen Toevoegen, medewerker wel', async () => {
    expect((await mountSectie({ rollen: ['viewer'] })).find('[data-testid="gg-toevoegen"]').exists()).toBe(false)
    expect((await mountSectie({ rollen: ['medewerker'] })).find('[data-testid="gg-toevoegen"]').exists()).toBe(true)
  })

  it('B6-a: organisatie is optioneel — submit zonder organisatie is toegestaan', async () => {
    api.gebruikersgroepen.maak.mockResolvedValueOnce({ id: 'new' })
    const w = await mountSectie()
    await w.find('[data-testid="gg-toevoegen"]').trigger('click')
    await flushPromises()
    await w.find('[data-testid="gg-form"]').trigger('submit')
    await flushPromises()
    expect(api.gebruikersgroepen.maak).toHaveBeenCalledWith({
      organisatie_id: null,
      afdeling: null,
      aantal_gebruikers: null,
      applicatie_id: APP,
    })
  })

  it('weigert een negatief aantal gebruikers client-side', async () => {
    const w = await mountSectie()
    await w.find('[data-testid="gg-toevoegen"]').trigger('click')
    await flushPromises()
    await w.find('[data-testid="gg-veld-aantal"]').setValue('-3')
    await w.find('[data-testid="gg-form"]').trigger('submit')
    await flushPromises()
    expect(w.find('[data-testid="gg-fout-aantal"]').exists()).toBe(true)
    expect(api.gebruikersgroepen.maak).not.toHaveBeenCalled()
  })

  it('focust het organisatie-zoekveld bij openen', async () => {
    const w = await mountSectie()
    await w.find('[data-testid="gg-toevoegen"]').trigger('click')
    await flushPromises()
    await new Promise((r) => setTimeout(r, 0))
    expect(document.activeElement).toBe(w.find('[data-testid="gg-veld-organisatie-input"]').element)
  })

  it('kiest een organisatie via de zoek-combobox en stuurt het id mee', async () => {
    api.gebruikersgroepen.maak.mockResolvedValueOnce({ id: 'new' })
    const w = await mountSectie()
    await w.find('[data-testid="gg-toevoegen"]').trigger('click')
    await flushPromises()
    // Open de combobox (focus → server-zoek) en kies de organisatie-optie.
    await w.find('[data-testid="gg-veld-organisatie-input"]').trigger('focus')
    await flushPromises()
    expect(api.partijen.lijst).toHaveBeenCalledWith(expect.objectContaining({ aard_in: ['organisatie', 'burger'] }))
    await w.find('[data-testid="gg-veld-organisatie-optie-org-1"]').trigger('mousedown')
    await flushPromises()
    await w.find('[data-testid="gg-form"]').trigger('submit')
    await flushPromises()
    expect(api.gebruikersgroepen.maak).toHaveBeenCalledWith({
      organisatie_id: 'org-1',
      afdeling: null,
      aantal_gebruikers: null,
      applicatie_id: APP,
    })
  })

  it('afdeling-picker verschijnt bij een organisatie en is verborgen bij een burger', async () => {
    const w = await mountSectie()
    await w.find('[data-testid="gg-toevoegen"]').trigger('click')
    await flushPromises()
    // organisatie (aard=organisatie) → afdeling-picker verschijnt
    await w.find('[data-testid="gg-veld-organisatie-input"]').trigger('focus')
    await flushPromises()
    await w.find('[data-testid="gg-veld-organisatie-optie-org-1"]').trigger('mousedown')
    await flushPromises()
    expect(w.find('[data-testid="gg-veld-afdeling-input"]').exists()).toBe(true)
    // burger kiezen → afdeling-picker verdwijnt (aard ≠ organisatie)
    api.partijen.lijst.mockResolvedValue({ items: [{ id: 'b1', naam: 'Burgers', aard: 'burger' }], volgende_cursor: null })
    api.partijen.haal.mockResolvedValue({ id: 'b1', naam: 'Burgers', aard: 'burger' })
    await w.find('[data-testid="gg-veld-organisatie-input"]').trigger('focus')
    await flushPromises()
    await w.find('[data-testid="gg-veld-organisatie-optie-b1"]').trigger('mousedown')
    await flushPromises()
    expect(w.find('[data-testid="gg-veld-afdeling-input"]').exists()).toBe(false)
  })

  it('afdeling-selectie reset bij het wisselen van organisatie', async () => {
    api.gebruikersgroepen.maak.mockResolvedValueOnce({ id: 'new' })
    const w = await mountSectie()
    await w.find('[data-testid="gg-toevoegen"]').trigger('click')
    await flushPromises()
    await w.find('[data-testid="gg-veld-organisatie-input"]').trigger('focus')
    await flushPromises()
    await w.find('[data-testid="gg-veld-organisatie-optie-org-1"]').trigger('mousedown')
    await flushPromises()
    // afdeling kiezen (naam wordt in het vrije tekstveld opgeslagen)
    api.partijen.lijst.mockResolvedValue({ items: [{ id: 'afd-1', naam: 'Burgerzaken', aard: 'organisatie_eenheid' }], volgende_cursor: null })
    api.partijen.haal.mockResolvedValue({ id: 'afd-1', naam: 'Burgerzaken', aard: 'organisatie_eenheid' })
    await w.find('[data-testid="gg-veld-afdeling-input"]').trigger('focus')
    await flushPromises()
    await w.find('[data-testid="gg-veld-afdeling-optie-afd-1"]').trigger('mousedown')
    await flushPromises()
    // wissel naar een andere organisatie → afdeling reset
    api.partijen.lijst.mockResolvedValue({ items: [{ id: 'org-2', naam: 'Andere org', aard: 'organisatie' }], volgende_cursor: null })
    api.partijen.haal.mockResolvedValue({ id: 'org-2', naam: 'Andere org', aard: 'organisatie' })
    await w.find('[data-testid="gg-veld-organisatie-input"]').trigger('focus')
    await flushPromises()
    await w.find('[data-testid="gg-veld-organisatie-optie-org-2"]').trigger('mousedown')
    await flushPromises()
    await w.find('[data-testid="gg-form"]').trigger('submit')
    await flushPromises()
    expect(api.gebruikersgroepen.maak).toHaveBeenCalledWith(expect.objectContaining({ organisatie_id: 'org-2', afdeling: null }))
  })
})
