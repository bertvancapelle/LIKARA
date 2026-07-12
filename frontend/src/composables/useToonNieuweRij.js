/**
 * useToonNieuweRij — "wat je zojuist hebt vastgelegd, zie je altijd" (LI039 blok B).
 *
 * Eén regel, één bouwsteen, twee lagen:
 *
 * - `useAanstip()` — de korte "kijk hier"-aanstip op een zojuist vastgelegde rij:
 *   zet `aangestiptId` (met timer) voor de gedeelde `.lk-aangestipt`-klasse
 *   (main.css — de bestaande selectietaal, `--lk-color-selectie`). Voor élke lijst,
 *   ook gepagineerde secties (DataTable via `rowClass`). De aanstip is de drager van
 *   de uitleg: "dit heb je zojuist toegevoegd" — óók wanneer het item vooraan is
 *   ingevoegd terwijl de natuurlijke volgorde anders is; de volgende verse laadbeurt
 *   toont gewoon de natuurlijke volgorde.
 *
 * - `useToonInBoom({ openTakken, zoekterm, matcht, ouderVan, wijkTekst })` — de
 *   boom-schermen (bedrijfsfuncties + processen), voor aanmaken ÉN verplaatsen:
 *   1. het pad naar de rij klapt open (ouderketen, cyclus-veilig);
 *   2. zou de actieve zoekterm de rij verbergen, dan wijkt die ZICHTBAAR: de term
 *      wordt gewist en `wijkMelding` draagt de leesbare mededeling (banner-patroon:
 *      de melding verdwijnt zodra de gebruiker de zoekterm zelf weer aanraakt);
 *   3. de rij wordt kort aangestipt.
 *   Nooit stil — een filter mag verbergen, maar nooit het resultaat van de eigen
 *   handeling van de gebruiker (P8-lijn).
 */
import { nextTick, ref, watch } from 'vue'

const _AANSTIP_MS = 2600

// LI039 UI-afronding punt 2 — "je ziet WÁÁR hij terechtkwam": staat de aangestipte rij
// buiten beeld, dan scrolt hij het zicht in mét zijn omgeving (block: 'center' — de
// ouder en de buren komen mee; niet tegen de rand geplakt), zacht (smooth — de
// gebruiker kan het beeld volgen). Staat de rij al volledig in beeld → NIETS bewegen
// (een verspringend scherm zonder reden is zelf verwarrend). Geëxporteerd voor de
// gedrags-tests; retourneert of er gescrold is.
export function scrolNaarRij(el) {
  if (!el) return false
  const r = el.getBoundingClientRect?.()
  const vh = (typeof window !== 'undefined' && window.innerHeight) || 0
  if (r && vh && r.height > 0 && r.top >= 0 && r.bottom <= vh) return false // al in beeld
  el.scrollIntoView?.({ block: 'center', behavior: 'smooth' })
  return true
}

export function useAanstip(duurMs = _AANSTIP_MS) {
  const aangestiptId = ref(null)
  let timer = null
  function aanstip(id) {
    if (timer) clearTimeout(timer)
    aangestiptId.value = id == null ? null : String(id)
    if (id != null) {
      timer = setTimeout(() => { aangestiptId.value = null }, duurMs)
      // Ná de render (de rij draagt dan de gedeelde .lk-aangestipt-klasse — boom-li's
      // én DataTable-rijen): breng hem het zicht in als hij daarbuiten staat. De
      // aanstip zegt WELKE rij, de scroll brengt je erheen — samen zijn ze het antwoord.
      nextTick(() => {
        if (typeof document === 'undefined') return
        scrolNaarRij(document.querySelector('.lk-aangestipt'))
      })
    }
  }
  return { aangestiptId, aanstip }
}

export function useToonInBoom({ openTakken, zoekterm, matcht, ouderVan, wijkTekst }) {
  const { aangestiptId, aanstip } = useAanstip()
  const wijkMelding = ref(null)

  // Banner-patroon: de melding hoort bij de geweken zoekterm en verdwijnt zodra de
  // gebruiker het zoekveld zelf weer aanraakt. De eigen wis-actie van toonRij mag de
  // melding niet direct doven (guard-vlag).
  let _eigenWijziging = false
  watch(zoekterm, () => {
    if (_eigenWijziging) {
      _eigenWijziging = false
      return
    }
    wijkMelding.value = null
  })

  function toonRij(id) {
    if (id == null) return
    const rijId = String(id)
    // 1. Pad openklappen — ouderketen omhoog, cyclus-veilig (visited-set).
    const open = new Set(openTakken.value)
    const bezocht = new Set([rijId])
    let cur = ouderVan(rijId)
    while (cur != null && !bezocht.has(String(cur))) {
      bezocht.add(String(cur))
      open.add(String(cur))
      cur = ouderVan(String(cur))
    }
    openTakken.value = [...open]
    // 2. Zoekterm wijkt zichtbaar als hij de rij zou verbergen — nooit stil.
    if (zoekterm.value.trim() && !matcht(rijId)) {
      _eigenWijziging = true
      zoekterm.value = ''
      wijkMelding.value = wijkTekst
    }
    // 3. Korte aanstip in de bestaande "kijk hier"-taal.
    aanstip(rijId)
  }

  return { aangestiptId, wijkMelding, toonRij }
}
