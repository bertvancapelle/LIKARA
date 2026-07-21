<script>
/**
 * Icoon — de tekens van LIKARA, in één bestand (LI048).
 *
 * WAAROM DIT BESTAAT en niet een iconenpakket:
 * Voor twee tekens honderden andere binnenhalen is scheef — plus een fontbestand dat bij élk
 * bezoek meelaadt en een afhankelijkheid die bij elke opwaardering terugkomt. En géén emoji: die
 * zien er op elk apparaat anders uit en volgen de kleur van de knop niet, waardoor het beeld
 * afhangt van de computer van de consultant. Dat is precies wat deze sessie bij de tabbladen en
 * de lijnen is rechtgetrokken.
 *
 * WAAR TEKENS WÉL VOOR ZIJN — de grens ligt niet bij de lengte van het woord maar bij **wat er
 * gebeurt als je verkeerd klikt**:
 * - Een **wegwijzer** brengt je ergens heen. Verkeerd geklikt? Dan ga je terug; een teken dat je
 *   even niet herkent kost één klik.
 * - Een **handeling** verandert iets. "Heropenen" geeft werk terug aan de wachtrij, "Verwijderen"
 *   is definitief. Die moeten in één blik te lezen zijn, ook door iemand die het scherm voor het
 *   eerst ziet. Een tooltip verschijnt pas als je met de muis blijft hangen — dus alleen als je al
 *   vermoedt wat er staat — en op een tablet helemaal niet. Voor een wegwijzer prima; voor een
 *   knop die iets weggooit te laat.
 *
 * Daarom staan hier ALLEEN wegwijzers. Komt er ooit een verzoek om Bewerken of Verwijderen een
 * teken te geven "voor de consistentie": dat is een bewust afgewezen keuze, geen omissie.
 *
 * VORM: `currentColor` en `1em`, dus het teken erft kleur én grootte van de knop waarin het staat.
 * Zet er nooit een vaste kleur of pixelmaat op — dan loopt het uit de pas met de tekst ernaast,
 * en valt een knoppenrij visueel uiteen (het probleem van de lijstkop eerder deze sessie).
 *
 * TOEGANKELIJKHEID: het teken zelf is `aria-hidden`. De naam hoort op de KNOP (`aria-label`),
 * niet op het pad — anders leest een schermlezer de knop als "knop" of dubbelt hij de tekst.
 */
const TEKENS = {
  // Het gevouwen kaartje: drie panelen met een knik ertussen, zoals in elke navigatie-app.
  kaart: {
    titel: 'Kaart',
    paden: [
      'M9 3 3 5.5v15L9 18l6 3 6-2.5v-15L15 6 9 3Z',
      'M9 3v15',
      'M15 6v15',
    ],
  },
  // Klok met een pijl tegen de wijzers in — het standaardteken voor terugkijken in de tijd,
  // bekend van "ongedaan maken" en versiegeschiedenis.
  geschiedenis: {
    titel: 'Geschiedenis',
    paden: [
      'M3 12a9 9 0 1 0 3-6.7',            // cirkel met een opening linksboven
      'M3 4v4h4',                          // de terugpijl in die opening
      'M12 7v5l3.5 2',                     // de wijzers
    ],
  },
}

export { TEKENS }
</script>

<script setup>
const props = defineProps({
  /** Naam van het teken; moet in TEKENS staan. */
  naam: {
    type: String,
    required: true,
    // Een onbekende naam is een PROGRAMMEERFOUT en moet luid falen, niet stil niets renderen.
    // Precies zo ontstond het defect dat deze slice opruimt: `icon="pi pi-info-circle"` verwees
    // naar een klasse die nergens bestond, dus er rendert al maanden niets zonder dat iets het
    // meldde. Een validator faalt in dev luid in de console; de bron-scan in check-css-build.mjs
    // vangt het bij élke build, ook in productie.
    validator: (waarde) => Object.hasOwn(TEKENS, waarde),
  },
})
</script>

<template>
  <svg
    v-if="TEKENS[naam]"
    :data-icoon="naam"
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 24 24"
    width="1em"
    height="1em"
    fill="none"
    stroke="currentColor"
    stroke-width="1.75"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
    focusable="false"
    class="inline-block shrink-0 align-[-0.125em]"
  >
    <path v-for="(d, i) in TEKENS[naam].paden" :key="i" :d="d" />
  </svg>
</template>
