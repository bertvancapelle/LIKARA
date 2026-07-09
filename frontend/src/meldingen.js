/**
 * meldingen — gedeelde succes-terugkoppeling (LI035-standaard).
 *
 * DE systeembrede regel: elke geslaagde actie met een expliciete opslaan-intentie
 * (dialog-submit, formulier-submit, toevoegregel-submit, bevestigde verwijdering)
 * toont een KORTE succes-toast — een werkwoord als samenvatting, 3000 ms. Deze helper
 * is dé vorm; roep hem aan ná de geslaagde call, vóór sluiten/herladen.
 *
 * Enige uitzondering (CD004): de hoogfrequente per-rij scoringslijst
 * (ChecklistscoreSectie) houdt per-rij INLINE status i.p.v. een toast per actie —
 * die norm geldt alléén daar, niet voor relatie-secties of dialogen.
 */
const _LIFE = 3000

export function toastSucces(toast, samenvatting, detail = undefined) {
  toast.add({ severity: 'success', summary: samenvatting, ...(detail ? { detail } : {}), life: _LIFE })
}
