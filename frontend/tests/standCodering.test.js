import { describe, it, expect } from 'vitest'
import { STAND_CODERING, standPillStyle } from '@modules/bwb_ontvlechting/frontend/standCodering'

// Slice B1 (G4-6) — de ENE bron voor "plek-stand → presentatie". Bewijst dat de mapping compleet
// is en dat de vijf standen hun ernst-kleur/tekst dragen; lijst (B1) én kaart/legenda (B2) erven dit.
describe('standCodering — de ene bron voor de vijf plek-standen', () => {
  const STANDEN = ['gat', 'werkvoorraad', 'hier', 'via_boven', 'niets']

  it('elke stand draagt ernst + kleur (lk-token) + icoon + lijstTekst + legendaTekst', () => {
    for (const stand of STANDEN) {
      const c = STAND_CODERING[stand]
      expect(c, stand).toBeTruthy()
      expect(typeof c.ernst).toBe('string')
      expect(c.kleur).toMatch(/^var\(--lk-color-/) // token, geen losse hex → dark-mode-safe
      expect(typeof c.icoon).toBe('string')
      expect(typeof c.lijstTekst({})).toBe('string')
      expect(typeof c.legendaTekst).toBe('string')
      expect(c.legendaTekst.length).toBeGreaterThan(0)
    }
    // De bron kent precies deze vijf standen.
    expect(Object.keys(STAND_CODERING).sort()).toEqual([...STANDEN].sort())
  })

  it('ernst→kleur: werk=amber (gat+werkvoorraad) · hier=groen · via_boven=blauw · niets=grijs', () => {
    expect(STAND_CODERING.gat.ernst).toBe('werk')
    expect(STAND_CODERING.werkvoorraad.ernst).toBe('werk')
    expect(STAND_CODERING.gat.kleur).toBe('var(--lk-color-warning)')
    expect(STAND_CODERING.werkvoorraad.kleur).toBe('var(--lk-color-warning)')
    expect(STAND_CODERING.hier.kleur).toBe('var(--lk-color-success)')
    expect(STAND_CODERING.via_boven.kleur).toBe('var(--lk-color-primary-700)')
    expect(STAND_CODERING.niets.kleur).toBe('var(--lk-color-text-muted)')
  })

  it('de twee amber-standen dragen ONDERSCHEIDEN tekst (één ernst, twee betekenissen)', () => {
    expect(STAND_CODERING.gat.lijstTekst({})).toContain('nog niet vastgelegd waarmee')
    expect(STAND_CODERING.werkvoorraad.lijstTekst({})).toContain('systeem bekend, gebruiker nog niet')
    expect(STAND_CODERING.gat.lijstTekst({})).not.toBe(STAND_CODERING.werkvoorraad.lijstTekst({}))
  })

  it('via_boven noemt de voorouder, of telt bij meerdere op gelijke afstand', () => {
    expect(STAND_CODERING.via_boven.lijstTekst({ voorouder: 'Klantenservice' })).toBe('ondersteund via Klantenservice')
    expect(STAND_CODERING.via_boven.lijstTekst({ viaAantal: 3 })).toBe('ondersteund via 3 bovenliggende functies')
  })

  it('standPillStyle geeft kleur + rand + tint uit de bron; onbekende stand → leeg', () => {
    const s = standPillStyle('gat')
    expect(s.color).toBe('var(--lk-color-warning)')
    expect(s.borderColor).toBe('var(--lk-color-warning)')
    expect(s.background).toContain('color-mix')
    expect(standPillStyle('onbekend')).toEqual({})
  })
})
