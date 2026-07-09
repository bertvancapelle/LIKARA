/** Tests — ProcesLijst (procesregister-boom, ADR-042 slice 4a). */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'

vi.mock('@/api', () => ({
  api: { processen: { lijst: vi.fn(), maak: vi.fn(), werkBij: vi.fn() } },
}))

// LI035 succes-standaard — helper gemockt zodat de succes-flow assertbaar is.
vi.mock('@/meldingen', () => ({ toastSucces: vi.fn() }))

import { api } from '@/api'
import { toastSucces } from '@/meldingen'
import { useAuthStore } from '@/store/auth'
import ProcesLijst from '@modules/bwb_ontvlechting/frontend/views/ProcesLijst.vue'

function maakRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/processen', name: 'proces-lijst', component: ProcesLijst },
      { path: '/processen/:id', name: 'proces-detail', component: { template: '<div/>' } },
    ],
  })
}

const _p = (id, naam, ouder_id = null, toelichting = null) => ({
  id, naam, ouder_id, toelichting,
  created_at: '2026-07-01T10:00:00Z', updated_at: '2026-07-01T10:00:00Z',
})

// Geseede boom: Vergunningverlening → Aanvraag behandelen; Burgerzaken → Verhuizing verwerken.
const _boom = () => [
  _p('vv', 'Vergunningverlening'),
  _p('ab', 'Aanvraag behandelen', 'vv'),
  _p('bz', 'Burgerzaken'),
  _p('verh', 'Verhuizing verwerken', 'bz'),
]

async function mountLijst({ rollen = ['medewerker'] } = {}) {
  const router = maakRouter()
  await router.push('/processen')
  await router.isReady()
  const pinia = createPinia()
  const auth = useAuthStore(pinia)
  auth.user = { sub: 's', tenant_id: 't', email: 'a@b.nl', roles: rollen }
  const w = mount(ProcesLijst, { global: { plugins: [pinia, [PrimeVue, { unstyled: true }], ToastService, router], stubs: { teleport: true } } })
  await flushPromises()
  return w
}

beforeEach(() => {
  vi.clearAllMocks()
  sessionStorage.clear() // lijststaat (useLijstStaat) mag niet tussen tests lekken
  api.processen.lijst.mockResolvedValue({ items: _boom(), volgende_cursor: null })
})
afterEach(() => vi.restoreAllMocks())

