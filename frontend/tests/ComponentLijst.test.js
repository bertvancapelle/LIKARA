/** Tests — ComponentLijst (technische laag; ADR-021 Fase D, CD054b). */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'

vi.mock('@/api', () => ({
  api: { componenten: { lijst: vi.fn(), opties: vi.fn() } },
}))

import { api } from '@/api'
import ComponentLijst from '@modules/bwb_ontvlechting/frontend/views/ComponentLijst.vue'
import { useAuthStore } from '@/store/auth'

function maakRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/componenten', name: 'component-lijst', component: ComponentLijst },
      { path: '/componenten/nieuw', name: 'component-nieuw', component: { template: '<div/>' } },
      { path: '/componenten/:id', name: 'component-detail', component: { template: '<div/>' } },
      { path: '/applicaties/:id', name: 'applicatie-detail', component: { template: '<div/>' } },
    ],
  })
}

async function mountLijst({ rollen = ['medewerker'], pad = '/componenten' } = {}) {
  const router = maakRouter()
  await router.push(pad)
  await router.isReady()
  const pinia = createPinia()
  const auth = useAuthStore(pinia)
  auth.user = { sub: 's', tenant_id: 't', email: 'a@b.nl', roles: rollen }
  const wrapper = mount(ComponentLijst, {
    global: { plugins: [pinia, [PrimeVue, { unstyled: true }], router] },
  })
  await flushPromises()
  return wrapper
}

const _comp = (naam, id, { type = 'database', label = 'Database', subtype = false } = {}) => ({
  id,
  naam,
  componenttype: type,
  componenttype_label: label,
  // ADR-023 Fase C: ArchiMate-typing-projectie (laag/element) uit de catalogus.
  archimate_element: subtype ? 'application_component' : 'system_software',
  laag: subtype ? 'application' : 'technology',
  hostingmodel: 'on_premise',
  heeft_applicatie_subtype: subtype,
  // Besturingsvelden (CD054b W1) — gevuld voor subtypen, null voor kale infra.
  eigenaar_organisatie: subtype ? 'Gemeente Veldendam' : null,
  complexiteit: subtype ? 'midden' : null,
  prioriteit: subtype ? 'hoog' : null,
  lifecycle_status: subtype ? 'concept' : null,
})

