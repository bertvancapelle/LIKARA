/** Tests — ImpactSectie (read-only impactanalyse; ADR-021 Fase E, CD056). */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import PrimeVue from 'primevue/config'

vi.mock('@/api', () => ({ api: { componenten: { impact: vi.fn() } } }))

import { api } from '@/api'
import ImpactSectie from '@modules/bwb_ontvlechting/frontend/views/ImpactSectie.vue'

const COMP = 'db-1'

function maakRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/componenten/:id', name: 'component-detail', component: { template: '<div/>' } },
      { path: '/applicaties/:id', name: 'applicatie-detail', component: { template: '<div/>' } },
    ],
  })
}

async function mountSectie() {
  const router = maakRouter()
  await router.push('/componenten/db-1')
  await router.isReady()
  const w = mount(ImpactSectie, {
    props: { componentId: COMP },
    global: { plugins: [[PrimeVue, { unstyled: true }], router] },
  })
  await flushPromises()
  return w
}

const _impact = (over = {}) => ({
  component: { id: COMP, naam: 'Oracle FIN-DB', componenttype_label: 'Database' },
  contracten: [
    { koppeling_id: 'k-1', contractnaam: 'Oracle licentie', leverancier_naam: 'Oracle', relatie_rol_label: 'Valt onder' },
  ],
  geraakt: [
    {
      component_id: 'app-1', naam: 'Belastingsysteem', componenttype_label: 'Applicatie',
      niveau: 1, pad: ['Oracle FIN-DB', 'Belastingsysteem'], relatietype_label: 'Draait op',
      lifecycle_status: 'geblokkeerd', open_blokkades: 2,
    },
    {
      component_id: 'app-2', naam: 'Zaaksysteem', componenttype_label: 'Applicatie',
      niveau: 2, pad: ['Oracle FIN-DB', 'Belastingsysteem', 'Zaaksysteem'], relatietype_label: 'Draait op',
      lifecycle_status: 'concept', open_blokkades: 0,
    },
  ],
  samenvatting: { aantal_geraakt: 2, aantal_applicaties: 2, aantal_geblokkeerd: 1 },
  ...over,
})

beforeEach(() => vi.clearAllMocks())
afterEach(() => vi.restoreAllMocks())

describe('ImpactSectie', () => {
  it('laadt pas na de knop; toont samenvatting, contracten en de geraakte tabel', async () => {
    api.componenten.impact.mockResolvedValueOnce(_impact())
    const w = await mountSectie()
    // Niet automatisch geladen (geen onMounted-fetch).
    expect(api.componenten.impact).not.toHaveBeenCalled()

    await w.find('[data-testid="im-analyseer"]').trigger('click')
    await flushPromises()

    expect(api.componenten.impact).toHaveBeenCalledWith(COMP)
    expect(w.find('[data-testid="im-samenvatting"]').text()).toContain('2')
    expect(w.find('[data-testid="im-contracten"]').text()).toContain('Oracle licentie')
    const tabel = w.find('[data-testid="im-tabel"]')
    expect(tabel.text()).toContain('Belastingsysteem')
    expect(tabel.text()).toContain('Zaaksysteem')
    // Pad uitgeklapt bij niveau > 1.
    expect(w.find('[data-testid="im-pad-app-2"]').text()).toContain('Oracle FIN-DB → Belastingsysteem → Zaaksysteem')
  })

  it('elke rij linkt naar ComponentDetail (LI059)', async () => {
    api.componenten.impact.mockResolvedValueOnce(_impact())
    const w = await mountSectie()
    await w.find('[data-testid="im-analyseer"]').trigger('click')
    await flushPromises()
    const hrefs = w.find('[data-testid="im-tabel"]').findAll('a').map((a) => a.attributes('href'))
    expect(hrefs.some((h) => h.includes('/componenten/app-1'))).toBe(true)
  })

  it('toont de lege-staat als niets afhankelijk is', async () => {
    api.componenten.impact.mockResolvedValueOnce(
      _impact({ geraakt: [], samenvatting: { aantal_geraakt: 0, aantal_applicaties: 0, aantal_geblokkeerd: 0 } }),
    )
    const w = await mountSectie()
    await w.find('[data-testid="im-analyseer"]').trigger('click')
    await flushPromises()
    expect(w.find('[data-testid="im-leeg"]').exists()).toBe(true)
    expect(w.find('[data-testid="im-tabel"]').exists()).toBe(false)
  })

  it('is read-only: geen schrijf-/actieknoppen (alleen de analyse-trigger)', async () => {
    api.componenten.impact.mockResolvedValueOnce(_impact())
    const w = await mountSectie()
    await w.find('[data-testid="im-analyseer"]').trigger('click')
    await flushPromises()
    const knoppen = w.findAll('button')
    expect(knoppen.length).toBe(1) // uitsluitend "Impactanalyse"
  })
})
