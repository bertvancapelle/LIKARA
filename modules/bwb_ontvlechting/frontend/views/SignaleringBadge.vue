<script setup>
/**
 * SignaleringBadge — kleine inline indicator van registratiegaten op een entiteit (ADR-035).
 * 🔴 N bij ≥1 kritiek; anders 🟡 N bij ≥1 aandacht; niets als beide 0.
 * Puur presentatie — laadt zelf niets; de ouder geeft de tellingen (en optioneel de
 * signaal-sleutels) door. Met `signalen` toont de tooltip de concrete signaalnamen
 * (bv. "BIV-classificatie onvolledig") i.p.v. een generieke telling.
 */
import { computed } from 'vue'
import { SIGNAAL_LABEL } from '../labels'

const props = defineProps({
  kritiek: { type: Number, default: 0 },
  aandacht: { type: Number, default: 0 },
  signalen: { type: Array, default: () => [] },
})

const namen = computed(() =>
  props.signalen.map((k) => SIGNAAL_LABEL[k] || k).join(', '),
)
const kritiekTitel = computed(() =>
  namen.value || `${props.kritiek} kritiek(e) registratiegat(en)`,
)
const aandachtTitel = computed(() =>
  namen.value || `${props.aandacht} aandachtspunt(en)`,
)
</script>

<template>
  <span
    v-if="kritiek > 0"
    data-testid="signalering-badge"
    :title="kritiekTitel"
    class="inline-flex items-center gap-0.5 rounded-[var(--lk-radius-badge)] bg-[var(--lk-color-danger)]/15 px-[var(--lk-space-xs)] py-0.5 text-[length:var(--lk-text-xs)] text-[var(--lk-color-danger)]"
  >🔴 {{ kritiek }}</span>
  <span
    v-else-if="aandacht > 0"
    data-testid="signalering-badge"
    :title="aandachtTitel"
    class="inline-flex items-center gap-0.5 rounded-[var(--lk-radius-badge)] bg-[var(--lk-color-warning)]/15 px-[var(--lk-space-xs)] py-0.5 text-[length:var(--lk-text-xs)]"
  >🟡 {{ aandacht }}</span>
</template>
