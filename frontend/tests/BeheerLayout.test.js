/** Tests — BeheerLayout (platform-shell, ADR-019 fase 2E-b). */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'

import BeheerLayout from '@/layouts/BeheerLayout.vue'
import { useAuthStore } from '@/store/auth'

function mountLayout() {
  const pinia = createPinia()
  const auth = useAuthStore(pinia)
  auth.user = { sub: 'p', email: 'beheer@platform.nl', roles: ['platformbeheerder'] }
  auth.sessionType = 'platform'
  const wrapper = mount(BeheerLayout, {
    global: {
      plugins: [pinia, [PrimeVue, { unstyled: true }], ToastService],
      stubs: { 'router-link': true, 'router-view': true },
    },
  })
  return { wrapper, auth }
}

beforeEach(() => {})
afterEach(() => vi.restoreAllMocks())

describe('BeheerLayout', () => {
  it('toont de beheer-badge, platform-e-mail en nav', () => {
    const { wrapper } = mountLayout()
    expect(wrapper.find('[data-testid="beheer-badge"]').text()).toBe('Beheer')
    expect(wrapper.find('[data-testid="platform-email"]').text()).toBe('beheer@platform.nl')
    expect(wrapper.find('[data-testid="nav-contractconfig"]').exists()).toBe(true)
  })

  it('uitloggen roept auth.logout aan', async () => {
    const { wrapper, auth } = mountLayout()
    const spy = vi.spyOn(auth, 'logout').mockResolvedValue(undefined)
    await wrapper.find('[data-testid="beheer-uitlog-knop"]').trigger('click')
    expect(spy).toHaveBeenCalled()
  })
})
