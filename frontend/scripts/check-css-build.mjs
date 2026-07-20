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
  // LI047 — kop-met-uitleg-rij: de margeneutralisatie is het hele punt van de klasse.
  // Sneuvelt juist die regel, dan zakt het icoon weer stilletjes 6px — dus toetsen we
  // de nakomeling-selector, niet alleen de klassenaam.
  { naam: 'kop-rij-margeneutralisatie', match: '.lk-kop-rij>:is(h1,h2)' },
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

// ── LI040: detailkop-bron-scan — de acties horen bij het object, niet bij het einde
// van de pagina. Elk detailscherm (bestandsnaam bevat 'Detail'; de bouwsteen zelf
// uitgezonderd) MOET de gedeelde DetailKop gebruiken, en de OBJECT-acties — de
// Bewerken-/Verwijderen-knop en de Geschiedenis-ingang (ObjectHistoriePaneel) — mogen
// UITSLUITEND binnen dat DetailKop-blok staan. Een eigen actiebalk (onderaan, in het
// midden, of als tweede kop) is daarmee structureel onmogelijk i.p.v. een afspraak.
// Sectie-acties ("+ Lid koppelen", rij-"Ontkoppelen", dialoog-"Definitief
// verwijderen") matchen deze exacte labels niet en blijven vrij in hun sectie.
function scanDetailkopOvertredingen(bron, label) {
  const overtredingen = []
  const tmpl = /<template>([\s\S]*)<\/template>/.exec(bron)
  if (!tmpl) return overtredingen
  const t = tmpl[1].replace(/<!--[\s\S]*?-->/g, '')
  const kopStart = t.indexOf('<DetailKop')
  if (kopStart < 0) {
    overtredingen.push(`${label}: detailscherm zonder <DetailKop> — elk detailscherm is consument van de bouwsteen`)
    return overtredingen
  }
  const kopEinde = t.indexOf('</DetailKop>', kopStart)
  if (kopEinde < 0) {
    overtredingen.push(`${label}: <DetailKop> zonder sluittag`)
    return overtredingen
  }
  const OBJECT_ACTIES = ['<ObjectHistoriePaneel', 'label="Bewerken"', 'label="Verwijderen"']
  // LI046 slice 2 (besluit B, randvoorwaarde 3) — de ENIGE toegestane Bewerken-knop buiten
  // de kop: de veld-anker-knop náást een via ?veld= gemarkeerd Overzicht-veld. Herkenbaar
  // aan zijn vaste testid; hij roept dezelfde kop-actie aan (naarBewerken), geen tweede
  // actiebalk. Elke andere knop buiten de kop blijft een overtreding.
  const VELD_ANKER_KNOP = 'data-testid="veld-bewerk-knop"'
  for (const naald of OBJECT_ACTIES) {
    let idx = t.indexOf(naald)
    while (idx >= 0) {
      if (idx < kopStart || idx > kopEinde) {
        const tag = t.slice(t.lastIndexOf('<', idx), t.indexOf('>', idx) + 1)
        if (!tag.includes(VELD_ANKER_KNOP)) {
          overtredingen.push(`${label}: object-actie ${naald} staat buiten de DetailKop — acties horen bij het object (in de kop)`)
        }
      }
      idx = t.indexOf(naald, idx + 1)
    }
  }
  return overtredingen
}

