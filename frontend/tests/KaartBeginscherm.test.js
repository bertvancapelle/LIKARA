/** Tests — KaartBeginscherm (Fase B slice 2b, LI023): het 4-ingangen-vertrekpunt van de kaart.
 *  De ingangen emitten componenten/views naar de parent; dit component muteert zelf niets. */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

vi.mock('@/api', () => ({
  api: {
    componenten: { lijst: vi.fn() },
    partijen: { lijst: vi.fn(), componentenViaContract: vi.fn() },
    contracten: { lijst: vi.fn(), componenten: vi.fn() },
    gebruikersgroepen: { contexten: vi.fn(), contextComponenten: vi.fn() },
  },
}))

import { api } from '@/api'
import KaartBeginscherm from '@modules/bwb_ontvlechting/frontend/views/KaartBeginscherm.vue'
import ZoekSelect from '@modules/bwb_ontvlechting/frontend/views/ZoekSelect.vue'

const OPTIES = [
  { optie_sleutel: 'applicatie', label: 'Applicatie' },
  { optie_sleutel: 'database', label: 'Database' },
]

function mountKB(props = {}) {
  return mount(KaartBeginscherm, { props: { componentOpties: OPTIES, ...props } })
}
// Vind de ZoekSelect-instantie van een context-sectie op zijn testid-prefix.
const zs = (w, testid) => w.findAllComponents(ZoekSelect).find((c) => c.props('testid') === testid)

beforeEach(() => {
  vi.clearAllMocks()
  api.componenten.lijst.mockResolvedValue({ items: [{ id: 'c1', naam: 'Zaaksysteem' }, { id: 'c2', naam: 'BRP' }] })
  api.partijen.lijst.mockResolvedValue({ items: [{ id: 'l1', naam: 'SaaS BV' }] })
  api.partijen.componentenViaContract.mockResolvedValue([
    { component_id: 'c1', component_naam: 'Zaaksysteem', contract_id: 'k1', contract_naam: 'C' },
  ])
  api.contracten.lijst.mockResolvedValue({ items: [{ id: 'k1', naam: 'Contract X' }] })
  api.contracten.componenten.mockResolvedValue([{ component_id: 'c3', component_naam: 'DMS', componenttype: 'applicatie' }])
  api.gebruikersgroepen.contexten.mockResolvedValue([
    { organisatie_id: 'o1', organisatie_naam: 'Tiel', afdeling_id: 'a1', afdeling: 'Burgerzaken', aantal_componenten: 4 },
  ])
  api.gebruikersgroepen.contextComponenten.mockResolvedValue([
    { component_id: 'c4', component_naam: 'Burgerportaal', componenttype: 'applicatie' },
  ])
})
afterEach(() => vi.restoreAllMocks())

