/** Tests — kaartBanen: scheiden op HOEDANIGHEID (LI046 / ADR-054-vervolg).
 *  Zuivere beslissing (LI044-patroon): we toetsen dat twee hoedanigheden tussen hetzelfde paar
 *  nooit op dezelfde plek belanden, dat een NIEUWE hoedanigheid het erft, en dat de beheerrollen
 *  tot één baan samenvallen. De render (unbundled-bezier + cpd) is browsercheck-materie. */
import { describe, expect, it } from 'vitest'
import { baanVerdeling, baanLabel, hoedanigheidVan } from '@modules/bwb_ontvlechting/frontend/kaartBanen'

const E = (bron, doel, relatietype, label = '') => ({ bron_id: bron, doel_id: doel, relatietype, label })
// Canonieke (richting-onafhankelijke) geometrische plek van een baan: cpd teruggespiegeld naar het
// canonieke frame. Twee banen op dezelfde canonieke plek zouden op elkaar liggen.
const canoniek = (g) => g.cpd * (String(g.bron_id) < String(g.doel_id) ? 1 : -1)

describe('kaartBanen — scheiden op hoedanigheid (LI046)', () => {
  it('twee hoedanigheden tussen hetzelfde paar → twee banen, nooit dezelfde plek', () => {
    const v = baanVerdeling([E('a', 'b', 'flow'), E('a', 'b', 'aggregation')])
    expect(v.length).toBe(2)
    expect(v.every((g) => g.banen === 2)).toBe(true)
    expect(new Set(v.map((g) => g.baan)).size).toBe(2) // twee onderscheiden banen
    expect(new Set(v.map(canoniek)).size).toBe(2) // twee onderscheiden geometrische plekken
  })

  it('een NIEUWE hoedanigheid (onbekend relatietype) erft het gedrag — eigen baan, zonder code-tak', () => {
    const v = baanVerdeling([E('a', 'b', 'flow'), E('a', 'b', 'toekomstige_soort')])
    expect(v.length).toBe(2)
    expect(new Set(v.map((g) => g.hoedanigheid)).size).toBe(2)
    expect(new Set(v.map(canoniek)).size).toBe(2)
  })

  it('drie hoedanigheden (eigenaar · gebruikt · beheer) → drie banen, één op de rechte lijn', () => {
    const v = baanVerdeling([
      E('o', 'c', 'eigenaar', 'is eigendom van'),
      E('o', 'c', 'gebruikt', 'gebruikt'),
      E('o', 'c', 'roltoewijzing', 'Functioneel beheer'),
    ])
    expect(v.length).toBe(3)
    expect(v.every((g) => g.banen === 3)).toBe(true)
    expect(v.filter((g) => g.cpd === 0).length).toBe(1) // middelste baan op de lijn
    expect(new Set(v.map(canoniek)).size).toBe(3) // drie onderscheiden plekken
  })

  it('beheerrollen vallen samen tot ÉÉN beheer-baan; ≤2 → namen, ≥3 → teller', () => {
    const twee = baanVerdeling([
      E('o', 'c', 'roltoewijzing', 'Functioneel beheer'),
      E('o', 'c', 'roltoewijzing', 'Technisch beheer'),
    ])
    expect(twee.length).toBe(1) // één beheer-groep, geen aparte banen per rol
    expect(twee[0].hoedanigheid).toBe('beheer')
    expect(twee[0].leden.length).toBe(2)
    expect(baanLabel(twee[0])).toBe('Functioneel beheer + Technisch beheer')
    const drie = baanVerdeling([
      E('o', 'c', 'roltoewijzing', 'A'), E('o', 'c', 'roltoewijzing', 'B'), E('o', 'c', 'roltoewijzing', 'C'),
    ])
    expect(drie.length).toBe(1)
    expect(baanLabel(drie[0])).toBe('3 beheerrollen')
  })

  it('een beheer-baan NAAST eigenaar/gebruikt telt als één van de banen (max blijft klein)', () => {
    // realistisch drukste geval: eigenaar + gebruikt + beheer(2 rollen) tussen partij↔systeem.
    const v = baanVerdeling([
      E('o', 'c', 'eigenaar'), E('o', 'c', 'gebruikt'),
      E('o', 'c', 'roltoewijzing', 'Functioneel beheer'), E('o', 'c', 'roltoewijzing', 'Technisch beheer'),
    ])
    expect(v.length).toBe(3) // eigenaar · gebruikt · beheer — niet vier
    expect(v.every((g) => g.banen === 3)).toBe(true)
  })

  it('bidirectionele flow (A→B én B→A) → twee gescheiden banen (richting is betekenis)', () => {
    const v = baanVerdeling([E('a', 'b', 'flow'), E('b', 'a', 'flow')])
    expect(v.length).toBe(2) // twee groepen (verschillende richting), niet samengevoegd
    expect(new Set(v.map((g) => g.baan)).size).toBe(2)
    expect(new Set(v.map(canoniek)).size).toBe(2) // fysiek tegengestelde zijden
  })

  it('één relatie tussen een paar → één rechte baan (cpd 0)', () => {
    const v = baanVerdeling([E('a', 'b', 'flow')])
    expect(v.length).toBe(1)
    expect(v[0].cpd).toBe(0)
    expect(v[0].banen).toBe(1)
  })

  it('hoedanigheidVan: roltoewijzing → beheer; overige → zichzelf', () => {
    expect(hoedanigheidVan('roltoewijzing')).toBe('beheer')
    expect(hoedanigheidVan('flow')).toBe('flow')
    expect(hoedanigheidVan('aggregation')).toBe('aggregation')
  })
})
