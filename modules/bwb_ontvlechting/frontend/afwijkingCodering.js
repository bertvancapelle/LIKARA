/**
 * afwijkingCodering — de ÉNE bron voor "soort norm-afwijking → presentatie" (ADR-052 besluit 8).
 *
 * Twee vensters tonen hetzelfde feit: het migratiegereedheid-blok (`MigratiegereedheidSectie`) en
 * het open-punten-kader (`OpenPuntenSectie`). Ze leunden al op dezelfde AFLEIDING
 * (`component_norm_service.splits_afwijking` — één bron, twee peildata), maar toonden hem
 * verschillend: het ene venster met amber vs. neutraal, het andere met louter tekstscheiding.
 * Daardoor kon een consultant in het open-punten-kader een besluit toeschrijven aan iemand die het
 * niet nam — precies de misleiding die ADR-052 besluit 8 benoemt en verbiedt.
 *
 * "Welke soort → welke toon/icoon/tekst" leeft UITSLUITEND hier — nergens inline in een view.
 * Zelfde vorm als `standCodering.js` (LI043: één bron voor PRESENTATIE, niet alleen voor data).
 *
 * DE TWEE SOORTEN — en waarom hun toon verschilt:
 *
 *   bewust     → AMBER (`--lk-color-warning`, ⚠)
 *                Een MENS heeft bij het klaar verklaren dit open feit gezien en toch besloten door
 *                te gaan. Het stond in de bevroren snapshot. Amber betekent in LIKARA: hier is
 *                bewust van de norm afgeweken — en dat verdient verantwoording (wie, wanneer, wat
 *                stond er open).
 *
 *   verschoven → NEUTRAAL (`--lk-color-text-muted`, ↔)
 *                De ORGANISATIE heeft haar norm ná die verklaring aangescherpt. Het feit stond
 *                NIET in de snapshot, dus niemand heeft hier iets over besloten. Neutraal in kleur
 *                én in taal: een uitnodiging om opnieuw te kijken, geen verwijt. Nooit amber —
 *                dat zou een besluit toeschrijven aan wie het niet nam.
 *
 * De twee sluiten elkaar NIET uit (besluit 3): een component kan beide dragen, en dat is de
 * normale situatie — niet een randgeval. Zaaksysteem in het demolandschap toont ze allebei.
 */

/**
 * De toon per soort. `klasse` is de gedeelde presentatieklasse (main.css); `token` staat erbij
 * zodat een consument die geen DOM is (een canvas, een export) dezelfde kleurbron kan lezen
 * zonder een tweede literal te introduceren — exact de reden waarom `standCodering` het ook doet.
 */
export const AFWIJKING_CODERING = {
  bewust: {
    token: '--lk-color-warning',
    kleur: 'var(--lk-color-warning)',
    klasse: 'lk-afwijking-bewust',
    icoon: '⚠',
    /** Kort label voor een opsomming; het venster levert zelf de omliggende zin. */
    aanhef: 'Bij het klaar verklaren afgewogen',
  },
  verschoven: {
    token: '--lk-color-text-muted',
    kleur: 'var(--lk-color-text-muted)',
    klasse: 'lk-afwijking-verschoven',
    icoon: '↔',
    aanhef: 'Pas daarna verplicht gesteld',
  },
}

/** De presentatie van één soort. Onbekende soort → `null`, zodat een view geen halve toon toont. */
export function afwijkingCodering(soort) {
  return AFWIJKING_CODERING[soort] ?? null
}

/**
 * De zin die zegt wát er aan de hand is, in de toon van de soort.
 *
 * `bewust` benoemt het besluit ("er is gekeken en toch doorgegaan"); `verschoven` benoemt de
 * verschuiving zónder iemand aan te wijzen ("daar is hier nog niet naar gekeken"). De formulering
 * leeft hier en niet in de view, want juist de TAAL is waar het verwijt in kan sluipen.
 */
export function afwijkingZin(soort, labels) {
  const n = labels?.length ?? 0
  if (!n) return ''
  const opsomming = labels.join(', ')
  if (soort === 'bewust') {
    return n === 1
      ? `Bij het klaar verklaren is ${opsomming} afgewogen en bewust opengelaten.`
      : `Bij het klaar verklaren zijn deze afgewogen en bewust opengelaten: ${opsomming}.`
  }
  if (soort === 'verschoven') {
    return n === 1
      ? `${opsomming} is pas daarna verplicht gesteld — daar is hier nog niet naar gekeken.`
      : `Deze zijn pas daarna verplicht gesteld — daar is hier nog niet naar gekeken: ${opsomming}.`
  }
  return ''
}
