<script setup>
/**
 * DetailKop — gedeelde detailkop-bouwsteen (LI040): de acties horen bij het object,
 * niet bij het einde van de pagina.
 *
 * Eén kop voor élk detailscherm: identiteit links (naam + badges + optionele
 * context-subtitel), acties rechts — direct zichtbaar zonder scrollen, en ze
 * verhuizen niet als het scherm groeit (een nieuw tabblad/sectie duwt ze nergens
 * heen). Elk detailscherm is consument; een eigen actiebalk bouwen is verboden en
 * wordt door de detailkop-bron-scan (check-css-build.mjs) afgedwongen.
 *
 * Zones (de bouwsteen bepaalt de plek; het scherm levert de knoppen):
 * - #badges       — typering/status naast de naam (Tags, SignaleringBadge).
 * - #acties       — object-actie (Bewerken, primair = zwaarst), statusovergangen
 *                   (ALLEEN renderen wanneer ze kunnen — geen grijze knop die
 *                   meereist) en navigatie (Bekijk op kaart, Geschiedenis; lichter).
 * - #destructief  — Verwijderen: een EIGEN zone, visueel gescheiden van de primaire
 *                   actie (rand + afstand) — een misklik mag geen object wissen.
 * - #subtitel     — context-in-header (hoort bij / valt onder / overgang / pad).
 *
 * De naam wrapt en wordt NOOIT afgekapt (LI040-identiteitsregel); de actiezone
 * wrapt mee zodat de knoppen bij elke breedte bereikbaar blijven. Rol-gating blijft
 * bij de consument (v-if op de knoppen) — de backend handhaaft.
 */
defineProps({
  naam: { type: String, required: true },
  /** id voor de h1 (aria-labelledby van de omliggende section). */
  titelId: { type: String, default: 'detail-titel' },
})
</script>

<template>
  <div class="mb-[var(--lk-space-md)]" data-testid="detail-kop">
    <div class="flex flex-wrap items-center gap-[var(--lk-space-md)]">
      <h1
        :id="titelId"
        class="min-w-0 break-words text-[length:var(--lk-text-2xl)] font-semibold text-[var(--lk-color-primary)]"
        data-testid="detail-kop-naam"
      >{{ naam }}</h1>
      <slot name="badges" />
      <div
        v-if="$slots.acties || $slots.destructief"
        class="ml-auto flex flex-wrap items-center gap-[var(--lk-space-sm)]"
        data-testid="detail-kop-acties"
      >
        <slot name="acties" />
        <div
          v-if="$slots.destructief"
          class="ml-[var(--lk-space-sm)] border-l border-[var(--lk-color-border)] pl-[var(--lk-space-md)]"
          data-testid="detail-kop-destructief"
        >
          <slot name="destructief" />
        </div>
      </div>
    </div>
    <slot name="subtitel" />
  </div>
</template>
