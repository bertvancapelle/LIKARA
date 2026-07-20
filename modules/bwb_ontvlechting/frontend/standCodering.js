/**
 * standCodering — de ÉNE bron voor "plek-stand → presentatie" (ADR-051 gate 4, slice B).
 *
 * De Bedrijfsfuncties-lijst (B1) én de kaart + legenda (B2) erven hieruit: één ernst-taal, geen twee
 * definities die uit de pas lopen (LI038; het `kleurOpDomein`-gat kan hier niet opnieuw ontstaan).
 * "Welke stand → welke kleur/tekst" leeft UITSLUITEND hier — nergens inline in een view.
 *
 * KLEUR — één literal per stand: het design-`token`. Daaruit derft alles:
 *   - `kleur` (`var(--lk-…)`) voor DOM-consumenten (lijst-pill, legenda) — CSS resolvet de var zelf.
 *   - `standKaartKleur(stand)` resolvet HETZELFDE token op tekenmoment naar een concrete waarde voor
 *     het Cytoscape-canvas (dat een CSS-`var()` niet kan resolven). Optie A (LI043): geen tweede
 *     hex-kopie — kaart en pill lezen dezelfde bron-literal.
 *
 * Ernst → token (de vier ernst-kleuren; er is geen dark-mode, elk token heeft één vaste waarde):
 *   werk    → --lk-color-warning     (amber)  · gat + werkvoorraad (onderscheiden door tekst, NIET kleur)
 *   in_orde → --lk-color-success     (groen)  · hier draait een systeem
 *   gedekt  → --lk-color-primary-700 (blauw)  · ondersteund via een bovenliggende functie
 *   besluit → --lk-color-text-muted  (grijs)  · bewust niets — een afgerond besluit, geen leeg gat
 *
 * `lijstTekst(ctx)` en `legendaTekst`: `ctx = { systeem, voorouder, viaAantal }` (voor hier/via_boven).
 */
const _stand = (token, rest) => ({ token, kleur: `var(${token})`, ...rest })

export const STAND_CODERING = {
  gat: _stand('--lk-color-warning', {
    ernst: 'werk',
    icoon: '○',
    lijstTekst: () => 'nog niet vastgelegd waarmee dit werk gedaan wordt',
    // GEEN legendaTekst (LI047) — zie de noot bij `werkvoorraad`: beide amber-standen delen één
    // legenda-regel, die haar eigen ernst-tekst draagt (STAND_LEGENDA).
  }),
  werkvoorraad: _stand('--lk-color-warning', {
    ernst: 'werk',
    icoon: '◑',
    lijstTekst: () => 'component bekend, gebruiker nog niet vastgelegd',
    // GEEN legendaTekst (LI047): `werkvoorraad` deelt op de kaart de amber ernst-regel met `gat`, en
    // die regel draagt haar eigen ernst-tekst (zie STAND_LEGENDA). Een legendaTekst hier zou nooit
    // gerenderd worden — en zich voordoen als de knop waaraan je de legenda verzet. Niet terugzetten:
    // wil je de legenda wijzigen, dan is STAND_LEGENDA de plek.
  }),
  hier: _stand('--lk-color-success', {
    ernst: 'in_orde',
    icoon: '✓',
    lijstTekst: (ctx = {}) => (ctx.systeem ? `hier draait: ${ctx.systeem}` : 'hier draait'),
    legendaTekst: 'hier draait een component',
  }),
  via_boven: _stand('--lk-color-primary-700', {
    ernst: 'gedekt',
    icoon: '↑',
    lijstTekst: (ctx = {}) =>
      ctx.voorouder
        ? `ondersteund via ${ctx.voorouder}`
        : `ondersteund via ${ctx.viaAantal ?? 0} bovenliggende functies`,
    legendaTekst: 'gedekt via een bovenliggende functie',
  }),
  niets: _stand('--lk-color-text-muted', {
    ernst: 'besluit',
    icoon: '⊘',
    lijstTekst: () => 'hier wordt bewust niets gebruikt',
    legendaTekst: 'hier wordt bewust niets gebruikt',
  }),
}

/**
 * De vier ERNST-regels voor de kaart-legenda (slice B2) — één regel per kleur, in oplopende-ernst-
 * volgorde. De twee amber-standen (gat + werkvoorraad) delen op de kaart één kleur en dus één legenda-
 * regel; het onderscheid leest de consultant via de lijst-pill/hover, niet via een tweede kleur.
 * Token + tekst komen uit deze ÉNE bron: de legenda kan niet los van de node-kleur lopen (LI038). Waar
 * een enkele stand de ernst representeert, derft de tekst uit `STAND_CODERING`; alleen de amber-regel
 * (twee standen) draagt een eigen ernst-tekst.
 */
export const STAND_LEGENDA = [
  { ernst: 'werk', token: STAND_CODERING.gat.token, tekst: 'nog vast te leggen (werk)' },
  { ernst: 'in_orde', token: STAND_CODERING.hier.token, tekst: STAND_CODERING.hier.legendaTekst },
  { ernst: 'gedekt', token: STAND_CODERING.via_boven.token, tekst: STAND_CODERING.via_boven.legendaTekst },
  { ernst: 'besluit', token: STAND_CODERING.niets.token, tekst: STAND_CODERING.niets.legendaTekst },
]

/**
 * Het pill-`:style`-object voor een stand: tekstkleur + rand uit de bron, met een lichte tint-
 * achtergrond (color-mix) zodat lijst én kaart-legenda dezelfde tint dragen. Eén plek — geen dubbele
 * kleurlogica. Onbekende stand → leeg object (geen crash). DOM-consument: gebruikt de CSS-var direct.
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

// Cache per token (geen dark-mode → statische waarden; alleen niet-lege resultaten cachen zodat een
// resolve vóór het laden van base.css niet een lege waarde vastpint).
const _kaartKleurCache = {}

/**
 * De stand-kleur als concrete waarde voor het Cytoscape-CANVAS (optie A, LI043): resolvet HETZELFDE
 * `token` dat de pill via `var()` gebruikt, op tekenmoment naar de effectieve waarde uit `base.css`.
 * Zo blijft er één kleur-definitie (het token) die kaart én lijst delen — canvas kan een `var()` niet
 * zelf resolven. Onbekende/onresolveerbare stand → `null` (aanroeper valt terug op neutraal).
 */
export function standKaartKleur(stand) {
  const c = STAND_CODERING[stand]
  if (!c) return null
  if (_kaartKleurCache[c.token]) return _kaartKleurCache[c.token]
  let v = ''
  try {
    v = getComputedStyle(document.documentElement).getPropertyValue(c.token).trim()
  } catch { /* geen DOM (SSR/edge) → null */ }
  if (v) _kaartKleurCache[c.token] = v
  return v || null
}