// Zelftest — bewijs dat de detailkop-scan bijt, bij élke run: (a) een detailscherm
// zonder DetailKop wordt gevangen, (b) een Bewerken-knop buiten de kop wordt gevangen,
// (c) een geldig scherm passeert, (d) sectie-/dialoog-labels ("Definitief verwijderen",
// "+ Lid koppelen") triggeren niet, (e) een ObjectHistoriePaneel buiten de kop wordt gevangen.
const KOP_ZELFTEST = [
  { naam: 'zonder-detailkop-gevangen', verwacht: 1, bron: '<template><h1>X</h1><Button label="Bewerken" /></template>' },
  {
    naam: 'bewerken-buiten-kop-gevangen', verwacht: 1,
    bron: '<template><DetailKop naam="X"></DetailKop><div><Button label="Bewerken" /></div></template>',
  },
  {
    naam: 'geldig-scherm-passeert', verwacht: 0,
    bron: '<template><DetailKop naam="X"><Button label="Bewerken" /><ObjectHistoriePaneel /><Button label="Verwijderen" /></DetailKop><Button label="Definitief verwijderen" /></template>',
  },
  {
    naam: 'sectie-acties-triggeren-niet', verwacht: 0,
    bron: '<template><DetailKop naam="X"></DetailKop><Button label="+ Lid koppelen" /><Button label="Ontkoppelen" /></template>',
  },
  {
    naam: 'historie-buiten-kop-gevangen', verwacht: 1,
    bron: '<template><DetailKop naam="X"></DetailKop><ObjectHistoriePaneel /></template>',
  },
  // LI046 slice 2 — de veld-anker-knop (herkenbaar testid) is de ene toegestane
  // uitzondering; een gewone knop ernaast blijft gevangen (de uitzondering lekt niet).
  {
    naam: 'veld-anker-knop-passeert', verwacht: 0,
    bron: '<template><DetailKop naam="X"></DetailKop><Button label="Bewerken" data-testid="veld-bewerk-knop" /></template>',
  },
  {
    naam: 'veld-anker-uitzondering-lekt-niet', verwacht: 1,
    bron: '<template><DetailKop naam="X"></DetailKop><Button label="Bewerken" data-testid="veld-bewerk-knop" /><Button label="Bewerken" /></template>',
  },
]
let kopZelftestFouten = 0
for (const { naam, verwacht, bron } of KOP_ZELFTEST) {
  const n = scanDetailkopOvertredingen(bron, 'zelftest').length
  if (n !== verwacht) {
    console.error(`  ✗ zelftest "${naam}": ${n} overtreding(en), verwacht ${verwacht} — de detailkop-scan bijt niet zoals bedoeld`)
    kopZelftestFouten++
  }
}
if (kopZelftestFouten > 0) {
  console.error('\n[css-build-check] FAAL: de detailkop-bron-scan doorstaat zijn eigen zelftest niet.')
  process.exit(1)
}
console.log(`[css-build-check] OK — detailkop-scan-zelftest: ${KOP_ZELFTEST.length}/${KOP_ZELFTEST.length} (de scan bijt).`)

let kopOvertredingen = []
let detailGescand = 0
for (const wortel of SCAN_WORTELS) {
  for (const bestand of vueBestanden(path.join(FRONTEND, wortel))) {
    const naam = path.basename(bestand)
    if (!naam.includes('Detail') || naam === 'DetailKop.vue') continue
    detailGescand++
    kopOvertredingen = kopOvertredingen.concat(
      scanDetailkopOvertredingen(readFileSync(bestand, 'utf8'), path.relative(FRONTEND, bestand)),
    )
  }
}
if (kopOvertredingen.length > 0) {
  console.error(`\n[css-build-check] FAAL: ${kopOvertredingen.length} detailkop-afwijking(en):`)
  for (const o of kopOvertredingen) console.error(`  ✗ ${o}`)
  console.error('De acties horen bij het object: gebruik de DetailKop-bouwsteen (src/components/DetailKop.vue) — geen eigen actiebalk.')
  process.exit(1)
}
console.log(`[css-build-check] OK — detailkop-scan: ${detailGescand} detailschermen op de bouwsteen (object-acties in de kop).`)

// ── LI047: kopstijl-bron-scan — één maat voor de paginatitel ────────────────────────────────
// Tailwind-preflight zet h1..h6 op `font-size: inherit; font-weight: inherit`; de basislaag
// (assets/main.css) herstelt maat + gewicht. Dáár leeft de kopstijl — een scherm dat 'm zelf
// zet negeert de bron, óók als het toevallig dezelfde maat kiest. Zo ontstond het verschil dat
// het beheer als een ander product liet lezen: 30 h1's, 17 op 2xl en 13 op xl.
// Meerregelig-bewust: een h1-tag die over vier regels loopt (DetailKop) moet net zo hard worden
// gevangen als een eenregelige — een regel-gebaseerde lezing zat er eerder tien mis.
const KOPSTIJL_TAG = /<(h[12])\b/g
const KOPSTIJL_VERBODEN = /^(?:text-\[length:var\(--lk-text-[a-z0-9]+\)\]|font-(?:thin|extralight|light|normal|medium|semibold|bold|extrabold|black))$/

