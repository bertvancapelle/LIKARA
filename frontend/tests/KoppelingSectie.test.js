/** Tests — KoppelingSectie (child-sectie via @modules; flow-relaties, twee richtingen). */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'

vi.mock('@/api', () => ({
  api: {
    // ADR-023: koppeling = flow-relatie → via het unified /relaties-endpoint.
    relaties: { lijst: vi.fn(), maak: vi.fn(), werkBij: vi.fn(), verwijder: vi.fn() },
    applicaties: { lijst: vi.fn() },
  },
}))

import { api } from '@/api'
import { useAuthStore } from '@/store/auth'
import KoppelingSectie from '@modules/bwb_ontvlechting/frontend/views/KoppelingSectie.vue'

const APP = 'app-1'
const ANDER = 'app-2'

// Eén flow-relatie (RELATIE-vorm): kenmerken dragen richting/protocol/impact.
function _rel(id, bron, doel) {
  return {
    id,
    bron_id: bron,
    doel_id: doel,
    relatietype: 'flow',
    kenmerken: { richting: 'eenrichting', protocol: 'api', impact_bij_verbreking: 'hoog' },
    omschrijving: null,
  }
}

async function mountSectie({ rollen = ['beheerder'] } = {}) {
  const pinia = createPinia()
  const auth = useAuthStore(pinia)
  auth.user = { sub: 's', tenant_id: 't', email: 'a@b.nl', roles: rollen }
  const wrapper = mount(KoppelingSectie, {
    props: { applicatieId: APP },
    attachTo: document.body,
    global: { plugins: [pinia, [PrimeVue, { unstyled: true }], ToastService], stubs: { teleport: true } },
  })
  await flushPromises()
  return wrapper
}

beforeEach(() => {
  vi.clearAllMocks()
  api.relaties.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
  // Voedt zowel de namenkaart (tegenpartij-kolom) als de ZoekSelect-pickers.
  api.applicaties.lijst.mockResolvedValue({
    items: [
      { id: APP, naam: 'Deze App' },
      { id: ANDER, naam: 'Andere App' },
    ],
    volgende_cursor: null,
  })
})

// ZoekSelect-interactie (CD049): focus → zoek → klik resultaat.
async function kiesZoek(w, prefix, id) {
  await w.find(`[data-testid="${prefix}-input"]`).trigger('focus')
  await flushPromises()
  await w.find(`[data-testid="${prefix}-optie-${id}"]`).trigger('mousedown')
  await flushPromises()
}
afterEach(() => vi.restoreAllMocks())

describe('KoppelingSectie — B4 gecureerde labels', () => {
  it('het formulier toont gecureerde veld-/optielabels (niet uit de veldnaam afgeleid)', async () => {
    const w = await mountSectie()
    await w.find('[data-testid="kp-toevoegen"]').trigger('click')
    await flushPromises()
    const form = w.find('[data-testid="kp-form"]').text()
    expect(form).toContain('Impact bij verbreking') // gecureerd veldlabel
    expect(form).not.toContain('impact bij verbreking') // niet de lowercase veldnaam-afleiding
    // optielabel gecureerd: 'hoog' → 'Hoog', 'eenrichting' → 'Eenrichting'
    const impactOpties = w.find('[data-testid="kp-veld-impact_bij_verbreking"]').findAll('option').map((o) => o.text())
    expect(impactOpties).toContain('Hoog')
    expect(impactOpties).not.toContain('hoog')
    const richtingOpties = w.find('[data-testid="kp-veld-richting"]').findAll('option').map((o) => o.text())
    expect(richtingOpties).toContain('Eenrichting')
  })
})

