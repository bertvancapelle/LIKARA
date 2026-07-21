/**
 * Tests — afwijkingCodering (ADR-052 besluit 8, slice 4a): wie besloot wat.
 *
 * De kern die hier geborgd wordt: "bewust afgewogen" en "de lat is verschoven" mogen er NIET
 * hetzelfde uitzien. Het eerste is een besluit van een mens, het tweede een aanscherping door de
 * organisatie — ze gelijk tonen schrijft een besluit toe aan wie het niet nam.
 *
 * De feitencheck in LI048 legde bloot dat niets dit dekte: `OpenPuntenSectie.test.js` toetste wél
 * dát de twee groepen gescheiden waren, maar niets over TOON. Daardoor kon het onderscheid
 * vervlakken zonder dat er iets rood werd — en dat was ook precies gebeurd.
 */
import { describe, expect, it } from 'vitest'
import { AFWIJKING_CODERING, afwijkingCodering, afwijkingZin } from '@modules/bwb_ontvlechting/frontend/afwijkingCodering'

describe('afwijkingCodering — de twee soorten zijn onderscheiden', () => {
  it('bewust is AMBER, verschoven is NEUTRAAL — nooit dezelfde kleurbron', () => {
    // Amber betekent in LIKARA: hier is bewust van de norm afgeweken. De verschoven lat mag dat
    // signaal niet dragen; daar heeft niemand iets besloten.
    expect(AFWIJKING_CODERING.bewust.token).toBe('--lk-color-warning')
    expect(AFWIJKING_CODERING.verschoven.token).toBe('--lk-color-text-muted')
    expect(AFWIJKING_CODERING.verschoven.token).not.toBe(AFWIJKING_CODERING.bewust.token)
  })

  it('elk onderdeel van de presentatie verschilt — klasse, icoon én kleur', () => {
    // Eén verschillend kanaal is niet genoeg: wie de kleur niet ziet (schermlezer, zwart-wit
    // print, kleurenblindheid) moet het onderscheid nog steeds kunnen maken.
    const b = AFWIJKING_CODERING.bewust
    const v = AFWIJKING_CODERING.verschoven
    for (const veld of ['klasse', 'icoon', 'kleur']) {
      expect(b[veld], `bewust en verschoven delen hetzelfde ${veld}`).not.toBe(v[veld])
    }
  })

  it('de TAAL verschilt: bewust benoemt het besluit, verschoven wijst niemand aan', () => {
    const bewust = afwijkingZin('bewust', ['BIV-classificatie'])
    const verschoven = afwijkingZin('verschoven', ['Bedoeling (migratiepad)'])
    // "afgewogen" / "bewust" — er is gekeken en toch doorgegaan.
    expect(bewust).toMatch(/afgewogen|bewust/)
    // De verschoven lat draagt géén verwijt-taal: niemand heeft hier iets besloten.
    expect(verschoven).toMatch(/nog niet naar gekeken/)
    for (const verwijt of ['afgewogen', 'bewust', 'toch', 'ondanks']) {
      expect(verschoven, `de verschoven-zin bevat verwijt-taal: "${verwijt}"`).not.toContain(verwijt)
    }
  })

  it('meervoud en enkelvoud lezen allebei als een zin', () => {
    expect(afwijkingZin('bewust', ['A'])).toContain('A')
    expect(afwijkingZin('bewust', ['A', 'B'])).toContain('A, B')
    expect(afwijkingZin('verschoven', ['A'])).toContain('A')
    expect(afwijkingZin('verschoven', ['A', 'B'])).toContain('A, B')
  })

  it('leeg of onbekend levert niets — nooit een halve toon', () => {
    expect(afwijkingZin('bewust', [])).toBe('')
    expect(afwijkingZin('onbekend', ['A'])).toBe('')
    expect(afwijkingCodering('onbekend')).toBeNull()
  })
})

// ── Beide vensters lezen dezelfde bron — anders lopen ze opnieuw uiteen ──────────────────────
// Dit is het defect zelf: het migratiegereedheid-blok had de toon inline, het open-punten-kader
// had hem helemaal niet. Beide leunden al op dezelfde AFLEIDING (`splits_afwijking`); de
// PRESENTATIE liep uiteen. Een bronscan is hier de juiste vorm: hij bewijst dat geen van beide
// vensters de toon zelf nabouwt, en hij bijt zodra iemand dat toch doet (LI041-bronscan-norm).
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

const VENSTERS = {
  'OpenPuntenSectie.vue': '../../modules/bwb_ontvlechting/frontend/views/OpenPuntenSectie.vue',
  'MigratiegereedheidSectie.vue': '../../modules/bwb_ontvlechting/frontend/views/MigratiegereedheidSectie.vue',
}

describe('afwijkingCodering — één presentatiebron voor beide vensters', () => {
  const bron = (pad) => readFileSync(fileURLToPath(new URL(pad, import.meta.url)), 'utf8')

  it.each(Object.entries(VENSTERS))('%s leest de gedeelde bron', (naam, pad) => {
    expect(bron(pad), `${naam} importeert afwijkingCodering niet`).toContain('afwijkingCodering')
    expect(bron(pad)).toContain('AFWIJKING_CODERING')
  })

  it.each(Object.entries(VENSTERS))('%s: waar de bron wordt gebruikt, staat geen tweede toon', (naam, pad) => {
    // PER ELEMENT scannen, niet per bestand. Beide vensters tonen namelijk óók amber voor een
    // ándere as: de checklist-afwijking ("N van M vragen open") en de dialoog-context bij het
    // klaar verklaren. Die horen amber te zijn en gaan niet over bewust-vs-verschoven; ze
    // wegscannen zou vals alarm geven — en een scan die vals alarm slaat wordt genegeerd.
    //
    // Het afleidbare criterium: élk element dat `AFWIJKING_CODERING.<soort>.klasse` draagt, moet
    // zijn toon UITSLUITEND daaruit halen. Zet zo'n element er zelf nog een vulling of tekstkleur
    // bij, dan is er weer een tweede bron en kan één venster afwijken. Geen lijst uitzonderingen,
    // geen testid-opsomming: de scan vindt zijn doelen zelf.
    const tmpl = /<template>([\s\S]*)<\/template>/.exec(bron(pad))?.[1] ?? ''
    const zonderComments = tmpl.replace(/<!--[\s\S]*?-->/g, '')

    const dragers = [...zonderComments.matchAll(/AFWIJKING_CODERING\.(bewust|verschoven)\.klasse/g)]
    expect(dragers.length, `${naam} gebruikt de gedeelde klasse nergens`).toBeGreaterThan(0)

    for (const m of dragers) {
      // De `:class`-expressie waarin de klasse staat: van de `[` ervoor tot de sluitende `]`.
      const start = zonderComments.lastIndexOf('[', m.index)
      const eind = zonderComments.indexOf(']', m.index)
      const expressie = zonderComments.slice(start, eind)
      // `hover:`/`focus:` mogen blijven: dat is interactie van de knop, niet de toon zelf.
      const tweedeToon = [...expressie.matchAll(
        /(?<!hover:)(?<!focus:)(?:bg|text)-\[(?:color-mix\(in_srgb,)?var\(--lk-color-(?:warning|text-muted)\)/g,
      )]
      expect(tweedeToon.map((t) => t[0]),
             `${naam} (${m[1]}) zet naast de gedeelde klasse een eigen toon`).toEqual([])
    }
  })
})
