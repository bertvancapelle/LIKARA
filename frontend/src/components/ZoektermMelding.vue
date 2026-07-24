<script setup>
/**
 * ZoektermMelding — DE ene bron voor de "zoekterm opgeschoond"-melding (LI051).
 *
 * Overal dezelfde tekst en toon (gedempt; het bestaande neutrale kanaal `MeldingBanner`
 * soort="info"). Alleen de PLEK verschilt per soort veld — die bepaalt de aanroeper (tussen
 * zoekveld en aantal, direct onder het zoekveld, of in de openklappende keuzelijst). De
 * aanroeper toont hem via `v-if` uitsluitend wanneer er werkelijk iets is weggehaald, met de
 * opgeschoonde term uitgelicht zodat de gebruiker hem kan vergelijken met wat hij bedoelde.
 */
import MeldingBanner from './MeldingBanner.vue'

defineProps({
  // De opgeschoonde term waarop werkelijk is gezocht.
  term: { type: String, required: true },
  testid: { type: String, default: 'zoek-opschoon-melding' },
})
</script>

<template>
  <MeldingBanner soort="info" :testid="testid">
    Uw zoekopdracht bevatte onzichtbare tekens — die komen vaak mee bij plakken uit een ander
    programma. Er is gezocht op <strong>{{ term }}</strong>.
  </MeldingBanner>
</template>