describe('ProcesLijst — boomweergave', () => {
  it('toont hoofdprocessen; deelprocessen pas na uitklappen', async () => {
    const w = await mountLijst()
    // Assert op de boom-container: de (i)-uitlegtekst noemt "Aanvraag behandelen" als voorbeeld.
    const boom = () => w.find('[data-testid="processen-boom"]').text()
    expect(boom()).toContain('Vergunningverlening')
    expect(boom()).toContain('Burgerzaken')
    expect(boom()).not.toContain('Aanvraag behandelen') // ingeklapt
    await w.find('[data-testid="proces-toggle-vv"]').trigger('click')
    expect(boom()).toContain('Aanvraag behandelen')
    expect(w.find('[data-testid="proces-toggle-vv"]').attributes('aria-expanded')).toBe('true')
  })

  it('haalt ALLE pagina\'s op voor de boom (keyset-lus)', async () => {
    api.processen.lijst
      .mockResolvedValueOnce({ items: [_p('vv', 'Vergunningverlening')], volgende_cursor: 'cur-1' })
      .mockResolvedValueOnce({ items: [_p('ab', 'Aanvraag behandelen', 'vv')], volgende_cursor: null })
    const w = await mountLijst()
    expect(api.processen.lijst).toHaveBeenCalledTimes(2)
    expect(api.processen.lijst).toHaveBeenLastCalledWith(expect.objectContaining({ after: 'cur-1' }))
    await w.find('[data-testid="proces-toggle-vv"]').trigger('click')
    expect(w.find('[data-testid="processen-boom"]').text()).toContain('Aanvraag behandelen')
  })

  it('zoeken filtert soepel (partieel, hoofdletter-ongevoelig) en klapt het pad naar de treffer open', async () => {
    const w = await mountLijst()
    await w.find('[data-testid="filter-zoek"]').setValue('  AANVRAAG ')
    const boom = w.find('[data-testid="processen-boom"]').text()
    expect(boom).toContain('Aanvraag behandelen') // treffer zichtbaar zonder handmatig uitklappen
    expect(boom).toContain('Vergunningverlening') // het pad ernaartoe blijft staan
    expect(boom).not.toContain('Burgerzaken') // niet-matchende tak verdwijnt
  })

  it('rij-link gaat naar de proces-detail-route', async () => {
    const w = await mountLijst()
    expect(w.find('[data-testid="proces-link"]').attributes('href')).toContain('/processen/')
  })

  it('nieuw top-level proces via de dialog → api.processen.maak zonder ouder', async () => {
    api.processen.maak.mockResolvedValue(_p('nieuw', 'Inkoop'))
    const w = await mountLijst()
    await w.find('[data-testid="nieuw-proces"]').trigger('click')
    await w.find('[data-testid="proces-naam"]').setValue('Inkoop')
    await w.find('[data-testid="proces-dialog-opslaan"]').trigger('submit')
    await flushPromises()
    expect(api.processen.maak).toHaveBeenCalledWith({ naam: 'Inkoop', toelichting: null })
    expect(toastSucces).toHaveBeenCalledWith(expect.anything(), 'Proces aangemaakt')
  })

  it('hernoemen opent voorgevuld en roept werkBij aan', async () => {
    api.processen.werkBij.mockResolvedValue(_p('vv', 'Vergunningen'))
    const w = await mountLijst()
    await w.find('[data-testid="proces-hernoem-vv"]').trigger('click')
    expect(w.find('[data-testid="proces-naam"]').element.value).toBe('Vergunningverlening')
    await w.find('[data-testid="proces-naam"]').setValue('Vergunningen')
    await w.find('[data-testid="proces-dialog-opslaan"]').trigger('submit')
    await flushPromises()
    expect(api.processen.werkBij).toHaveBeenCalledWith('vv', { naam: 'Vergunningen', toelichting: null })
    expect(toastSucces).toHaveBeenCalledWith(expect.anything(), 'Opgeslagen')
  })

  it('rol-gating: viewer ziet geen aanmaak-/hernoem-affordances', async () => {
    const w = await mountLijst({ rollen: ['viewer'] })
    expect(w.find('[data-testid="nieuw-proces"]').exists()).toBe(false)
    expect(w.find('[data-testid="proces-hernoem-vv"]').exists()).toBe(false)
  })
})

describe('ProcesLijst — lijststaat behouden bij terugnavigeren (useLijstStaat)', () => {
  it('herstelt zoekterm + uitgeklapte takken uit de bewaarde staat', async () => {
    sessionStorage.setItem(
      'lijst-state:proces-lijst',
      JSON.stringify({ zoekterm: '', openTakken: ['bz'] }),
    )
    const w = await mountLijst()
    // De bz-tak staat hersteld open zonder klik; vv niet (assert op de boom-container —
    // de (i)-uitlegtekst noemt "Aanvraag behandelen" als voorbeeld).
    const boom = w.find('[data-testid="processen-boom"]').text()
    expect(boom).toContain('Verhuizing verwerken')
    expect(boom).not.toContain('Aanvraag behandelen')
  })

  it('bewaart de actuele staat op het beforeunload-pad (F5-gedrag) en pruned onbekende takken', async () => {
    sessionStorage.setItem(
      'lijst-state:proces-lijst',
      JSON.stringify({ zoekterm: '', openTakken: ['bz', 'weg-tak'] }),
    )
    const w = await mountLijst()
    await w.find('[data-testid="filter-zoek"]').setValue('burger')
    window.dispatchEvent(new Event('beforeunload'))
    const bewaard = JSON.parse(sessionStorage.getItem('lijst-state:proces-lijst'))
    expect(bewaard.zoekterm).toBe('burger')
    expect(bewaard.openTakken).toEqual(['bz']) // 'weg-tak' bestaat niet meer → stil geprund
    w.unmount()
  })
})
