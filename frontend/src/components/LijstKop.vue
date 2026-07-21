<script setup>
/**
 * LijstKop — gedeelde kop-bouwsteen voor élk lijstscherm (LI048).
 *
 * De consultant loopt de hele dag van Componenten naar Partijen naar Contracten. Stond de
 * besturing op elk scherm net iets anders, dan leert hij per scherm opnieuw waar hij zoekt en
 * waar hij iets nieuws maakt. Zes schermen bouwden deze rij al met de hand, byte-identiek —
 * hetzelfde patroon dat `DetailKop` voor detailschermen oploste, alleen zonder bouwsteen.
 *
 * DE VOLGORDE LIGT VAST — dat ís het punt:
 *
 *     [schermnaam]   [zoekveld — de resterende breedte]   [Filter (N)]   [Nieuw …]
 *
 * - **De naam blijft staan, op élk scherm.** Het menu links kan dicht; dan is de naam het enige
 *   dat vertelt waar je bent. Hij is bovendien de paginakop voor een schermlezer, het
 *   browsertabblad en een afdruk.
 * - **De naam houdt zijn eigen breedte, het zoekveld krijgt de rest** (`shrink-0` op de kop,
 *   `flex-1` op het zoekslot) — nooit andersom. De langste schermnaam is "Architectuur — lagen";
 *   die mag het zoekveld niet wegdrukken, en het zoekveld mag de naam niet afkappen.
 * - **De indeling is overal gelijk, ook zonder zoekveld** (regel 3): naam links, acties rechts.
 *   Ontbreekt het zoekveld, dan blijft de ruimte ertussen leeg — de aanmaakknop staat op élk
 *   scherm op dezelfde plek. Hem laten opschuiven betekent dat de consultant hem per scherm
 *   opnieuw moet zoeken. Vandaar de `flex-1`-spacer óók als het slot leeg is.
 *
 * WAT HIER NIET IN HOORT (regel 1): in de kop staat wat de LIJST bepaalt — zoeken, filteren,
 * aanmaken bepalen *welke* dingen je ziet. Een weergaveschakelaar (Boom|Diagram, Lagen|Tabel)
 * bepaalt *hoe* je hetzelfde ziet en hoort in de zone eronder, bij de inhoud. Zonder die grens
 * wordt de kop een verzamelplek en staan er over drie sessies weer dertien dingen.
 *
 * EÉN ACTIE, NIET TWEE (regel 2): alleen de gewone aanmaakactie. Een zeldzame, ingrijpende actie
 * (zoals "Model inlezen") hoort niet in dezelfde vorm naast iets wat de consultant wekelijks doet
 * — dan lijken ze even gewoon. Die gaat naar de zone onder de kop.
 *
 * Slots (elk optioneel; de volgorde is niet door de call-site te wijzigen):
 * - #zoek   — het zoekveld; krijgt de resterende breedte.
 * - #filter — de Filter-knop met zijn teller.
 * - #actie  — de aanmaakactie. Eén.
 *
 * De chiprij met actieve filters hoort ONDER deze kop (`FilterResultaatRegel`), niet erin: hij
 * hoort bij de uitkomst, niet bij de besturing.
 *
 * Bron-scan: `check-css-build.mjs` dwingt af dat een lijstscherm zijn kop niet met de hand
 * bouwt — zonder die scan bouwt het volgende scherm zijn eigen rij terug, en zo zijn deze zes
 * ontstaan.
 */
defineProps({
  /** De schermnaam zoals hij op het scherm staat. Verdwijnt nooit. */
  titel: { type: String, required: true },
  /** id voor de h1 (aria-labelledby van de omliggende section). */
  titelId: { type: String, required: true },
})
</script>

<template>
  <div
    class="mb-[var(--lk-space-md)] flex flex-wrap items-center gap-[var(--lk-space-md)]"
    data-testid="lijst-kop"
  >
    <!-- `shrink-0` + `break-words`: de naam wordt nooit afgekapt en nooit platgedrukt. -->
    <h1
      :id="titelId"
      class="shrink-0 break-words text-[var(--lk-color-primary)]"
      data-testid="lijst-kop-titel"
    >{{ titel }}</h1>

    <!-- Het zoekslot krijgt de resterende breedte. Ook LEEG blijft het de ruimte vullen, zodat
         de actie rechts op élk scherm op dezelfde plek staat (regel 3). `min-w-0` laat het veld
         krimpen op een smal venster in plaats van de rij open te breken. -->
    <div class="min-w-0 flex-1" data-testid="lijst-kop-zoek">
      <slot name="zoek" />
    </div>

    <div v-if="$slots.filter" class="shrink-0" data-testid="lijst-kop-filter">
      <slot name="filter" />
    </div>

    <div v-if="$slots.actie" class="shrink-0" data-testid="lijst-kop-actie">
      <slot name="actie" />
    </div>
  </div>
</template>
