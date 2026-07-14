<script setup>
/**
 * IdentiteitLabel — DE gedeelde weergave van een afdeling-/persoon-identiteit (LI040).
 *
 * Vaste vorm (besluit Bert): `afdeling — organisatie` / `persoon — afdeling — organisatie`.
 * De NAAM is de scanlaag; alles ná het eerste em-streepje is de leeslaag en wordt
 * visueel secundair (gedempt, bestaand token) — op DEZELFDE regel, geen tweede regel,
 * geen tooltip-only. Identiteit wordt nooit ingekort: geen truncate, de tekst wrapt.
 *
 * De delen komen als losse props binnen (nooit tekst-splitsen op "—": een náám mag
 * zelf een streepje bevatten). De volledige tekst is identiek aan
 * `partijIdentiteit(naam, afdeling, organisatie)` (labels.js) — pickers gebruiken die
 * string voor de geselecteerde waarde (een input kent geen twee tinten), dit component
 * voor lijsten/kolommen/koppen. Fix afwijkingen HIER, niet per consument.
 */
import { computed, watchEffect } from 'vue'

const props = defineProps({
  naam: { type: String, default: '' },
  afdeling: { type: String, default: '' },
  organisatie: { type: String, default: '' },
})

// LI040-harding — een lege naam is een PROGRAMMEERFOUT van de consument (verkeerde
// veldnaam, niet-aangeleverde data), nooit een geldige weergave: zonder scanlaag blijft
// alleen de gedempte leeslaag over en zijn alle regels identiek (de partijpicker-bug).
// Faal LUID: een zichtbare ⚠-marker (in élke omgeving — dit mag nooit stil doorglippen)
// + console.error zodat de dev-console de consument aanwijst.
const naamOntbreekt = computed(() => !(props.naam || '').trim())
watchEffect(() => {
  if (naamOntbreekt.value) {
    console.error(
      '[IdentiteitLabel] lege naam — de consument levert de naam niet (verkeerde veldnaam?). '
      + `context: afdeling="${props.afdeling}" organisatie="${props.organisatie}"`,
    )
  }
})

const rest = computed(() =>
  [props.afdeling, props.organisatie].map((d) => (d || '').trim()).filter(Boolean).join(' — '),
)
</script>

<template>
  <span class="whitespace-normal">
    <span
      v-if="naamOntbreekt"
      class="font-semibold text-[var(--lk-color-danger)]"
      data-testid="identiteit-naam-ontbreekt"
    >⚠ naam ontbreekt</span
    ><span v-else>{{ naam }}</span
    ><span
      v-if="rest"
      class="text-[var(--lk-color-text-muted)]"
      data-testid="identiteit-rest"
    > — {{ rest }}</span>
  </span>
</template>
