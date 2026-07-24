/**
 * Blok E (LI051) — de wachter over het VOLLEDIGE bereik van zoekvelden aan de voorkant.
 *
 * De naad die dit spoor blootlegde: een nieuw zoekveld valt door de mazen — de invoer-weerbaarheid
 * kijkt alleen naar formulieren en ziet een zoekterm niet, de accent-wachter borgt alleen het
 * accent-negeren. Zonder wachter ontstaat dat gat over een half jaar opnieuw, zonder dat iemand het
 * merkt. Deze wachter faalt zodra een zoekveld buiten de opschoning (`schoonZoekterm`) omgaat.
 *
 * BEREIK — afgeleid, geen bestandslijst: elk `.vue` met een vrije-tekst zoek-affordance, d.w.z. een
 * `type="search"`-input (de eigen zoekvelden) OF een `role="combobox"` (de gedeelde FK-kiezer
 * ZoekSelect, die ~30 formulierplekken voedt). Elk zo'n bestand MOET `schoonZoekterm` gebruiken.
 * Komt er later een zoekveld bij, dan valt het vanzelf binnen het bereik.
 *
 * WAT DEZE WACHTER WÉL DEKT: dat élk zoekveld-dragend bestand de gedeelde opschoning aanroept
 * (voorkant). WAT HIJ NIET DEKT: (1) of binnen een bestand met méér dan één zoekveld élk afzonderlijk
 * veld bedraad is — dat borgen de gedrag-tests per soort (zoekterm_melding / ComponentLijst /
 * BedrijfsfunctieLijst); (2) de ACHTERKANT — die is geborgd doordat élk zoeken via `zoek_clause`
 * loopt (test_zoektekst_een_bron_li051) en `zoek_clause` de term opschoont (test_zoekterm_opschonen).
 */
import { mkdtempSync, readdirSync, readFileSync, rmSync, statSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import path from 'node:path'
import { describe, expect, it } from 'vitest'

const FRONTEND = process.cwd() // vitest-root = frontend/
const ROOTS = [
  path.join(FRONTEND, 'src'),
  path.join(FRONTEND, '..', 'modules', 'bwb_ontvlechting', 'frontend'),
]

// Een vrije-tekst zoek-affordance: een eigen zoekveld (type="search") of de gedeelde combobox.
const ZOEKVELD = /type="search"|role="combobox"/
const OPSCHONING = /schoonZoekterm/

function vueBestanden(root) {
  const uit = []
  for (const naam of readdirSync(root)) {
    const p = path.join(root, naam)
    const st = statSync(p)
    if (st.isDirectory()) uit.push(...vueBestanden(p))
    else if (naam.endsWith('.vue')) uit.push(p)
  }
  return uit
}

/** De overtreders: bestanden met een zoekveld die de gedeelde opschoning NIET aanroepen. */
function overtreders(roots) {
  const fout = []
  for (const root of roots) {
    for (const p of vueBestanden(root)) {
      const bron = readFileSync(p, 'utf8')
      if (ZOEKVELD.test(bron) && !OPSCHONING.test(bron)) fout.push(path.basename(p))
    }
  }
  return fout
}

function dragers(roots) {
  return roots.flatMap(vueBestanden).filter((p) => ZOEKVELD.test(readFileSync(p, 'utf8')))
}

describe('Blok E — elk zoekveld loopt via de gedeelde opschoning', () => {
  it('geen enkel zoekveld-dragend bestand omzeilt schoonZoekterm', () => {
    expect(overtreders(ROOTS)).toEqual([])
  })

  it('het bereik is niet leeg (anders zegt "groen" niets)', () => {
    // Zakt dit onder de bekende telling, dan is er een zoekveld uit het bereik gevallen — een
    // bevinding, geen bij te werken getal.
    expect(dragers(ROOTS).length).toBeGreaterThanOrEqual(8)
  })

  it('BIJT: een nieuw zoekveld zonder opschoning wordt betrapt (tijdelijk overtreder-bestand)', () => {
    const dir = mkdtempSync(path.join(tmpdir(), 'zoekwachter-'))
    try {
      // Een overtreder: een zoekveld dat de opschoning omzeilt.
      writeFileSync(
        path.join(dir, 'Overtreder.vue'),
        '<template><input type="search" data-testid="x" /></template>\n',
      )
      expect(overtreders([dir])).toEqual(['Overtreder.vue'])

      // Een net bestand met zoekveld ÉN opschoning wordt niet geflagd (geen valse beet).
      writeFileSync(
        path.join(dir, 'Netjes.vue'),
        '<script setup>import { schoonZoekterm } from "@/zoekterm"</script>\n<template><input type="search" /></template>\n',
      )
      expect(overtreders([dir])).toEqual(['Overtreder.vue'])
    } finally {
      rmSync(dir, { recursive: true, force: true })
    }
  })
})
