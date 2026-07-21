// @vitest-environment node
/**
 * Laag A — Token-contracttest (UI-borging interactiestates).
 *
 * Faalt als een afgesproken `--lk-`-token dat de knop-/tab-standaard draagt
 * ontbreekt of een lege waarde heeft in `themes/base.css`. Zo kan een toekomstige
 * wijziging die een token hernoemt/verwijdert niet meer stil een interactie-state
 * breken (bv. tab-hover die op `--lk-color-primary-50` leunt).
 *
 * Uitbreiden = een token aan VEREISTE_TOKENS toevoegen.
 */
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

// Tokens die de knop- + tab-interactiestandaard dragen (zie likara-frontend).
const VEREISTE_TOKENS = [
  '--lk-color-primary',
  '--lk-color-primary-50',
  '--lk-color-primary-100',
  '--lk-color-primary-700',
  '--lk-color-danger',
  // LI035 — het warn-token (MeldingBanner + warn-banners); de `--lk-color-warn`-typo
  // (token bestond niet → banners zonder tint) mag niet terugkomen.
  '--lk-color-warning',
  '--lk-color-border',
  // LI048 — de buitenrand van een werkvlak. Aparte token omdat hij een eigen REGEL draagt
  // (zie de luminantietoets onderaan), niet omdat de waarde bijzonder is.
  '--lk-color-border-sterk',
  '--lk-color-text',
  '--lk-radius-btn',
  '--lk-text-sm',
  '--lk-text-xs',
]

const BASE_CSS = readFileSync(
  fileURLToPath(new URL('../src/themes/base.css', import.meta.url)),
  'utf8',
)

/** Parseer alle `--token: waarde;`-definities uit base.css naar een map. */
function parseTokens(css) {
  const map = {}
  for (const m of css.matchAll(/(--lk-[a-z0-9-]+)\s*:\s*([^;]+);/gi)) {
    map[m[1]] = m[2].trim()
  }
  return map
}

describe('Token-contract — base.css', () => {
  const tokens = parseTokens(BASE_CSS)

  it.each(VEREISTE_TOKENS)('token %s bestaat en heeft een niet-lege waarde', (naam) => {
    expect(tokens, `token ${naam} ontbreekt in base.css`).toHaveProperty(naam)
    expect(tokens[naam], `token ${naam} heeft een lege waarde`).toBeTruthy()
    expect(tokens[naam].length).toBeGreaterThan(0)
  })
})

// ── LI048 — de buitenrand is ALTIJD zwaarder dan de lijnen erbinnen ──────────────────────────
// Dit toetst de REGEL, niet de waarde: welke tint de buitenrand precies heeft mag veranderen,
// maar hij moet donkerder blijven dan `--lk-color-border` (de scheidingslijntjes in lijsten en
// formulieren, `th/td` in main.css). Waren ze gelijk — en dat wáren ze, beide #e2e8f0 — dan
// hoort de buitenrand nergens meer bij en ziet de consultant niet waar zijn werkgebied begint.
//
// Deze toets valt om in BEIDE richtingen: als iemand de buitenrand verlicht, én als iemand de
// binnenlijn verzwaart. Dat tweede is de sluipweg die anders niemand opmerkt.
//
// Relatieve luminantie volgens WCAG 2.x — dezelfde formule waarmee de tint gekozen is.
function luminantie(hex) {
  const h = hex.trim().replace('#', '')
  const kanaal = (n) => {
    const c = n / 255
    return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4
  }
  const [r, g, b] = [0, 2, 4].map((i) => kanaal(parseInt(h.slice(i, i + 2), 16)))
  return 0.2126 * r + 0.7152 * g + 0.0722 * b
}

describe('LI048 — buitenrand zwaarder dan binnenlijn', () => {
  const tokens = parseTokens(BASE_CSS)

  it('beide randtokens zijn een hex-kleur (anders is de vergelijking zinloos)', () => {
    for (const naam of ['--lk-color-border', '--lk-color-border-sterk']) {
      expect(tokens[naam], `${naam} is geen hex — de luminantietoets kan niet meten`)
        .toMatch(/^#[0-9a-f]{6}$/i)
    }
  })

  it('de buitenrand is donkerder dan de scheidingslijnen erbinnen', () => {
    const binnen = luminantie(tokens['--lk-color-border'])
    const buiten = luminantie(tokens['--lk-color-border-sterk'])
    expect(buiten, 'de buitenrand is niet donkerder dan de binnenlijn').toBeLessThan(binnen)
  })

  it('de RANGORDE klopt: zware buitenrand > kader/blok > streepjes erbinnen', () => {
    // Drie lijnen, drie betekenissen (likara-frontend §"Drie lijngewichten, drie betekenissen"):
    //   zwaar  = hier begint en eindigt mijn werkgebied  (--lk-color-border-sterk)
    //   gewoon = dit hoort bij elkaar, één blok          (--lk-color-border)
    //   dun    = regels binnen een lijst                 (--lk-color-border, lichter door 1px op wit)
    // Het kader om de inhoud en de omlijning van de schakelaar dragen bewust het GEWONE gewicht:
    // zouden zij de sterke token pakken, dan wordt het een raster van kaders in kaders en is de
    // buitenrand geen buitenrand meer. Deze toets bewaakt die volgorde — in beide richtingen.
    const zwaar = luminantie(tokens['--lk-color-border-sterk'])
    const gewoon = luminantie(tokens['--lk-color-border'])
    expect(zwaar, 'de buitenrand moet de zwaarste lijn op het scherm zijn').toBeLessThan(gewoon)
    // En de gewone lijn moet zélf nog zichtbaar zijn op wit — anders is "dit hoort bij elkaar"
    // geen signaal maar een vermoeden.
    const contrastOpWit = (l) => (1.0 + 0.05) / (l + 0.05)
    expect(contrastOpWit(gewoon), 'de gewone lijn is te licht om iets bij elkaar te houden')
      .toBeGreaterThan(1.15)
  })

  it('maar niet zó zwaar dat het kader de aandacht van de inhoud wegtrekt', () => {
    // Een dikke of donkere omlijsting om élk werkvlak wordt bij twintig schermen per dag een
    // raster. De grens is ruim gekozen (slate-400 ≈ 2,08× zou hem overschrijden); hij bewaakt
    // de bovenkant van de bandbreedte, niet één specifieke tint.
    const contrastOpWit = (l) => (1.0 + 0.05) / (l + 0.05)
    const verhouding =
      contrastOpWit(luminantie(tokens['--lk-color-border-sterk'])) /
      contrastOpWit(luminantie(tokens['--lk-color-border']))
    expect(verhouding, 'de buitenrand is te zwaar — dat leest als een raster').toBeLessThan(1.8)
  })
})
