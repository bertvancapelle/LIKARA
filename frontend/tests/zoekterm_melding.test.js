/**
 * Tests — de gedeelde zoekterm-melding (LI051, blok C).
 *
 * Twee dingen:
 * 1. `ZoektermMelding` is DE ene bron voor de tekst: de vaste zin, de gebruikte term uitgelicht,
 *    en het gedempte neutrale kanaal (MeldingBanner soort="info" → role="status", ℹ).
 * 2. Een keuzelijst-soort veld (ZoekSelect): geplakte rommel toont de melding IN de openklappende
 *    lijst met de opgeschoonde term; een gewone zoekopdracht toont niets. De melding verdwijnt
 *    met de lijst mee (staat erin).
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

import ZoektermMelding from '@/components/ZoektermMelding.vue'
import ZoekSelect from '@modules/bwb_ontvlechting/frontend/views/ZoekSelect.vue'

describe('ZoektermMelding — één bron voor de tekst', () => {
  it('toont de vaste zin met de gebruikte term uitgelicht, gedempt (info)', () => {
    const w = mount(ZoektermMelding, { props: { term: 'zaaksysteem' } })
    expect(w.text()).toContain('onzichtbare tekens')
    expect(w.text()).toContain('plakken uit een ander programma')
    expect(w.text()).toContain('Er is gezocht op')
    expect(w.find('strong').text()).toBe('zaaksysteem') // de term uitgelicht
    expect(w.find('[data-testid="zoek-opschoon-melding"]').exists()).toBe(true)
    expect(w.find('[role="status"]').exists()).toBe(true) // neutraal, geen alarm
    expect(w.find('[role="alert"]').exists()).toBe(false) // geen waarschuwingsrol
  })
})

describe('ZoekSelect — keuzelijst: melding in de openklappende lijst', () => {
  beforeEach(() => vi.clearAllMocks())
  afterEach(() => vi.restoreAllMocks())

  function mountZS(zoekFunctie) {
    const w = mount(ZoekSelect, { props: { zoekFunctie, id: 'zs', testid: 'zs' } })
    return { w, input: () => w.find('[data-testid="zs-input"]') }
  }

  it('geplakte rommel → melding in de lijst met de opgeschoonde term; het veld toont schoon', async () => {
    vi.useFakeTimers()
    const zoekFunctie = vi.fn().mockResolvedValue({ items: [], volgende_cursor: null })
    const { w, input } = mountZS(zoekFunctie)
    await input().trigger('focus') // opent de lijst (startlijst, geen melding)
    await vi.runAllTimersAsync()
    await input().setValue('zaak\x00systeem') // rommel geplakt
    await vi.advanceTimersByTimeAsync(300) // debounce → zoek()
    vi.useRealTimers()

    const melding = w.find('[data-testid="zs-zoek-melding"]')
    expect(melding.exists()).toBe(true)
    expect(melding.text()).toContain('zaaksysteem')
    // Er is met de OPGESCHOONDE term gezocht (geen nulteken naar de achterkant).
    expect(zoekFunctie).toHaveBeenLastCalledWith(expect.objectContaining({ zoek: 'zaaksysteem' }))
    // Het veld toont de opgeschoonde term (anders komt de melding elke toetsaanslag terug).
    expect(input().element.value).toBe('zaaksysteem')
  })

  it('gewone zoekopdracht → geen melding', async () => {
    vi.useFakeTimers()
    const zoekFunctie = vi.fn().mockResolvedValue({ items: [], volgende_cursor: null })
    const { w, input } = mountZS(zoekFunctie)
    await input().trigger('focus')
    await vi.runAllTimersAsync()
    await input().setValue('zaaksysteem')
    await vi.advanceTimersByTimeAsync(300)
    vi.useRealTimers()

    expect(w.find('[data-testid="zs-zoek-melding"]').exists()).toBe(false)
  })
})
