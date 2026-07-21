/**
 * Laag B — Component-render-state-test (UI-borging interactiestates).
 *
 * Bewaakt de twee centrale componenten die de knop-/tab-interactie-taal dragen:
 *  1. presets/Button.js — elke variant zet de juiste token-klasse + één vaste
 *     hoogte (h-10, GEEN size-variatie/h-8 meer).
 *  2. AppTabs.vue — gekozen vs. niet-gekozen tab dragen de juiste token-/state-
 *     klassen, en de hover-klassen staan op het klikbare element (de tab-button).
 *
 * Vangt "state op verkeerd element" en "verkeerde/ontbrekende token-klasse".
 */
import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import buttonPreset from '@/presets/Button.js'
import AppTabs from '@modules/bwb_ontvlechting/frontend/views/AppTabs.vue'

// DE-VERVUILING: dit testbestand staat onder frontend/ en wordt door Tailwind v4
// gescand. Module-UNIEKE class-tokens (die alléén in AppTabs voorkomen) mogen hier
// niet AANEENGESLOTEN als literal staan — anders pikt Tailwind ze als candidate op
// en genereert ze zelf, waardoor de build-CSS-check (laag C) vals-groen wordt. We
// bouwen zulke verwachte tokens uit fragmenten (sluit-`]` afgesplitst → ongebalanceerde
// `[` = geen candidate). De assertie vergelijkt alsnog de volledige string.
const cls = (...delen) => delen.join('')

/** Vlakke class-string uit de (array-)class van de preset-root. */
function rootClass(props) {
  const out = buttonPreset.root({ props })
  return [out.class].flat(Infinity).join(' ')
}

describe('Laag B — Button-preset varianten', () => {
  it('primary (default): donkerblauwe vulling + witte tekst', () => {
    const c = rootClass({})
    expect(c).toContain('bg-[var(--lk-color-primary)]')
    expect(c).toContain('text-white')
  })

  it('secondary: lichtblauwe vulling + mid-blauwe tekst (token-klassen)', () => {
    const c = rootClass({ severity: 'secondary' })
    expect(c).toContain('bg-[var(--lk-color-primary-50)]')
    expect(c).toContain('text-[var(--lk-color-primary-700)]')
  })

  it('danger: rode vulling via --lk-color-danger', () => {
    expect(rootClass({ severity: 'danger' })).toContain('bg-[var(--lk-color-danger)]')
  })

  it('text (ghost): transparant + primary-tekst, wint van severity', () => {
    const c = rootClass({ text: true, severity: 'secondary' })
    expect(c).toContain('bg-transparent')
    expect(c).toContain('text-[var(--lk-color-primary)]')
    // ghost wint: geen secondary-vulling
    expect(c).not.toContain('bg-[var(--lk-color-primary-50)]')
  })

  it('één vaste hoogte h-10 op élke variant; geen h-8/size-variatie', () => {
    for (const props of [{}, { severity: 'secondary' }, { severity: 'danger' }, { text: true }, { size: 'small' }]) {
      const c = rootClass(props)
      expect(c, `h-10 ontbreekt voor ${JSON.stringify(props)}`).toContain('h-10')
      expect(c, `h-8 mag niet voorkomen voor ${JSON.stringify(props)}`).not.toContain('h-8')
    }
  })
})

