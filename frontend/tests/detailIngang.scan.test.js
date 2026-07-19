// LI046 — dekkingsscan van de gedeelde detail-ingang (recept: tests/api.filter.test.js —
// allowlist + LUIDE fout). Borgt structureel dat er GEEN tweede route-pad naar een
// detailscherm bestaat: elk bestand dat zelf een `name: '<x>-detail'`-route bouwt (buiten
// de allowlist) laat deze test falen met bestand + regel. Zo kan een nieuwe view de
// éne-ingang-regel niet stil vergeten — de regel leeft in een scan, niet in tekst.
import { describe, expect, it } from 'vitest'
import { readdirSync, readFileSync, statSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join, relative } from 'node:path'

const HIER = dirname(fileURLToPath(import.meta.url))
const FRONTEND_SRC = join(HIER, '..', 'src')
const MODULE_FRONTEND = join(HIER, '..', '..', 'modules', 'bwb_ontvlechting', 'frontend')
const REPO = join(HIER, '..', '..')

// Toegestane plekken voor een detail-route-naam:
// - de router zelf (route-definities + legacy `applicatie-*`-redirects);
// - de gedeelde ingang (dé ene plek die routes bouwt);
// - testbestanden (asserties op route-objecten zijn geen navigatie-pad).
const ALLOWLIST = new Set([
  'frontend/src/router/index.js',
  'frontend/src/detailIngang.js',
])

// `name:` ervoor is essentieel: alleen route-OBJECTEN tellen, niet een naam in een comment.
const PATROON = /name:\s*['"](?:component|contract|partij)-detail['"]/

function* bronbestanden(dir) {
  for (const naam of readdirSync(dir)) {
    const pad = join(dir, naam)
    if (statSync(pad).isDirectory()) {
      if (naam === 'node_modules' || naam === 'dist') continue
      yield* bronbestanden(pad)
    } else if (/\.(vue|js)$/.test(naam) && !/\.test\.js$/.test(naam)) {
      yield pad
    }
  }
}

describe('dekkingsscan detail-ingang (LI046)', () => {
  it('geen enkel bronbestand bouwt zelf een detail-route buiten de gedeelde ingang', () => {
    const overtreders = []
    for (const wortel of [FRONTEND_SRC, MODULE_FRONTEND]) {
      for (const pad of bronbestanden(wortel)) {
        const rel = relative(REPO, pad).replaceAll('\\', '/')
        if (ALLOWLIST.has(rel)) continue
        const regels = readFileSync(pad, 'utf8').split('\n')
        regels.forEach((regel, i) => {
          if (PATROON.test(regel)) overtreders.push(`${rel}:${i + 1}`)
        })
      }
    }
    expect(
      overtreders,
      `Detail-route buiten de gedeelde ingang gevonden — gebruik detailRoute() uit ` +
        `'@/detailIngang' (of breid bewust de allowlist uit):\n  ${overtreders.join('\n  ')}`,
    ).toEqual([])
  })

  it('de allowlist bevat alleen bestaande bestanden (geen dode uitzonderingen)', () => {
    for (const rel of ALLOWLIST) {
      expect(() => statSync(join(REPO, rel)), `allowlist-bestand ontbreekt: ${rel}`).not.toThrow()
    }
  })
})
