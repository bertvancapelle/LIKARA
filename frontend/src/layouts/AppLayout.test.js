import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'

import App from '../App.vue'
import AppLayout from './AppLayout.vue'
import { useAuthStore } from '../store/auth'

const DashStub = { template: '<div data-testid="dash-stub">dash</div>' }

function maakRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      {
        path: '/',
        component: AppLayout,
        meta: { requiresAuth: true },
        children: [
          { path: '', name: 'dashboard', component: DashStub },
          { path: 'applicaties', name: 'applicatie-lijst', component: { template: '<div/>' } },
          { path: 'componenten', name: 'component-lijst', component: { template: '<div/>' } },
          { path: 'leveranciers', name: 'leverancier-lijst', component: { template: '<div/>' } },
          { path: 'contracten', name: 'contract-lijst', component: { template: '<div/>' } },
          { path: 'blokkades', name: 'blokkades', component: { template: '<div/>' } },
          { path: 'koppelingenkaart', name: 'koppelingenkaart', component: { template: '<div/>' } },
          { path: 'checklistvragen', name: 'checklistvragen', component: { template: '<div/>' } },
          // ADR-023 Fase F (F-1) — migratielaag-nav (gegate op tenant-rol).
          { path: 'migratie/plateaus', name: 'plateau-lijst', component: { template: '<div/>' } },
          { path: 'migratie/gaps', name: 'gap-lijst', component: { template: '<div/>' } },
          { path: 'migratie/werkpakketten', name: 'work-package-lijst', component: { template: '<div/>' } },
          { path: 'migratie/deliverables', name: 'deliverable-lijst', component: { template: '<div/>' } },
        ],
      },
      { path: '/login', name: 'login', component: { template: '<div/>' } },
    ],
  })
}

async function mountShell() {
  const pinia = createPinia()
  const auth = useAuthStore(pinia)
  auth.user = { sub: 's', tenant_id: 't', email: 'jan@example.nl', roles: ['beheerder'] }
  const logoutSpy = vi.spyOn(auth, 'logout').mockResolvedValue()

  const router = maakRouter()
  await router.push('/')
  await router.isReady()

  const wrapper = mount(App, {
    global: { plugins: [pinia, [PrimeVue, { unstyled: true }], ToastService, router] },
  })
  return { wrapper, logoutSpy }
}

beforeEach(() => {
  try {
    localStorage.clear()
  } catch {
    /* geen localStorage */
  }
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('AppLayout', () => {
  it('rendert de topbar met app-naam en gebruiker-e-mail', async () => {
    const { wrapper } = await mountShell()
    expect(wrapper.text()).toContain('CompliData')
    expect(wrapper.find('[data-testid="gebruiker-email"]').text()).toBe('jan@example.nl')
  })

  it('rendert de child-view in de hoofd-router-view', async () => {
    const { wrapper } = await mountShell()
    expect(wrapper.find('[data-testid="dash-stub"]').exists()).toBe(true)
  })

  it('markeert de actieve Dashboard-link met aria-current', async () => {
    const { wrapper } = await mountShell()
    const link = wrapper.find('[data-testid="nav-dashboard"]')
    expect(link.attributes('aria-current')).toBe('page')
  })

  it('toont Componenten als enige ingang; "Applicaties" als apart menu-item is vervallen (CD054b W1)', async () => {
    const { wrapper } = await mountShell()
    expect(wrapper.find('[data-testid="nav-bwb-binnenkort"]').exists()).toBe(false)
    // Menu-sanering: geen apart Applicaties-item meer.
    expect(wrapper.find('[data-testid="nav-applicaties"]').exists()).toBe(false)
    const link = wrapper.find('[data-testid="nav-componenten"]')
    expect(link.exists()).toBe(true)
    expect(link.element.tagName).toBe('A')
    expect(link.attributes('href')).toContain('/componenten')
  })

  it('toont de Koppelingenkaart-navlink (CD023)', async () => {
    const { wrapper } = await mountShell()
    const link = wrapper.find('[data-testid="nav-koppelingenkaart"]')
    expect(link.exists()).toBe(true)
    expect(link.attributes('href')).toContain('/koppelingenkaart')
  })

  it('toggelt de sidebar en werkt aria-expanded bij', async () => {
    const { wrapper } = await mountShell()
    const toggle = wrapper.find('[data-testid="sidebar-toggle"]')
    expect(toggle.attributes('aria-expanded')).toBe('true')
    // v-show open: geen display:none op de sidebar.
    expect(wrapper.find('#hoofd-navigatie').attributes('style') || '').not.toContain('display: none')

    await toggle.trigger('click')
    expect(toggle.attributes('aria-expanded')).toBe('false')
    // v-show ingeklapt: sidebar verborgen via display:none.
    expect(wrapper.find('#hoofd-navigatie').attributes('style') || '').toContain('display: none')
  })

  it('roept logout aan bij klik op de uitlog-knop', async () => {
    const { wrapper, logoutSpy } = await mountShell()
    await wrapper.find('[data-testid="uitlog-knop"]').trigger('click')
    expect(logoutSpy).toHaveBeenCalledTimes(1)
  })
})
