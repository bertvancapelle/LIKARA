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
  // LI040 — veldbouwsteen: handgeschreven main.css-klassen (geen vals-groen-risico).
  { naam: 'veldbouwsteen', match: '.lk-veld' },
  { naam: 'veldbouwsteen-tekstvlak', match: '.lk-veld-tekstvlak' },
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

// ── Bron-scan veldbouwsteen (LI040) ─────────────────────────────────────────────
// WAAROM: het veld-recept (hoogte/padding/rand/radius/achtergrond/focus/font-size)
// leeft UITSLUITEND in de veldbouwsteen (main.css). Vóór LI040 zetten 136 van de 183
// velden hun eigen recept per call-site — vier verschillende hoogtes, drie in één
// dialoog. Deze scan maakt herhaling structureel onmogelijk: elke input/select/
// textarea in een view MOET de bouwsteen-klasse dragen en MAG geen recept-klassen
// zetten. Layout blijft vrij per call-site (w-*, min-w-*, flex*, pr-*/pl-* voor
// icoon-ruimte, text-left/-right).
//
// PARSER-LESSEN (uit het LI040-checkpoint — beide gaven daar vals-positieven):
// 1. alleen het <template>-blok scannen (een veld-tag in een script-comment telt niet);
// 2. quote-bewust tot de sluitende '>' lezen (een '=>' in een inline handler
//    beëindigt de tag niet). Een scan die vals alarm slaat wordt genegeerd.
const VELD_TAG = /<(input|select|textarea)\b/g
const VELD_SKIP_TYPES = new Set(['checkbox', 'radio', 'hidden', 'range', 'file', 'submit', 'button'])
// Prefix-verboden op veld-tags: het recept. (`pr-`/`pl-` matchen 'px-'/'py-' niet.)
const VELD_VERBODEN_PREFIX = ['h-', 'py-', 'px-', 'border', 'rounded', 'bg-', 'focus:', 'disabled:', 'text-[length:']

function vindTagEinde(tekst, start) {
  let quote = null
  for (let i = start; i < tekst.length; i++) {
    const c = tekst[i]
    if (quote) { if (c === quote) quote = null }
    else if (c === '"' || c === "'") quote = c
    else if (c === '>') return i + 1
  }
  return -1
}

function scanVeldOvertredingen(bron, label) {
  const overtredingen = []
  const tmpl = /<template>([\s\S]*)<\/template>/.exec(bron)
  if (!tmpl) return overtredingen
  const t = tmpl[1].replace(/<!--[\s\S]*?-->/g, '') // HTML-comments tellen niet
  VELD_TAG.lastIndex = 0
  let m
  while ((m = VELD_TAG.exec(t)) !== null) {
    const einde = vindTagEinde(t, m.index)
    if (einde < 0) continue
    const tag = t.slice(m.index, einde)
    const typeM = /type="([^"]*)"/.exec(tag)
    if (typeM && VELD_SKIP_TYPES.has(typeM[1])) continue
    const regel = bron.slice(0, bron.indexOf(tag)).split('\n').length
    const clsM = /(?<![:-])class="([^"]*)"/.exec(tag)
    const klassen = clsM ? clsM[1].split(/\s+/).filter(Boolean) : []
    if (!klassen.includes('lk-veld') && !klassen.includes('lk-veld-tekstvlak')) {
      overtredingen.push(`${label}:${regel} <${m[1]}> mist de veldbouwsteen-klasse`)
    }
    for (const k of klassen) {
      if (VELD_VERBODEN_PREFIX.some((p) => k.startsWith(p))) {
        overtredingen.push(`${label}:${regel} <${m[1]}> zet een eigen veld-recept: "${k}"`)
      }
    }
  }
  return overtredingen
}

// Zelftest — bewijs dat de scan bijt, bij ÉLKE run: (a) een eigen recept wordt
// gevangen, (b) een ontbrekende bouwsteen-klasse wordt gevangen, (c) een geldig veld
// passeert, (d) een veld-tag in een script-comment telt niet (vals-positief-les),
// (e) een multi-line tag met '=>' in een handler wordt correct gelezen.
const ZELFTEST = [
  { naam: 'eigen-recept-gevangen', verwacht: 1, bron: '<template><input class="lk-veld py-2" /></template>' },
  { naam: 'bouwsteen-verplicht', verwacht: 1, bron: '<template><select class="w-full"></select></template>' },
  { naam: 'geldig-veld-passeert', verwacht: 0, bron: '<template><input class="lk-veld w-full pr-7" /></template>' },
  { naam: 'script-comment-telt-niet', verwacht: 0, bron: '<template><p /></template><script>// een <select> in een comment</script>' },
  {
    // 2 verwacht: het eigen recept (h-10) ÉN de ontbrekende bouwsteen-klasse — de
    // '=>' en de "'>'" in de handler mogen de tag-lezing niet afbreken.
    naam: 'multiline-met-pijl-handler', verwacht: 2,
    bron: '<template><input\n  :aria-label="x"\n  @keydown="(e) => e.key === \'>\' && f()"\n  class="h-10"\n/></template>',
  },
]
let zelftestFouten = 0
for (const { naam, verwacht, bron } of ZELFTEST) {
  const n = scanVeldOvertredingen(bron, 'zelftest').length
  if (n !== verwacht) {
    console.error(`  ✗ zelftest "${naam}": ${n} overtreding(en), verwacht ${verwacht} — de scan bijt niet zoals bedoeld`)
    zelftestFouten++
  }
}
if (zelftestFouten > 0) {
  console.error('\n[css-build-check] FAAL: de veld-bron-scan doorstaat zijn eigen zelftest niet.')
  process.exit(1)
}
console.log(`[css-build-check] OK — veld-bron-scan-zelftest: ${ZELFTEST.length}/${ZELFTEST.length} (de scan bijt).`)

const SCAN_WORTELS = ['src', '../modules/bwb_ontvlechting/frontend']
function vueBestanden(dir) {
  const uit = []
  for (const naam of readdirSync(dir, { withFileTypes: true })) {
    const vol = path.join(dir, naam.name)
    if (naam.isDirectory()) uit.push(...vueBestanden(vol))
    else if (naam.name.endsWith('.vue') && !naam.name.includes('.test.')) uit.push(vol)
  }
  return uit
}
let veldOvertredingen = []
let gescand = 0
for (const wortel of SCAN_WORTELS) {
  for (const bestand of vueBestanden(path.join(FRONTEND, wortel))) {
    gescand++
    veldOvertredingen = veldOvertredingen.concat(
      scanVeldOvertredingen(readFileSync(bestand, 'utf8'), path.relative(FRONTEND, bestand)),
    )
  }
}
if (veldOvertredingen.length > 0) {
  console.error(`\n[css-build-check] FAAL: ${veldOvertredingen.length} veld(en) wijken af van de veldbouwsteen:`)
  for (const o of veldOvertredingen) console.error(`  ✗ ${o}`)
  console.error('Het veld-recept leeft in .lk-veld / .lk-veld-tekstvlak (main.css) — zet geen eigen hoogte/padding/rand/radius/achtergrond/focus op een veld.')
  process.exit(1)
}
console.log(`[css-build-check] OK — veld-bron-scan: 0 afwijkingen in ${gescand} views (alle velden op de bouwsteen).`)
