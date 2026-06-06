/** Tests — ApplicatieDetail (module-view via @modules). */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'

vi.mock('@/api', () => ({
  api: {
    applicaties: {
      haal: vi.fn(),
      startInventarisatie: vi.fn(),
      verwijder: vi.fn(),
    },
  },
}))

import { api } from '@/api'
import { useAuthStore } from '@/store/auth'
import ApplicatieDetail from '@modules/bwb_ontvlechting/frontend/views/ApplicatieDetail.vue'

const _ID = 'app-1'

function _app(extra = {}) {
  return {
    id: _ID,
    naam: 'Zaaksysteem',
    beschrijving: null,
    hostingmodel: 'saas',
    eigenaar_organisatie: 'Gemeente Veldendam',
    eigenaar_naam: null,
    leverancier: null,
    migratiepad: 'herbouw',
    complexiteit: 'midden',
    prioriteit: 'hoog',
    lifecycle_status: 'concept',
    ...extra,
  }
}

async function mountDetail({ rollen = ['beheerder'] } = {}) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/applicaties', name: 'applicatie-lijst', component: { template: '<div/>' } },
      { path: '/applicaties/:id', name: 'applicatie-detail', component: ApplicatieDetail, props: true },
      { path: '/applicaties/:id/bewerken', name: 'applicatie-bewerken', component: { template: '<div/>' } },
    ],
  })
  await router.push(`/applicaties/${_ID}`)
  await router.isReady()
  const pushSpy = vi.spyOn(router, 'push')

  const pinia = createPinia()
  const auth = useAuthStore(pinia)
  auth.user = { sub: 's', tenant_id: 't', email: 'a@b.nl', roles: rollen }

  const wrapper = mount(ApplicatieDetail, {
    props: { id: _ID },
    global: {
      plugins: [pinia, [PrimeVue, { unstyled: true }], ToastService, router],
      // Dialog teleporteert naar body; inline renderen zodat find() de inhoud ziet.
      stubs: { teleport: true },
    },
  })
  await flushPromises()
  return { wrapper, pushSpy }
}

beforeEach(() => vi.clearAllMocks())
afterEach(() => vi.restoreAllMocks())

describe('ApplicatieDetail', () => {
  it('toont de applicatiegegevens en de lifecycle-status', async () => {
    api.applicaties.haal.mockResolvedValueOnce(_app())
    const { wrapper } = await mountDetail()
    expect(wrapper.text()).toContain('Zaaksysteem')
    expect(wrapper.text()).toContain('Gemeente Veldendam')
    expect(wrapper.find('[data-testid="detail-status"]').text()).toContain('Concept')
  })

  it('gate: Beheerder ziet bewerken + verwijderen + start (bij concept)', async () => {
    api.applicaties.haal.mockResolvedValueOnce(_app())
    const { wrapper } = await mountDetail({ rollen: ['beheerder'] })
    expect(wrapper.find('[data-testid="bewerken-knop"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="verwijder-knop"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="start-knop"]').exists()).toBe(true)
  })

  it('gate: Viewer ziet geen actieknoppen', async () => {
    api.applicaties.haal.mockResolvedValueOnce(_app())
    const { wrapper } = await mountDetail({ rollen: ['viewer'] })
    expect(wrapper.find('[data-testid="bewerken-knop"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="verwijder-knop"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="start-knop"]').exists()).toBe(false)
  })

  it('gate: Medewerker ziet geen verwijderen; start verdwijnt buiten concept', async () => {
    api.applicaties.haal.mockResolvedValueOnce(_app({ lifecycle_status: 'in_inventarisatie' }))
    const { wrapper } = await mountDetail({ rollen: ['medewerker'] })
    expect(wrapper.find('[data-testid="bewerken-knop"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="verwijder-knop"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="start-knop"]').exists()).toBe(false) // niet concept
  })

  it('start-inventarisatie roept de api aan en werkt de status bij', async () => {
    api.applicaties.haal.mockResolvedValueOnce(_app())
    api.applicaties.startInventarisatie.mockResolvedValueOnce(_app({ lifecycle_status: 'in_inventarisatie' }))
    const { wrapper } = await mountDetail({ rollen: ['medewerker'] })
    await wrapper.find('[data-testid="start-knop"]').trigger('click')
    await flushPromises()
    expect(api.applicaties.startInventarisatie).toHaveBeenCalledWith(_ID)
    expect(wrapper.find('[data-testid="detail-status"]').text()).toContain('In inventarisatie')
  })

  it('verwijderen verloopt via bevestiging en navigeert naar de lijst', async () => {
    api.applicaties.haal.mockResolvedValueOnce(_app())
    api.applicaties.verwijder.mockResolvedValueOnce(null)
    const { wrapper, pushSpy } = await mountDetail({ rollen: ['beheerder'] })

    await wrapper.find('[data-testid="verwijder-knop"]').trigger('click')
    await wrapper.find('[data-testid="verwijder-bevestig"]').trigger('click')
    await flushPromises()

    expect(api.applicaties.verwijder).toHaveBeenCalledWith(_ID)
    expect(pushSpy).toHaveBeenCalledWith({ name: 'applicatie-lijst' })
  })

  it('vangt een 403 bij verwijderen af zonder te navigeren', async () => {
    api.applicaties.haal.mockResolvedValueOnce(_app())
    const err = new Error('Onvoldoende rechten')
    err.status = 403
    api.applicaties.verwijder.mockRejectedValueOnce(err)
    const { wrapper, pushSpy } = await mountDetail({ rollen: ['beheerder'] })

    await wrapper.find('[data-testid="verwijder-knop"]').trigger('click')
    await wrapper.find('[data-testid="verwijder-bevestig"]').trigger('click')
    await flushPromises()

    expect(api.applicaties.verwijder).toHaveBeenCalled()
    expect(pushSpy).not.toHaveBeenCalledWith({ name: 'applicatie-lijst' })
  })
})
