/** Tests — PartijDetail (ADR-024 slice 2a): aard-tag, soort, contracten-sectie alleen voor
 *  externe partij, verwijderen (409 IN_GEBRUIK blijft op detail). */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'
import DataTable from 'primevue/datatable'

vi.mock('@/api', () => ({
  api: {
    partijen: { haal: vi.fn(), verwijder: vi.fn(), lijst: vi.fn(), componentenViaContract: vi.fn() },
    contracten: { lijst: vi.fn() },
    // ADR-024 slice 2b — PartijRollenSectie (alleen-lezen) laadt bij mount.
    roltoewijzingen: { lijst: vi.fn(() => Promise.resolve([])) },
  },
}))

import { api } from '@/api'
import { useAuthStore } from '@/store/auth'
import PartijDetail from '@modules/bwb_ontvlechting/frontend/views/PartijDetail.vue'

function maakRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/partijen', name: 'partij-lijst', component: { template: '<div/>' } },
      { path: '/partijen/nieuw', name: 'partij-nieuw', component: { template: '<div/>' } },
      { path: '/partijen/:id', name: 'partij-detail', component: PartijDetail, props: true },
      { path: '/partijen/:id/bewerken', name: 'partij-bewerken', component: { template: '<div/>' } },
      { path: '/contracten/:id', name: 'contract-detail', component: { template: '<div/>' } },
      { path: '/componenten/:id', name: 'component-detail', component: { template: '<div/>' } },
    ],
  })
}

async function mountDetail({ rollen = ['beheerder'], id = 'p1' } = {}) {
  const router = maakRouter()
  await router.push(`/partijen/${id}`)
  await router.isReady()
  const pinia = createPinia()
  const auth = useAuthStore(pinia)
  auth.user = { sub: 's', tenant_id: 't', email: 'a@b.nl', roles: rollen }
  const w = mount(PartijDetail, {
    props: { id },
    attachTo: document.body,
    global: { plugins: [pinia, [PrimeVue, { unstyled: true }], ToastService, router], stubs: { teleport: true } },
  })
  await flushPromises()
  return { w, router }
}

const _partij = (over = {}) => ({
  id: 'p1', aard: 'externe_partij', naam: 'Acme BV', soort: 'leverancier',
  straat_huisnummer: null, postcode: null, plaats: 'Tiel', contactpersoon_id: null,
  telefoon: null, mobiel: null, email: null, omschrijving: null, ...over,
})

// Leden-secties vragen per aard apart op (organisatie_eenheid / persoon). Mock per aard.
function mockLeden({ afdelingen = [], personen = [] } = {}) {
  api.partijen.lijst.mockImplementation((params) => {
    if (params?.aard === 'organisatie_eenheid') return Promise.resolve({ items: afdelingen, volgende_cursor: null })
    if (params?.aard === 'persoon') return Promise.resolve({ items: personen, volgende_cursor: null })
    return Promise.resolve({ items: [], volgende_cursor: null })
  })
}

beforeEach(() => {
  vi.clearAllMocks()
  api.contracten.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
  api.partijen.lijst.mockResolvedValue({ items: [], volgende_cursor: null })  // leden-overzicht (default leeg)
  api.partijen.componentenViaContract.mockResolvedValue([]) // LI019 — leverancier-componenten (default leeg)
})
afterEach(() => vi.restoreAllMocks())