describe('Laag B — AppTabs tabvorm (LI048 snede 2)', () => {
  const tabs = [
    { key: 'a', label: 'Tab A' },
    { key: 'b', label: 'Tab B' },
  ]

  function rij(orientation = 'horizontal') {
    return mount(AppTabs, {
      props: { tabs, modelValue: 'a', ariaLabel: 'Test', idPrefix: 't', orientation },
    })
  }

  // Vóór LI048 droeg een tabblad de KNOPVORM: `h-10`, de knopradius, een omkadering en
  // een gevulde gekozen-staat. Bij dertien tabbladen las die rij als dertien knoppen. Deze
  // toets legt de knip vast en valt om zodra iemand de knopvorm terugzet — de vorm-signalen
  // hieronder zijn precies wat de oude tab droeg.
  const KNOPVORM_SIGNALEN = [
    ['vaste knophoogte', 'h-10'],
    ['knopradius', cls('rounded-[var(--lk-radius-btn)', ']')],
    ['omkadering', cls('border-[0.5px', ']')],
    ['gevulde staat', cls('bg-[var(--lk-color-primary)', ']')],
  ]

  it.each(KNOPVORM_SIGNALEN)('een tabblad draagt geen knopvorm: %s', (_naam, signaal) => {
    const w = rij()
    for (const testid of ['t-tab-a', 't-tab-b']) {
      expect(w.find(`[data-testid="${testid}"]`).classes().join(' ')).not.toContain(signaal)
    }
  })

  it('de vorm leeft in de gedeelde klassen, niet op de call-site', () => {
    const w = rij()
    const el = w.find('[data-testid="t-tab-b"]')
    // het klikbare element is de tab-button (role=tab), niet een wrapper
    expect(el.attributes('role')).toBe('tab')
    expect(el.classes()).toContain('lk-tab')
    // De RIJ draagt de doorlopende lijn (`.lk-tabrij-h`), niet elk tabblad een eigen rand.
    expect(w.find('[role="tablist"]').classes()).toEqual(
      expect.arrayContaining(['lk-tabrij', 'lk-tabrij-h']),
    )
  })

  it('verticaal krijgt de rij zijn eigen kant — het vlak zit ernaast, niet eronder', () => {
    const w = rij('vertical')
    expect(w.find('[role="tablist"]').classes()).toEqual(
      expect.arrayContaining(['lk-tabrij', 'lk-tabrij-v']),
    )
    expect(w.find('[role="tablist"]').classes()).not.toContain('lk-tabrij-h')
  })

  // ── LI048 2c — HET DEFECT: wit op wit ────────────────────────────────────────────────────
  // De eerste sub-rij stond transparant op het witte werkvlak. Een niet-gekozen tabblad had dan
  // geen ondergrond om uit naar voren te komen: alleen de gekozen pil was zichtbaar, de rest
  // zweefde als losse tekst en de rij las niet als een rij. Deze toets legt vast dát de rij een
  // eigen ondergrond draagt en valt om zodra iemand hem weer op transparant/wit zet.
  it('2c: de sub-rij draagt een eigen ondergrond — niet-gekozen tabbladen staan niet op wit', () => {
    const w = mount(AppTabs, {
      props: { tabs, modelValue: 'a', ariaLabel: 'Test', idPrefix: 't', niveau: '2' },
    })
    const rij = w.find('[role="tablist"]')
    expect(rij.classes()).toContain('lk-tabrij-sub')
    // De band-tint en de wit-versmelting leven in main.css (`.lk-tabrij-*.lk-tabrij-sub`); de
    // build-CSS-check bewijst dat ze in de dist staan. Hier borgen we de bedrading: niveau 2
    // krijgt de sub-klasse, niveau 1 níét — anders erft de hoofdrij stilletjes de band.
    const hoofd = mount(AppTabs, {
      props: { tabs, modelValue: 'a', ariaLabel: 'Test', idPrefix: 't' },
    })
    expect(hoofd.find('[role="tablist"]').classes()).not.toContain('lk-tabrij-sub')
  })

  it('de gekozen staat leeft in aria-selected — geen tweede, losse staat-class', () => {
    // Zo kunnen het toegankelijkheidsfeit en het zichtbare feit structureel niet uiteenlopen
    // (de fout die snede 1 blootlegde: een rij die er gekozen uitzag maar het niet wás, of
    // andersom). De CSS leest `[aria-selected="true"]`; valt iemand terug op een class, dan
    // dragen gekozen en niet-gekozen tab verschillende classes en valt deze toets om.
    const w = rij()
    const gekozen = w.find('[data-testid="t-tab-a"]')
    const rest = w.find('[data-testid="t-tab-b"]')
    expect(gekozen.attributes('aria-selected')).toBe('true')
    expect(rest.attributes('aria-selected')).toBe('false')
    expect(gekozen.classes()).toEqual(rest.classes())
  })
})
