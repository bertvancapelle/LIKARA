/** Tests — ComponentBedrijfsfunctieSectie (ADR-043 gate 4, G2/G9): koppelen vanuit het systeem. */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'

vi.mock('@/api', () => ({
  api: {
    functievervullingen: { componentKoppelingen: vi.fn(), maak: vi.fn(), verwijder: vi.fn(), zetOordeel: vi.fn() },
    bedrijfsfuncties: { lijst: vi.fn(), haal: vi.fn() },
  },
}))
vi.mock('@/meldingen', () => ({ toastSucces: vi.fn() }))

import { api } from '@/api'
import { toastSucces } from '@/meldingen'
import { useAuthStore } from '@/store/auth'
import ComponentBedrijfsfunctieSectie from '@modules/bwb_ontvlechting/frontend/views/ComponentBedrijfsfunctieSectie.vue'

async function mountSectie({ rollen = ['medewerker'], naam = 'Zaaksysteem' } = {}) {
  const pinia = createPinia()
  const auth = useAuthStore(pinia)
  auth.user = { sub: 's', tenant_id: 't', email: 'a@b.nl', roles: rollen }
  const w = mount(ComponentBedrijfsfunctieSectie, {
    props: { componentId: 'c-1', componentNaam: naam },
    attachTo: document.body,
    global: { plugins: [pinia, [PrimeVue, { unstyled: true }], ToastService], stubs: { teleport: true } },
  })
  await flushPromises()
  return { w }
}

beforeEach(() => {
  vi.clearAllMocks()
  api.functievervullingen.componentKoppelingen.mockResolvedValue([])
  api.bedrijfsfuncties.lijst.mockResolvedValue({
    items: [
      { id: 'toezicht', naam: 'Toezicht', ouder_ids: ['milieu', 'bouwen'], vervallen: false },
      { id: 'verg', naam: 'Vergunningverlening', ouder_ids: [], vervallen: false },
      { id: 'oud', naam: 'Vervallen functie', ouder_ids: [], vervallen: true },
    ],
    volgende_cursor: null,
  })
  api.bedrijfsfuncties.haal.mockImplementation((id) =>
    Promise.resolve({ id, naam: { milieu: 'Milieu', bouwen: 'Bouwen' }[id] || id }))
})

afterEach(() => vi.restoreAllMocks())

describe('ComponentBedrijfsfunctieSectie — lezen (uit de leeslaag)', () => {
  it('toont een grove koppeling met de reikwijdte + verdringing UIT de leeslaag', async () => {
    api.functievervullingen.componentKoppelingen.mockResolvedValue([{
      vervulling_id: 'g1', herkomst: 'grof', functie_id: 'toezicht', functie_naam: 'Toezicht',
      ouder_functie_id: null, ouder_naam: null, oordeel: null,
      grof_totaal_plekken: 2, grof_geldt_op: 1, verdrongen_op: 1,
    }])
    const { w } = await mountSectie()
    const rij = w.find('[data-testid="cbf-regel-g1"]')
    expect(rij.text()).toContain('Toezicht')
    expect(rij.text()).toContain('geldt overal')
    // De reikwijdte/verdringing komt uit de server-afleiding — niet hier berekend.
    expect(w.find('[data-testid="cbf-reikwijdte-g1"]').text()).toContain('geldt op 1 van de 2 plekken')
    expect(w.find('[data-testid="cbf-reikwijdte-g1"]').text()).toContain('1 plek verfijnd met een ander systeem')
  })

  it('toont een fijne koppeling met de plek-context', async () => {
    api.functievervullingen.componentKoppelingen.mockResolvedValue([{
      vervulling_id: 'f1', herkomst: 'fijn', functie_id: 'toezicht', functie_naam: 'Toezicht',
      ouder_functie_id: 'milieu', ouder_naam: 'Milieu', oordeel: 'noodoplossing',
    }])
    const { w } = await mountSectie()
    expect(w.find('[data-testid="cbf-regel-f1"]').text()).toContain('alleen onder Milieu')
  })

  it('lege staat wijst de weg voor de medewerker', async () => {
    const { w } = await mountSectie()
    expect(w.find('[data-testid="cbf-leeg"]').text()).toContain('Koppel het hieronder aan een bedrijfsfunctie')
  })
})

