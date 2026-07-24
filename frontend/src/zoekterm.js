/**
 * zoekterm — opschoning van een ingetypte/geplakte zoekterm aan de VOORKANT (LI051).
 *
 * Besluit Bert: zoeken weigert nooit. De regel is per Unicode-CATEGORIE (niet als handgeschreven
 * lijst codes — die mist morgen weer een teken):
 *
 * - `Zs` (spatie-separator: vaste spatie, smalle vaste spatie, en/em-spatie, ideografische spatie)
 *   → één gewone spatie. Wie een spatie intypte, bedoelde een spatie — de woordgrens blijft staan.
 * - `Cf` (opmaakteken: zero-width, woordverbinder, bytemarkering/BOM) → weg. Onzichtbaar, betekenisloos.
 * - `Cc` (stuurteken: NUL, regelovergang, tab, DEL) → weg (zoeken weigert nooit).
 * - Daarna: opeenvolgende gewone spaties samenvouwen tot één, en begin/eind trimmen.
 *
 * DEZE REGEL MOET AANTOONBAAR HETZELFDE ZIJN als de achterkant (`schemas/tekstschoning` +
 * `services/zoektekst.schoon_zoekterm`) en de invoerkant (`schemas/_validators`). De gedeelde reeks
 * in `tests/fixtures/zoekterm_gelijkheid.json` wordt door BEIDE kanten gedraaid; wijkt één kant af,
 * dan valt een suite om.
 */

// Unicode-eigenschapsklassen (u-flag). Per teken hergebruikt met .test().
const CF = /\p{Cf}/u // opmaaktekens: zero-width, woordverbinder, BOM
const ZS = /\p{Zs}/u // spatie-separators: NBSP, en/em-spatie, ideografische spatie, …
const CC = /\p{Cc}/u // stuurtekens: NUL, regelovergang, tab, DEL/C1

/**
 * Schoon een zoekterm op. Geeft `{ schoon, ietsWeggehaald }`:
 * - `schoon` — NFC; `Zs` → gewone spatie; `Cf`/`Cc` weg; spaties samengevouwen + getrimd.
 * - `ietsWeggehaald` — of er werkelijk IETS is verdwenen: een `Cf`/`Cc`-teken weggehaald, óf spaties
 *   samengevouwen. NIET waar wanneer een onzichtbare spatie alleen door een gewone is vervangen
 *   (dan ziet het resultaat er identiek uit — een melding zou meer verwarren dan helpen, blok C).
 *
 * Idempotent.
 */
export function schoonZoekterm(ruw) {
  const genormaliseerd = (ruw ?? '').normalize('NFC')
  let tussen = ''
  let verdwenen = false
  for (const ch of genormaliseerd) {
    if (CF.test(ch) || CC.test(ch)) {
      verdwenen = true // opmaak-/stuurteken weggehaald
      continue
    }
    tussen += ZS.test(ch) ? ' ' : ch
  }
  // Eerst trimmen, dan samenvouwen — zo telt alleen het samenvouwen van INTERNE spaties mee voor de
  // melding (rand-spaties weghalen is gewone hygiëne, geen "er is iets verdwenen"). De opgeschoonde
  // string is identiek aan de achterkant (samenvouwen-dan-trimmen levert dezelfde tekst).
  const getrimd = tussen.trim()
  const gevouwen = getrimd.replace(/ {2,}/g, ' ')
  if (gevouwen !== getrimd) verdwenen = true // interne spaties samengevouwen
  return { schoon: gevouwen, ietsWeggehaald: verdwenen }
}
