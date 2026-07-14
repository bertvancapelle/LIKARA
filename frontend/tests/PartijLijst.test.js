/** Tests — PartijLijst (module-view via @modules; ADR-024 slice 2a). */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'

vi.mock('@/api', () => ({ api: { partijen: { lijst: vi.fn() } } }))

import { api } from '@/api'
import { useAuthStore } from '@/store/auth'
import PartijLijst from '@modules/bwb_ontvlechting/frontend/views/PartijLijst.vue'

function maakRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/partijen', name: 'partij-lijst', component: PartijLijst },
      { path: '/partijen/nieuw', name: 'partij-nieuw', component: { template: '<div/>' } },
      { path: '/partijen/:id', name: 'partij-detail', component: { template: '<div/>' } },
    ],
  })
}

async function mountLijst({ rollen = ['medewerker'] } = {}) {
  const router = maakRouter()
  await router.push('/partijen')
  await router.isReady()
  const pinia = createPinia()
  const auth = useAuthStore(pinia)
  auth.user = { sub: 's', tenant_id: 't', email: 'a@b.nl', roles: rollen }
  const w = mount(PartijLijst, { global: { plugins: [pinia, [PrimeVue, { unstyled: true }], router] } })
  await flushPromises()
  return w
}

const _partij = (naam, id, aard = 'externe_partij') => ({
  id, naam, aard, plaats: 'Tiel',
  contactpersoon_id: 'cp-1', contactpersoon_naam: 'J. Jansen',
})

beforeEach(() => {
  vi.clearAllMocks()
  sessionStorage.clear() // lijststaat (useLijstStaat) mag niet tussen tests lekken
})
afterEach(() => vi.restoreAllMocks())

describe('PartijLijst', () => {
  it('LI040: een afdeling/persoon toont zijn volledige identiteit in de naamkolom (naam + gedempte org)', async () => {
    api.partijen.lijst.mockResolvedValue({
      items: [
        { id: 'a1', naam: 'Burgerzaken', aard: 'organisatie_eenheid', organisatie_naam: 'Gemeente Tiel' },
        { id: 'p1', naam: 'J. de Vries', aard: 'persoon', afdeling_naam: 'Burgerzaken', organisatie_naam: 'Gemeente Tiel' },
      ],
      volgende_cursor: null,
    })
    const w = await mountLijst()
    const links = w.findAll('[data-testid="rij-link"]').map((n) => n.text().replace(/\s+/g, ' '))
    expect(links[0]).toBe('Burgerzaken — Gemeente Tiel')
    expect(links[1]).toBe('J. de Vries — Burgerzaken — Gemeente Tiel')
    expect(w.find('[data-testid="identiteit-naam-ontbreekt"]').exists()).toBe(false)
  })

  it('rendert de geladen partijen met aard-label', async () => {
    api.partijen.lijst.mockResolvedValueOnce({
      items: [_partij('Acme BV', 'l1'), _partij('Afdeling I&A', 'a1', 'organisatie_eenheid')],
      volgende_cursor: null,
    })
    const w = await mountLijst()
    expect(w.text()).toContain('Acme BV')
    expect(w.text()).toContain('Afdeling I&A')
    // aard-kolom toont leesbare labels
    expect(w.findAll('[data-testid="rij-aard"]').map((n) => n.text())).toEqual(['Externe partij', 'Afdeling'])
  })

  it('aard-filter geeft de gekozen aard mee aan de API + reset cursor', async () => {
    api.partijen.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
    const w = await mountLijst()
    await w.find('[data-testid="filter-aard"]').setValue('persoon')
    await flushPromises()
    expect(api.partijen.lijst).toHaveBeenLastCalledWith(
      expect.objectContaining({ aard: 'persoon', after: undefined }),
    )
  })

  it('"Meer laden" pagineert met de cursor', async () => {
    api.partijen.lijst
      .mockResolvedValueOnce({ items: [_partij('Eerste', 'l1')], volgende_cursor: 'cur-1' })
      .mockResolvedValueOnce({ items: [_partij('Tweede', 'l2')], volgende_cursor: null })
    const w = await mountLijst()
    await w.find('[data-testid="meer-laden"]').trigger('click')
    await flushPromises()
    expect(api.partijen.lijst).toHaveBeenLastCalledWith({ limit: 25, after: 'cur-1' })
    expect(w.find('[data-testid="meer-laden"]').exists()).toBe(false)
  })

  it('linkt elke rij naar de partij-detail-route', async () => {
    api.partijen.lijst.mockResolvedValueOnce({ items: [_partij('Acme', 'l-42')], volgende_cursor: null })
    const w = await mountLijst()
    expect(w.find('[data-testid="rij-link"]').attributes('href')).toContain('/partijen/l-42')
  })

  it('aanspreekpunt-kolom linkt door naar de persoon (contactpersoon_id + naam)', async () => {
    api.partijen.lijst.mockResolvedValueOnce({ items: [_partij('Acme', 'l1')], volgende_cursor: null })
    const w = await mountLijst()
    const link = w.find('[data-testid="rij-contactpersoon-link"]')
    expect(link.exists()).toBe(true)
    expect(link.text()).toBe('J. Jansen')
    expect(link.attributes('href')).toContain('/partijen/cp-1')
  })

  it('aanspreekpunt-kolom toont — zonder contactpersoon_id', async () => {
    api.partijen.lijst.mockResolvedValueOnce({
      items: [{ id: 'l2', naam: 'Geen contact', aard: 'organisatie', plaats: 'Tiel' }],
      volgende_cursor: null,
    })
    const w = await mountLijst()
    expect(w.find('[data-testid="rij-contactpersoon-link"]').exists()).toBe(false)
  })

  it('lege status zonder items', async () => {
    api.partijen.lijst.mockResolvedValueOnce({ items: [], volgende_cursor: null })
    expect((await mountLijst()).find('[data-testid="lijst-leeg"]').exists()).toBe(true)
  })

  it('foutmelding (role=alert) bij API-fout', async () => {
    api.partijen.lijst.mockRejectedValueOnce(new Error('Netwerkfout'))
    const w = await mountLijst()
    expect(w.find('[data-testid="lijst-fout"]').attributes('role')).toBe('alert')
  })

  it('bij een 401 (verlopen sessie) toont de lijst geen rauwe code (vangrail redirect)', async () => {
    const err = new Error('NIET_GEAUTHENTICEERD')
    err.status = 401
    api.partijen.lijst.mockRejectedValueOnce(err)
    const w = await mountLijst()
    expect(w.text()).not.toContain('NIET_GEAUTHENTICEERD')
    expect(w.find('[data-testid="lijst-fout"]').exists()).toBe(false) // fout=null → geen banner
  })

  it('rol-gating: aanmaak-knop alleen voor medewerker+', async () => {
    api.partijen.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
    expect((await mountLijst({ rollen: ['medewerker'] })).find('[data-testid="nieuwe-partij"]').exists()).toBe(true)
    expect((await mountLijst({ rollen: ['viewer'] })).find('[data-testid="nieuwe-partij"]').exists()).toBe(false)
  })
})

