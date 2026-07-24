/**
 * Tests — zoekterm-opschoning aan de VOORKANT (LI051, blok D + de categorie-regel).
 *
 * Geborgd:
 * 1. GELIJKHEID met de achterkant — dezelfde gedeelde reeks (`fixtures/zoekterm_gelijkheid.json`)
 *    die de backend-test ook draait, met dezelfde 'uit'. Wijkt een kant af, dan valt die suite om.
 * 2. De VLAG `ietsWeggehaald` (blok C): waar als er iets is VERDWENEN (opmaak-/stuurteken weg of
 *    spaties samengevouwen); onwaar als een onzichtbare spatie alleen een gewone is geworden.
 * 3. De regel per CATEGORIE (Zs/Cf/Cc) over het hele Unicode-bereik — niet per lijst codes.
 *
 * Onzichtbare tekens worden hier uit hun code point OPGEBOUWD (String.fromCharCode) — de bron blijft
 * puur ASCII, zodat er nooit een letterlijk onzichtbaar teken in het bestand sluipt.
 */
import { describe, expect, it } from 'vitest'

import { schoonZoekterm } from '../src/zoekterm.js'
import reeks from './fixtures/zoekterm_gelijkheid.json'

const ch = (cp) => String.fromCodePoint(cp)
const NUL = ch(0x00)
const NBSP = ch(0x00a0)
const NNBSP = ch(0x202f)
const EMSP = ch(0x2003)
const IDSP = ch(0x3000)
const ZWSP = ch(0x200b)
const WJ = ch(0x2060)
const BOM = ch(0xfeff)
const COMB_ACUTE = ch(0x0301) // combining acute -> é

describe('zoekterm — voorkant schoont gelijk aan de gedeelde reeks (blok D)', () => {
  for (const { in: ruw, uit } of reeks.gevallen) {
    it(`schoont ${JSON.stringify(ruw)} -> ${JSON.stringify(uit)}`, () => {
      expect(schoonZoekterm(ruw).schoon).toBe(uit)
    })
  }
})

describe('zoekterm — de vlag ietsWeggehaald stuurt de melding (blok C)', () => {
  it('is waar als er iets is VERDWENEN: opmaak-/stuurteken weg, of spaties samengevouwen', () => {
    expect(schoonZoekterm('zaak' + NUL + 'systeem').ietsWeggehaald).toBe(true) // NUL (Cc)
    expect(schoonZoekterm('regel1\nregel2').ietsWeggehaald).toBe(true) // regelovergang (Cc)
    expect(schoonZoekterm('kol1\tkol2').ietsWeggehaald).toBe(true) // tab (Cc)
    expect(schoonZoekterm('zaak' + ZWSP + 'systeem').ietsWeggehaald).toBe(true) // zero-width (Cf)
    expect(schoonZoekterm('zaak' + WJ + 'systeem').ietsWeggehaald).toBe(true) // word joiner (Cf)
    expect(schoonZoekterm(BOM + 'zaak').ietsWeggehaald).toBe(true) // BOM (Cf)
    expect(schoonZoekterm('zaak  systeem').ietsWeggehaald).toBe(true) // dubbele gewone spatie
    expect(schoonZoekterm('zaak' + NBSP + NBSP + 'systeem').ietsWeggehaald).toBe(true) // dubbele NBSP
  })

  it('is ONWAAR wanneer een onzichtbare spatie alleen een gewone wordt (niets verdwenen)', () => {
    for (const sp of [NBSP, EMSP, NNBSP, IDSP]) {
      const r = schoonZoekterm('zaak' + sp + 'systeem')
      expect(r.schoon).toBe('zaak systeem') // woordgrens blijft
      expect(r.ietsWeggehaald).toBe(false) // geen melding
    }
  })

  it('is onwaar bij een gewone zoekopdracht, NFC-vouwing of het trimmen van rand-spaties', () => {
    expect(schoonZoekterm('zaaksysteem').ietsWeggehaald).toBe(false)
    expect(schoonZoekterm('Select & Go ' + ch(0x1f680)).ietsWeggehaald).toBe(false)
    const los = 'Jose' + COMB_ACUTE // gedecomponeerd -> NFC José
    expect(schoonZoekterm(los).schoon).toBe('Jos' + ch(0x00e9))
    expect(schoonZoekterm(los).ietsWeggehaald).toBe(false)
    expect(schoonZoekterm('  Zaaksysteem  ').ietsWeggehaald).toBe(false) // alleen rand-trim
  })

  it('is idempotent: nogmaals opschonen verandert niets', () => {
    for (const ruw of ['zaak' + NUL + 'systeem', 'zaak' + NBSP + 'systeem', 'Jose' + COMB_ACUTE, '  x  ', ' ']) {
      const een = schoonZoekterm(ruw).schoon
      expect(schoonZoekterm(een).schoon).toBe(een)
    }
  })
})

describe('zoekterm — de regel per CATEGORIE, niet per lijst codes', () => {
  const CF = /\p{Cf}/u
  const ZS = /\p{Zs}/u
  const CC = /\p{Cc}/u

  it('elke Zs -> gewone spatie; elke Cf/Cc -> weg (over het hele Unicode-bereik)', () => {
    // Zo glipt een teken dat niemand opschreef er niet doorheen. We toetsen alleen de tekens die
    // ECHT in een van de categorieën vallen (de rest wordt goedkoop overgeslagen).
    const fout = []
    for (let cp = 0; cp <= 0x10ffff && fout.length <= 5; cp++) {
      if (cp >= 0xd800 && cp <= 0xdfff) continue // surrogaat-helften: geen echt teken
      const c = String.fromCodePoint(cp)
      const zs = ZS.test(c)
      const weg = CF.test(c) || CC.test(c)
      if (!zs && !weg) continue
      const uit = schoonZoekterm('a' + c + 'b').schoon
      if (zs && uit !== 'a b') fout.push('Zs U+' + cp.toString(16))
      else if (weg && uit !== 'ab') fout.push('Cf/Cc U+' + cp.toString(16))
    }
    expect(fout).toEqual([])
  })
})
