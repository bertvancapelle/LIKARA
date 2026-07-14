/**
 * PrimeVue PassThrough preset — Textarea.
 *
 * LI040 — consument van de veldbouwsteen: `.lk-veld-tekstvlak` (assets/main.css)
 * is de ENIGE toegestane afwijking van de één-hoogte-regel — meerregelig dus
 * hoger, maar met exact dezelfde rand/radius/focus/achtergrond als `.lk-veld`.
 * Geen eigen hoogte/padding/kleuren hier.
 */
export default {
  root: {
    class: [
      'lk-veld-tekstvlak w-full',
      'font-[var(--lk-font-family)]',
      'transition-all duration-[var(--lk-transition-fast)]',
    ],
  },
}