beforeEach(() => {
  vi.clearAllMocks()
  api.componenten.opties.mockResolvedValue({
    componenttype: [
      { optie_sleutel: 'database', label: 'Database', laag: 'technology', archimate_element: 'system_software' },
      { optie_sleutel: 'applicatie', label: 'Applicatie', laag: 'application', archimate_element: 'application_component' },
    ],
    structuurrelatie_type: [],
  })
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('ComponentLijst', () => {
  it('rendert de geladen componenten met type-label', async () => {
    api.componenten.lijst.mockResolvedValueOnce({
      items: [
        _comp('Oracle FIN-DB', 'db-1'),
        _comp('Belastingsysteem', 'app-1', { type: 'applicatie', label: 'Applicatie', subtype: true }),
      ],
      volgende_cursor: null,
    })
    const w = await mountLijst()
    const tekst = w.find('[data-testid="componenten-tabel"]').text()
    expect(tekst).toContain('Oracle FIN-DB')
    expect(tekst).toContain('Database')
    expect(tekst).toContain('Belastingsysteem')
  })

  it('subtype-rij linkt naar ApplicatieDetail, niet-subtype naar ComponentDetail', async () => {
    api.componenten.lijst.mockResolvedValueOnce({
      items: [
        _comp('Oracle FIN-DB', 'db-1'),
        _comp('Belastingsysteem', 'app-1', { type: 'applicatie', label: 'Applicatie', subtype: true }),
      ],
      volgende_cursor: null,
    })
    const w = await mountLijst()
    const links = w.findAll('[data-testid="rij-link"]')
    const hrefs = links.map((l) => l.attributes('href'))
    expect(hrefs.some((h) => h.includes('/componenten/db-1'))).toBe(true)
    expect(hrefs.some((h) => h.includes('/applicaties/app-1'))).toBe(true)
  })

  it('type-filter stuurt componenttype mee en reset de cursor', async () => {
    api.componenten.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
    const w = await mountLijst()
    await w.find('[data-testid="filter-type"]').setValue('database')
    await flushPromises()
    expect(api.componenten.lijst).toHaveBeenLastCalledWith(
      expect.objectContaining({ componenttype: 'database', after: undefined }),
    )
  })

  it('laag-filter (ADR-023 Fase C) stuurt laag mee en reset de cursor', async () => {
    api.componenten.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
    const w = await mountLijst()
    // Het laag-filter wordt uit de catalogus-typing afgeleid (application/technology).
    await w.find('[data-testid="filter-laag"]').setValue('technology')
    await flushPromises()
    expect(api.componenten.lijst).toHaveBeenLastCalledWith(
      expect.objectContaining({ laag: 'technology', after: undefined }),
    )
  })

  it('toont per rij een ArchiMate-laag-label', async () => {
    api.componenten.lijst.mockResolvedValueOnce({
      items: [_comp('Oracle FIN-DB', 'db-1')],
      volgende_cursor: null,
    })
    const w = await mountLijst()
    expect(w.find('[data-testid="rij-laag"]').text()).toBe('Technologie')
    // Het element-label staat als verfijning onder de laag.
    expect(w.find('[data-testid="componenten-tabel"]').text()).toContain('Systeemsoftware')
  })

  it('zoekfilter (gedebounced) stuurt zoek mee', async () => {
    vi.useFakeTimers()
    api.componenten.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
    const w = await mountLijst()
    await w.find('[data-testid="filter-zoek"]').setValue('oracle')
    vi.advanceTimersByTime(350)
    vi.useRealTimers()
    await flushPromises()
    expect(api.componenten.lijst).toHaveBeenLastCalledWith(
      expect.objectContaining({ zoek: 'oracle' }),
    )
  })

  it('"Meer laden" gebruikt de cursor en voegt resultaten toe', async () => {
    api.componenten.lijst
      .mockResolvedValueOnce({ items: [_comp('A', 'a-1')], volgende_cursor: 'cur-1' })
      .mockResolvedValueOnce({ items: [_comp('B', 'b-1')], volgende_cursor: null })
    const w = await mountLijst()
    expect(w.find('[data-testid="meer-laden"]').exists()).toBe(true)
    await w.find('[data-testid="meer-laden"]').trigger('click')
    await flushPromises()
    expect(api.componenten.lijst).toHaveBeenLastCalledWith(
      expect.objectContaining({ after: 'cur-1' }),
    )
    expect(w.find('[data-testid="componenten-tabel"]').text()).toContain('B')
  })

  it('zonder schrijfrol geen "Nieuw component"-knop', async () => {
    api.componenten.lijst.mockResolvedValueOnce({ items: [], volgende_cursor: null })
    const w = await mountLijst({ rollen: ['viewer'] })
    expect(w.find('[data-testid="nieuw-component"]').exists()).toBe(false)
  })

  it('toont besturingskolommen gevuld voor subtypen en "—" voor kale infra', async () => {
    api.componenten.lijst.mockResolvedValueOnce({
      items: [
        _comp('Belastingsysteem', 'app-1', { type: 'applicatie', label: 'Applicatie', subtype: true }),
        _comp('Oracle FIN-DB', 'db-1'),
      ],
      volgende_cursor: null,
    })
    const w = await mountLijst()
    const tekst = w.find('[data-testid="componenten-tabel"]').text()
    // Subtype: eigenaar + niveaus + status-Tag gevuld.
    expect(tekst).toContain('Gemeente Veldendam')
    expect(tekst).toContain('Concept')
    // Kale infra: minstens één "—" voor de lege besturingsvelden.
    expect(w.findAll('[data-testid="status-leeg"]').length).toBeGreaterThan(0)
  })

  it('status-filter stuurt de status-array mee en reset de cursor', async () => {
    api.componenten.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
    const w = await mountLijst()
    await w.find('[data-testid="filter-status-geblokkeerd"]').setValue(true)
    await flushPromises()
    expect(api.componenten.lijst).toHaveBeenLastCalledWith(
      expect.objectContaining({ status: ['geblokkeerd'], after: undefined }),
    )
  })

  it('hostingmodel- en eigenaar-filter worden meegestuurd', async () => {
    vi.useFakeTimers()
    api.componenten.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
    const w = await mountLijst()
    await w.find('[data-testid="filter-hosting"]').setValue('saas')
    await flushPromises()
    expect(api.componenten.lijst).toHaveBeenLastCalledWith(expect.objectContaining({ hostingmodel: 'saas' }))
    await w.find('[data-testid="filter-eigenaar"]').setValue('veldendam')
    vi.advanceTimersByTime(350)
    vi.useRealTimers()
    await flushPromises()
    expect(api.componenten.lijst).toHaveBeenLastCalledWith(expect.objectContaining({ eigenaar: 'veldendam' }))
  })

  it('een ?type=applicatie-query preselecteert het typefilter (Applicaties-redirect)', async () => {
    api.componenten.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
    await mountLijst({ pad: '/componenten?type=applicatie' })
    expect(api.componenten.lijst).toHaveBeenLastCalledWith(
      expect.objectContaining({ componenttype: 'applicatie' }),
    )
  })
})
