<script setup>
/**
 * MeldingBanner — gedeelde, zichtbare melding op de actieplek (LI035).
 *
 * HET meldingspatroon voor secties/formulieren: een getint vlak + icoon + tekst —
 * nooit alléén kleur (toegankelijkheidslijn). Stramien = de bestaande warn-banners
 * (checklist-gesloten 🔒 / klaarverklaring-afwijking ⚠): rustig van toon, niet te
 * missen. A11y: `role="status"` (polite) voor warn/info — een verwachtbare weigering
 * of informatie, geen alarm; `role="alert"` (assertive) voor danger — echte fouten.
 *
 * Soorten: `warn` (weigering/conflict, bv. "bestaat al"), `danger` (fout),
 * `info` (neutrale toelichting). Tekst via de `tekst`-prop of het default-slot.
 *
 * Scroll-vangnet (LI035): bij VERSCHIJNEN (mount — het gangbare gebruik is `v-if`)
 * scrolt de banner zichzelf net in beeld met `scrollIntoView({block:'nearest'})` —
 * 'nearest' scrolt minimaal en doet niets als hij al volledig zichtbaar is. Een
 * props-update zonder zichtbaarheidswissel hertriggert dit niet (geen re-mount).
 */
import { computed, onMounted, ref } from 'vue'

const props = defineProps({
  soort: {
    type: String,
    default: 'warn',
    validator: (w) => ['warn', 'danger', 'info'].includes(w),
  },
  tekst: { type: String, default: '' },
  testid: { type: String, default: 'melding-banner' },
})

// Volledige class-literals per soort (Tailwind scant glob-gebaseerd — nooit dynamisch
// samenstellen). Kleur + icoon + tekst samen; het icoon is decoratief (aria-hidden).
const STIJL = {
  warn: 'bg-[color-mix(in_srgb,var(--lk-color-warning)_12%,transparent)] text-[var(--lk-color-warning)]',
  danger: 'bg-[color-mix(in_srgb,var(--lk-color-danger)_12%,transparent)] text-[var(--lk-color-danger)]',
  info: 'bg-[color-mix(in_srgb,var(--lk-color-primary)_12%,transparent)] text-[var(--lk-color-primary)]',
}
const ICOON = { warn: '⚠', danger: '⚠', info: 'ℹ' }

const rol = computed(() => (props.soort === 'danger' ? 'alert' : 'status'))
const klassen = computed(() => STIJL[props.soort])
const icoon = computed(() => ICOON[props.soort])

// Scroll-vangnet: alleen bij verschijnen (mount), guarded voor testomgevingen.
const wortel = ref(null)
onMounted(() => {
  wortel.value?.scrollIntoView?.({ block: 'nearest', behavior: 'smooth' })
})
</script>

<template>
  <p
    ref="wortel"
    :role="rol"
    :data-testid="testid"
    class="flex items-start gap-[var(--lk-space-xs)] rounded-[var(--lk-radius-input)] px-[var(--lk-space-sm)] py-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]"
    :class="klassen"
  >
    <span aria-hidden="true" :data-testid="`${testid}-icoon`">{{ icoon }}</span>
    <span><slot>{{ tekst }}</slot></span>
  </p>
</template>
