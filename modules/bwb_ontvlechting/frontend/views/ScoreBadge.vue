<script setup>
/**
 * ScoreBadge — toont een score (Ja/Deels/Nee/N.v.t.) met de gedeelde kleurcode.
 *
 * Eén gedeelde bron voor score → kleur (`SCORE_KLEUR` in labels.js): Ja groen ·
 * Deels oranje · Nee rood · N.v.t. grijs. Toegankelijk: de scoretekst staat altijd
 * naast de kleur (kleur is niet de enige drager). Leeg/ongescoord ⇒ neutraal streepje.
 */
import { SCORE, scoreKleur, label } from '../labels'

defineProps({ score: { type: String, default: null } })
</script>

<template>
  <span
    v-if="score"
    :data-testid="`score-badge-${score}`"
    :class="['font-semibold', scoreKleur(score)]"
  >
    {{ label(SCORE, score) }}
  </span>
  <span v-else class="text-[var(--cd-color-text-muted)]">—</span>
</template>
