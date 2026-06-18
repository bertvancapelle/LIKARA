/** Tests — PartijRollenSectie (rollen van één partij op objecten; ADR-024 slice 2b, alleen-lezen). */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'

vi.mock('@/api', () => ({ api: { roltoewijzingen: { lijst: vi.fn() } } }))

import { api } from '@/api'
import PartijRollenSectie from '@modules/bwb_ontvlechting/frontend/views/PartijRollenSectie.vue'

const PARTIJ = 'p1'

function maakRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/componenten/:id', name: 'component-detail', component: { template: '<div/>' } },
      { path: '/contracten/:id', name: 'contract-detail', component: { template: '<div/>' } },
    ],
  })
}

async function mountSectie() {
  const router = maakRouter()
  await router.push('/componenten/c1')
  await router.isReady()
  const pinia = createPinia()
  const w = mount(PartijRollenSectie, {
    props: { partijId: PARTIJ },
    global: { plugins: [pinia, [PrimeVue, { unstyled: true }], router] },
  })
  await flushPromises()
  return w
}

beforeEach(() => {
  vi.clearAllMocks()
  api.roltoewijzingen.lijst.mockResolvedValue([
    { toewijzing_id: 't1', rol: 'eigenaar', rol_label: 'Eigenaar', object_id: 'c1', object_naam: 'Zaaksysteem', object_type: 'component' },
    { toewijzing_id: 't2', rol: 'contractbeheer', rol_label: 'Contractbeheer', object_id: 'k1', object_naam: 'Mantel X', object_type: 'contract' },
  ])
})
afterEach(() => vi.restoreAllMocks())

describe('PartijRollenSectie', () => {
  it('toont object-naam, type en rol-label per regel', async () => {
    const w = await mountSectie()
    const t = w.find('[data-testid="pr-tabel"]').text()
    expect(t).toContain('Zaaksysteem')
    expect(t).toContain('Eigenaar')
    expect(t).toContain('Mantel X')
    expect(t).toContain('Contractbeheer')
    expect(api.roltoewijzingen.lijst).toHaveBeenCalledWith({ partij_id: PARTIJ })
  })

  it('linkt een component-rij naar component-detail en een contract-rij naar contract-detail', async () => {
    const w = await mountSectie()
    const hrefs = w.findAll('[data-testid="pr-object-link"]').map((a) => a.attributes('href'))
    expect(hrefs.some((h) => h.includes('/componenten/c1'))).toBe(true)
    expect(hrefs.some((h) => h.includes('/contracten/k1'))).toBe(true)
  })

  it('lege staat zonder rollen', async () => {
    api.roltoewijzingen.lijst.mockResolvedValueOnce([])
    const w = await mountSectie()
    expect(w.find('[data-testid="pr-leeg"]').exists()).toBe(true)
  })
})
