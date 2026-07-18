/**
 * popoverPositie — gedeelde positioneer-bouwsteen voor overlay-vensters (ADR-052 slice 3c).
 *
 * Een popover/overlay mag nooit buiten beeld vallen. Deze bouwsteen bepaalt of het paneel ONDER of
 * BOVEN de trigger komt (afhankelijk van de beschikbare ruimte) en klemt het horizontaal binnen het
 * zichtbare gebied. De rekenkern is een PURE functie (`berekenPopoverPositie`) zodat de flip-/klem-
 * logica getest kan worden zonder layout-engine; de composable (`usePopoverPositie`) draadt die aan
 * de echte DOM (getBoundingClientRect + resize/scroll) via `position: fixed`.
 *
 * A11y (Escape/klik-buiten/focus-terug/aria) blijft bij de aanroeper — dit gaat puur over plaatsing.
 */
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'

/**
 * Pure plaatsingsberekening in viewport-coördinaten.
 * @param {{top:number,bottom:number,left:number}} trigger  getBoundingClientRect van de trigger
 * @param {{width:number,height:number}} paneel             afmetingen van het paneel
 * @param {{w:number,h:number}} viewport                    window.innerWidth/innerHeight
 * @param {number} [marge]  minimale marge tot de vensterrand
 * @param {number} [gat]    tussenruimte trigger↔paneel
 * @returns {{top:number,links:number,plaatsBoven:boolean}}
 */
export function berekenPopoverPositie({ trigger, paneel, viewport, marge = 8, gat = 4 }) {
  const ruimteOnder = viewport.h - trigger.bottom
  const ruimteBoven = trigger.top
  // Boven plaatsen alleen als het onder écht niet past én er boven meer ruimte is.
  const plaatsBoven = ruimteOnder < paneel.height + gat + marge && ruimteBoven > ruimteOnder
  let top = plaatsBoven ? trigger.top - paneel.height - gat : trigger.bottom + gat
  top = Math.max(marge, Math.min(top, viewport.h - paneel.height - marge))
  let links = Math.min(trigger.left, viewport.w - paneel.width - marge)
  links = Math.max(marge, links)
  return { top, links, plaatsBoven }
}

/**
 * Composable: koppelt de pure berekening aan een paneel-ref en herpositioneert bij openen + bij
 * resize/scroll zolang het paneel open is. Retourneert een reactieve `stijl` (bind op :style).
 * @param {import('vue').Ref<HTMLElement|null>} paneelRef
 */
export function usePopoverPositie(paneelRef) {
  const stijl = ref({})
  let trigger = null

  function herbereken() {
    const p = paneelRef.value
    if (!trigger || !p) return
    const t = trigger.getBoundingClientRect()
    const pr = p.getBoundingClientRect()
    const { top, links } = berekenPopoverPositie({
      trigger: { top: t.top, bottom: t.bottom, left: t.left },
      paneel: { width: pr.width || p.offsetWidth, height: pr.height || p.offsetHeight },
      viewport: { w: window.innerWidth, h: window.innerHeight },
    })
    stijl.value = { position: 'fixed', top: `${top}px`, left: `${links}px` }
  }

  function open(el) {
    trigger = el
    nextTick(herbereken)
  }
  function sluit() {
    trigger = null
  }
  function _herpositioneer() {
    if (trigger) herbereken()
  }

  onMounted(() => {
    window.addEventListener('resize', _herpositioneer, true)
    window.addEventListener('scroll', _herpositioneer, true)
  })
  onBeforeUnmount(() => {
    window.removeEventListener('resize', _herpositioneer, true)
    window.removeEventListener('scroll', _herpositioneer, true)
  })

  return { stijl, open, sluit, herbereken }
}
