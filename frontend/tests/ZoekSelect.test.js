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

  it('voorgevulde picker toont bij openen de VOLLEDIGE lijst — prefill niet als zoekfilter (LI032)', async () => {
    const alle = [
      { id: 'a1', naam: 'Beheer & Exploitatie' },
      { id: 'a2', naam: 'Directie' },
      { id: 'a3', naam: 'Informatievoorziening' },
      { id: 'a4', naam: 'Klantbeheer & Relatiebeheer' },
    ]
    // Realistische mock: filtert op de zoekterm (zoals de backend-ILIKE) — zo betrapt de test de bug.
    const zoekFunctie = vi.fn((params) =>
      Promise.resolve({
        items: params.zoek ? alle.filter((a) => a.naam.toLowerCase().includes(params.zoek.toLowerCase())) : alle,
        volgende_cursor: null,
      }),
    )
    const { w, input } = mountZS({ zoekFunctie, modelValue: 'a3', initieelWeergave: 'Informatievoorziening' })
    await flushPromises()
    expect(input().element.value).toBe('Informatievoorziening') // label voorgevuld
    await input().trigger('focus')
    await flushPromises()
    // Bij openen: zoek met lege term (NIET de prefill) → volledige lijst zichtbaar.
    expect(zoekFunctie).toHaveBeenLastCalledWith(expect.objectContaining({ zoek: undefined }))
    expect(w.findAll('[role="option"]').length).toBe(4)
  })

  it('LI038-v2 — klik op een al-gefocust veld heropent de volledige lijst (ná een keuze vuurt @focus niet)', async () => {
    const alle = [
      { id: 'a1', naam: 'Beheer & Exploitatie' },
      { id: 'a2', naam: 'Directie' },
      { id: 'a3', naam: 'Informatievoorziening' },
    ]
    const zoekFunctie = vi.fn((params) =>
      Promise.resolve({
        items: params.zoek ? alle.filter((a) => a.naam.toLowerCase().includes(params.zoek.toLowerCase())) : alle,
        volgende_cursor: null,
      }),
    )
    const { w, input } = mountZS({ zoekFunctie })
    await input().trigger('focus')
    await flushPromises()
    await w.find('[data-testid="zs-optie-a2"]').trigger('mousedown')
    expect(input().element.value).toBe('Directie') // keuze staat als label; lijst dicht
    expect(input().attributes('aria-expanded')).toBe('false')
    // De input hield focus (mousedown.prevent) → een nieuwe klik geeft GEEN focus-event.
    await input().trigger('click')
    await flushPromises()
    // Volledige lijst — de gekozen naam is een label, geen zoekfilter.
    expect(zoekFunctie).toHaveBeenLastCalledWith(expect.objectContaining({ zoek: undefined }))
    expect(w.findAll('[role="option"]').length).toBe(3)
    expect(input().attributes('aria-expanded')).toBe('true')
  })

  it('LI038-v2 — een klik tijdens het typen (lijst al open) reset de zoekterm NIET', async () => {
    const zoekFunctie = vi.fn().mockResolvedValue({ items: [], volgende_cursor: null })
    const { input } = mountZS({ zoekFunctie })
    await input().trigger('focus')
    await flushPromises()
    vi.useFakeTimers()
    await input().setValue('Dir')
    vi.advanceTimersByTime(300)
    vi.useRealTimers()
    await flushPromises()
    const aanroepen = zoekFunctie.mock.calls.length
    await input().trigger('click') // cursor verplaatsen — lijst is al open
    await flushPromises()
    expect(zoekFunctie.mock.calls.length).toBe(aanroepen) // géén reset-zoek
    expect(input().element.value).toBe('Dir')
  })

  it('LI038-v2 — ×-wis: keuze weg (modelValue null), veld leeg, volledige lijst weer open', async () => {
    const zoekFunctie = vi.fn().mockResolvedValue({
      items: [{ id: 'a1', naam: 'Directie' }, { id: 'a2', naam: 'Informatievoorziening' }],
      volgende_cursor: null,
    })
    const { w, input } = mountZS({ zoekFunctie })
    expect(w.find('[data-testid="zs-wis"]').exists()).toBe(false) // leeg veld → geen wis-gebaar
    await input().trigger('focus')
    await flushPromises()
    await w.find('[data-testid="zs-optie-a1"]').trigger('mousedown')
    expect(input().element.value).toBe('Directie')
    const wis = w.find('[data-testid="zs-wis"]')
    expect(wis.exists()).toBe(true)
    expect(wis.attributes('aria-label')).toBe('Wis en zoek opnieuw')
    await wis.trigger('click')
    await flushPromises()
    expect(input().element.value).toBe('')
    expect(w.emitted('update:modelValue').at(-1)).toEqual([null])
    expect(input().attributes('aria-expanded')).toBe('true') // volledige lijst staat weer open
    expect(zoekFunctie).toHaveBeenLastCalledWith(expect.objectContaining({ zoek: undefined }))
  })

  it('typen ná openen filtert wél soepel op de getypte term', async () => {
    const zoekFunctie = vi.fn().mockResolvedValue({ items: [], volgende_cursor: null })
    const { input } = mountZS({ zoekFunctie, modelValue: 'a3', initieelWeergave: 'Informatievoorziening' })
    await input().trigger('focus')
    await flushPromises()
    vi.useFakeTimers()
    await input().setValue('Dir')
    vi.advanceTimersByTime(300)
    vi.useRealTimers()
    await flushPromises()
    expect(zoekFunctie).toHaveBeenLastCalledWith(expect.objectContaining({ zoek: 'Dir' }))
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
