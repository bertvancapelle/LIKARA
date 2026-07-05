/** Tests — ContactpersoonSelect (ADR-039): persoon-picker van déze partij + search-first inline-aanmaak. */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'

vi.mock('@/api', () => ({ api: { partijen: { lijst: vi.fn(), maak: vi.fn() } } }))

import { api } from '@/api'
import ContactpersoonSelect from '@modules/bwb_ontvlechting/frontend/views/ContactpersoonSelect.vue'

function mountCp({ partijId = 'part1', modelValue = null, magAanmaken = true } = {}) {
  return mount(ContactpersoonSelect, {
    props: { partijId, modelValue, magAanmaken },
    global: { plugins: [[PrimeVue, { unstyled: true }], ToastService] },
  })
}

async function opendropdown(w) {
  await w.find('[data-testid="veld-contactpersoon-input"]').trigger('focus')
  await flushPromises()
}

beforeEach(() => {
  vi.clearAllMocks()
  api.partijen.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
})
afterEach(() => vi.restoreAllMocks())

describe('ContactpersoonSelect', () => {
  it('zoekt personen ván déze partij (aard=persoon + organisatie_id)', async () => {
    const w = mountCp({ partijId: 'part9' })
    await opendropdown(w)
    expect(api.partijen.lijst).toHaveBeenCalledWith(
      expect.objectContaining({ aard: 'persoon', organisatie_id: 'part9' }),
    )
  })

  it('kiezen van een persoon emit update:modelValue', async () => {
    api.partijen.lijst.mockResolvedValue({
      items: [{ id: 'per1', naam: 'M. de Boer', aard: 'persoon' }], volgende_cursor: null,
    })
    const w = mountCp()
    await opendropdown(w)
    await w.find('[data-testid="veld-contactpersoon-optie-per1"]').trigger('mousedown')
    await flushPromises()
    expect(w.emitted('update:modelValue')?.at(-1)).toEqual(['per1'])
  })

  it('lege zoekstaat toont de aanmaak-actie alleen met recht', async () => {
    const w = mountCp({ magAanmaken: false })
    await opendropdown(w)
    expect(w.find('[data-testid="cp-aanmaak-open"]').exists()).toBe(false)
    const w2 = mountCp({ magAanmaken: true })
    await opendropdown(w2)
    expect(w2.find('[data-testid="cp-aanmaak-open"]').exists()).toBe(true)
  })

  it('inline-aanmaak: naam verplicht (geen API-call bij leeg)', async () => {
    const w = mountCp()
    await opendropdown(w)
    await w.find('[data-testid="cp-aanmaak-open"]').trigger('mousedown')
    await w.find('[data-testid="cp-aanmaak-open"]').trigger('click')
    await flushPromises()
    // naam leegmaken (was voorgevuld met de — lege — zoekterm; forceer leeg)
    await w.find('[data-testid="cp-naam"]').setValue('')
    await w.find('[data-testid="cp-aanmaak-bevestig"]').trigger('click')
    await flushPromises()
    expect(w.find('[data-testid="cp-naam-fout"]').exists()).toBe(true)
    expect(api.partijen.maak).not.toHaveBeenCalled()
  })

  it('inline-aanmaak: maakt persoon onder deze partij + kiest hem', async () => {
    api.partijen.maak.mockResolvedValueOnce({ id: 'nieuw1', naam: 'S. El Amrani' })
    const w = mountCp({ partijId: 'part9' })
    await opendropdown(w)
    await w.find('[data-testid="cp-aanmaak-open"]').trigger('mousedown')
    await w.find('[data-testid="cp-aanmaak-open"]').trigger('click')
    await flushPromises()
    await w.find('[data-testid="cp-naam"]').setValue('S. El Amrani')
    await w.find('[data-testid="cp-email"]').setValue('s@civdata.test')
    await w.find('[data-testid="cp-aanmaak-bevestig"]').trigger('click')
    await flushPromises()
    expect(api.partijen.maak).toHaveBeenCalledWith(
      expect.objectContaining({
        aard: 'persoon', naam: 'S. El Amrani', organisatie_id: 'part9', email: 's@civdata.test',
      }),
    )
    expect(w.emitted('update:modelValue')?.at(-1)).toEqual(['nieuw1'])
    expect(w.find('[data-testid="cp-aanmaak-form"]').exists()).toBe(false)  // sluit na aanmaak
  })

  // LI032 — genest ter-plekke-aanmaken: het afdelingsveld in het contactpersoon-blok (niveau 1) is
  // een AfdelingSelect; een niet-bestaande afdeling kan hier ter plekke (niveau 2). Bladniveau → geen 3.
  it('afdelingsveld in het nieuwe-contactpersoon-blok kan ter plekke een afdeling aanmaken (2 niveaus)', async () => {
    api.partijen.maak.mockResolvedValueOnce({ id: 'afd9', naam: 'Directie' })
    const w = mountCp({ partijId: 'part9' })
    await opendropdown(w)
    await w.find('[data-testid="cp-aanmaak-open"]').trigger('mousedown')
    await w.find('[data-testid="cp-aanmaak-open"]').trigger('click')
    await flushPromises()
    // Niveau 1 = het contactpersoon-blok met de tint; daarin de afdeling-picker (AfdelingSelect).
    expect(w.find('[data-testid="cp-aanmaak-form"]').attributes('class')).toContain('primary-50')
    expect(w.find('[data-testid="cp-afdeling-input"]').exists()).toBe(true)
    // Open het geneste afdeling-aanmaakblok (niveau 2) via de lege zoekstaat.
    await w.find('[data-testid="cp-afdeling-input"]').trigger('focus')
    await flushPromises()
    await w.find('[data-testid="cp-afdeling-aanmaak-open"]').trigger('mousedown')
    await w.find('[data-testid="cp-afdeling-aanmaak-open"]').trigger('click')
    await flushPromises()
    const genest = w.find('[data-testid="cp-afdeling-aanmaak-form"]')
    expect(genest.exists()).toBe(true)
    expect(genest.attributes('class')).toContain('primary-100') // niveau 2 = dieper
    // Geen derde laag: het afdeling-blok bevat geen verder entiteit-keuzeveld.
    expect(genest.find('[role="combobox"]').exists()).toBe(false)
    // Aanmaken landt binnen déze partij.
    await w.find('[data-testid="cp-afdeling-naam"]').setValue('Directie')
    await w.find('[data-testid="cp-afdeling-aanmaak-bevestig"]').trigger('click')
    await flushPromises()
    expect(api.partijen.maak).toHaveBeenCalledWith({
      aard: 'organisatie_eenheid', naam: 'Directie', organisatie_id: 'part9',
    })
  })
})
