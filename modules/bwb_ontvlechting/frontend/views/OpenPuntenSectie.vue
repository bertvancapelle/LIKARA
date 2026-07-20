<script setup>
/**
 * OpenPuntenSectie — "wat heeft dit component nog nodig?" (LI047, ADR-052 besluiten 1-22).
 *
 * De consultant hoefde voorheen zes tot acht plekken langs om te weten of hij klaar was. Hier staat
 * het bij elkaar, met per punt een route naar de plek waar hij het antwoord vastlegt.
 *
 * Drie blokken als sub-tabbladen met de teller in de naam (besluit 2). Teller én lijst komen uit
 * dezelfde respons (besluit 14) — het getal is `aantal` uit de server, dat per definitie de lengte
 * van `punten` is; hier wordt niets opnieuw geteld.
 *
 * Nul is een uitkomst, geen storing (besluit 4): een leeg blok blijft bestaan, toont "0" en zegt
 * geopend wát er niets open is.
 */
import { computed, ref, watch } from 'vue'
import { api } from '@/api'
import { NORM_FEIT_LABEL } from '../labels'
import AppTabs from './AppTabs.vue'

const props = defineProps({ componentId: { type: String, required: true } })
const emit = defineEmits(['ga-naar'])

const data = ref(null)
const laden = ref(false)
const fout = ref(null)

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

// Besluit 4 — de teller staat in de tabnaam en komt uit dezelfde respons als de lijst.
const blokTabs = computed(() =>
  BLOKKEN.map((b) => ({ key: b.key, label: `${b.label} (${data.value?.[b.key]?.aantal ?? 0})` })),
)
const huidig = computed(() => data.value?.[actiefBlok.value] ?? { aantal: 0, punten: [] })
const kv = computed(() => data.value?.klaarverklaring ?? null)

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

function puntLabel(punt) {
  // Besluit 20 — de feitnamen komen uit de gedeelde labelbron; geen plek waar hetzelfde feit
  // anders heet dan op het scherm waar je het vastlegt.
  if (punt.feit) return NORM_FEIT_LABEL[punt.feit] ?? punt.feit
  return (VALT_OP_TEKST[punt.soort] ?? (() => punt.soort))(punt.aantal)
}

async function laad() {
  laden.value = true
  fout.value = null
  try {
    data.value = await api.componentNormen.openPunten(props.componentId)
  } catch (e) {
    fout.value = e?.status === 401 ? null : e?.message || 'Laden van de open punten mislukt.'
  } finally {
    laden.value = false
  }
}

watch(
  () => props.componentId,
  () => {
    actiefBlok.value = 'moet_nog' // besluit 5 — geen onthouden blok-keuze over componenten heen
    laad()
  },
  { immediate: true },
)

defineExpose({ herlaad: laad })
</script>

<template>
  <section data-testid="open-punten-sectie">
    <div class="lk-kop-rij gap-[var(--lk-space-md)] mb-[var(--lk-space-sm)]">
      <h2 id="open-punten-titel">Wat heeft dit component nog nodig</h2>
    </div>

    <p v-if="fout" role="alert" data-testid="op-fout" class="text-[var(--lk-color-danger)] mb-[var(--lk-space-sm)]">{{ fout }}</p>
    <p v-if="laden" data-testid="op-laden" class="text-[var(--lk-color-text-muted)]">Laden…</p>

    <template v-if="data">
      <!-- Besluiten 16/17 — vóór klaarverklaring neutraal; erná verantwoording, mét wie en wanneer.
           De punten verdwijnen niet (15): er is besloten er niet op te wachten, niet dat ze weg zijn. -->
      <div
        v-if="kv"
        data-testid="op-klaarverklaring"
        class="mb-[var(--lk-space-md)] rounded-[var(--lk-radius-card)] border border-[var(--lk-color-border)] bg-[var(--lk-color-surface)] p-[var(--lk-space-sm)]"
      >
        <p class="text-[length:var(--lk-text-sm)]">
          Dit component is klaar verklaard door <strong>{{ kv.verklaard_door }}</strong>.
          De punten hieronder zijn niet vastgesteld; er is besloten er niet op te wachten.
        </p>
        <!-- Besluit 17 — nooit op één hoop: LIKARA schrijft geen besluit toe aan wie het niet nam. -->
        <p v-if="kv.bewust?.length" data-testid="op-kv-bewust" class="mt-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]">
          Bij het klaar verklaren afgewogen: {{ kv.bewust.map((f) => NORM_FEIT_LABEL[f] ?? f).join(', ') }}.
        </p>
        <p v-if="kv.verschoven?.length" data-testid="op-kv-verschoven" class="mt-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]">
          Pas daarna verplicht gesteld: {{ kv.verschoven.map((f) => NORM_FEIT_LABEL[f] ?? f).join(', ') }}.
        </p>
      </div>

      <AppTabs
        v-model="actiefBlok"
        :tabs="blokTabs"
        id-prefix="open-punten"
        aria-label="Soorten open punten"
      />

      <!-- Besluit 21 — de norm-aanduiding staat ÉÉN keer boven het blok, niet per rij: in blok 1 is
           elk punt per definitie een norm-feit, en dat tien keer herhalen is geen informatie. -->
      <p
        v-if="actiefBlok === 'moet_nog' && huidig.aantal"
        data-norm-lat
        data-testid="op-norm-aanduiding"
        class="mt-[var(--lk-space-sm)] text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]"
      >
        Uw organisatie heeft deze feiten verplicht gesteld om een component klaar te kunnen verklaren.
      </p>

      <p
        v-if="!huidig.aantal"
        :data-testid="`op-leeg-${actiefBlok}`"
        class="mt-[var(--lk-space-md)] text-[var(--lk-color-text-muted)]"
      >
        {{ LEEG_TEKST[actiefBlok] }}
      </p>

      <ul v-else class="mt-[var(--lk-space-sm)] flex flex-col gap-[var(--lk-space-xs)]" :data-testid="`op-lijst-${actiefBlok}`">
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
    </template>
  </section>
</template>
