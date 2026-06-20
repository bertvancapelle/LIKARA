/**
 * PrimeVue PassThrough preset — Button (ADR-047 B6)
 *
 * Function-based preset: leest `props.severity`, `props.size` en `props.text`
 * zodat views geen inline :pt= meer hoeven te geven. Ondersteunt:
 *   severity: undefined | 'secondary' | 'danger'
 *   size:     undefined | 'small'
 *   text:     ghost/tertiair (geen achtergrond, geen rand, primary-tekst,
 *             hover:underline) — voor informatieve/tertiaire acties zoals
 *             "Geschiedenis". Wint van `severity`.
 *
 * Canonieke Button-styling — views gebruiken
 * <Button severity="..." size="..." /> (of <Button text /> voor ghost)
 * zonder :pt=. ACT-148 SC2.
 */
export default {
  root: ({ props }) => ({
    class: [
      'inline-flex items-center justify-center gap-2',
      'rounded-[var(--cd-radius-btn)]',
      'font-[var(--cd-font-family)]',
      'cursor-pointer transition-all duration-[var(--cd-transition-fast)]',
      'disabled:opacity-50 disabled:cursor-not-allowed',

      // Size-variant
      props.size === 'small'
        ? 'px-3 py-1 text-[length:var(--cd-text-xs)]'
        : 'px-4 py-2 text-[length:var(--cd-text-sm)]',

      // Variant — `text` (ghost/tertiair) wint van `severity`
      props.text
        ? [
            'bg-transparent text-[var(--cd-color-primary)]',
            'hover:underline',
            'focus:outline-2 focus:outline-offset-2 focus:outline-[var(--cd-color-primary)]',
          ]
        : props.severity === 'danger'
          ? 'bg-[var(--cd-color-danger)] text-white hover:opacity-90'
          : props.severity === 'secondary'
            ? 'bg-[var(--cd-color-primary-50)] text-[var(--cd-color-primary-700)] hover:bg-[var(--cd-color-primary-100)]'
            : [
                'bg-[var(--cd-color-primary)] text-white',
                'hover:bg-[#2D6DB5]',
                'focus:outline-2 focus:outline-offset-2 focus:outline-[var(--cd-color-primary)]',
              ],
    ],
  }),
  label: {
    class: 'font-semibold',
  },
  icon: {
    class: 'text-[length:var(--cd-text-base)]',
  },
}
