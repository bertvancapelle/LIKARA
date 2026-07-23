/** Wachter — een werkvlak-blok draagt een zichtbare grens (LI048-regel, LI050-les).
 *
 * Wat hier misging: het vraagblok kreeg `card` — dat draagt GEEN rand, alleen een
 * 5%-schaduw — en stond wit-op-wit binnen de categoriekaart (1,00:1): onzichtbaar.
 * De bestaande toets (tokens.contract) vergelijkt alleen twee kleurwaarden; niets
 * bewaakte de consument. Deze wachter dekt twee lagen, en eerlijk niet meer dan dat:
 *
 * 1. GENEST vlak: een `card` binnen een `card` is verboden — daar valt de grens
 *    volledig weg (wit op wit; de schaduw doet niets). Binnen een werkvlak hoort
 *    het kader-patroon (`lk-inhoudskader`) of het tabvlak.
 * 2. DEFINITIE: de kader-klassen (`lk-inhoudskader`, `lk-tabvlak`) dragen een échte
 *    1px-rand, en het tabvlak de STERKE (buitenrand > binnenlijn).
 *
 * NIET gedekt (bewust, geen valse belofte): een top-level `card` op de paginatint —
 * dat is vandaag het geaccepteerde brede patroon (32 consumenten) en een eigen
 * weging; en werkvlakken die met kale utilities zijn gebouwd. De browsercheck
 * blijft dáár het sluitpunt.
 */
import { describe, expect, it } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'

const WORTELS = [
  path.resolve(__dirname, '../src'),
  path.resolve(__dirname, '../../modules/bwb_ontvlechting/frontend'),
]

function vueBestanden(map) {
  const uit = []
  for (const naam of fs.readdirSync(map, { withFileTypes: true })) {
    const vol = path.join(map, naam.name)
    if (naam.isDirectory()) uit.push(...vueBestanden(vol))
    else if (naam.name.endsWith('.vue')) uit.push(vol)
  }
  return uit
}

// `card` als KLASSE-token — niet de substring in `var(--lk-radius-card)` e.d.
const CARD_TOKEN = /(?<![-\w])card(?![-\w)])/

function heeftCardKlasse(attrs) {
  const klassen = [...attrs.matchAll(/(?::?class)="([^"]*)"/g)]
  return klassen.some((m) => CARD_TOKEN.test(m[1]))
}

const VOID = new Set(['input', 'br', 'img', 'hr', 'meta', 'link', 'area', 'base', 'col', 'embed', 'source', 'track', 'wbr'])

/** Vindt elementen met een card-klasse die binnen een ander card-element staan.
 * Parser is quote-bewust (een `>` in een attribuutexpressie breekt de tag niet af)
 * en leest alleen het template-deel (geen `<`-vergelijkingen uit script). */
function gnesteCards(bron) {
  const t0 = bron.indexOf('<template>')
  const t1 = bron.lastIndexOf('</template>')
  if (t0 < 0) return []
  const tpl = bron.slice(t0, t1)
  const tags = [...tpl.matchAll(/<\/?([a-zA-Z][\w-]*)((?:"[^"]*"|'[^']*'|[^>"'])*)\/?>/g)]
  const stack = []
  let diepte = 0
  const overtreders = []
  for (const [vol, naam, attrs] of tags) {
    if (vol.startsWith('</')) {
      const top = stack.pop()
      if (top) diepte--
      continue
    }
    const zelfsluitend = vol.endsWith('/>') || VOID.has(naam.toLowerCase())
    const c = heeftCardKlasse(attrs || '')
    if (c && diepte > 0) overtreders.push(naam)
    if (!zelfsluitend) {
      stack.push(c)
      if (c) diepte++
    }
  }
  return overtreders
}

describe('werkvlak-grens — de wachter (LI048/LI050)', () => {
  it('een card binnen een card bestaat nergens — daar is de grens onzichtbaar (wit op wit)', () => {
    const bestanden = WORTELS.flatMap(vueBestanden)
    expect(bestanden.length).toBeGreaterThan(50) // luid falen als het bereik krimpt
    const overtreders = []
    for (const b of bestanden) {
      const genest = gnesteCards(fs.readFileSync(b, 'utf8'))
      if (genest.length) overtreders.push(`${path.basename(b)}: <${genest.join('>, <')}>`)
    }
    expect(
      overtreders,
      `genest vlak zonder grens — gebruik binnen een werkvlak het kader-patroon (lk-inhoudskader): ${overtreders.join('; ')}`,
    ).toEqual([])
  })

  it('de kader-klassen dragen hun rand: lk-inhoudskader (gewoon) en lk-tabvlak (sterk)', () => {
    const css = fs.readFileSync(path.resolve(__dirname, '../src/assets/main.css'), 'utf8')
    const kader = css.match(/\.lk-inhoudskader\s*\{([^}]*)\}/)?.[1] ?? ''
    const tabvlak = css.match(/\.lk-tabvlak\s*\{([^}]*)\}/)?.[1] ?? ''
    // Zonder deze regels verliest het kader zijn bestaansrecht: het IS de grens.
    expect(kader).toMatch(/border:\s*1px solid var\(--lk-color-border\)/)
    // Buitenrand van het werkvlak = de sterkste lijn op het scherm (LI048).
    expect(tabvlak).toMatch(/border:\s*1px solid var\(--lk-color-border-sterk\)/)
  })

  it('zelftest: de scan bijt op een nagebootste geneste card…', () => {
    const nep = '<template><div class="card"><ul><li class="card flex">x</li></ul></div></template>'
    expect(gnesteCards(nep)).toEqual(['li'])
  })

  it('…en slaat geen vals alarm op de substring in var(--lk-radius-card)', () => {
    const goed =
      '<template><div class="card"><span class="rounded-[var(--lk-radius-card)] border">popover</span></div></template>'
    expect(gnesteCards(goed)).toEqual([])
  })
})
