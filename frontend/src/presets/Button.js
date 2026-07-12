/**
 * PrimeVue PassThrough preset — Button (ADR-047 B6)
 *
 * Function-based preset: leest `props.severity`, `props.text` en `props.outlined`
 * zodat views geen inline :pt= meer hoeven te geven. Ondersteunt:
 *   severity: undefined | 'secondary' | 'danger'
 *   text:     ghost/tertiair (geen achtergrond, geen rand, primary-tekst,
 *             hover:underline) — NAVIGATIE-taal: doorklik/"hier ga je naartoe"
 *             (bv. "Geschiedenis", "Toon in functiebeeld →"). Wint van `severity`.
 *   outlined: rustige MUTATIE-knop (LI039 UI-afronding, punt 1) — lichte omlijning,
 *             transparante vulling, gedempte tekstkleur: onmiskenbaar een knop,
 *             maar zonder de kleurdruk van secondary. Voor rij-acties die iets
 *             VERANDEREN (Bewerken/Verplaatsen/+ Deelfunctie) — zichtbaar anders
 *             dan de text-doorklik. De standaard-PrimeVue `outlined`-prop,
 *             hier in het preset geactiveerd (één bron; geen call-site-maatwerk).
 *
 * KNOPSTANDAARD (LIKARA): de knop heeft ÉÉN vaste hoogte (h-10). Er is GEEN
 * size-variatie — een `size`-prop op een call-site heeft geen hoogte-effect.
 * Enige variatie: kleur/vorm per rol (severity/text/outlined) + breedte (volgt de tekst).
 *
 * Canonieke Button-styling — views gebruiken
 * <Button severity="..." /> (of <Button text /> / <Button outlined />) zonder :pt=. ACT-148 SC2.
 */
export default {
  root: ({ props }) => ({
    class: [
      'inline-flex items-center justify-center gap-2',
      'rounded-[var(--lk-radius-btn)]',
      'font-[var(--lk-font-family)]',
      'cursor-pointer transition-all duration-[var(--lk-transition-fast)]',
      'disabled:opacity-50 disabled:cursor-not-allowed',

      // Eén vaste hoogte (h-10) voor élke knop — geen size-variatie. Zo kan er
      // nooit meer een afwijkende knophoogte ontstaan; `items-center` (root) centreert.
      'h-10 px-4 text-[length:var(--lk-text-sm)]',

      // Variant — `text` (navigatie/ghost) wint van alles; `outlined` (rustige
      // mutatie) wint van `severity`; danger blijft de destructieve vorm (LI037).
      props.text
        ? [
            'bg-transparent text-[var(--lk-color-primary)]',
            'hover:underline',
            'focus:outline-2 focus:outline-offset-2 focus:outline-[var(--lk-color-primary)]',
          ]
        : props.outlined
          ? [
              'bg-transparent border border-[var(--lk-color-border)] text-[var(--lk-color-text-muted)]',
              'hover:border-[var(--lk-color-primary)] hover:text-[var(--lk-color-primary)]',
              'focus:outline-2 focus:outline-offset-2 focus:outline-[var(--lk-color-primary)]',
            ]
          : props.severity === 'danger'
            ? 'bg-[var(--lk-color-danger)] text-white hover:opacity-90'
            : props.severity === 'secondary'
              ? 'bg-[var(--lk-color-primary-50)] text-[var(--lk-color-primary-700)] hover:bg-[var(--lk-color-primary-100)]'
              : [
                  'bg-[var(--lk-color-primary)] text-white',
                  'hover:bg-[#2D6DB5]',
                  'focus:outline-2 focus:outline-offset-2 focus:outline-[var(--lk-color-primary)]',
                ],
    ],
  }),
  label: {
    class: 'font-semibold',
  },
  icon: {
    class: 'text-[length:var(--lk-text-base)]',
  },
}
