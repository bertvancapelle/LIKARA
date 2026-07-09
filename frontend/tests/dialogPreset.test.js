/**
 * Borging Dialog-primitive (LI035): vaste voetbalk + tweezijdige scroll-schaduw.
 *
 * Deze tests asserten de BRON (preset + main.css), niet de gecompileerde CSS —
 * de aanwezigheid van de klasse in de build borgt check-css-build.mjs (laag C).
 * De vier schaduw-toestanden (boven/midden/onder/past-alles) zijn geen JS-toestand
 * maar een CSS-mechanisme (background-attachment: local); hier wordt dat mechanisme
 * geborgd — de visuele uitkomst is browsercheck-terrein.
 */
import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import DialogPreset from '../src/presets/Dialog.js'

// cwd = frontend/ (vitest draait ALTIJD vanuit frontend/ — vaste projectnorm;
// import.meta.url is onder happy-dom geen file-URL, dus geen alternatief hier).
const mainCss = readFileSync(resolve(process.cwd(), 'src/assets/main.css'), 'utf8')

describe('Dialog-preset — scroll-structuur (vaste kop + voetbalk)', () => {
  const root = DialogPreset.root.class.join(' ')
  const content = DialogPreset.content.class.join(' ')

  it('de dialoog past binnen de viewport met marge en alléén de inhoud scrolt', () => {
    // Root: kolom-flex met hoogte-kader; 10vh boven + max 80vh = altijd marge rondom.
    expect(root).toContain('flex flex-col')
    expect(root).toContain('max-h-[80vh]')
    expect(root).toContain('mt-[10vh]')
    // Content: hét scroll-gebied, mét krimpgarantie. Zonder min-h-0 weigert het
    // flex-item kleiner te worden dan zijn inhoud en duwt lange inhoud de voetbalk
    // (het #footer-slot) uit het kader — precies de 4b-browserbevinding.
    expect(content).toContain('overflow-y-auto')
    expect(content).toContain('min-h-0')
    // Eigen padding: veldranden en focus-ringen clippen niet tegen de scrollrand.
    expect(content).toContain('px-6')
  })

  it('het content-gebied draagt de scroll-schaduw en die klasse bestaat in main.css', () => {
    expect(content).toContain('lk-scroll-schaduw')
    expect(mainCss).toContain('.lk-scroll-schaduw')
  })
})

describe('scroll-schaduw-patroon — vier toestanden via background-attachment', () => {
  const blok = mainCss.slice(mainCss.indexOf('.lk-scroll-schaduw'))
  const declaratie = blok.slice(0, blok.indexOf('}'))

  it('twee mee-scrollende dekkers + twee vaste schaduwen (local,local,scroll,scroll)', () => {
    // Dit is het hele mechanisme: bovenaan gescrold → bovendekker bedekt de
    // bovenschaduw (alleen onder zichtbaar); onderaan → omgekeerd; middenin →
    // beide schaduwen; past alles → beide bedekt. Volgorde en aantal zijn dus
    // betekenisvol — dekkers éérst (local), schaduwen daarna (scroll).
    expect(declaratie).toMatch(/background-attachment:\s*local,\s*local,\s*scroll,\s*scroll/)
    expect(declaratie.match(/linear-gradient/g)).toHaveLength(2) // boven- + onderdekker
    expect(declaratie.match(/radial-gradient/g)).toHaveLength(2) // boven- + onderschaduw
  })

  it('de schaduw is getint op het primaire LIKARA-blauw (steunkleur, niet grijs)', () => {
    // Beide schaduwlagen mengen het primaire token subtiel naar transparant;
    // de fallback-loze var()-verwijzing wordt door de token-check bewaakt.
    const schaduwen = declaratie.match(/color-mix\(in srgb, var\(--lk-color-primary\) \d+%, transparent\)/g)
    expect(schaduwen).toHaveLength(2)
  })

  it('dekkers zijn groter dan de schaduwen (schaduw valt in ruststand volledig weg)', () => {
    const maten = declaratie.match(/background-size:\s*([^;]+);/)
    expect(maten).not.toBe(null)
    const [dekkerBoven, dekkerOnder, schaduwBoven, schaduwOnder] = maten[1]
      .split(',')
      .map((m) => parseInt(m.trim().split(/\s+/)[1], 10))
    expect(dekkerBoven).toBeGreaterThan(schaduwBoven)
    expect(dekkerOnder).toBeGreaterThan(schaduwOnder)
  })
})
