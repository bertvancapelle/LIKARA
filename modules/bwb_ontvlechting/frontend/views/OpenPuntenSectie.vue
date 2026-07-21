<script setup>
/**
 * OpenPuntenSectie — "wat heeft dit component nog nodig?" (LI047, ADR-052 besluiten 1-22).
 *
 * De consultant hoefde voorheen zes tot acht plekken langs om te weten of hij klaar was. Hier staat
 * het bij elkaar, met per punt een route naar de plek waar hij het antwoord vastlegt.
 *
 * Drie blokken als één SCHAKELAAR met de teller in elke stand (besluit 2; vorm herzien LI048 2c/2d
 * — het waren tabbladen, maar ze wisselen geen paneel: ze filteren één lijst, en de tab-semantiek
 * wees naar panelen die niet bestonden). Teller én lijst komen uit dezelfde respons (besluit 14) —
 * het getal is `aantal` uit de server, dat per definitie de lengte van `punten` is; hier wordt
 * niets opnieuw geteld.
 *
 * Nul is een uitkomst, geen storing (besluit 4): een leeg blok blijft bestaan, toont "0" en zegt
 * geopend wát er niets open is.
 */
import { computed, ref, watch } from 'vue'
import { NORM_FEIT_LABEL } from '../labels'
// ADR-052 besluit 8 — de gedeelde PRESENTATIE-bron voor de twee soorten norm-afwijking. Dit
// venster en het migratiegereedheid-blok lazen al dezelfde afleiding (`splits_afwijking`), maar
// toonden hem verschillend; nu erven beide de toon uit één plek (LI043).
import { AFWIJKING_CODERING, afwijkingZin } from '../afwijkingCodering'

// LI047 snede 2 — ÉÉN laadpunt: `ComponentDetail` haalt de open punten op en voedt hiermee zowel
// het getal in het tablabel "Open punten (N)" als deze lijst. Deze sectie laadt dus NIET zelf; een
// tweede aanroep zou twee laadmomenten geven die na een mutatie uiteen kunnen lopen, en dan zegt
// het tabblad "4" terwijl het paneel drie regels toont — een leugen die niemand opmerkt.
// (LI048: het getal stond tot dan op een knop in de detailkop; de bron is dezelfde gebleven.)
const props = defineProps({
  componentId: { type: String, required: true },
  data: { type: Object, default: null },
})
const emit = defineEmits(['ga-naar'])

// Besluit 5 — "Dit moet nog" staat bij binnenkomst open, ook bij terugkeer. Deze keuze leeft
// bewust NIET in de URL en niet in sessionStorage: het blok is geen plek die je deelt, en een
// onthouden sub-blok zou de gebruiker terugzetten op wat hij het laatst opensloeg i.p.v. op wat
// er moet gebeuren. Reset daarom bij elke componentwissel.
const BLOKKEN = [
  { key: 'moet_nog', label: 'Dit moet nog' },
  { key: 'netjes', label: 'Dit zou netjes zijn' },
  { key: 'valt_op', label: 'Dit valt op' },
]
const actiefBlok = ref('moet_nog')

// Besluit 4 — de teller staat in het filterlabel en komt uit dezelfde respons als de lijst.
const blokFilters = computed(() =>
  BLOKKEN.map((b) => ({ key: b.key, label: `${b.label} (${props.data?.[b.key]?.aantal ?? 0})` })),
)
const huidig = computed(() => props.data?.[actiefBlok.value] ?? { aantal: 0, punten: [] })
const kv = computed(() => props.data?.klaarverklaring ?? null)
// De feitnamen komen uit de gedeelde labelbron (besluit 20); de TOON uit `afwijkingCodering`.
const _labels = (feiten) => (feiten ?? []).map((f) => NORM_FEIT_LABEL[f] ?? f)
const bewustLabels = computed(() => _labels(kv.value?.bewust))
const verschovenLabels = computed(() => _labels(kv.value?.verschoven))

// Besluit 3 — blok 3 draagt wat géén ontbrekend feit is; de checklistregel is GEBUNDELD.
const VALT_OP_TEKST = {
  checklist_nee_deels: (n) => `${n} checklistantwoord${n === 1 ? '' : 'en'} op "nee" of "deels"`,
  staat_los: () => 'Dit component staat los in het landschap — er is geen koppeling vastgelegd',
}

// Besluit 4 — wát er niets open is, per blok. Eén rustige regel, geen lege staat met een uitroep.
const LEEG_TEKST = {
  moet_nog: 'Er staat niets meer open dat uw organisatie verplicht heeft gesteld.',
  netjes: 'Alle overige feiten zijn vastgesteld.',
  valt_op: 'Er is niets bijzonders opgevallen bij dit component.',
}