function scanKopstijlOvertredingen(bron, label) {
  const overtredingen = []
  const tmpl = /<template>([\s\S]*)<\/template>/.exec(bron)
  if (!tmpl) return overtredingen
  const t = tmpl[1].replace(/<!--[\s\S]*?-->/g, '') // HTML-comments tellen niet
  KOPSTIJL_TAG.lastIndex = 0
  let m
  while ((m = KOPSTIJL_TAG.exec(t)) !== null) {
    const einde = vindTagEinde(t, m.index)
    if (einde < 0) continue
    const tag = t.slice(m.index, einde)
    const regel = bron.slice(0, bron.indexOf(tag)).split('\n').length
    const clsM = /(?<![:-])class="([^"]*)"/.exec(tag)
    if (!clsM) continue
    for (const k of clsM[1].split(/\s+/).filter(Boolean)) {
      if (KOPSTIJL_VERBODEN.test(k)) {
        overtredingen.push(`${label}:${regel} <${m[1]}> zet een eigen titelmaat/-gewicht: "${k}"`)
      }
    }
  }
  return overtredingen
}

// Zelftest — bewijs dat de scan bijt, bij ÉLKE run: (a) een eigen maat wordt gevangen, ook als
// het de JUISTE maat is (een scherm dat 24px hardcodeert negeert de bron evengoed); (b) een eigen
// gewicht wordt gevangen; (c) een kop die alleen kleur/positionering draagt passeert; (d) een
// MEERREGELIGE tag wordt gelezen (de val waar de eerste telling tien mis zat); (e) een h1 in een
// HTML-comment telt niet; (f) een `text-[var(--lk-color-…)]` is kleur, geen maat — geen vals alarm.
const KOPSTIJL_ZELFTEST = [
  { naam: 'eigen-maat-gevangen', verwacht: 1, bron: '<template><h1 class="text-[length:var(--lk-text-xl)]">X</h1></template>' },
  { naam: 'juiste-maat-óók-gevangen', verwacht: 1, bron: '<template><h1 class="text-[length:var(--lk-text-2xl)]">X</h1></template>' },
  { naam: 'eigen-gewicht-gevangen', verwacht: 1, bron: '<template><h2 class="font-semibold">X</h2></template>' },
  { naam: 'kleur-en-positie-passeren', verwacht: 0, bron: '<template><h1 class="min-w-0 break-words text-[var(--lk-color-primary)]">X</h1></template>' },
  {
    naam: 'meerregelige-tag-gevangen', verwacht: 2,
    bron: '<template><h1\n  :id="t"\n  class="text-[length:var(--lk-text-2xl)] font-semibold"\n  data-testid="x"\n>{{ n }}</h1></template>',
  },
  { naam: 'comment-telt-niet', verwacht: 0, bron: '<template><!-- <h1 class="font-bold">X</h1> --><p /></template>' },
  { naam: 'kleur-token-geen-vals-alarm', verwacht: 0, bron: '<template><h2 class="text-[var(--lk-color-text-muted)]">X</h2></template>' },
]
let kopstijlZelftestFouten = 0
for (const { naam, verwacht, bron } of KOPSTIJL_ZELFTEST) {
  const n = scanKopstijlOvertredingen(bron, 'zelftest').length
  if (n !== verwacht) {
    console.error(`  ✗ zelftest "${naam}": ${n} overtreding(en), verwacht ${verwacht} — de kopstijl-scan bijt niet zoals bedoeld`)
    kopstijlZelftestFouten++
  }
}
if (kopstijlZelftestFouten > 0) {
  console.error('\n[css-build-check] FAAL: de kopstijl-bron-scan doorstaat zijn eigen zelftest niet.')
  process.exit(1)
}
console.log(`[css-build-check] OK — kopstijl-scan-zelftest: ${KOPSTIJL_ZELFTEST.length}/${KOPSTIJL_ZELFTEST.length} (de scan bijt).`)

