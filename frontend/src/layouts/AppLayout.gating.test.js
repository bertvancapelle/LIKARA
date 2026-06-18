/**
 * Tests — AppLayout migratie-nav-gating (ADR-023 Fase F / F-1 + F-5).
 * De "Migratie"-navgroep is de affordance achter leesrecht: zichtbaar voor elke tenant-rol,
 * verborgen zonder rol. PrimeVue (unstyled) voor Button/Toast; memory-router voor de links.
 */
import { afterEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'

import AppLayout from './AppLayout.vue'
import { useAuthStore } from '../store/auth'

const STUB = { template: '<div/>' }
const NAMEN = [
  'dashboard', 'component-lijst', 'partij-lijst', 'contract-lijst', 'blokkades',
  'koppelingenkaart', 'architectuur', 'landschapskaart', 'plaatsingssignalen', 'checklistvragen',
  'plateau-lijst', 'gap-lijst', 'work-package-lijst', 'deliverable-lijst',
]

function maakRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: NAMEN.map((name, i) => ({ path: i === 0 ? '/' : `/${name}`, name, component: STUB })),
  })
}

async function mountLayout(roles) {
  const router = maakRouter()
  await router.push('/')
  await router.isReady()
  const pinia = createPinia()
  const auth = useAuthStore(pinia)
  auth.user = { email: 'u@x.nl', roles }
  return mount(AppLayout, {
    global: { plugins: [pinia, [PrimeVue, { unstyled: true }], ToastService, router] },
  })
}

afterEach(() => vi.clearAllMocks())

describe('AppLayout — migratie-nav-gating', () => {
  it('toont de Migratie-groep met de vier sub-items voor een tenant-rol', async () => {
    const w = await mountLayout(['viewer'])
    expect(w.find('[data-testid="nav-migratie-groep"]').exists()).toBe(true)
    for (const t of ['nav-plateaus', 'nav-gaps', 'nav-werkpakketten', 'nav-deliverables']) {
      expect(w.find(`[data-testid="${t}"]`).exists()).toBe(true)
    }
  })

  it('verbergt de Migratie-groep zonder rol (geen leesrecht-affordance)', async () => {
    const w = await mountLayout([])
    expect(w.find('[data-testid="nav-migratie-groep"]').exists()).toBe(false)
    expect(w.find('[data-testid="nav-plateaus"]').exists()).toBe(false)
  })
})