// Datum in gewone taal, zoals elders in LIKARA (MigratiegereedheidSectie gebruikt dezelfde vorm).
const _datum = (iso) => (iso ? new Date(iso).toLocaleString('nl-NL', { dateStyle: 'medium', timeStyle: 'short' }) : '')

// Besluit 16 — de verantwoording draagt WIE én WANNEER. Zonder moment is het geen verantwoording:
// je wilt weten of het besluit van vorige week is of van twee jaar geleden, want dat bepaalt of het
// nog geldt. `verklaard_op` is NOT NULL, dus het moment is er altijd; de NAAM is nullable (de kolom
// mag leeg zijn en is dat in het hele demolandschap). Bij een lege naam laten we geen gat vallen en
// schrijven we ook geen "onbekend" alsof dat een persoon is — de zin zegt dán expliciet dát het
// ontbreekt, want dit is juist de zin die verantwoording moet afleggen.
const verantwoordingszin = computed(() => {
  const wanneer = _datum(kv.value?.verklaard_op)
  const wie = kv.value?.verklaard_door
  if (wie && wanneer) return `Dit component is op ${wanneer} klaar verklaard door ${wie}.`
  if (wie) return `Dit component is klaar verklaard door ${wie}; wanneer dat gebeurde is niet vastgelegd.`
  if (wanneer) return `Dit component is op ${wanneer} klaar verklaard; wie dat deed is niet vastgelegd.`
  return 'Dit component is klaar verklaard; wie dat deed en wanneer is niet vastgelegd.'
})

function puntLabel(punt) {
  // Besluit 20 — de feitnamen komen uit de gedeelde labelbron; geen plek waar hetzelfde feit
  // anders heet dan op het scherm waar je het vastlegt.
  if (punt.feit) return NORM_FEIT_LABEL[punt.feit] ?? punt.feit
  return (VALT_OP_TEKST[punt.soort] ?? (() => punt.soort))(punt.aantal)
}

// Besluit 5 — bij een componentwissel terug naar "Dit moet nog": de bezoeker wil zien wat er moet,
// niet welk blok hij het laatst opensloeg.
watch(() => props.componentId, () => { actiefBlok.value = 'moet_nog' })

</script>