describe('KaartBeginscherm', () => {
  it('zoekterm → api.componenten.lijst met type (default applicatie) + zoek', async () => {
    const w = mountKB()
    await w.find('[data-testid="kb-zoek"]').setValue('zaak')
    await w.vm.zoek()
    expect(api.componenten.lijst).toHaveBeenCalledWith({ componenttype: 'applicatie', zoek: 'zaak' })
  })

  it('type-filter wijzigen → query bevat het nieuwe type', async () => {
    const w = mountKB()
    await w.find('[data-testid="kb-type"]').setValue('database')
    await flushPromises() // @change="zoek"
    expect(api.componenten.lijst).toHaveBeenLastCalledWith({ componenttype: 'database' })
  })

  it('component aanvinken → voegComponentenToe met het juiste component-object', async () => {
    const w = mountKB()
    await w.vm.zoek()
    await flushPromises()
    await w.find('[data-testid="kb-res-check-c1"]').trigger('change')
    expect(w.emitted('voegComponentenToe')[0][0]).toEqual([{ id: 'c1', naam: 'Zaaksysteem' }])
  })

  it('reeds toegevoegd component is gemarkeerd/uitgeschakeld (geen dubbel)', async () => {
    const w = mountKB()
    await w.vm.zoek()
    await flushPromises()
    await w.find('[data-testid="kb-res-check-c1"]').trigger('change')
    expect(w.find('[data-testid="kb-res-check-c1"]').attributes('disabled')).toBeDefined()
    // Opnieuw proberen geeft geen tweede emit.
    await w.find('[data-testid="kb-res-check-c1"]').trigger('change')
    expect(w.emitted('voegComponentenToe').length).toBe(1)
  })

  it('+ Filters toggelt het filterblok', async () => {
    const w = mountKB()
    expect(w.find('[data-testid="kb-filters"]').exists()).toBe(false)
    await w.find('[data-testid="kb-filters-toggle"]').trigger('click')
    expect(w.find('[data-testid="kb-filters"]').exists()).toBe(true)
  })

  it('leverancier selecteren → componentenViaContract → voegComponentenToe', async () => {
    const w = mountKB()
    await zs(w, 'kb-leverancier').vm.$emit('keuze', { id: 'l1', naam: 'SaaS BV' })
    await flushPromises()
    expect(api.partijen.componentenViaContract).toHaveBeenCalledWith('l1')
    expect(w.emitted('voegComponentenToe')[0][0]).toEqual([{ id: 'c1', naam: 'Zaaksysteem' }])
  })

  it('contract selecteren → contracten.componenten → voegComponentenToe', async () => {
    const w = mountKB()
    await zs(w, 'kb-contract').vm.$emit('keuze', { id: 'k1', naam: 'Contract X' })
    await flushPromises()
    expect(api.contracten.componenten).toHaveBeenCalledWith('k1')
    expect(w.emitted('voegComponentenToe')[0][0]).toEqual([{ id: 'c3', naam: 'DMS', componenttype: 'applicatie' }])
  })

  it('gebruikerscontext selecteren → contextComponenten met (organisatie_id, afdeling_id) → voegComponentenToe', async () => {
    const w = mountKB()
    await zs(w, 'kb-context').vm.$emit('keuze', { organisatie_id: 'o1', afdeling_id: 'a1', afdeling: 'Burgerzaken', _key: 'o1|a1' })
    await flushPromises()
    expect(api.gebruikersgroepen.contextComponenten).toHaveBeenCalledWith({ organisatie_id: 'o1', afdeling_id: 'a1' })
    expect(w.emitted('voegComponentenToe')[0][0]).toEqual([{ id: 'c4', naam: 'Burgerportaal', componenttype: 'applicatie' }])
  })

  it('"toon het hele landschap" → toonHeleLandschap-event', async () => {
    const w = mountKB()
    await w.find('[data-testid="lk-toon-hele-landschap"]').trigger('click')
    expect(w.emitted('toonHeleLandschap')).toBeTruthy()
  })

  it('opgeslagen view klikken → openView-event met de view', async () => {
    const w = mountKB({ opgeslagenViews: [{ id: 'v1', naam: 'Mijn view' }] })
    await w.find('[data-testid="kb-view-v1"]').trigger('click')
    expect(w.emitted('openView')[0][0]).toEqual({ id: 'v1', naam: 'Mijn view' })
  })

  it('lege staat zichtbaar zonder views en zonder zoekactie', () => {
    const w = mountKB({ opgeslagenViews: [] })
    expect(w.find('[data-testid="kb-leeg"]').exists()).toBe(true)
    expect(w.find('[data-testid="kb-views"]').exists()).toBe(false)
  })

  // LI023 — actiebalk bovenaan: knop VERBORGEN bij lege set (v-if), niet langer disabled.
  it('setGrootte=0 → knop niet zichtbaar', () => {
    const w = mountKB({ setGrootte: 0 })
    expect(w.find('[data-testid="toon-op-kaart-knop"]').exists()).toBe(false)
  })

  it('setGrootte=3 → knop zichtbaar met "Toon 3 componenten op de kaart"', () => {
    const w = mountKB({ setGrootte: 3 })
    const knop = w.find('[data-testid="toon-op-kaart-knop"]')
    expect(knop.exists()).toBe(true)
    expect(knop.text()).toBe('Toon 3 componenten op de kaart')
  })

  it('setGrootte=1 → enkelvoud "Toon 1 component op de kaart"', () => {
    const w = mountKB({ setGrootte: 1 })
    expect(w.find('[data-testid="toon-op-kaart-knop"]').text()).toBe('Toon 1 component op de kaart')
  })

  it('klik op de knop (setGrootte ≥ 1) → sluit-event', async () => {
    const w = mountKB({ setGrootte: 2 })
    await w.find('[data-testid="toon-op-kaart-knop"]').trigger('click')
    expect(w.emitted('sluit')).toBeTruthy()
  })

  // LI023 — na aanvinken meteen opruimen (geen handmatig wissen).
  it('na aanvinken component → zoekterm is leeg', async () => {
    const w = mountKB()
    await w.find('[data-testid="kb-zoek"]').setValue('zaak')
    await w.vm.zoek()
    await flushPromises()
    await w.find('[data-testid="kb-res-check-c1"]').trigger('change')
    expect(w.vm.zoekterm).toBe('')
  })

  it('na aanvinken component → dropdown is gesloten', async () => {
    const w = mountKB()
    await w.find('[data-testid="kb-zoek"]').setValue('zaak')
    await w.vm.zoek()
    await flushPromises()
    expect(w.vm.zoekOpen).toBe(true) // dropdown stond open
    await w.find('[data-testid="kb-res-check-c1"]').trigger('change')
    expect(w.vm.zoekOpen).toBe(false) // en is nu gesloten
  })
})
