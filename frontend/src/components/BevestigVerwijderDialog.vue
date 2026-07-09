<script setup>
/**
 * BevestigVerwijderDialog — gedeelde bevestigingsdialoog voor regel-acties (LI035).
 *
 * HET standaardpatroon voor "verwijderen/ontkoppelen vraagt altijd bevestiging, met de
 * regel leesbaar in de vraag" (regelacties-inventaris LI035). Props: kop + leesbare
 * omschrijving (of een rijker default-slot); bevestigen emit't `bevestig` (de aanroeper
 * doet de api-call en sluit door `visible` op false te zetten); Annuleren/Escape/
 * klik-buiten = niets doen. Danger-knop conform de knopstandaard. A11y via de
 * PrimeVue-Dialog (modal; focus keert bij sluiten terug naar de trigger).
 *
 * Nieuwe secties gebruiken déze component; de historisch gekloonde bevestigings-
 * dialogen migreren is een eigen opvolgpunt.
 */
import { Button, Dialog } from '@/primevue'

defineProps({
  visible: { type: Boolean, required: true },
  kop: { type: String, required: true },
  // Leesbare omschrijving van de regel ("registreren in Verhuizing verwerken — Zaaksysteem").
  omschrijving: { type: String, default: '' },
  bevestigLabel: { type: String, default: 'Verwijderen' },
  bezig: { type: Boolean, default: false },
  testid: { type: String, default: 'bevestig-verwijder' },
})
const emit = defineEmits(['update:visible', 'bevestig'])
</script>

<template>
  <Dialog
    :visible="visible"
    modal
    :header="kop"
    :data-testid="`${testid}-dialog`"
    @update:visible="(v) => emit('update:visible', v)"
  >
    <p class="mb-[var(--lk-space-md)] max-w-prose" :data-testid="`${testid}-omschrijving`">
      <slot>{{ omschrijving }}</slot>
    </p>
    <div class="flex gap-[var(--lk-space-md)]">
      <Button
        type="button"
        label="Annuleren"
        severity="secondary"
        :data-testid="`${testid}-annuleer`"
        @click="emit('update:visible', false)"
      />
      <Button
        type="button"
        :label="bevestigLabel"
        severity="danger"
        :data-testid="`${testid}-bevestig`"
        :disabled="bezig"
        @click="emit('bevestig')"
      />
    </div>
  </Dialog>
</template>
