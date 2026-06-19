/** Tests — ComponentLijst (technische laag; ADR-021 Fase D, CD054b). */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'

vi.mock('@/api', () => ({
  // UX-B6-b — partijen.lijst voedt de eigenaar-organisatie-ZoekSelect (filter).
  api: { componenten: { lijst: vi.fn(), opties: vi.fn() }, partijen: { lijst: vi.fn() } },
}))

import { api } from '@/api'
import { Column, DataTable } from '@/primevue'
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
      { path: '/partijen/:id', name: 'partij-detail', component: { template: '<div/>' } },
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
  eigenaar_organisatie_id: subtype ? 'org-1' : null,
  eigenaar_organisatie_naam: subtype ? 'Gemeente Veldendam' : null,
  complexiteit: subtype ? 'midden' : null,
  prioriteit: subtype ? 'hoog' : null,
  lifecycle_status: subtype ? 'concept' : null,
})

beforeEach(() => {
  vi.clearAllMocks()
  api.partijen.lijst.mockResolvedValue({ items: [{ id: 'org-1', naam: 'Gemeente Veldendam', aard: 'organisatie' }], volgende_cursor: null })
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

  it('status-filter (multi-select dropdown) stuurt de status-array mee en reset de cursor', async () => {
    api.componenten.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
    const w = await mountLijst()
    // Multi-select dropdown: open de trigger, vink een status aan.
    await w.find('[data-testid="filter-status-trigger"]').trigger('click')
    await w.find('[data-testid="filter-status-checkbox-geblokkeerd"]').trigger('change')
    await flushPromises()
    expect(api.componenten.lijst).toHaveBeenLastCalledWith(
      expect.objectContaining({ status: ['geblokkeerd'], after: undefined }),
    )
  })

  it('hostingmodel- en eigenaar-filter worden meegestuurd', async () => {
    api.componenten.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
    const w = await mountLijst()
    await w.find('[data-testid="filter-hosting"]').setValue('saas')
    await flushPromises()
    expect(api.componenten.lijst).toHaveBeenLastCalledWith(expect.objectContaining({ hostingmodel: 'saas' }))
    // UX-B6-b — eigenaar-filter is een organisatie-keuze (ZoekSelect op eigenaar_organisatie_id).
    await w.find('[data-testid="filter-eigenaar-input"]').trigger('focus')
    await flushPromises()
    await w.find('[data-testid="filter-eigenaar-optie-org-1"]').trigger('mousedown')
    await flushPromises()
    expect(api.componenten.lijst).toHaveBeenLastCalledWith(expect.objectContaining({ eigenaar_organisatie_id: 'org-1' }))
  })

  it('een ?type=applicatie-query preselecteert het typefilter (Applicaties-redirect)', async () => {
    api.componenten.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
    await mountLijst({ pad: '/componenten?type=applicatie' })
    expect(api.componenten.lijst).toHaveBeenLastCalledWith(
      expect.objectContaining({ componenttype: 'applicatie' }),
    )
  })

  it('een ?status=geblokkeerd-query preselecteert het statusfilter (dashboard-doorklik)', async () => {
    api.componenten.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
    const w = await mountLijst({ pad: '/componenten?status=geblokkeerd' })
    expect(api.componenten.lijst).toHaveBeenLastCalledWith(
      expect.objectContaining({ status: ['geblokkeerd'] }),
    )
    // De dropdown-trigger toont de voorgezette selectie (1 gekozen → het statuslabel).
    expect(w.find('[data-testid="filter-status-trigger"]').text()).toContain('Geblokkeerd')
  })

  it('ADR-027: ?klaarverklaring=klaar belandt als api-filter + toont de wisbare chip', async () => {
    api.componenten.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
    const w = await mountLijst({ pad: '/componenten?klaarverklaring=klaar' })
    expect(api.componenten.lijst).toHaveBeenLastCalledWith(
      expect.objectContaining({ klaarverklaring: 'klaar' }),
    )
    expect(w.find('[data-testid="klaarverklaring-filter-chip"]').exists()).toBe(true)
  })

  it('ADR-027: ?afwijking=1 belandt als afwijking-filter (impliceert geen losse klaarverklaring-param)', async () => {
    api.componenten.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
    const w = await mountLijst({ pad: '/componenten?afwijking=1' })
    const call = api.componenten.lijst.mock.calls.at(-1)[0]
    expect(call.afwijking).toBe(1)
    expect(call.klaarverklaring).toBeUndefined() // afwijking impliceert server-side de klaar-join
    expect(w.find('[data-testid="klaarverklaring-filter-chip"]').text()).toContain('nog niet compleet')
  })

  it('ADR-027: chip wissen verwijdert de filter uit de volgende api-call', async () => {
    api.componenten.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
    const w = await mountLijst({ pad: '/componenten?afwijking=1' })
    await w.find('[data-testid="klaarverklaring-filter-wis"]').trigger('click')
    const call = api.componenten.lijst.mock.calls.at(-1)[0]
    expect(call.afwijking).toBeUndefined()
    expect(call.klaarverklaring).toBeUndefined()
    expect(w.find('[data-testid="klaarverklaring-filter-chip"]').exists()).toBe(false)
  })

  it('?status= + ?type= samen zetten beide filters voor (exacte dashboard-tegel-match)', async () => {
    api.componenten.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
    await mountLijst({ pad: '/componenten?status=migratieklaar&type=applicatie' })
    expect(api.componenten.lijst).toHaveBeenLastCalledWith(
      expect.objectContaining({ status: ['migratieklaar'], componenttype: 'applicatie' }),
    )
  })

  it('een ongeldige ?status=-waarde wordt genegeerd (default-gedrag)', async () => {
    api.componenten.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
    await mountLijst({ pad: '/componenten?status=onzin' })
    const call = api.componenten.lijst.mock.calls.at(-1)[0]
    expect(call.status).toBeUndefined()
  })

  // ── Server-side kolomsortering (ADR-017) ───────────────────────────────────
  it('default-laad stuurt GEEN sort/order mee (server-default created_at asc)', async () => {
    api.componenten.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
    await mountLijst()
    const call = api.componenten.lijst.mock.calls.at(-1)[0]
    expect(call.sort).toBeUndefined()
    expect(call.order).toBeUndefined()
  })

  it('een sorteerklik stuurt sort/order mee, reset de cursor en herlaadt', async () => {
    api.componenten.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
    const w = await mountLijst()
    w.findComponent(DataTable).vm.$emit('sort', { sortField: 'hostingmodel', sortOrder: -1 })
    await flushPromises()
    expect(api.componenten.lijst).toHaveBeenLastCalledWith(
      expect.objectContaining({ sort: 'hostingmodel', order: 'desc', after: undefined }),
    )
  })

  it('de 7 kolommen zijn sorteerbaar en Laag bewust niet', async () => {
    api.componenten.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
    const w = await mountLijst()
    const sortFields = w.findAllComponents(Column).map((c) => ({
      header: c.props('header'),
      sortable: c.props('sortable'),
    }))
    const sorteerbaar = sortFields.filter((c) => c.sortable).map((c) => c.header)
    expect(sorteerbaar).toEqual(
      expect.arrayContaining(['Naam', 'Type', 'Eigenaar', 'Hosting', 'Complexiteit', 'Prioriteit', 'Status']),
    )
    expect(sorteerbaar).toHaveLength(7)
    expect(sorteerbaar).not.toContain('Laag')
  })

  it('sorteren behoudt een actief filter', async () => {
    api.componenten.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
    const w = await mountLijst({ pad: '/componenten?type=applicatie' })
    w.findComponent(DataTable).vm.$emit('sort', { sortField: 'naam', sortOrder: 1 })
    await flushPromises()
    expect(api.componenten.lijst).toHaveBeenLastCalledWith(
      expect.objectContaining({ sort: 'naam', order: 'asc', componenttype: 'applicatie' }),
    )
  })
})
