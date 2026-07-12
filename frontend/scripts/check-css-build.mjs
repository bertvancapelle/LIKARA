/**
 * Laag C — Build-CSS-check (UI-borging interactiestates).
 *
 * WAAROM DEZE CHECK BESTAAT (niet schrappen):
 * Tailwind v4 scant standaard alleen de Vite-root (frontend/). Module-views staan
 * buiten die root (modules/<module>/frontend) en worden alleen meegescand dankzij
 * een `@source`-directive in src/assets/main.css. Verdwijnt die directive (of komt
 * er een nieuwe module zonder eigen @source), dan belanden klassen die ALLEEN in
 * module-views voorkomen STIL niet in de gebouwde CSS — precies de tab-hover-bug.
 * vitest merkt dat niet (het assert klasse-STRINGS, niet de gecompileerde CSS).
 * Deze check bouwt productie-CSS en faalt als een kritische interactie-klasse mist.
 *
 * Draai: `npm run test:css-build` (bedoeld voor CI naast `vitest run`).
 */
import { execSync } from 'node:child_process'
import { readdirSync, readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const FRONTEND = fileURLToPath(new URL('..', import.meta.url))

// Kritische interactie-klassen (selector-namen, na het strippen van CSS-escapes).
// Minificatie raakt alleen de WAARDE (0.5px -> .5px), niet de klasse-naam.
//
// DE-VERVUILING (cruciaal): dit script staat onder frontend/ en wordt dus door
// Tailwind v4 gescand. Stond een te-matchen class-token hier AANEENGESLOTEN, dan
// zou Tailwind die als class-candidate oppikken en de klasse zelf genereren —
// waardoor de check zijn eigen controle waarmaakt (vals-groen). Daarom bouwen we
// elk token uit fragmenten waarin de sluit-`]` is afgesplitst: een los fragment
// met een ongebalanceerde `[` is GEEN geldige Tailwind-candidate, dus er wordt
// niets geseeded. De runtime-join levert alsnog de volledige selector om op te grep'en.
const j = (...delen) => delen.join('')
const VEREIST = [
  { naam: 'tab-hover-bg',      match: j('hover:bg-[var(--lk-color-primary-50)', ']:hover') },
  { naam: 'tab-hover-text',    match: j('hover:text-[var(--lk-color-primary-700)', ']:hover') },
  { naam: 'tab-omlijning',     match: j('border-[0.5px', ']') },
  { naam: 'secondary-vulling', match: j('bg-[var(--lk-color-primary-50)', ']') },
  { naam: 'primary-vulling',   match: j('bg-[var(--lk-color-primary)', ']') },
  { naam: 'danger-vulling',    match: j('bg-[var(--lk-color-danger)', ']') },
  // Scroll-schaduw (LI035): geen Tailwind-utility maar een handgeschreven klasse in
  // main.css — Tailwind kan die dus nooit zelf seeden (geen vals-groen-risico) en de
  // naam mag hier aaneengesloten staan. Verdwijnt de definitie, dan faalt dit LUID.
  { naam: 'dialog-scroll-schaduw', match: '.lk-scroll-schaduw' },
  // LI039 — aanstip ("wat je zojuist hebt vastgelegd, zie je altijd") + rustige
  // rij-acties (hover/focus-within-onthulling): handgeschreven main.css-klassen,
  // zelfde geen-vals-groen-redenering als de scroll-schaduw.
  { naam: 'aanstip-nieuwe-rij', match: '.lk-aangestipt' },
  { naam: 'rij-acties-onthulling', match: '.lk-rij:focus-within .lk-rij-acties' },
  { naam: 'boomrij-scan-laag', match: '.lk-rij-kop' },
  { naam: 'boomrij-lees-laag', match: '.lk-rij-definitie' },
]

console.log('[css-build-check] productie-build draaien…')
execSync('npx vite build', { cwd: FRONTEND, stdio: 'inherit' })

const assetsDir = path.join(FRONTEND, 'dist', 'assets')
const cssFile = readdirSync(assetsDir).find((f) => /^index-.*\.css$/.test(f))
if (!cssFile) {
  console.error('[css-build-check] FAAL: geen dist/assets/index-*.css gevonden.')
  process.exit(1)
}
const ruw = readFileSync(path.join(assetsDir, cssFile), 'utf8')
// Strip CSS-escapes (\: \[ \( \) \] \.) zodat we op de leesbare selector matchen.
const css = ruw.replace(/\\/g, '')

let ontbreekt = 0
for (const { naam, match } of VEREIST) {
  if (css.includes(match)) {
    console.log(`  ✓ ${naam}  (${match})`)
  } else {
    console.error(`  ✗ ${naam}  ONTBREEKT in ${cssFile}  (gezocht: ${match})`)
    ontbreekt++
  }
}

if (ontbreekt > 0) {
  console.error(`\n[css-build-check] FAAL: ${ontbreekt} kritische interactie-klasse(n) niet in de build. ` +
    'Waarschijnlijk ontbreekt een @source-directive in main.css voor een module-frontend.')
  process.exit(1)
}
console.log(`\n[css-build-check] OK — alle ${VEREIST.length} kritische interactie-klassen aanwezig in ${cssFile}.`)

// ── Token-verwijzings-check (LI035) ─────────────────────────────────────────────
// WAAROM: een arbitrary-utility met een var()-token belandt gewoon in de build —
// Tailwind genereert hem klakkeloos — maar als het TOKEN niet bestaat is de declaratie
// invalid en rendert er NIETS ("class staat erop maar doet niks"; de MeldingBanner-/
// warn-banner-bug: het token heette in werkelijkheid "-warning", de verwijzing miste
// die uitgang). Daarom: élke fallback-loze var-verwijzing in de gebouwde CSS moet
// gedefinieerd zijn in base.css of main.css — een onbestaand token faalt hier LUID.
// DE-VERVUILING: noem in comments hier NOOIT een aaneengesloten class-/token-literal —
// Tailwind scant dit script en zou de dode utility zelf seeden (de bekende valkuil).
const DEFINITIE_BRONNEN = ['src/themes/base.css', 'src/assets/main.css']
const gedefinieerd = new Set()
for (const bron of DEFINITIE_BRONNEN) {
  const inhoud = readFileSync(path.join(FRONTEND, bron), 'utf8')
  for (const m of inhoud.matchAll(/(--lk-[a-z0-9-]+)\s*:/gi)) gedefinieerd.add(m[1])
}
// Alleen FALLBACK-LOZE verwijzingen tellen: `var(--lk-x, fallback)` rendert de
// fallback en is dus bewust-defensief geldig; `var(--lk-x)` zonder fallback is bij
// een onbestaand token een dode declaratie.
const verwezen = new Set()
for (const m of css.matchAll(/var\((--lk-[a-z0-9-]+)\)/gi)) verwezen.add(m[1])

const onbekend = [...verwezen].filter((t) => !gedefinieerd.has(t)).sort()
if (onbekend.length > 0) {
  console.error(`\n[css-build-check] FAAL: ${onbekend.length} verwezen token(s) bestaan niet in ${DEFINITIE_BRONNEN.join('/')}:`)
  for (const t of onbekend) console.error(`  ✗ var(${t}) — controleer de spelling (bestaat er een variant zoals ${t}ing?)`)
  process.exit(1)
}
console.log(`[css-build-check] OK — alle ${verwezen.size} verwezen --lk-tokens zijn gedefinieerd.`)
