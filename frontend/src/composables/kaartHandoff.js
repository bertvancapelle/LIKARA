/**
 * kaartHandoff (LI033) — eenmalige overdracht van een component-set (+ grof-only-markering) van het
 * "Gebruikte applicaties"-blok naar de Landschapskaart.
 *
 * Bewust een klein module-niveau handoff-object i.p.v. een route-query: de set-id-lijst wordt te lang
 * voor een URL (zelfde reden waarom de subgraaf een POST is). Het blok zet de payload en navigeert; de
 * kaart consumeert 'm ÉÉN keer bij mount (consume-once, zodat een latere directe navigatie geen oude
 * set herintroduceert). Puur client-side, read-only overdracht — geen store-afhankelijkheid nodig.
 */
import { ref } from 'vue'

const _payload = ref(null)

/**
 * @param {{ componentIds: string[], grofOnlyIds?: string[], naam?: string }} payload
 */
export function zetKaartHandoff(payload) {
  _payload.value = payload
}

/** Haal de payload op en wis 'm (consume-once). Geeft `null` als er niets klaarstaat. */
export function neemKaartHandoff() {
  const p = _payload.value
  _payload.value = null
  return p
}