describe('PartijDetail', () => {
  it('toont naam + aard-tag + soort', async () => {
    api.partijen.haal.mockResolvedValue(_partij())
    const { w } = await mountDetail()
    expect(w.find('#partij-detail-titel').text()).toContain('Acme BV')
    expect(w.find('[data-testid="detail-aard"]').text()).toContain('Externe partij')
    expect(w.text()).toContain('leverancier')  // soort-rij
  })

  // ADR-038 — intern/extern als leesregel.
  it('toont "Intern" bij een organisatie met scope=intern', async () => {
    api.partijen.haal.mockResolvedValue(_partij({ aard: 'organisatie', scope: 'intern' }))
    const { w } = await mountDetail()
    expect(w.find('[data-testid="detail-scope"]').text()).toBe('Intern')
  })

  it('toont "Extern" bij een externe partij', async () => {
    api.partijen.haal.mockResolvedValue(_partij({ aard: 'externe_partij', scope: 'extern' }))
    const { w } = await mountDetail()
    expect(w.find('[data-testid="detail-scope"]').text()).toBe('Extern')
  })

  it('toont geen intern/extern-regel bij een afdeling (afgeleid)', async () => {
    api.partijen.haal.mockResolvedValue(_partij({ aard: 'organisatie_eenheid', scope: null, organisatie_id: 'o1' }))
    const { w } = await mountDetail()
    expect(w.find('[data-testid="detail-scope"]').exists()).toBe(false)
  })

  it('toont de alleen-lezen "Rollen op objecten"-sectie (ADR-024 slice 2b)', async () => {
    api.partijen.haal.mockResolvedValue(_partij())
    const { w } = await mountDetail()
    expect(w.find('[data-testid="pr-sectie"]').exists()).toBe(true)
    expect(api.roltoewijzingen.lijst).toHaveBeenCalledWith({ partij_id: 'p1' })
  })

  it('contracten-sectie + contractenlaad ALLEEN voor een externe partij', async () => {
    api.partijen.haal.mockResolvedValue(_partij({ aard: 'persoon', naam: 'J. de Vries', soort: null }))
    const { w } = await mountDetail()
    expect(w.find('[data-testid="detail-aard"]').text()).toContain('Persoon')
    expect(w.find('[data-testid="partij-contracten-sectie"]').exists()).toBe(false)
    expect(api.contracten.lijst).not.toHaveBeenCalled()
  })

  it('externe partij: contracten-sectie zichtbaar + contracten geladen', async () => {
    api.partijen.haal.mockResolvedValue(_partij())
    const { w } = await mountDetail()
    expect(w.find('[data-testid="partij-contracten-sectie"]').exists()).toBe(true)
    expect(api.contracten.lijst).toHaveBeenCalledWith(expect.objectContaining({ leverancier_id: 'p1' }))
  })

  it('LI019 — externe partij: Componenten-sectie toont "[component] (via [contract])" met link', async () => {
    api.partijen.haal.mockResolvedValue(_partij())
    api.partijen.componentenViaContract.mockResolvedValue([
      { component_id: 'c1', component_naam: 'Zaaksysteem', contract_id: 'k1', contract_naam: 'Onderhoud 2026' },
    ])
    const { w } = await mountDetail()
    expect(api.partijen.componentenViaContract).toHaveBeenCalledWith('p1')
    const rij = w.find('[data-testid="partij-component-c1"]')
    expect(rij.exists()).toBe(true)
    expect(rij.text()).toContain('Zaaksysteem')
    expect(rij.text()).toContain('via Onderhoud 2026')
    expect(w.find('[data-testid="partij-component-link"]').attributes('href')).toContain('/componenten/c1')
  })

  it('LI019 — niet-externe partij: geen Componenten-sectie', async () => {
    api.partijen.haal.mockResolvedValue(_partij({ aard: 'organisatie' }))
    const { w } = await mountDetail()
    expect(w.find('[data-testid="partij-componenten-sectie"]').exists()).toBe(false)
    expect(api.partijen.componentenViaContract).not.toHaveBeenCalled()
  })

  it('organisatie: aparte secties Afdelingen + Personen (met e-mail/telefoon-kolommen)', async () => {
    api.partijen.haal.mockResolvedValue(_partij({ aard: 'organisatie', naam: 'Gemeente X', soort: null }))
    mockLeden({
      afdelingen: [{ id: 'a1', naam: 'Afdeling I&A', aard: 'organisatie_eenheid' }],
      personen: [{ id: 'pp1', naam: 'J. Jansen', aard: 'persoon', email: 'j@x.nl', telefoon: '0612' }],
    })
    const { w } = await mountDetail()
    expect(w.find('[data-testid="partij-afdelingen-sectie"]').exists()).toBe(true)
    expect(w.find('[data-testid="partij-personen-sectie"]').exists()).toBe(true)
    expect(api.partijen.lijst).toHaveBeenCalledWith(expect.objectContaining({ organisatie_id: 'p1', aard: 'organisatie_eenheid' }))
    expect(api.partijen.lijst).toHaveBeenCalledWith(expect.objectContaining({ organisatie_id: 'p1', aard: 'persoon' }))
    expect(w.find('[data-testid="partij-afdelingen-tabel"]').text()).toContain('Afdeling I&A')
    const personenTekst = w.find('[data-testid="partij-personen-tabel"]').text()
    expect(personenTekst).toContain('J. Jansen')
    expect(personenTekst).toContain('j@x.nl')      // e-mail-kolom
    expect(personenTekst).toContain('0612')        // telefoon-kolom
  })

  it('navigatie naar een andere partij herlaadt het scherm (watch op props.id)', async () => {
    api.partijen.haal.mockImplementation((id) =>
      Promise.resolve(id === 'p1' ? _partij({ id: 'p1', naam: 'Partij A' }) : _partij({ id: 'p2', naam: 'Partij B' })),
    )
    const { w } = await mountDetail({ id: 'p1' })
    expect(w.find('#partij-detail-titel').text()).toContain('Partij A')
    await w.setProps({ id: 'p2' })
    await flushPromises()
    expect(api.partijen.haal).toHaveBeenCalledWith('p2')
    expect(w.find('#partij-detail-titel').text()).toContain('Partij B')
  })

  it('persoon: "hoort bij" toont klikbare org- én afdeling-router-link', async () => {
    api.partijen.haal.mockImplementation((id) =>
      id === 'p1'
        ? Promise.resolve(_partij({ aard: 'persoon', naam: 'J. de Vries', soort: null, organisatie_id: 'org9', afdeling_id: 'afd9' }))
        : id === 'org9'
          ? Promise.resolve(_partij({ id: 'org9', aard: 'organisatie', naam: 'Gemeente X' }))
          : Promise.resolve(_partij({ id: 'afd9', aard: 'organisatie_eenheid', naam: 'Afdeling I&A', organisatie_id: 'org9' })),
    )
    const { w } = await mountDetail()
    const orgLink = w.find('[data-testid="hoortbij-org-link"]')
    const afdLink = w.find('[data-testid="hoortbij-afd-link"]')
    expect(orgLink.exists()).toBe(true)
    expect(orgLink.text()).toContain('Gemeente X')
    expect(afdLink.exists()).toBe(true)
    expect(afdLink.text()).toContain('Afdeling I&A')
  })

  it('persoon met organisatie maar zonder afdeling: alleen de org-link in de subtitel', async () => {
    api.partijen.haal.mockImplementation((id) =>
      id === 'p1'
        ? Promise.resolve(_partij({ aard: 'persoon', naam: 'J. de Vries', soort: null, organisatie_id: 'org9', afdeling_id: null }))
        : Promise.resolve(_partij({ id: 'org9', aard: 'organisatie', naam: 'Gemeente X' })),
    )
    const { w } = await mountDetail()
    expect(w.find('[data-testid="hoortbij-org-link"]').exists()).toBe(true)
    expect(w.find('[data-testid="hoortbij-afd-link"]').exists()).toBe(false)
  })

  it('organisatie (geen ouder): "hoort bij"-subtitel is verborgen', async () => {
    api.partijen.haal.mockResolvedValue(_partij({ aard: 'organisatie', naam: 'Gemeente X', soort: null }))
    mockLeden({})
    const { w } = await mountDetail()
    expect(w.find('[data-testid="partij-hoortbij"]').exists()).toBe(false)
  })

  it('UX-A2/A3: organisatie toont "+ Afdeling" en "+ Persoon"; klik prefilt de organisatie', async () => {
    api.partijen.haal.mockResolvedValue(_partij({ aard: 'organisatie', naam: 'Gemeente X', soort: null }))
    api.partijen.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
    const { w, router } = await mountDetail()
    expect(w.find('[data-testid="lid-afdeling"]').exists()).toBe(true)
    expect(w.find('[data-testid="lid-persoon"]').exists()).toBe(true)
    await w.find('[data-testid="lid-afdeling"]').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.name).toBe('partij-nieuw')
    expect(router.currentRoute.value.query).toMatchObject({ aard: 'organisatie_eenheid', organisatie_id: 'p1' })
  })

  it('UX-A2/A3: "+ Persoon" op organisatie prefilt aard persoon + organisatie', async () => {
    api.partijen.haal.mockResolvedValue(_partij({ aard: 'organisatie', naam: 'Gemeente X', soort: null }))
    api.partijen.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
    const { w, router } = await mountDetail()
    await w.find('[data-testid="lid-persoon"]').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.query).toMatchObject({ aard: 'persoon', organisatie_id: 'p1' })
    expect(router.currentRoute.value.query.afdeling_id).toBeUndefined()
  })

  it('UX-A2/A3: afdeling toont alleen "+ Persoon" en prefilt afdeling + organisatie', async () => {
    api.partijen.haal.mockResolvedValue(
      _partij({ aard: 'organisatie_eenheid', naam: 'Afdeling I&A', soort: null, organisatie_id: 'org-parent' }),
    )
    api.partijen.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
    const { w, router } = await mountDetail()
    expect(w.find('[data-testid="lid-afdeling"]').exists()).toBe(false)  // geen sub-afdelingen
    expect(w.find('[data-testid="lid-persoon"]').exists()).toBe(true)
    await w.find('[data-testid="lid-persoon"]').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.query).toMatchObject({
      aard: 'persoon', organisatie_id: 'org-parent', afdeling_id: 'p1',
    })
  })

  it('UX-A2/A3: viewer ziet geen lid-toevoeg-knoppen (rol-gating)', async () => {
    api.partijen.haal.mockResolvedValue(_partij({ aard: 'organisatie', naam: 'Gemeente X', soort: null }))
    api.partijen.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
    const { w } = await mountDetail({ rollen: ['viewer'] })
    expect(w.find('[data-testid="lid-afdeling"]').exists()).toBe(false)
    expect(w.find('[data-testid="lid-persoon"]').exists()).toBe(false)
  })

  it('afdelingen-sectie sorteert server-side met cursor-reset', async () => {
    api.partijen.haal.mockResolvedValue(_partij({ aard: 'organisatie', naam: 'Gemeente X', soort: null }))
    mockLeden({})
    const { w } = await mountDetail()
    // initiële afdelingen-load: org-filter + aard=organisatie_eenheid + default naam/asc
    expect(api.partijen.lijst).toHaveBeenCalledWith(
      expect.objectContaining({ organisatie_id: 'p1', aard: 'organisatie_eenheid', sort: 'naam', order: 'asc', after: undefined }),
    )
    // @sort op de afdelingen-tabel (eerste DataTable) aflopend → refetch met order=desc, gereset cursor
    await w.findComponent(DataTable).vm.$emit('sort', { sortField: 'naam', sortOrder: -1 })
    await flushPromises()
    expect(api.partijen.lijst).toHaveBeenLastCalledWith(
      expect.objectContaining({ aard: 'organisatie_eenheid', sort: 'naam', order: 'desc', after: undefined }),
    )
  })

  it('personen-sectie pagineert met de keyset-cursor ("Meer laden")', async () => {
    api.partijen.haal.mockResolvedValue(_partij({ aard: 'organisatie', naam: 'Gemeente X', soort: null }))
    api.partijen.lijst.mockImplementation((params) => {
      if (params?.aard === 'persoon') {
        return params.after
          ? Promise.resolve({ items: [{ id: 'pp2', naam: 'Bob', aard: 'persoon' }], volgende_cursor: null })
          : Promise.resolve({ items: [{ id: 'pp1', naam: 'Jan', aard: 'persoon' }], volgende_cursor: 'cur-1' })
      }
      return Promise.resolve({ items: [], volgende_cursor: null })
    })
    const { w } = await mountDetail()
    expect(w.find('[data-testid="personen-meer-laden"]').exists()).toBe(true)
    await w.find('[data-testid="personen-meer-laden"]').trigger('click')
    await flushPromises()
    expect(api.partijen.lijst).toHaveBeenLastCalledWith(expect.objectContaining({ aard: 'persoon', after: 'cur-1' }))
    expect(w.find('[data-testid="personen-meer-laden"]').exists()).toBe(false)  // cursor op null
    const tekst = w.find('[data-testid="partij-personen-tabel"]').text()
    expect(tekst).toContain('Jan')
    expect(tekst).toContain('Bob')
  })

  it('externe partij zonder leden → beide secties tonen een lege-staat', async () => {
    api.partijen.haal.mockResolvedValue(_partij())  // externe_partij, organisatie-achtig
    mockLeden({})
    const { w } = await mountDetail()
    expect(w.find('[data-testid="partij-afdelingen-sectie"]').exists()).toBe(true)
    expect(w.find('[data-testid="partij-afdelingen-leeg"]').exists()).toBe(true)
    expect(w.find('[data-testid="partij-personen-sectie"]').exists()).toBe(true)
    expect(w.find('[data-testid="partij-personen-leeg"]').exists()).toBe(true)
  })

  it('afdeling: alleen Personen-sectie + klikbare "hoort bij" de organisatie', async () => {
    api.partijen.haal.mockImplementation((id) =>
      id === 'p1'
        ? Promise.resolve(_partij({ aard: 'organisatie_eenheid', naam: 'Afdeling I&A', soort: null, organisatie_id: 'org9' }))
        : Promise.resolve(_partij({ id: 'org9', aard: 'organisatie', naam: 'Gemeente X' })),
    )
    mockLeden({ personen: [{ id: 'pp1', naam: 'J. Jansen', aard: 'persoon' }] })
    const { w } = await mountDetail()
    expect(w.find('[data-testid="partij-afdelingen-sectie"]').exists()).toBe(false)  // geen sub-afdelingen
    expect(w.find('[data-testid="partij-personen-sectie"]').exists()).toBe(true)
    expect(api.partijen.lijst).toHaveBeenCalledWith(expect.objectContaining({ afdeling_id: 'p1', aard: 'persoon' }))
    expect(w.find('[data-testid="hoortbij-org-link"]').text()).toContain('Gemeente X')
    expect(w.find('[data-testid="partij-personen-tabel"]').text()).toContain('J. Jansen')
  })

  it('verwijderen 409 IN_GEBRUIK blijft op het detail', async () => {
    api.partijen.haal.mockResolvedValue(_partij())
    api.partijen.verwijder.mockRejectedValueOnce({ status: 409, code: 'IN_GEBRUIK', message: 'In gebruik.' })
    const { w, router } = await mountDetail()
    await w.find('[data-testid="verwijder-knop"]').trigger('click')
    await flushPromises()
    await w.find('[data-testid="verwijder-bevestig"]').trigger('click')
    await flushPromises()
    expect(api.partijen.verwijder).toHaveBeenCalledWith('p1')
    expect(router.currentRoute.value.name).toBe('partij-detail')
  })

  it('verwijderen lukt → navigeert naar de partijenlijst', async () => {
    api.partijen.haal.mockResolvedValue(_partij())
    api.partijen.verwijder.mockResolvedValueOnce({})
    const { w, router } = await mountDetail()
    await w.find('[data-testid="verwijder-knop"]').trigger('click')
    await flushPromises()
    await w.find('[data-testid="verwijder-bevestig"]').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.name).toBe('partij-lijst')
  })

  // ADR-039 — aanspreekpunt: doorklikbare persoon op organisatie/externe partij.
  it('externe partij met aanspreekpunt: doorklikbare persoon (id + geresolvede naam)', async () => {
    api.partijen.haal.mockImplementation((id) =>
      id === 'cp9'
        ? Promise.resolve(_partij({ id: 'cp9', aard: 'persoon', naam: 'M. de Boer', organisatie_id: 'p1' }))
        : Promise.resolve(_partij({ contactpersoon_id: 'cp9' })),
    )
    const { w } = await mountDetail()
    const link = w.find('[data-testid="detail-aanspreekpunt-link"]')
    expect(link.exists()).toBe(true)
    expect(link.text()).toContain('M. de Boer')
    expect(link.attributes('href')).toContain('/partijen/cp9')
    expect(api.partijen.haal).toHaveBeenCalledWith('cp9')
  })

  it('organisatie zonder aanspreekpunt: rij toont — (geen link)', async () => {
    api.partijen.haal.mockResolvedValue(_partij({ aard: 'organisatie', soort: null, contactpersoon_id: null }))
    mockLeden({})
    const { w } = await mountDetail()
    expect(w.find('[data-testid="detail-aanspreekpunt"]').exists()).toBe(true)
    expect(w.find('[data-testid="detail-aanspreekpunt-link"]').exists()).toBe(false)
  })

  it('afdeling/persoon: geen aanspreekpunt-rij (dragen er geen)', async () => {
    api.partijen.haal.mockResolvedValue(_partij({ aard: 'persoon', naam: 'J', soort: null, organisatie_id: 'o1' }))
    const { w } = await mountDetail()
    expect(w.find('[data-testid="detail-aanspreekpunt"]').exists()).toBe(false)
  })

  it('rol-gating: viewer ziet geen bewerk-/verwijder-knop', async () => {
    api.partijen.haal.mockResolvedValue(_partij())
    const { w } = await mountDetail({ rollen: ['viewer'] })
    expect(w.find('[data-testid="bewerken-knop"]').exists()).toBe(false)
    expect(w.find('[data-testid="verwijder-knop"]').exists()).toBe(false)
  })
})
