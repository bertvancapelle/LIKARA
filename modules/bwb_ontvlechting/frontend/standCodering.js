/**
 * standCodering — de ÉNE bron voor "plek-stand → presentatie" (ADR-051 gate 4, slice B).
 *
 * De Bedrijfsfuncties-lijst (B1) én de kaart + legenda (B2) erven hieruit: één ernst-taal, geen twee
 * definities die uit de pas lopen (LI038; het `kleurOpDomein`-gat kan hier niet opnieuw ontstaan).
 * "Welke stand → welke kleur/tekst" leeft UITSLUITEND hier — nergens inline in een view.
 *
 * Kleur via de bestaande LIKARA-ernst-tokens (dark-mode-safe; géén losse hex):
 *   werk    → --lk-color-warning  (amber)   · gat + werkvoorraad (onderscheiden door tekst)
 *   in_orde → --lk-color-success  (groen)    · hier draait een systeem
 *   gedekt  → --lk-color-primary-700 (blauw) · ondersteund via een bovenliggende functie
 *   besluit → --lk-color-text-muted (grijs)  · bewust niets — een afgerond besluit, geen leeg gat
 *
 * `lijstTekst(ctx)` en `legendaTekst`: `ctx = { systeem, voorouder, viaAantal }` (voor hier/via_boven).
 */
export const STAND_CODERING = {
  gat: {
    ernst: 'werk',
    kleur: 'var(--lk-color-warning)',
    icoon: '○',
    lijstTekst: () => 'nog niet vastgelegd waarmee dit werk gedaan wordt',
    legendaTekst: 'nog niet vastgelegd waarmee',
  },
  werkvoorraad: {
    ernst: 'werk',
    kleur: 'var(--lk-color-warning)',
    icoon: '◑',
    lijstTekst: () => 'systeem bekend, gebruiker nog niet vastgelegd',
    legendaTekst: 'systeem er, gebruiker nog niet',
  },
  hier: {
    ernst: 'in_orde',
    kleur: 'var(--lk-color-success)',
    icoon: '✓',
    lijstTekst: (ctx = {}) => (ctx.systeem ? `hier draait: ${ctx.systeem}` : 'hier draait'),
    legendaTekst: 'hier draait een systeem',
  },
  via_boven: {
    ernst: 'gedekt',
    kleur: 'var(--lk-color-primary-700)',
    icoon: '↑',
    lijstTekst: (ctx = {}) =>
      ctx.voorouder
        ? `ondersteund via ${ctx.voorouder}`
        : `ondersteund via ${ctx.viaAantal ?? 0} bovenliggende functies`,
    legendaTekst: 'gedekt via een bovenliggende functie',
  },
  niets: {
    ernst: 'besluit',
    kleur: 'var(--lk-color-text-muted)',
    icoon: '⊘',
    lijstTekst: () => 'hier wordt bewust niets gebruikt',
    legendaTekst: 'hier wordt bewust niets gebruikt',
  },
}

/**
 * Het pill-`:style`-object voor een stand: tekstkleur + rand uit de bron, met een lichte tint-
 * achtergrond (color-mix, dark-mode-safe) zodat lijst én kaart-legenda dezelfde tint dragen. Eén
 * plek — geen dubbele kleurlogica. Onbekende stand → leeg object (geen crash).
 */
export function standPillStyle(stand) {
  const c = STAND_CODERING[stand]
  if (!c) return {}
  return {
    color: c.kleur,
    borderColor: c.kleur,
    background: `color-mix(in srgb, ${c.kleur} 12%, transparent)`,
  }
}
