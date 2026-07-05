/** Tests — ZoekSelect (generieke server-side zoek-combobox, CD049). */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ZoekSelect from '@modules/bwb_ontvlechting/frontend/views/ZoekSelect.vue'

function mountZS(props = {}) {
  const zoekFunctie = props.zoekFunctie || vi.fn().mockResolvedValue({ items: [], volgende_cursor: null })
  const w = mount(ZoekSelect, { props: { zoekFunctie, id: 'zs', ...props } })
  return { w, zoekFunctie, input: () => w.find('[data-testid="zs-input"]') }
}

beforeEach(() => vi.clearAllMocks())
afterEach(() => vi.restoreAllMocks())

describe('ZoekSelect', () => {
  it('heeft het combobox-aria-patroon', () => {
    const { input } = mountZS()
    const el = input()
    expect(el.attributes('role')).toBe('combobox')
    expect(el.attributes('aria-expanded')).toBe('false')
    expect(el.attributes('aria-controls')).toBe('zs-listbox')
  })

  it('leeg veld → startlijst (zoek undefined, limit 11) bij focus', async () => {
    const { input, zoekFunctie } = mountZS()
    await input().trigger('focus')
    await flushPromises()
    expect(zoekFunctie).toHaveBeenCalledWith(expect.objectContaining({ zoek: undefined, limit: 11 }))
  })

  it('debounced zoeken roept zoekFunctie met de zoekterm', async () => {
    const zoekFunctie = vi.fn().mockResolvedValue({ items: [], volgende_cursor: null })
    const { input } = mountZS({ zoekFunctie })
    vi.useFakeTimers()
    await input().setValue('Civ')
    vi.advanceTimersByTime(300)
    vi.useRealTimers()
    await flushPromises()
    expect(zoekFunctie).toHaveBeenLastCalledWith(expect.objectContaining({ zoek: 'Civ', limit: 11 }))
  })

  it('toont max 10 resultaten + "verfijn"-regel bij meer', async () => {
    const zoekFunctie = vi.fn().mockResolvedValue({
      items: Array.from({ length: 11 }, (_, i) => ({ id: `id-${i}`, naam: `L${i}` })),
      volgende_cursor: null,
    })
    const { w, input } = mountZS({ zoekFunctie })
    await input().trigger('focus')
    await flushPromises()
    expect(w.findAll('[role="option"]').length).toBe(10)
    expect(w.find('[data-testid="zs-meer"]').exists()).toBe(true)
  })

  it('selecteren levert het id via v-model en toont de naam', async () => {
    const zoekFunctie = vi.fn().mockResolvedValue({ items: [{ id: 'civ-1', naam: 'CivData Solutions' }], volgende_cursor: null })
    const { w, input } = mountZS({ zoekFunctie })
    await input().trigger('focus')
    await flushPromises()
    await w.find('[data-testid="zs-optie-civ-1"]').trigger('mousedown')
    expect(w.emitted('update:modelValue')[0]).toEqual(['civ-1'])
    expect(input().element.value).toBe('CivData Solutions')
  })

  it('toetsenbord: ArrowDown + Enter selecteert; Escape sluit', async () => {
    const zoekFunctie = vi.fn().mockResolvedValue({
      items: [{ id: 'a', naam: 'A' }, { id: 'b', naam: 'B' }],
      volgende_cursor: null,
    })
    const { w, input } = mountZS({ zoekFunctie })
    await input().trigger('focus')
    await flushPromises()
    await input().trigger('keydown', { key: 'ArrowDown' }) // 0 → 1
    await input().trigger('keydown', { key: 'Enter' })
    expect(w.emitted('update:modelValue').at(-1)).toEqual(['b'])

    await input().trigger('focus')
    await flushPromises()
    expect(input().attributes('aria-expanded')).toBe('true')
    await input().trigger('keydown', { key: 'Escape' })
    expect(input().attributes('aria-expanded')).toBe('false')
  })

  it('geeft extraFilters server-side door (mantel-select-spiegeling)', async () => {
    const zoekFunctie = vi.fn().mockResolvedValue({ items: [], volgende_cursor: null })
    const { input } = mountZS({ zoekFunctie, extraFilters: { contracttype: 'mantelcontract', leverancierId: 'l1' } })
    await input().trigger('focus')
    await flushPromises()
    expect(zoekFunctie).toHaveBeenCalledWith(
      expect.objectContaining({ contracttype: 'mantelcontract', leverancierId: 'l1', limit: 11 }),
    )
  })

  it('bewerken-modus: toont initieelWeergave bij een preset modelValue', () => {
    const { input } = mountZS({ modelValue: 'l1', initieelWeergave: 'GemSoft B.V.' })
    expect(input().element.value).toBe('GemSoft B.V.')
  })

  it('toont een foutmelding (role=alert) bij een zoek-fout', async () => {
    const zoekFunctie = vi.fn().mockRejectedValue(new Error('Netwerkfout'))
    const { w, input } = mountZS({ zoekFunctie })
    await input().trigger('focus')
    await flushPromises()
    expect(w.find('[data-testid="zs-fout"]').attributes('role')).toBe('alert')
  })

  it('een niet-401-fout toont een generieke tekst, NOOIT de rauwe boodschap', async () => {
    const zoekFunctie = vi.fn().mockRejectedValue(new Error('DB kapot xyz'))
    const { w, input } = mountZS({ zoekFunctie })
    await input().trigger('focus')
    await flushPromises()
    const t = w.find('[data-testid="zs-fout"]').text()
    expect(t).toContain('Zoeken mislukt')
    expect(t).not.toContain('DB kapot')
  })

  it('bij een 401 (verlopen sessie) toont het geen rauwe code — de centrale vangrail redirect', async () => {
    const err = new Error('NIET_GEAUTHENTICEERD')
    err.status = 401
    const zoekFunctie = vi.fn().mockRejectedValue(err)
    const { w, input } = mountZS({ zoekFunctie })
    await input().trigger('focus')
    await flushPromises()
    expect(w.text()).not.toContain('NIET_GEAUTHENTICEERD')
    expect(w.find('[data-testid="zs-fout"]').exists()).toBe(false) // leeg → geen fout-li
  })
})
