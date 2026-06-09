/** Tests — ChecklistConfigBeheer (platform-beheer-view, ADR-019 fase 2E-c). */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'

vi.mock('@/api', () => ({
  api: {
    platformChecklistconfig: {
      lijst: vi.fn(),
      zetAntwoordtype: vi.fn(),
      voegOptieToe: vi.fn(),
      wijzigOptie: vi.fn(),
      deactiveerOptie: vi.fn(),
    },
  },
}))

import { api } from '@/api'
import ChecklistConfigBeheer from '@/views/ChecklistConfigBeheer.vue'

const VRAGEN = [
  { code: '9.1', vraag: 'V negen', antwoordtype: 'geen', opties: [] },
  {
    code: '2.1', vraag: 'Hosting', antwoordtype: 'enkelvoudige_keuze',
    opties: [{ id: 'o1', optie_sleutel: 'saas', label: 'SaaS', volgorde: 0, actief: true, afgeleid_bron: 'HostingModel' }],
  },
  {
    code: '1.3', vraag: 'Eigenaar', antwoordtype: 'enkelvoudige_keuze',
    opties: [{ id: 'o2', optie_sleutel: 'bwb', label: 'BWB', volgorde: 0, actief: true, afgeleid_bron: null }],
  },
]

async function mountView() {
  const wrapper = mount(ChecklistConfigBeheer, {
    global: { plugins: [createPinia(), [PrimeVue, { unstyled: true }], ToastService] },
  })
  await flushPromises()
  return wrapper
}

beforeEach(() => {
  vi.clearAllMocks()
  api.platformChecklistconfig.lijst.mockResolvedValue(structuredClone(VRAGEN))
})
afterEach(() => vi.restoreAllMocks())

describe('ChecklistConfigBeheer', () => {
  it('laadt en toont de vragen + antwoordtype', async () => {
    const w = await mountView()
    expect(w.find('[data-testid="cfg-vraag-9.1"]').exists()).toBe(true)
    expect(w.find('[data-testid="cfg-type-2.1"]').element.value).toBe('enkelvoudige_keuze')
  })

  it('filtert op categorie (afgeleid uit de code-prefix)', async () => {
    const w = await mountView()
    await w.find('[data-testid="cfg-categorie-filter"]').setValue('1')
    expect(w.find('[data-testid="cfg-vraag-1.3"]').exists()).toBe(true)
    expect(w.find('[data-testid="cfg-vraag-9.1"]').exists()).toBe(false)
    expect(w.find('[data-testid="cfg-vraag-2.1"]').exists()).toBe(false)
  })

  it('zet antwoordtype op een geen-vraag', async () => {
    api.platformChecklistconfig.zetAntwoordtype.mockResolvedValue({
      code: '9.1', vraag: 'V negen', antwoordtype: 'getal', opties: [],
    })
    const w = await mountView()
    await w.find('[data-testid="cfg-type-9.1"]').setValue('getal')
    await flushPromises()
    expect(api.platformChecklistconfig.zetAntwoordtype).toHaveBeenCalledWith('9.1', 'getal')
  })

  it('toont een 409 (CONFIGURATIE_CONFLICT) bij type-wisseling netjes', async () => {
    const err = new Error('Een reeds geconfigureerde vraag kan niet van antwoordtype wisselen.')
    err.status = 409
    err.code = 'CONFIGURATIE_CONFLICT'
    api.platformChecklistconfig.zetAntwoordtype.mockRejectedValue(err)
    const w = await mountView()
    await w.find('[data-testid="cfg-type-1.3"]').setValue('meerkeuze')
    await flushPromises()
    expect(w.find('[data-testid="cfg-actie-fout"]').text()).toContain('niet van antwoordtype wisselen')
  })

  it('voegt een optie toe aan een vrije set', async () => {
    api.platformChecklistconfig.voegOptieToe.mockResolvedValue({
      id: 'o9', optie_sleutel: 'tiel', label: 'Tiel', volgorde: 1, actief: true, afgeleid_bron: null,
    })
    const w = await mountView()
    await w.find('[data-testid="cfg-nieuw-sleutel-1.3"]').setValue('tiel')
    await w.find('[data-testid="cfg-nieuw-label-1.3"]').setValue('Tiel')
    await w.find('[data-testid="cfg-toevoegen-1.3"]').trigger('submit')
    await flushPromises()
    expect(api.platformChecklistconfig.voegOptieToe).toHaveBeenCalledWith('1.3', {
      optie_sleutel: 'tiel', label: 'Tiel', volgorde: 0,
    })
  })

  it('deactiveert een vrije optie (soft)', async () => {
    api.platformChecklistconfig.deactiveerOptie.mockResolvedValue({
      id: 'o2', optie_sleutel: 'bwb', label: 'BWB', volgorde: 0, actief: false, afgeleid_bron: null,
    })
    const w = await mountView()
    await w.find('[data-testid="cfg-optie-deactiveren-o2"]').trigger('click')
    await flushPromises()
    expect(api.platformChecklistconfig.deactiveerOptie).toHaveBeenCalledWith('o2')
  })

  it('afgeleide set: badge, label-only, geen toevoegen/deactiveren/volgorde', async () => {
    const w = await mountView()
    expect(w.find('[data-testid="cfg-afgeleid-2.1"]').exists()).toBe(true)
    expect(w.find('[data-testid="cfg-toevoegen-2.1"]').exists()).toBe(false) // geen toevoegen
    expect(w.find('[data-testid="cfg-optie-volgorde-o1"]').attributes('disabled')).toBeDefined()
    expect(w.find('[data-testid="cfg-optie-deactiveren-o1"]').exists()).toBe(false)
    expect(w.find('[data-testid="cfg-optie-label-o1"]').exists()).toBe(true) // label wél editbaar
  })
})
