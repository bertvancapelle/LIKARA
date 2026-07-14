/** Tests — FilterResultaatRegel (LI040): de gedeelde bouwsteen die de filterbalk laat
 * vertellen wat hij doet — aantal (altijd), elk actief filter uitgeschreven, los wisbaar. */
import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import FilterResultaatRegel from '@/components/FilterResultaatRegel.vue'

const mountRegel = (props = {}) =>
  mount(FilterResultaatRegel, {
    props: { eenheid: 'componenten', eenheidEnkelvoud: 'component', ...props },
  })

describe('FilterResultaatRegel', () => {
  it('zonder filters: het kale totaal ("19 componenten")', () => {
    const w = mountRegel({ totaal: 19, totaalAlles: 19, chips: [] })
    expect(w.find('[data-testid="resultaat-aantal"]').text()).toBe('19 componenten')
  })

  it('met filters: "X van Y" + elk filter uitgeschreven als chip (label + waarde)', () => {
    const w = mountRegel({
      totaal: 3,
      totaalAlles: 19,
      chips: [
        { sleutel: 'levensfase', label: 'Levensfase', waarde: 'In ontwikkeling' },
        { sleutel: 'werk', label: 'Ondersteunt werk', waarde: 'Nee' },
      ],
    })
    expect(w.find('[data-testid="resultaat-aantal"]').text()).toBe('3 van 19 componenten')
    // Zichtbare TEKST — het antwoord op "waarom is dit leeg?" staat er letterlijk.
    expect(w.find('[data-testid="filter-chip-levensfase"]').text()).toContain('Levensfase: In ontwikkeling')
    expect(w.find('[data-testid="filter-chip-werk"]').text()).toContain('Ondersteunt werk: Nee')
  })

  it('enkelvoud bij 1 ("1 van 19 componenten" / kale "1 component")', () => {
    const met = mountRegel({ totaal: 1, totaalAlles: 19, chips: [{ sleutel: 'x', label: 'X', waarde: 'y' }] })
    expect(met.find('[data-testid="resultaat-aantal"]').text()).toBe('1 van 19 componenten')
    const kaal = mountRegel({ totaal: 1, totaalAlles: 1, chips: [] })
    expect(kaal.find('[data-testid="resultaat-aantal"]').text()).toBe('1 component')
  })

  it('✕ op een chip emit "wis" met exact die sleutel (los wisbaar)', async () => {
    const w = mountRegel({
      totaal: 0,
      totaalAlles: 19,
      chips: [
        { sleutel: 'levensfase', label: 'Levensfase', waarde: 'In ontwikkeling' },
        { sleutel: 'werk', label: 'Ondersteunt werk', waarde: 'Nee' },
      ],
    })
    await w.find('[data-testid="chip-wis-werk"]').trigger('click')
    expect(w.emitted('wis')).toEqual([['werk']])
  })

  it('zonder totaal (nog niet geladen) rendert de regel niet', () => {
    const w = mountRegel({ totaal: null, totaalAlles: null, chips: [] })
    expect(w.find('[data-testid="resultaat-regel"]').exists()).toBe(false)
  })
})