describe('ComponentBedrijfsfunctieSectie — koppelen (grof default; fijn kiest een plek)', () => {
  async function kiesFunctie(w, id) {
    await w.find('[data-testid="cbf-functie-input"]').trigger('focus')
    await flushPromises()
    await w.find(`[data-testid="cbf-functie-optie-${id}"]`).trigger('mousedown')
    await flushPromises()
  }

  it('grof: kies een functie zonder plek → koppelt overal (ouder_functie_id null)', async () => {
    api.functievervullingen.maak.mockResolvedValue({})
    const { w } = await mountSectie()
    await kiesFunctie(w, 'verg')
    await w.find('[data-testid="cbf-koppel"]').trigger('click')
    await flushPromises()
    expect(api.functievervullingen.maak).toHaveBeenCalledWith({
      component_id: 'c-1', functie_id: 'verg', ouder_functie_id: null, oordeel: null, toelichting: null,
    })
    expect(toastSucces).toHaveBeenCalledWith(expect.anything(), 'Gekoppeld')
  })

  it('fijn: kies een functie mét plekken → "één plek" → koppelt op de plek', async () => {
    api.functievervullingen.maak.mockResolvedValue({})
    const { w } = await mountSectie()
    await kiesFunctie(w, 'toezicht')
    await w.find('[data-testid="cbf-scope-hier"]').setValue()
    await flushPromises()
    await w.find('[data-testid="cbf-plek"]').setValue('milieu')
    await w.find('[data-testid="cbf-koppel"]').trigger('click')
    await flushPromises()
    expect(api.functievervullingen.maak).toHaveBeenCalledWith({
      component_id: 'c-1', functie_id: 'toezicht', ouder_functie_id: 'milieu', oordeel: null, toelichting: null,
    })
  })

  it('een vervallen functie verschijnt niet in de picker (weren vooraf)', async () => {
    const { w } = await mountSectie()
    await w.find('[data-testid="cbf-functie-input"]').trigger('focus')
    await flushPromises()
    expect(w.find('[data-testid="cbf-functie-optie-oud"]').exists()).toBe(false)
    expect(w.find('[data-testid="cbf-functie-optie-verg"]').exists()).toBe(true)
  })
})

describe('ComponentBedrijfsfunctieSectie — corrigeren (rolgrens)', () => {
  it('oordeel bijstellen roept zetOordeel aan', async () => {
    api.functievervullingen.componentKoppelingen.mockResolvedValue([{
      vervulling_id: 'g1', herkomst: 'grof', functie_id: 'verg', functie_naam: 'Vergunningverlening',
      ouder_functie_id: null, ouder_naam: null, oordeel: null, grof_totaal_plekken: 1, grof_geldt_op: 1, verdrongen_op: 0,
    }])
    api.functievervullingen.zetOordeel.mockResolvedValue({})
    const { w } = await mountSectie()
    await w.find('[data-testid="cbf-oordeel-g1"]').setValue('noodoplossing')
    await flushPromises()
    expect(api.functievervullingen.zetOordeel).toHaveBeenCalledWith('g1', 'noodoplossing')
  })

  it('verwijderen roept verwijder aan + succes-toast', async () => {
    api.functievervullingen.componentKoppelingen.mockResolvedValue([{
      vervulling_id: 'g1', herkomst: 'grof', functie_id: 'verg', functie_naam: 'Vergunningverlening',
      ouder_functie_id: null, ouder_naam: null, oordeel: null, grof_totaal_plekken: 1, grof_geldt_op: 1, verdrongen_op: 0,
    }])
    api.functievervullingen.verwijder.mockResolvedValue(undefined)
    const { w } = await mountSectie()
    await w.find('[data-testid="cbf-verwijder-g1"]').trigger('click')
    await w.find('[data-testid="cbf-verwijder-bevestig"]').trigger('click')
    await flushPromises()
    expect(api.functievervullingen.verwijder).toHaveBeenCalledWith('g1')
    expect(toastSucces).toHaveBeenCalledWith(expect.anything(), 'Koppeling weggehaald')
  })

  it('een viewer ziet geen koppel-/verwijder-acties', async () => {
    api.functievervullingen.componentKoppelingen.mockResolvedValue([{
      vervulling_id: 'g1', herkomst: 'grof', functie_id: 'verg', functie_naam: 'Vergunningverlening',
      ouder_functie_id: null, ouder_naam: null, oordeel: null, grof_totaal_plekken: 1, grof_geldt_op: 1, verdrongen_op: 0,
    }])
    const { w } = await mountSectie({ rollen: ['viewer'] })
    expect(w.find('[data-testid="cbf-toevoegregel"]').exists()).toBe(false)
    expect(w.find('[data-testid="cbf-verwijder-g1"]').exists()).toBe(false)
  })
})
