/** Tests — meervoudBoomStructuur (ADR-044) + regressie op procesBoomStructuur.
 *
 * De gedeelde pure module `procesBoom.js` draagt sinds ADR-044 twee structuur-varianten:
 * - `procesBoomStructuur` — één-ouder-wereld (processen, kaart-proceszone): de
 *   dubbele-ouder-guard BLIJFT (tweede ouder valt stil weg — daar is één ouder de waarheid);
 * - `meervoudBoomStructuur` — plaatsingen-wereld (bedrijfsfuncties): élke (kind, ouder)-
 *   plaatsing telt; één functie kan onder meerdere ouders staan.
 * Deze tests borgen beide kanten — vooral dat de proces-semantiek NIET meebewoog.
 */
import { describe, expect, it } from 'vitest'
import {
  meervoudBoomStructuur,
  procesBoomStructuur,
} from '@modules/bwb_ontvlechting/frontend/procesBoom'

const NAMEN = { a: 'Alfa', b: 'Bravo', c: 'Charlie', d: 'Delta' }
const naamVan = (id) => NAMEN[id] || String(id)

describe('meervoudBoomStructuur (ADR-044 — plaatsingen)', () => {
  it('draagt meerdere ouders: het kind staat in kinderenVan van BEIDE ouders', () => {
    const ids = new Set(['a', 'b', 'c'])
    const edges = [
      { bron: 'c', doel: 'a' },
      { bron: 'c', doel: 'b' },
    ]
    const { wortels, oudersVan, kinderenVan } = meervoudBoomStructuur(ids, edges, naamVan)
    expect(oudersVan.get('c')).toEqual(['a', 'b']) // gesorteerd, beide aanwezig
    expect(kinderenVan.get('a')).toEqual(['c'])
    expect(kinderenVan.get('b')).toEqual(['c'])
    expect(wortels).toEqual(['a', 'b']) // c heeft ouders → geen wortel
  })

  it('ontdubbelt identieke plaatsings-paren en negeert self-edges', () => {
    const ids = new Set(['a', 'c'])
    const edges = [
      { bron: 'c', doel: 'a' },
      { bron: 'c', doel: 'a' }, // dubbel — telt één keer
      { bron: 'a', doel: 'a' }, // self — genegeerd
    ]
    const { oudersVan, kinderenVan } = meervoudBoomStructuur(ids, edges, naamVan)
    expect(oudersVan.get('c')).toEqual(['a'])
    expect(kinderenVan.get('a')).toEqual(['c'])
    expect(oudersVan.has('a')).toBe(false)
  })

  it('sorteert kinderen én ouders deterministisch op naam→id', () => {
    const ids = new Set(['a', 'b', 'c', 'd'])
    const edges = [
      { bron: 'd', doel: 'b' },
      { bron: 'c', doel: 'b' },
      { bron: 'd', doel: 'a' },
    ]
    const { kinderenVan, oudersVan } = meervoudBoomStructuur(ids, edges, naamVan)
    expect(kinderenVan.get('b')).toEqual(['c', 'd']) // Charlie < Delta
    expect(oudersVan.get('d')).toEqual(['a', 'b']) // Alfa < Bravo
  })

  it('edges buiten de id-set tellen niet mee; lege set geeft lege structuur', () => {
    const { wortels } = meervoudBoomStructuur(new Set(['a']), [{ bron: 'a', doel: 'x' }], naamVan)
    expect(wortels).toEqual(['a'])
    expect(meervoudBoomStructuur(new Set(), [], naamVan).wortels).toEqual([])
  })
})

describe('procesBoomStructuur — regressie: de één-ouder-semantiek bewoog NIET mee', () => {
  it('dropt een tweede ouder stil (dubbele-ouder-guard, de ProcesLijst-waarheid)', () => {
    const ids = new Set(['a', 'b', 'c'])
    const edges = [
      { bron: 'c', doel: 'a' },
      { bron: 'c', doel: 'b' }, // tweede ouder — valt weg in de één-ouder-wereld
    ]
    const { ouderVan, kinderenVan, wortels } = procesBoomStructuur(ids, edges, naamVan)
    expect(ouderVan.get('c')).toBe('a') // de eerste wint; géén array
    expect(kinderenVan.get('b')).toBeUndefined()
    expect(wortels).toEqual(['a', 'b'])
  })
})
