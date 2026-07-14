/**
 * PrimeVue PassThrough preset — InputText.
 *
 * LI040 — consument van de veldbouwsteen: het volledige veld-recept (hoogte, rand,
 * radius, focus, achtergrond, placeholder, disabled) leeft in `.lk-veld`
 * (assets/main.css) + `--lk-veld-h` (themes/base.css). Hier alleen layout en de
 * overgang — geen eigen hoogte/padding/kleuren, zodat dit preset niet opnieuw
 * uit de pas kan lopen met de native velden.
 */
export default {
  root: {
    class: [
      'lk-veld w-full',
      'font-[var(--lk-font-family)]',
      'transition-all duration-[var(--lk-transition-fast)]',
    ],
  },
}
