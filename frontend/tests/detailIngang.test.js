// LI046 — gedragstests van de gedeelde detail-ingang (`src/detailIngang.js`).
import { describe, expect, it } from 'vitest'
import { detailRoute } from '@/detailIngang'

describe('detailRoute — de ene ingang naar een detailscherm', () => {
  it('bouwt de kale detail-route per objectsoort', () => {
    expect(detailRoute('component', 'abc')).toEqual({ name: 'component-detail', params: { id: 'abc' } })
    expect(detailRoute('contract', 'c1')).toEqual({ name: 'contract-detail', params: { id: 'c1' } })
    expect(detailRoute('partij', 'p1')).toEqual({ name: 'partij-detail', params: { id: 'p1' } })
    expect(detailRoute('plateau', 'x')).toEqual({ name: 'plateau-detail', params: { id: 'x' } })
  })

  it('een soort zonder detailscherm geeft null — geen route-belofte zonder landingsplek', () => {
    expect(detailRoute('gebruikersgroep', 'g1')).toBeNull()
    expect(detailRoute('datatype', 'd1')).toBeNull()
    expect(detailRoute('proces', 'pr1')).toBeNull() // MVP-verborgen (ADR-043)
    expect(detailRoute('onzin', 'x')).toBeNull()
  })

  it('zonder id geen route', () => {
    expect(detailRoute('component', null)).toBeNull()
    expect(detailRoute('component', undefined)).toBeNull()
  })

  it('bedrijfsfunctie landt op de lijst met focus (besluit 4)', () => {
    expect(detailRoute('bedrijfsfunctie', 'f1')).toEqual({
      name: 'bedrijfsfunctie-lijst',
      query: { focus: 'f1' },
    })
  })

  it('de aanleiding vertaalt naar de bestaande query-landingsplekken', () => {
    expect(detailRoute('component', 'abc', { markeer: '2.2', tab: 'checklist', cat: '2' })).toEqual({
      name: 'component-detail',
      params: { id: 'abc' },
      query: { markeer: '2.2', tab: 'checklist', cat: '2' },
    })
    expect(detailRoute('component', 'abc', { bewerk: '1' })).toEqual({
      name: 'component-detail',
      params: { id: 'abc' },
      query: { bewerk: '1' },
    })
  })

  it('lege aanleiding-waarden vallen bewust weg (geen lege query-sleutels in de URL)', () => {
    expect(detailRoute('component', 'abc', { markeer: null, tab: undefined, cat: '' })).toEqual({
      name: 'component-detail',
      params: { id: 'abc' },
    })
  })

  // ── LI046 slice 2 — het veld-anker ──
  it('het veld-anker vertaalt naar ?veld= voor de vijf Overzicht-velden', () => {
    for (const veld of ['eigenaar', 'biv', 'levensfase', 'bedoeling', 'beschrijving']) {
      expect(detailRoute('component', 'abc', { veld })).toEqual({
        name: 'component-detail',
        params: { id: 'abc' },
        query: { veld },
      })
    }
  })

  it('een onbekend veld-anker is een LUIDE fout — geen route-belofte zonder landingsplek', () => {
    expect(() => detailRoute('component', 'abc', { veld: 'hostingmodel' })).toThrow(/onbekend veld-anker 'hostingmodel'/)
  })

  it('een onbekende aanleiding-sleutel is een LUIDE fout (api.filter-conventie)', () => {
    expect(() => detailRoute('component', 'abc', { veldje: 'x' })).toThrow(/onbekende aanleiding-sleutel 'veldje'/)
  })
})
