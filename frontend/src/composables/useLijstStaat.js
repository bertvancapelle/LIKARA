/**
 * useLijstStaat — lijststaat (filters/zoekterm/sortering) behouden over navigatie heen.
 *
 * HÉT patroon voor elk lijstscherm met filters/zoek/sortering (bestaand én toekomstig):
 * een gebruiker die een item opent en terugkeert — of het scherm herlaadt (F5) — vindt
 * zijn lijst precies zoals hij hem verliet. Hergebruikt het bewezen `lk-state`-patroon
 * van de Landschapskaart (LI022/LI034): sessionStorage = in-sessie MOMENTSTAAT (bewust
 * géén persoonlijke voorkeur-laag, ADR-041), bewaard op `onBeforeRouteLeave` ÉN
 * `beforeunload` (route-leave vuurt niet bij een reload; kaart-les LI034), gevalideerd
 * hersteld bij mount. Bewust NIET bewaard: cursor/paginering en de data zelf — herstel
 * is een verse fetch vanaf pagina 1 met de herstelde stand (cursor-discipline ADR-017).
 *
 * Precedentie is een verantwoordelijkheid van het scherm (kaart-lijn):
 *   doorklik-query in de URL  >  bewaarde staat  >  kale defaults.
 * Bij een doorklik-query slaat het scherm `herstel()` in zijn geheel over — de
 * gebruiker krijgt exact wat hij aanklikte, zonder dat een oude zoekterm/filter de
 * selectie stil uitdunt. Zodra hij het scherm daarna verlaat, wordt de dan-actieve
 * staat vanzelf de nieuwe bewaarde staat (het bewaar-moment leest altijd de refs).
 *
 * Gebruik:
 *   const { herstel } = useLijstStaat('partij-lijst',
 *     { filterAard, filterZoek, sortVeld, sortRichting },
 *     { valideer: { filterAard: (w) => AARDEN.includes(w) } })
 *   onMounted(() => { if (!heeftDoorklikQuery) herstel(); laad({ reset: true }) })
 */
import { onBeforeUnmount, onMounted } from 'vue'
import { onBeforeRouteLeave } from 'vue-router'

// Alleen JSON-primitieven en platte arrays daarvan zijn geldige lijststaat-waarden;
// al het andere (objecten, geneste arrays) is per definitie stale/corrupt → default.
const _primitief = (w) => w === null || ['string', 'number', 'boolean'].includes(typeof w)
const _geldigeVorm = (w) => _primitief(w) || (Array.isArray(w) && w.every(_primitief))

/**
 * @param {string} sleutel — stabiele scherm-sleutel (conventie: de route-naam).
 * @param {Record<string, import('vue').Ref>} velden — de refs die samen de lijststaat vormen.
 * @param {{ valideer?: Record<string, (w: unknown) => boolean> }} [opties] — optionele
 *   per-veld domeinvalidator; een waarde die 'm niet passeert blijft stil op de default
 *   (nooit een kapot scherm door een stale opgeslagen stand).
 */
export function useLijstStaat(sleutel, velden, { valideer = {} } = {}) {
  const KEY = `lijst-state:${sleutel}`

  function bewaar() {
    try {
      const s = {}
      for (const [naam, r] of Object.entries(velden)) s[naam] = r.value
      sessionStorage.setItem(KEY, JSON.stringify(s))
    } catch {
      /* sessionStorage niet beschikbaar — negeren */
    }
  }

  /** Herstelt de bewaarde staat in de refs (gevalideerd, per veld). @returns {boolean} iets hersteld */
  function herstel() {
    let s = null
    try {
      s = JSON.parse(sessionStorage.getItem(KEY) || 'null')
    } catch {
      s = null
    }
    if (!s || typeof s !== 'object' || Array.isArray(s)) return false
    let hersteld = false
    for (const [naam, r] of Object.entries(velden)) {
      if (!(naam in s)) continue
      const w = s[naam]
      if (!_geldigeVorm(w)) continue
      if (valideer[naam] && !valideer[naam](w)) continue
      r.value = w
      hersteld = true
    }
    return hersteld
  }

  function wis() {
    try {
      sessionStorage.removeItem(KEY)
    } catch {
      /* negeren */
    }
  }

  // Bewaarmomenten: route-leave dekt navigatie (naar detail, sidebar, …);
  // beforeunload dekt F5/reload (kaart-les LI034). Listener opgeruimd bij unmount.
  onBeforeRouteLeave(bewaar)
  const _opUnload = () => bewaar()
  onMounted(() => window.addEventListener('beforeunload', _opUnload))
  onBeforeUnmount(() => window.removeEventListener('beforeunload', _opUnload))

  return { herstel, bewaar, wis }
}