// ── LI047: kop-rij-bron-scan — de "i" hoort bij zijn kop ────────────────────────────────────
// Een kop draagt een ondermarge; in een `items-center`-rij centreert `align-items` de MARGEbox
// mee, waardoor het uitleg-icoon precies een halve ondermarge te laag hangt (h2: 6px). Acht
// schermen bouwden die rij met de hand na, dus stond hij overal even scheef. De rij leeft nu op
// één plek (.lk-kop-rij, assets/main.css). Regel: staat een <VeldUitleg> als DIRECTE broer van
// een <h1>/<h2>, dan moet hun gezamenlijke ouder .lk-kop-rij dragen.
// Directe-broer is het juiste criterium: alleen dán delen ze een flex-regel. Een VeldUitleg die
// dieper genest zit (bv. naast een veldlabel in een sectie die óók een kop heeft) staat niet in
// die regel en hoort niet gevangen te worden — vandaar de diepte-telling i.p.v. regel-nabijheid.
const KOPRIJ_TAG = /<\/?([A-Za-z][\w.-]*)/g
const KOPRIJ_VOID = new Set(['br', 'hr', 'img', 'input', 'meta', 'link', 'source', 'area', 'base', 'col', 'embed', 'param', 'track', 'wbr'])

function scanKoprijOvertredingen(bron, label) {
  const overtredingen = []
  const tmpl = /<template>([\s\S]*)<\/template>/.exec(bron)
  if (!tmpl) return overtredingen
  const t = tmpl[1].replace(/<!--[\s\S]*?-->/g, '') // HTML-comments tellen niet
  const stapel = []
  KOPRIJ_TAG.lastIndex = 0
  let m
  while ((m = KOPRIJ_TAG.exec(t)) !== null) {
    const naam = m[1]
    if (t[m.index + 1] === '/') {
      // Sluittag: rol af tot en met het bijpassende open element.
      for (let i = stapel.length - 1; i >= 0; i--) {
        if (stapel[i].naam !== naam) continue
        const el = stapel[i]
        stapel.length = i
        if (el.kop && el.uitleg && !el.klassen.includes('lk-kop-rij')) {
          overtredingen.push(
            `${label}:${el.regel} <${el.naam}> zet een kop en een VeldUitleg naast elkaar zonder .lk-kop-rij — het icoon hangt dan een halve kopmarge te laag`,
          )
        }
        break
      }
      continue
    }
    const einde = vindTagEinde(t, m.index)
    if (einde < 0) continue
    const tag = t.slice(m.index, einde)
    const ouder = stapel[stapel.length - 1]
    if (ouder) {
      if (/^h[12]$/.test(naam)) ouder.kop = true
      if (naam === 'VeldUitleg') ouder.uitleg = true
    }
    if (!/\/>\s*$/.test(tag) && !KOPRIJ_VOID.has(naam.toLowerCase())) {
      const clsM = /(?<![:-])class="([^"]*)"/.exec(tag)
      stapel.push({
        naam,
        klassen: clsM ? clsM[1].split(/\s+/).filter(Boolean) : [],
        kop: false,
        uitleg: false,
        regel: bron.slice(0, bron.indexOf(tag)).split('\n').length,
      })
    }
    KOPRIJ_TAG.lastIndex = einde // attributen niet opnieuw als tag lezen
  }
  return overtredingen
}

