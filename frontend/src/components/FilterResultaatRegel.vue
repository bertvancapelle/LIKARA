<script setup>
/**
 * FilterResultaatRegel — gedeelde bouwsteen (LI040): "de filterbalk vertelt wat hij doet".
 *
 * Altijd zichtbaar boven een gefilterde lijst, met drie beloften:
 * 1. HET AANTAL, altijd — zonder filters "19 componenten", mét filters "3 van 19
 *    componenten": de gebruiker weet meteen of hij naar het geheel of een selectie kijkt.
 * 2. ELK ACTIEF FILTER UITGESCHREVEN (label + gekozen waarde) als chip — het antwoord op
 *    "waarom is dit leeg?" staat naast de lege-melding, niet verstopt in de dropdowns.
 * 3. ELK FILTER LOS WISBAAR (✕ op de chip; emit 'wis' met de chip-sleutel) — "alles
 *    wissen" blijft een zaak van de lijst zelf.
 *
 * Generiek over lijsten (eenheid/eenheidEnkelvoud als props): de componentenlijst is de
 * eerste consument; contract-/partij-/proces-/bedrijfsfunctie-/architectuurlijst delen
 * dezelfde filterbalk-vorm en haken hier bij hun eigen count-support aan (OPVOLGPUNTEN).
 * Een regel die niet in een bouwsteen zit, wordt bij de volgende lijst geschonden.
 */
const props = defineProps({
  /** Gefilterd totaal over de HELE dataset (null = nog niet geladen → regel verbergt). */
  totaal: { type: Number, default: null },
  /** Ongefilterd totaal; bij actieve filters wordt "X van Y" getoond. */
  totaalAlles: { type: Number, default: null },
  /** [{ sleutel, label, waarde }] — één chip per actief filterveld. */
  chips: { type: Array, default: () => [] },
  eenheid: { type: String, default: 'resultaten' },
  eenheidEnkelvoud: { type: String, default: 'resultaat' },
})
defineEmits(['wis'])

const eenheidVoor = (n) => (n === 1 ? props.eenheidEnkelvoud : props.eenheid)
</script>

<template>
  <div
    v-if="totaal !== null"
    data-testid="resultaat-regel"
    class="mb-[var(--lk-space-md)] flex flex-wrap items-center gap-[var(--lk-space-sm)] text-[length:var(--lk-text-sm)]"
    role="status"
  >
    <span class="font-semibold" data-testid="resultaat-aantal">
      <template v-if="chips.length && totaalAlles !== null">{{ totaal }} van {{ totaalAlles }} {{ eenheidVoor(totaalAlles) }}</template>
      <template v-else>{{ totaal }} {{ eenheidVoor(totaal) }}</template>
    </span>
    <span
      v-for="chip in chips"
      :key="chip.sleutel"
      :data-testid="`filter-chip-${chip.sleutel}`"
      class="inline-flex items-center gap-[var(--lk-space-xs)] rounded-[var(--lk-radius-badge)] bg-[var(--lk-color-accent)] px-[var(--lk-space-sm)] py-[2px]"
    >
      <span><span class="text-[var(--lk-color-text-muted)]">{{ chip.label }}:</span> {{ chip.waarde }}</span>
      <button
        type="button"
        :data-testid="`chip-wis-${chip.sleutel}`"
        :aria-label="`Filter ${chip.label} wissen`"
        class="font-semibold hover:text-[var(--lk-color-danger)] focus:outline-2 focus:outline-offset-2 focus:outline-[var(--lk-color-primary)]"
        @click="$emit('wis', chip.sleutel)"
      >✕</button>
    </span>
  </div>
</template>