describe('PartijLijst — lijststaat behouden bij terugnavigeren (useLijstStaat)', () => {
  it('herstelt de bewaarde lijststaat end-to-end in de eerste API-aanroep én de controls', async () => {
    sessionStorage.setItem(
      'lijst-state:partij-lijst',
      JSON.stringify({ filterAard: 'organisatie', filterZoek: 'tiel', sortVeld: 'naam', sortRichting: 'desc' }),
    )
    api.partijen.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
    const w = await mountLijst()
    // V012-les: bewijs de keten — de herstelde stand belandt in de api-call.
    expect(api.partijen.lijst).toHaveBeenCalledWith(
      expect.objectContaining({ aard: 'organisatie', zoek: 'tiel', sort: 'naam', order: 'desc' }),
    )
    // …én de controls tonen de herstelde stand (geen onzichtbaar actief filter).
    expect(w.find('[data-testid="filter-aard"]').element.value).toBe('organisatie')
    expect(w.find('[data-testid="filter-zoek"]').element.value).toBe('tiel')
  })

  it('valt stil terug op defaults bij een ongeldige bewaarde stand (geldige velden herstellen wél)', async () => {
    sessionStorage.setItem(
      'lijst-state:partij-lijst',
      JSON.stringify({ filterAard: 'bestaat_niet', sortVeld: 'geen_kolom', sortRichting: 'omhoog', filterZoek: 'acme' }),
    )
    api.partijen.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
    await mountLijst()
    const params = api.partijen.lijst.mock.calls[0][0]
    expect(params.aard).toBeUndefined()
    expect(params.sort).toBeUndefined()
    expect(params.zoek).toBe('acme')
  })

  it('bewaart een wijziging ná herstel (beforeunload-pad = F5-gedrag)', async () => {
    api.partijen.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
    const w = await mountLijst()
    await w.find('[data-testid="filter-aard"]').setValue('organisatie')
    await flushPromises()
    window.dispatchEvent(new Event('beforeunload'))
    const bewaard = JSON.parse(sessionStorage.getItem('lijst-state:partij-lijst'))
    expect(bewaard.filterAard).toBe('organisatie')
    w.unmount() // listener netjes opruimen voor de volgende test
  })
})
