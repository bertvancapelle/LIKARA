/**
 * Tests — procesFocusSet + procesSubboomSet (LI038 gate 1/3, pure module procesBoom.js).
 *
 * De focus-selectie van het proces-only structuurbeeld: centrum + ouderketen (boven) +
 * volledige subboom (beneden) + zusjes (opzij, zónder hun subbomen). De subboom-set is de
 * dubbelklik-inzoom-scope: alleen het proces + zijn subboom. Beide cyclus-veilig.
 */
import { describe, expect, it } from 'vitest'
import { procesFocusSet, procesSubboomSet } from '@modules/bwb_ontvlechting/frontend/procesBoom'

// Twee bomen:
//   w ─ a ─ a1 ─ a1x        w2 ─ w2a
//     │    └ a2 ─ a2x
//     └ b ─ b1
const IDS = new Set(['w', 'a', 'b', 'a1', 'a2', 'a1x', 'a2x', 'b1', 'w2', 'w2a'])
const EDGES = [
  { bron: 'a', doel: 'w' }, { bron: 'b', doel: 'w' },
  { bron: 'a1', doel: 'a' }, { bron: 'a2', doel: 'a' },
  { bron: 'a1x', doel: 'a1' }, { bron: 'a2x', doel: 'a2' },
  { bron: 'b1', doel: 'b' },
  { bron: 'w2a', doel: 'w2' },
]

describe('procesFocusSet', () => {
  it('centrum mid-boom: ouderketen boven + subboom beneden + zusjes opzij', () => {
    const focus = procesFocusSet('a1', IDS, EDGES)
    // Keten omhoog: a, w. Subboom: a1x. Zusje: a2 — maar diens subboom (a2x) NIET.
    expect(focus).toEqual(new Set(['a1', 'a', 'w', 'a1x', 'a2']))
  })

  it('zusjes-subbomen en ooms blijven buiten beeld', () => {
    const focus = procesFocusSet('a1', IDS, EDGES)
    expect(focus.has('a2x')).toBe(false) // subboom van het zusje
    expect(focus.has('b')).toBe(false) // oom (zusje van de ouder)
    expect(focus.has('w2')).toBe(false) // andere boom
  })

  it('wortel-centrum: geen ouder, geen zusjes (andere wortels horen er niet bij), wel de hele subboom', () => {
    const focus = procesFocusSet('w', IDS, EDGES)
    expect(focus).toEqual(new Set(['w', 'a', 'b', 'a1', 'a2', 'a1x', 'a2x', 'b1']))
    expect(focus.has('w2')).toBe(false)
  })

  it('blad-centrum: keten tot de wortel + zusjes, geen kinderen', () => {
    const focus = procesFocusSet('a1x', IDS, EDGES)
    expect(focus).toEqual(new Set(['a1x', 'a1', 'a', 'w']))
  })

  it('onbekend of leeg centrum geeft een lege set', () => {
    expect(procesFocusSet('bestaat-niet', IDS, EDGES)).toEqual(new Set())
    expect(procesFocusSet(null, IDS, EDGES)).toEqual(new Set())
    expect(procesFocusSet('a1', new Set(), EDGES)).toEqual(new Set())
  })

  it('termineert op een (geconstrueerde) datakring — nooit hangen', () => {
    const ids = new Set(['c1', 'c2', 'c3'])
    const edges = [
      { bron: 'c1', doel: 'c2' }, { bron: 'c2', doel: 'c1' }, // kring
      { bron: 'c3', doel: 'c1' },
    ]
    const focus = procesFocusSet('c3', ids, edges)
    expect(focus.has('c3')).toBe(true)
    expect(focus.has('c1')).toBe(true) // ouder
    expect(focus.has('c2')).toBe(true) // voorouder tot de kring dichtklapt
  })
})

describe('procesSubboomSet (LI038 gate 3 — inzoom-scope)', () => {
  it('levert het proces + zijn volledige subboom, zónder keten of zusjes', () => {
    expect(procesSubboomSet('a', IDS, EDGES)).toEqual(new Set(['a', 'a1', 'a2', 'a1x', 'a2x']))
    expect(procesSubboomSet('a', IDS, EDGES).has('w')).toBe(false) // geen ouderketen
    expect(procesSubboomSet('a', IDS, EDGES).has('b')).toBe(false) // geen zusjes
  })

  it('een blad zonder kinderen geeft alleen zichzelf (inzoom weigert nooit)', () => {
    expect(procesSubboomSet('a1x', IDS, EDGES)).toEqual(new Set(['a1x']))
  })

  it('onbekend centrum → lege set; datakring termineert', () => {
    expect(procesSubboomSet('bestaat-niet', IDS, EDGES)).toEqual(new Set())
    const ids = new Set(['c1', 'c2'])
    const edges = [{ bron: 'c1', doel: 'c2' }, { bron: 'c2', doel: 'c1' }]
    expect(procesSubboomSet('c1', ids, edges).has('c1')).toBe(true) // eindigt, hangt niet
  })
})
