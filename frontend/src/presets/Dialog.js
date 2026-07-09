export default {
  root: {
    class: [
      'font-[var(--lk-font-family)]',
      'bg-[var(--lk-color-surface)]',
      'rounded-[var(--lk-radius-dialog)]',
      'shadow-[var(--lk-shadow-lg)]',
      'w-full max-w-lg mx-auto mt-[10vh]',
      'flex flex-col max-h-[80vh]',
    ],
  },
  mask: { class: 'fixed inset-0 bg-black/50 z-50' },
  header: {
    class: [
      'flex items-center justify-between',
      'px-6 pt-6 pb-2',
      'border-b border-[var(--lk-border)]',
    ],
  },
  title: {
    class: 'font-medium text-[length:var(--lk-text-base)] text-[var(--lk-text-primary)]',
  },
  headerActions: { class: 'flex items-center' },
  pcCloseButton: {
    root: { class: 'p-1 rounded hover:bg-[var(--lk-surface-alt)] text-[var(--lk-text-secondary)]' },
  },
  // Scroll-gedrag is HIER geborgd, in de gedeelde primitive — élk Dialog-gebruik erft het:
  // - `min-h-0` is de krimpgarantie: de root is flex-col met max-h-[80vh]; zonder min-h-0
  //   weigert dit flex-item kleiner te worden dan zijn inhoud en duwt lange inhoud de
  //   voetbalk uit het kader. Mét: kop en #footer-slot blijven altijd in beeld en alléén
  //   de inhoud scrolt (mt-[10vh] + max-h-[80vh] = de dialoog past binnen de viewport).
  // - `lk-scroll-schaduw` (main.css) toont toestandsafhankelijk een randschaduw waar nog
  //   inhoud buiten beeld is — hét patroon voor scrollende dialooginhoud.
  // Views bouwen GEEN eigen scroll-wrapper (die clipt veldranden/focus-ringen en laat de
  // voetbalk mee-scrollen); vaste knoppenbalken horen in het #footer-slot.
  content: { class: ['px-6 py-4 overflow-y-auto min-h-0 lk-scroll-schaduw', 'text-[var(--lk-text-primary)]'] },
  footer: { class: 'flex items-center justify-end gap-2 px-6 pb-6 pt-2' },
}