<template>
  <section data-testid="open-punten-sectie">
    <div class="lk-kop-rij gap-[var(--lk-space-md)] mb-[var(--lk-space-sm)]">
      <h2 id="open-punten-titel">Wat heeft dit component nog nodig</h2>
    </div>

    <template v-if="props.data">
      <!-- Besluiten 16/17 — vóór klaarverklaring neutraal; erná verantwoording, mét wie en wanneer.
           De punten verdwijnen niet (15): er is besloten er niet op te wachten, niet dat ze weg zijn. -->
      <div
        v-if="kv"
        data-testid="op-klaarverklaring"
        class="mb-[var(--lk-space-md)] rounded-[var(--lk-radius-card)] border border-[var(--lk-color-border)] bg-[var(--lk-color-surface)] p-[var(--lk-space-sm)]"
      >
        <p data-testid="op-kv-zin" class="text-[length:var(--lk-text-sm)]">
          {{ verantwoordingszin }}
          De punten hieronder zijn niet vastgesteld; er is besloten er niet op te wachten.
        </p>
        <!-- Besluit 17 / besluit 8 (slice 4a) — nooit op één hoop: LIKARA schrijft geen besluit toe
             aan wie het niet nam. De twee soorten stonden hier in dezelfde toon, met alleen andere
             woorden; wie snel las kon het besluit van de organisatie aanzien voor dat van de mens.
             Toon, icoon én zinsbouw komen nu uit `afwijkingCodering` — dezelfde bron die het
             migratiegereedheid-blok gebruikt, zodat hetzelfde feit er overal hetzelfde uitziet.
             Beide kunnen tegelijk staan (besluit 3): het een overschrijft het ander niet. -->
        <p
          v-if="bewustLabels.length"
          data-testid="op-kv-bewust"
          :class="[AFWIJKING_CODERING.bewust.klasse, 'mt-[var(--lk-space-sm)] flex items-start gap-[var(--lk-space-xs)] px-[var(--lk-space-sm)] py-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]']"
        >
          <span aria-hidden="true">{{ AFWIJKING_CODERING.bewust.icoon }}</span>
          <span>{{ afwijkingZin('bewust', bewustLabels) }}</span>
        </p>
        <p
          v-if="verschovenLabels.length"
          data-testid="op-kv-verschoven"
          :class="[AFWIJKING_CODERING.verschoven.klasse, 'mt-[var(--lk-space-sm)] flex items-start gap-[var(--lk-space-xs)] px-[var(--lk-space-sm)] py-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]']"
        >
          <span aria-hidden="true">{{ AFWIJKING_CODERING.verschoven.icoon }}</span>
          <span>{{ afwijkingZin('verschoven', verschovenLabels) }}</span>
        </p>
      </div>

      <!-- LI048 2c/2d — één SCHAKELAAR met drie standen, geen tabrij. Deze drie wisselen geen
           paneel: ze filteren één lijst (`huidig`). Ze waren als `AppTabs` gebouwd, dus met
           `role="tab"` en `aria-controls` naar `open-punten-panel-*` — panelen die niet bestaan;
           er is geen enkele `role="tabpanel"` in deze sectie. Een schermlezer kondigde daarmee
           een tabblad aan en verwees naar het niets. Nu toggle-knoppen in een `role="group"`:
           `aria-pressed` zegt wat waar is, en de vorm (`.lk-schakelaar`) zegt dat dit één keuze
           is en geen plek waar je heen gaat. -->
      <div
        role="group"
        aria-label="Soorten open punten"
        data-testid="op-filters"
        class="lk-schakelaar mb-[var(--lk-space-sm)]"
      >
        <button
          v-for="b in blokFilters"
          :key="b.key"
          type="button"
          class="lk-schakelaar-stand"
          :aria-pressed="b.key === actiefBlok"
          :data-testid="`op-filter-${b.key}`"
          @click="actiefBlok = b.key"
        >{{ b.label }}</button>
      </div>

      <!-- Het kader om wat er UIT de gekozen stand komt. Zonder dit hing de lijst los onder de
           schakelaar en moest de consultant het verband aannemen; nu wisselt de inhoud zichtbaar
           BINNEN dit kader. De vulling blijft wit — de signalen erin hebben een schone vloer. -->
      <div class="lk-inhoudskader" data-testid="op-inhoudskader">
        <!-- Besluit 21 — de norm-aanduiding staat ÉÉN keer boven het blok, niet per rij: in blok 1
             is elk punt per definitie een norm-feit, en dat tien keer herhalen is geen informatie.
             Hij hoort BINNEN het kader (bovenaan, met een lijn eronder): de regel verandert mee per
             stand, en buiten het kader zou hij lijken te gelden voor alle drie. -->
        <p
          v-if="actiefBlok === 'moet_nog' && huidig.aantal"
          data-norm-lat
          data-testid="op-norm-aanduiding"
          class="lk-inhoudskader-uitleg text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]"
        >
          Uw organisatie heeft deze feiten verplicht gesteld om een component klaar te kunnen verklaren.
        </p>

        <p
          v-if="!huidig.aantal"
          :data-testid="`op-leeg-${actiefBlok}`"
          class="text-[var(--lk-color-text-muted)]"
        >
          {{ LEEG_TEKST[actiefBlok] }}
        </p>

        <ul v-else class="flex flex-col gap-[var(--lk-space-xs)]" :data-testid="`op-lijst-${actiefBlok}`">
          <li
            v-for="(punt, i) in huidig.punten"
            :key="punt.feit ?? punt.soort"
            :data-testid="`op-punt-${punt.feit ?? punt.soort}`"
            class="lk-rij flex items-center gap-[var(--lk-space-sm)] border-t border-[var(--lk-color-border)] py-[var(--lk-space-xs)]"
            :class="i === 0 ? 'border-t-0' : ''"
          >
            <span class="min-w-0 flex-1">{{ puntLabel(punt) }}</span>
            <!-- Besluit 8 — elk punt een route. Geen route betekent dat er voor DIT componenttype
                 geen plek is om het antwoord vast te leggen; dan liever geen knop dan een dode link
                 (ADR-054: nooit een route beloven waar niets te landen valt). -->
            <button
              v-if="punt.route"
              type="button"
              :data-testid="`op-ga-${punt.feit ?? punt.soort}`"
              class="shrink-0 text-[var(--lk-color-primary)] hover:underline"
              @click="emit('ga-naar', punt.route)"
            >
              Vastleggen
            </button>
            <span
              v-else
              :data-testid="`op-geen-route-${punt.feit ?? punt.soort}`"
              class="shrink-0 text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]"
            >Geen invoerplek voor dit componenttype</span>
          </li>
        </ul>
      </div>
    </template>
  </section>
</template>