describe('KoppelingSectie', () => {
  it('doet twee flow-calls (uitgaand bron_id + inkomend doel_id) en toont beide sets', async () => {
    api.relaties.lijst.mockImplementation(({ bron_id }) =>
      Promise.resolve(
        bron_id === APP
          ? { items: [_rel('k1', APP, ANDER)], volgende_cursor: null } // uitgaand
          : { items: [_rel('k2', ANDER, APP)], volgende_cursor: null }, // inkomend
      ),
    )
    const w = await mountSectie()
    const calls = api.relaties.lijst.mock.calls.map((c) => c[0])
    expect(calls.every((a) => a.relatietype === 'flow')).toBe(true)
    expect(calls.some((a) => a.bron_id === APP)).toBe(true)
    expect(calls.some((a) => a.doel_id === APP)).toBe(true)
    expect(w.find('[data-testid="kp-tabel-uitgaand"]').exists()).toBe(true)
    expect(w.find('[data-testid="kp-tabel-inkomend"]').exists()).toBe(true)
    // tegenpartij-naam client-side geresolveerd uit de namenkaart.
    expect(w.find('[data-testid="kp-tabel-uitgaand"]').text()).toContain('Andere App')
  })

  it('rol-gating: viewer geen Toevoegen, beheerder wel', async () => {
    expect((await mountSectie({ rollen: ['viewer'] })).find('[data-testid="kp-toevoegen"]').exists()).toBe(false)
    expect((await mountSectie({ rollen: ['beheerder'] })).find('[data-testid="kp-toevoegen"]').exists()).toBe(true)
  })

  it('vult bron met de default-app (ZoekSelect-label) en weigert bron == doel', async () => {
    const w = await mountSectie()
    await w.find('[data-testid="kp-toevoegen"]').trigger('click')
    await flushPromises()
    expect(w.find('[data-testid="kp-veld-bron-input"]').element.value).toBe('Deze App')
    await kiesZoek(w, 'kp-veld-doel', APP)
    await w.find('[data-testid="kp-veld-richting"]').setValue('eenrichting')
    await w.find('[data-testid="kp-veld-protocol"]').setValue('api')
    await w.find('[data-testid="kp-veld-impact_bij_verbreking"]').setValue('hoog')
    await w.find('[data-testid="kp-form"]').trigger('submit')
    await flushPromises()
    expect(w.find('[data-testid="kp-fout-doel"]').exists()).toBe(true)
    expect(api.relaties.maak).not.toHaveBeenCalled()
  })

  it('maakt een flow-relatie aan met geldige bron≠doel en ververst beide richtingen', async () => {
    api.relaties.maak.mockResolvedValueOnce({ id: 'new' })
    const w = await mountSectie()
    const voor = api.relaties.lijst.mock.calls.length
    await w.find('[data-testid="kp-toevoegen"]').trigger('click')
    await flushPromises()
    await kiesZoek(w, 'kp-veld-doel', ANDER)
    await w.find('[data-testid="kp-veld-richting"]').setValue('eenrichting')
    await w.find('[data-testid="kp-veld-protocol"]').setValue('api')
    await w.find('[data-testid="kp-veld-impact_bij_verbreking"]').setValue('hoog')
    await w.find('[data-testid="kp-form"]').trigger('submit')
    await flushPromises()
    expect(api.relaties.maak).toHaveBeenCalledTimes(1)
    expect(api.relaties.maak.mock.calls[0][0]).toMatchObject({
      bron_id: APP,
      doel_id: ANDER,
      relatietype: 'flow',
      kenmerken: { richting: 'eenrichting', protocol: 'api', impact_bij_verbreking: 'hoog' },
    })
    expect(api.relaties.lijst.mock.calls.length).toBe(voor + 2) // beide richtingen herladen
  })

  it('verwijdert een koppeling via api.relaties.verwijder', async () => {
    api.relaties.lijst.mockImplementation(({ bron_id }) =>
      Promise.resolve(bron_id === APP ? { items: [_rel('k1', APP, ANDER)], volgende_cursor: null } : { items: [], volgende_cursor: null }),
    )
    api.relaties.verwijder.mockResolvedValueOnce(undefined)
    const w = await mountSectie()
    await w.find('[data-testid="kp-verwijder-k1"]').trigger('click')
    await flushPromises()
    await w.find('[data-testid="kp-verwijder-bevestig"]').trigger('click')
    await flushPromises()
    expect(api.relaties.verwijder).toHaveBeenCalledWith('k1')
  })

  it('per-richting "Meer laden" gebruikt de cursor van de juiste richting (flow)', async () => {
    api.relaties.lijst.mockImplementation(({ bron_id }) =>
      Promise.resolve(
        bron_id === APP
          ? { items: [_rel('k1', APP, ANDER)], volgende_cursor: 'cur-uit' }
          : { items: [_rel('k2', ANDER, APP)], volgende_cursor: null },
      ),
    )
    const w = await mountSectie()
    expect(w.find('[data-testid="kp-meer-uitgaand"]').exists()).toBe(true)
    expect(w.find('[data-testid="kp-meer-inkomend"]').exists()).toBe(false)
    await w.find('[data-testid="kp-meer-uitgaand"]').trigger('click')
    await flushPromises()
    expect(api.relaties.lijst).toHaveBeenLastCalledWith({ relatietype: 'flow', bron_id: APP, limit: 25, after: 'cur-uit' })
  })
})