// Zelftest — bewijs dat de scan bijt, bij ÉLKE run: (a) een kop-rij zonder de klasse wordt
// gevangen; (b) mét de klasse passeert; (c) een VeldUitleg zonder kop-broer (het gewone geval,
// 52 van de 60 plekken) geeft geen vals alarm; (d) een MEERREGELIGE containertag wordt gelezen;
// (e) genest telt niet als broer — kop in de buitenste div, uitleg in een binnenste; (f) een
// kop-rij in een HTML-comment telt niet; (g) twee kop-rijen fout in één bestand → twee meldingen.
const KOPRIJ_ZELFTEST = [
  { naam: 'koprij-zonder-klasse-gevangen', verwacht: 1, bron: '<template><div class="flex items-center"><h2>X</h2><VeldUitleg veld="a" /></div></template>' },
  { naam: 'koprij-met-klasse-passeert', verwacht: 0, bron: '<template><div class="lk-kop-rij gap-2"><h2>X</h2><VeldUitleg veld="a" /></div></template>' },
  { naam: 'uitleg-zonder-kop-geen-vals-alarm', verwacht: 0, bron: '<template><div class="flex items-center"><label>X</label><VeldUitleg veld="a" /></div></template>' },
  {
    naam: 'meerregelige-containertag-gelezen', verwacht: 1,
    bron: '<template><div\n  :id="x"\n  class="flex items-center gap-[var(--lk-space-md)]"\n><h1>X</h1><VeldUitleg veld="a" /></div></template>',
  },
  { naam: 'genest-telt-niet-als-broer', verwacht: 0, bron: '<template><div class="card"><h2>X</h2><div class="flex"><label>L</label><VeldUitleg veld="a" /></div></div></template>' },
  { naam: 'comment-telt-niet', verwacht: 0, bron: '<template><!-- <div class="flex"><h2>X</h2><VeldUitleg veld="a" /></div> --><p /></template>' },
  {
    naam: 'twee-fouten-twee-meldingen', verwacht: 2,
    bron: '<template><div><div class="flex"><h2>A</h2><VeldUitleg veld="a" /></div><div class="flex"><h2>B</h2><VeldUitleg veld="b" /></div></div></template>',
  },
]
let koprijZelftestFouten = 0
for (const { naam, verwacht, bron } of KOPRIJ_ZELFTEST) {
  const n = scanKoprijOvertredingen(bron, 'zelftest').length
  if (n !== verwacht) {
    console.error(`  ✗ zelftest "${naam}": ${n} overtreding(en), verwacht ${verwacht} — de kop-rij-scan bijt niet zoals bedoeld`)
    koprijZelftestFouten++
  }
}
if (koprijZelftestFouten > 0) {
  console.error('\n[css-build-check] FAAL: de kop-rij-bron-scan doorstaat zijn eigen zelftest niet.')
  process.exit(1)
}
console.log(`[css-build-check] OK — kop-rij-scan-zelftest: ${KOPRIJ_ZELFTEST.length}/${KOPRIJ_ZELFTEST.length} (de scan bijt).`)

let kopstijlOvertredingen = []
let koprijOvertredingen = []
let koprijGescand = 0
let kopstijlGescand = 0
for (const wortel of SCAN_WORTELS) {
  for (const bestand of vueBestanden(path.join(FRONTEND, wortel))) {
    const bron = readFileSync(bestand, 'utf8')
    if (/<VeldUitleg\b/.test(bron)) {
      koprijGescand++
      koprijOvertredingen = koprijOvertredingen.concat(
        scanKoprijOvertredingen(bron, path.relative(FRONTEND, bestand)),
      )
    }
    if (!/<h[12]\b/.test(bron)) continue
    kopstijlGescand++
    kopstijlOvertredingen = kopstijlOvertredingen.concat(
      scanKopstijlOvertredingen(bron, path.relative(FRONTEND, bestand)),
    )
  }
}
if (koprijOvertredingen.length > 0) {
  console.error(`\n[css-build-check] FAAL: ${koprijOvertredingen.length} kop-rij-afwijking(en):`)
  for (const o of koprijOvertredingen) console.error(`  ✗ ${o}`)
  console.error('De kop-met-uitleg-rij leeft in de componentenlaag (src/assets/main.css, .lk-kop-rij) — bouw hem niet per scherm na.')
  process.exit(1)
}
console.log(`[css-build-check] OK — kop-rij-scan: ${koprijGescand} schermen met uitleg-iconen, elke kop-met-uitleg op de gedeelde rij.`)
if (kopstijlOvertredingen.length > 0) {
  console.error(`\n[css-build-check] FAAL: ${kopstijlOvertredingen.length} kopstijl-afwijking(en):`)
  for (const o of kopstijlOvertredingen) console.error(`  ✗ ${o}`)
  console.error('De titelmaat leeft in de basislaag (src/assets/main.css) — zet hem niet per scherm.')
  process.exit(1)
}
console.log(`[css-build-check] OK — kopstijl-scan: ${kopstijlGescand} schermen met koppen, allemaal op de gedeelde maat.`)
