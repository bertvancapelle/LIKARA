<script setup>
/**
 * RijActies — de gedeelde drager van rustige rij-acties (LI039 C0).
 *
 * "Eerst rust, dan signaal": een lees-scherm (boom/lijst) toont zijn rij-acties niet
 * permanent — ze verschijnen op de actieve rij (hover) en via het toetsenbord
 * (:focus-within), en blijven op aanraakschermen permanent zichtbaar (de bewuste
 * MVP-afweging: hover is daar onvindbaar; vangnet in main.css `@media (hover: none)`).
 *
 * Contract (CSS in assets/main.css): de RIJ draagt de klasse `lk-rij`; dit component
 * levert de `lk-rij-acties`-container. Actie-knoppen binnen de slot zijn tertiair
 * (`severity="text"`) — behalve destructieve acties, die per de vaste knopstandaard
 * (LI037) de `danger`-vorm HOUDEN: de gevaarlijkste actie mag er niet het minst
 * gevaarlijk uitzien. De rust komt uit het verschijnen-op-de-actieve-rij, niet uit
 * het afzwakken van het gevaarsignaal.
 */
</script>

<template>
  <div class="lk-rij-acties ml-auto flex shrink-0 items-center gap-[var(--lk-space-xs)]">
    <slot />
  </div>
</template>
