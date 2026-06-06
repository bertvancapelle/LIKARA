import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia } from 'pinia'

import DashboardView from './DashboardView.vue'
import { useAuthStore } from '../store/auth'

function mountDashboard(user) {
  const pinia = createPinia()
  const auth = useAuthStore(pinia)
  auth.user = user
  return mount(DashboardView, { global: { plugins: [pinia] } })
}

describe('DashboardView', () => {
  it('begroet de ingelogde gebruiker met e-mail', () => {
    const w = mountDashboard({ sub: 's', tenant_id: 't', email: 'jan@example.nl', roles: ['medewerker'] })
    expect(w.text()).toContain('Welkom')
    expect(w.text()).toContain('jan@example.nl')
  })

  it('toont de rol(len) van de gebruiker', () => {
    const w = mountDashboard({ sub: 's', tenant_id: 't', email: 'a@b.nl', roles: ['beheerder', 'auditor'] })
    const rollen = w.find('[data-testid="dashboard-rollen"]')
    expect(rollen.exists()).toBe(true)
    expect(rollen.text()).toContain('beheerder')
    expect(rollen.text()).toContain('auditor')
  })

  it('toont geen rol-regel zonder rollen', () => {
    const w = mountDashboard({ sub: 's', tenant_id: 't', email: 'a@b.nl', roles: [] })
    expect(w.find('[data-testid="dashboard-rollen"]').exists()).toBe(false)
  })
})
