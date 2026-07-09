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
