/** Tests — AfdelingSelect (LI032): afdeling-picker ván een partij + search-first ter-plekke-aanmaken. */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'

vi.mock('@/api', () => ({ api: { partijen: { lijst: vi.fn(), maak: vi.fn() } } }))

import { api } from '@/api'
import AfdelingSelect from '@modules/bwb_ontvlechting/frontend/views/AfdelingSelect.vue'

function mountAS(props = {}) {
  return mount(AfdelingSelect, {
    props: { partijId: 'org1', magAanmaken: true, testid: 'afd', ...props },
    global: { plugins: [[PrimeVue, { unstyled: true }], ToastService] },
  })
}
async function open(w) {
  await w.find('[data-testid="afd-input"]').trigger('focus')
  await flushPromises()
}
async function openAanmaak(w) {
  await open(w)
  await w.find('[data-testid="afd-aanmaak-open"]').trigger('mousedown')
  await w.find('[data-testid="afd-aanmaak-open"]').trigger('click')
  await flushPromises()
}

beforeEach(() => {
  vi.clearAllMocks()
  api.partijen.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
})
afterEach(() => vi.restoreAllMocks())

describe('AfdelingSelect', () => {
  it('zoekt afdelingen ván deze partij (aard=organisatie_eenheid + organisatie_id)', async () => {
    const w = mountAS({ partijId: 'org9' })
    await open(w)
    expect(api.partijen.lijst).toHaveBeenCalledWith(
      expect.objectContaining({ aard: 'organisatie_eenheid', organisatie_id: 'org9' }),
    )
  })

  it('lege zoekstaat → aanmaak-actie (search-first), alleen met recht', async () => {
    const w = mountAS({ magAanmaken: false })
    await open(w)
    expect(w.find('[data-testid="afd-aanmaak-open"]').exists()).toBe(false)
    const w2 = mountAS({ magAanmaken: true })
    await open(w2)
    expect(w2.find('[data-testid="afd-aanmaak-open"]').exists()).toBe(true)
  })

  it('bestaande afdeling gevonden → géén aanmaak-actie (soepel zoeken vóór dubbel)', async () => {
    api.partijen.lijst.mockResolvedValue({
      items: [{ id: 'a1', naam: 'Directie', aard: 'organisatie_eenheid' }], volgende_cursor: null,
    })
    const w = mountAS()
    await open(w)
    expect(w.find('[data-testid="afd-aanmaak-open"]').exists()).toBe(false) // #leeg toont niet bij resultaten
    expect(w.find('[data-testid="afd-optie-a1"]').exists()).toBe(true)
  })

  it('aanmaken → endpoint met organisatie_eenheid + organisatie_id + selecteert de nieuwe afdeling', async () => {
    api.partijen.maak.mockResolvedValueOnce({ id: 'nieuw1', naam: 'Directie' })
    const w = mountAS({ partijId: 'org9' })
    await openAanmaak(w)
    await w.find('[data-testid="afd-naam"]').setValue('Directie')
    await w.find('[data-testid="afd-aanmaak-bevestig"]').trigger('click')
    await flushPromises()
    expect(api.partijen.maak).toHaveBeenCalledWith({
      aard: 'organisatie_eenheid', naam: 'Directie', organisatie_id: 'org9',
    })
    expect(w.emitted('update:modelValue')?.at(-1)).toEqual(['nieuw1'])
    expect(w.find('[data-testid="afd-aanmaak-form"]').exists()).toBe(false) // sluit na aanmaak
  })

  it('naam verplicht (geen API-call bij leeg)', async () => {
    const w = mountAS()
    await openAanmaak(w)
    await w.find('[data-testid="afd-naam"]').setValue('')
    await w.find('[data-testid="afd-aanmaak-bevestig"]').trigger('click')
    await flushPromises()
    expect(w.find('[data-testid="afd-naam-fout"]').exists()).toBe(true)
    expect(api.partijen.maak).not.toHaveBeenCalled()
  })

  it('bewerken-voorvulling toont de naam (initieel-weergave)', async () => {
    const w = mountAS({ modelValue: 'a1', initieelWeergave: 'Directie' })
    await flushPromises()
    expect(w.find('[data-testid="afd-input"]').element.value).toBe('Directie')
  })

  it('genest → aanmaakblok krijgt de diepere tint (niveau 2) en blijft bladniveau (geen laag 3)', async () => {
    const w = mountAS({ genest: true })
    await openAanmaak(w)
    const blok = w.find('[data-testid="afd-aanmaak-form"]')
    expect(blok.attributes('class')).toContain('primary-100') // één tint dieper
    // Afdeling = naam-only: geen entiteit-keuzeveld (combobox) in het aanmaakblok → geen laag 3.
    expect(blok.find('[role="combobox"]').exists()).toBe(false)
  })

  it('niet-genest → aanmaakblok krijgt de niveau-1-tint', async () => {
    const w = mountAS({ genest: false })
    await openAanmaak(w)
    expect(w.find('[data-testid="afd-aanmaak-form"]').attributes('class')).toContain('primary-50')
  })
})
