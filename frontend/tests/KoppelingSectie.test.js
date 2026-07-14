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
    componenten: { lijst: vi.fn() },
  },
}))

import { api } from '@/api'
import { DataTable, Column } from '@/primevue'
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
  api.componenten.lijst.mockResolvedValue({
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

  it('ADR-050 rol-gating: een koppeling is een uitspraak → medewerker mag verwijderen; viewer niet', async () => {
    api.relaties.lijst.mockImplementation(({ bron_id }) =>
      Promise.resolve(bron_id === APP ? { items: [_rel('k1', APP, ANDER)], volgende_cursor: null } : { items: [], volgende_cursor: null }),
    )
    const m = await mountSectie({ rollen: ['medewerker'] })
    expect(m.find('[data-testid="kp-toevoegen"]').exists()).toBe(true)
    expect(m.find('[data-testid="kp-bewerk-k1"]').exists()).toBe(true)
    expect(m.find('[data-testid="kp-verwijder-k1"]').exists()).toBe(true) // ADR-050: wie legt, neemt terug
    const b = await mountSectie({ rollen: ['viewer'] })
    expect(b.find('[data-testid="kp-verwijder-k1"]').exists()).toBe(false)
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

  it('LI039 blok B — een nieuwe flow staat direct VOORAAN in de juiste richtingtabel, aangestipt', async () => {
    api.relaties.maak.mockResolvedValueOnce({
      id: 'new', bron_id: APP, doel_id: ANDER, naam: 'Mijn koppeling',
      kenmerken: { richting: 'eenrichting', protocol: 'api', impact_bij_verbreking: 'hoog' },
      omschrijving: null,
    })
    const w = await mountSectie()
    const voor = api.relaties.lijst.mock.calls.length
    await w.find('[data-testid="kp-toevoegen"]').trigger('click')
    await flushPromises()
    await w.find('[data-testid="kp-veld-naam"]').setValue('Mijn koppeling')
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
      naam: 'Mijn koppeling',
      kenmerken: { richting: 'eenrichting', protocol: 'api', impact_bij_verbreking: 'hoog' },
    })
    // Geen herlaad-sprong: het aanmaak-antwoord wordt via dezelfde mapper vooraan in de
    // uitgaande tabel gezet (created_at asc zou het achter "Meer laden" verstoppen);
    // de aanstip draagt de uitleg. Een verse laadbeurt toont de natuurlijke volgorde.
    expect(api.relaties.lijst.mock.calls.length).toBe(voor)
    const eersteRij = w.find('[data-testid="kp-tabel-uitgaand"] tbody tr')
    expect(eersteRij.text()).toContain('Mijn koppeling')
    expect(eersteRij.attributes('class')).toContain('lk-aangestipt')
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

describe('KoppelingSectie — ADR-023a Fase 4 (naam, DUBBEL, naam-kolom, sortering)', () => {
  async function vulGeldigFormulier(w, naam = 'K1') {
    await w.find('[data-testid="kp-toevoegen"]').trigger('click')
    await flushPromises()
    await w.find('[data-testid="kp-veld-naam"]').setValue(naam)
    await kiesZoek(w, 'kp-veld-doel', ANDER)
    await w.find('[data-testid="kp-veld-richting"]').setValue('eenrichting')
    await w.find('[data-testid="kp-veld-protocol"]').setValue('api')
    await w.find('[data-testid="kp-veld-impact_bij_verbreking"]').setValue('hoog')
  }

  it('toont een verplicht Naam-veld in het aanmaakformulier', async () => {
    const w = await mountSectie()
    await w.find('[data-testid="kp-toevoegen"]').trigger('click')
    await flushPromises()
    expect(w.find('[data-testid="kp-veld-naam"]').exists()).toBe(true)
    expect(w.find('[data-testid="kp-form"]').text()).toContain('Naam *')
  })

  it('toont het Naam-veld voorgevuld bij bewerken', async () => {
    api.relaties.lijst.mockImplementation(({ bron_id }) =>
      Promise.resolve(
        bron_id === APP
          ? { items: [{ ..._rel('k1', APP, ANDER), naam: 'Bestaande naam' }], volgende_cursor: null }
          : { items: [], volgende_cursor: null },
      ),
    )
    const w = await mountSectie()
    await w.find('[data-testid="kp-bewerk-k1"]').trigger('click')
    await flushPromises()
    expect(w.find('[data-testid="kp-veld-naam"]').element.value).toBe('Bestaande naam')
  })

  it('leeg Naam-veld → client-side fout en geen submit', async () => {
    const w = await mountSectie()
    await w.find('[data-testid="kp-toevoegen"]').trigger('click')
    await flushPromises()
    await kiesZoek(w, 'kp-veld-doel', ANDER)
    await w.find('[data-testid="kp-veld-richting"]').setValue('eenrichting')
    await w.find('[data-testid="kp-veld-protocol"]').setValue('api')
    await w.find('[data-testid="kp-veld-impact_bij_verbreking"]').setValue('hoog')
    await w.find('[data-testid="kp-form"]').trigger('submit')
    await flushPromises()
    expect(w.find('[data-testid="kp-fout-naam"]').exists()).toBe(true)
    expect(api.relaties.maak).not.toHaveBeenCalled()
  })

  it('409 KOPPELING_DUBBEL toont een bevestigingsdialoog (geen fout-toast)', async () => {
    api.relaties.maak.mockRejectedValueOnce({ status: 409, code: 'KOPPELING_DUBBEL' })
    const w = await mountSectie()
    await vulGeldigFormulier(w)
    await w.find('[data-testid="kp-form"]').trigger('submit')
    await flushPromises()
    expect(w.find('[data-testid="kp-dubbel-dialog"]').exists()).toBe(true)
    expect(api.relaties.maak).toHaveBeenCalledTimes(1)
  })

  it('na "Toch aanmaken" hersubmit met negeer_waarschuwing=true', async () => {
    api.relaties.maak.mockRejectedValueOnce({ status: 409, code: 'KOPPELING_DUBBEL' })
    api.relaties.maak.mockResolvedValueOnce({ id: 'new' })
    const w = await mountSectie()
    await vulGeldigFormulier(w)
    await w.find('[data-testid="kp-form"]').trigger('submit')
    await flushPromises()
    await w.find('[data-testid="kp-dubbel-bevestig"]').trigger('click')
    await flushPromises()
    expect(api.relaties.maak).toHaveBeenCalledTimes(2)
    expect(api.relaties.maak.mock.calls[1][0]).toMatchObject({ naam: 'K1', negeer_waarschuwing: true })
  })

  it('toont een Naam-kolom in beide tabellen', async () => {
    const w = await mountSectie()
    const headers = w.findAllComponents(Column).map((c) => c.props('header'))
    expect(headers.filter((h) => h === 'Naam').length).toBe(2)
  })

  it('klik op de Naam-kolomheader stuurt sort=naam server-side mee (per tabel)', async () => {
    const w = await mountSectie()
    const voor = api.relaties.lijst.mock.calls.length
    // Eerste DataTable = Uitgaand (bron_id = deze app).
    w.findAllComponents(DataTable)[0].vm.$emit('sort', { sortField: 'naam', sortOrder: -1 })
    await flushPromises()
    const laatste = api.relaties.lijst.mock.calls.at(-1)[0]
    expect(laatste).toMatchObject({ relatietype: 'flow', bron_id: APP, sort: 'naam', order: 'desc' })
    expect(api.relaties.lijst.mock.calls.length).toBeGreaterThan(voor)
  })
})
