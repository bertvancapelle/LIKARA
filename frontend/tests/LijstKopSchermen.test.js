/**
 * De belofte van regel 3, over de schermen HEEN (LI048 snede 2).
 *
 * Elke suite hierboven kijkt naar één scherm. Maar de belofte is juist een vergelijking: de
 * consultant loopt van Componenten naar Plateaus naar Auditlog, en de aanmaakknop moet elke keer
 * op dezelfde plek staan. Dat is per definitie onzichtbaar in een toets die één scherm mount —
 * en daarom staat deze hier apart.
 *
 * Er wordt geen enkel scherm gemount: dit leest de bronbestanden. Dat is bewust. De vraag is niet
 * "rendert dit scherm goed?" maar "gebruiken al deze schermen dezelfde bouwsteen op dezelfde
 * manier?" — een structuurvraag, en de bouwsteen zelf is elders (LijstKop.test.js) al op gedrag
 * getoetst.
 */
import { readFileSync } from 'node:fs'
import path from 'node:path'
import { describe, expect, it } from 'vitest'

// `import.meta.url` is onder de happy-dom-omgeving géén file:-URL (fileURLToPath gooit dan),
// dus het anker is de vitest-root: frontend/.
const FRONTEND = process.cwd()

/** Leest de menu-routes en levert per hoofdmenu-lijstscherm zijn bron. Zelfde afleiding als de
 *  bronscan in scripts/check-css-build.mjs — het bereik komt uit het menu, niet uit een lijst. */
function hoofdmenuLijstschermen() {
  const layout = readFileSync(path.join(FRONTEND, 'src/layouts/AppLayout.vue'), 'utf8')
  const router = readFileSync(path.join(FRONTEND, 'src/router/index.js'), 'utf8')
  const routes = [...layout.matchAll(/:to="\{\s*name:\s*'([^']+)'/g)].map((m) => m[1])
  const perRoute = new Map(
    [...router.matchAll(/name:\s*'([^']+)',\s*component:\s*([A-Za-z0-9_]+)/g)].map((m) => [m[1], m[2]]),
  )
  const perComponent = new Map(
    [...router.matchAll(/const\s+([A-Za-z0-9_]+)\s*=\s*\(\)\s*=>\s*import\('([^']+)'\)/g)]
      .map((m) => [m[1], m[2]]),
  )
  const uit = []
  for (const route of routes) {
    const rel = perComponent.get(perRoute.get(route))
    if (!rel) continue
    const vol = rel.startsWith('@modules/') ? path.join(FRONTEND, '..', rel.slice(1))
      : rel.startsWith('@/') ? path.join(FRONTEND, 'src', rel.slice(2))
      : path.resolve(path.join(FRONTEND, 'src/router'), rel)
    const bron = readFileSync(vol, 'utf8')
    const tmpl = /<template>([\s\S]*)<\/template>/.exec(bron)
    if (!tmpl) continue
    const t = tmpl[1].replace(/<!--[\s\S]*?-->/g, '')
    if (/role="tab"|<AppTabs/.test(t)) continue
    if (!/<DataTable|<table/.test(t) && !t.includes('<LijstKop')) continue
    uit.push({ route, template: t, naam: path.basename(vol) })
  }
  return uit
}

const SCHERMEN = hoofdmenuLijstschermen()

describe('De lijstkop over alle hoofdmenu-schermen heen', () => {
  it('vindt alle veertien schermen (anders klopt de inventarisatie niet)', () => {
    // Zakt dit getal, dan is er een scherm uit het bereik gevallen — precies het stille
    // smaller-worden waar deze snede twee keer tegenaan liep (een niet-geresolvede alias, en
    // een boom-scherm zonder tabel). Dan is het een bevinding, geen bij te werken getal.
    expect(SCHERMEN.length).toBe(14)
  })

  it('elk scherm draagt de gedeelde bouwsteen, geen handgebouwde kop', () => {
    const zonder = SCHERMEN.filter((s) => !s.template.includes('<LijstKop')).map((s) => s.naam)
    expect(zonder).toEqual([])
  })

  it('geen scherm heeft meer dan één zoekveld', () => {
    const dubbel = SCHERMEN
      .map((s) => [s.naam, (s.template.match(/type="search"/g) || []).length])
      .filter(([, n]) => n > 1)
    expect(dubbel).toEqual([])
  })

  it('DE BELOFTE: de aanmaakactie staat overal in de kop, nooit erbuiten', () => {
    // Dit is regel 3 en het is de reden dat zoekloze schermen meedoen. Een aanmaakactie die
    // buiten de kop staat, staat per definitie ergens anders dan op de andere dertien schermen
    // — en dan moet de consultant hem per scherm opnieuw zoeken.
    const AANMAAK = /label="(\+ )?(Nieuw|Nieuwe|Gebruiker toevoegen)[^"]*"/g
    const fout = []
    for (const { naam, template } of SCHERMEN) {
      const kopStart = template.indexOf('<LijstKop')
      const tagEinde = template.indexOf('>', kopStart)
      const zelfsluitend = template[tagEinde - 1] === '/'
      const kopEinde = zelfsluitend ? tagEinde : template.indexOf('</LijstKop>', kopStart)
      for (const m of template.matchAll(AANMAAK)) {
        if (m.index < kopStart || m.index > kopEinde) fout.push(`${naam}: ${m[0]}`)
      }
    }
    expect(fout).toEqual([])
  })

  it('geen scherm zet een tweede paginakop onder de lijstkop', () => {
    const fout = []
    for (const { naam, template } of SCHERMEN) {
      const kopStart = template.indexOf('<LijstKop')
      const tagEinde = template.indexOf('>', kopStart)
      const zelfsluitend = template[tagEinde - 1] === '/'
      const kopEinde = zelfsluitend ? tagEinde : template.indexOf('</LijstKop>', kopStart)
      for (const m of template.matchAll(/<h1/g)) {
        if (m.index < kopStart || m.index > kopEinde) fout.push(naam)
      }
    }
    expect(fout).toEqual([])
  })

  it('Migratienorm houdt zijn toelichting, ONDER de kop', () => {
    // Deze tekst is geen extra informatie maar de sleutel tot het scherm: de consultant bepaalt
    // hier wat er straks bij élk component als verplicht verschijnt, en dat is te ingrijpend om
    // op een gok te doen. Hij mag dus niet achter een uitleg-"i" verdwijnen en niet in de kop
    // belanden. `max-w-prose` houdt hem smal — het is een alinea, geen kop.
    //
    // NB deze toets staat hier en niet in een NormBeheer-suite omdat dat scherm er geen heeft;
    // dat gat is als bevinding gemeld, niet stil gelaten.
    const norm = SCHERMEN.find((s) => s.naam === 'NormBeheer.vue')
    expect(norm).toBeDefined()
    const t = norm.template
    const kopEinde = t.indexOf('>', t.indexOf('<LijstKop'))
    const toelichting = t.indexOf('data-testid="norm-toelichting"')
    expect(toelichting).toBeGreaterThan(kopEinde)          // onder de kop, niet erin
    const alinea = t.slice(t.lastIndexOf('<p', toelichting), t.indexOf('</p>', toelichting))
    expect(alinea).toContain('max-w-prose')                 // smal, leest als alinea
    expect(alinea).toContain('migratieklaar')               // de tekst zelf staat er nog
  })
})
