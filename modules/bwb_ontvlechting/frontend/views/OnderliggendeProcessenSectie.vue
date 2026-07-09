<script setup>
/**
 * OnderliggendeProcessenSectie — "Onderliggende processen" (ADR-042 slice 5, samengevoegd
 * blok — ontwerpbesluit LI035): deelprocessen en hun doorgerolde componentregels gaan
 * over hetzelfde onderwerp en vormen daarom ÉÉN blok.
 *
 * Per direct deelproces een kopje (naam klikbaar + toelichting) met daaronder zijn
 * componentregels gegroepeerd (read-only; de groepering ís de herkomst, dus géén
 * bijschrift op regels van het deelproces zelf). Regels uit diepere lagen staan onder
 * het kopje van hun tak (groepeersleutel = `tak_id` uit de backend — namen kunnen
 * botsen, ids niet) mét klikbaar pad-bijschrift vanaf dat deelproces. "+ Deelproces
 * toevoegen" woont in de blokkop (emit — de dialog blijft bij de ouder, met de ouder
 * voorgevuld). Open-tenzij-groot op het geheel: t/m DREMPEL doorgerolde regels direct
 * zichtbaar, daarboven samengevouwen tot de telling-regel (uniek geteld); de kopjes
 * blijven áltijd zichtbaar (navigatie verliest niets). Uitklapstand onthouden via het
 * lijststaat-patroon. Lege staat zonder deelprocessen: rustige tekst + de toevoegknop.
 */
import { computed, ref, watch } from 'vue'
import { Button } from '@/primevue'
import { api } from '@/api'
import { useAuthStore } from '@/store/auth'
import { useLijstStaat } from '@/composables/useLijstStaat'
import MeldingBanner from '@/components/MeldingBanner.vue'

const props = defineProps({
  procesId: { type: String, required: true },
  // De directe deelprocessen — de ouder (ProcesDetail) laadt ze al; geen dubbele fetch.
  kinderen: { type: Array, default: () => [] },
})
const emit = defineEmits(['toevoegen'])

const auth = useAuthStore()
const magBewerken = computed(() => auth.hasRole('medewerker', 'beheerder'))

// Open-tenzij-groot: tot en met deze drempel staan de doorgerolde regels direct open.
const DREMPEL = 10

const regels = ref([])
const laden = ref(false)
const fout = ref(null)
const open = ref(true)

// Uitklapstand onthouden per proces (lijststaat-patroon; sessie-momentstaat).
const { herstel } = useLijstStaat(`proces-onderliggend:${props.procesId}`, { open }, {
  valideer: { open: (w) => typeof w === 'boolean' },
})

const aantalComponenten = computed(() => new Set(regels.value.map((r) => r.component_id)).size)
const aantalHerkomst = computed(() => new Set(regels.value.map((r) => r.proces_id)).size)

const regelsPerTak = computed(() => {
  const m = new Map()
  for (const r of regels.value) {
    const tak = r.tak_id ?? r.proces_id
    if (!m.has(tak)) m.set(tak, [])
    m.get(tak).push(r)
  }
  return m
})

// Groepen = de directe deelprocessen; vangnet voor regels waarvan de tak buiten de
// kinderen-lijst valt (bv. voorbij de lijst-limiet): eigen kopje op tak-naam.
const groepen = computed(() => {
  const bekend = new Set(props.kinderen.map((k) => k.id))
  const extra = []
  for (const [tak, rs] of regelsPerTak.value) {
    if (!bekend.has(tak)) {
      extra.push({ id: tak, naam: rs[0]?.proces_pad?.[0] || rs[0]?.proces_naam || 'Deelproces', toelichting: null })
      bekend.add(tak)
    }
  }
  return [...props.kinderen, ...extra]
})

async function laad() {
  if (!props.kinderen.length) {
    regels.value = []
    return
  }
  laden.value = true
  fout.value = null
  try {
    regels.value = await api.processen.rollup(props.procesId)
    // Standaardstand uit de data (open-tenzij-groot); een bewaarde stand wint.
    open.value = regels.value.length <= DREMPEL
    herstel()
  } catch (e) {
    fout.value = e?.status === 401 ? null : 'Laden van de componenten in onderliggende processen is mislukt.'
  } finally {
    laden.value = false
  }
}

function wissel() {
  open.value = !open.value
}

// De ouder laadt de kinderen ná de proces-mount — reageer op beide.
watch(() => [props.procesId, props.kinderen], () => laad(), { immediate: true })
</script>

<template>
  <section class="card mt-[var(--lk-space-md)]" aria-labelledby="onderliggend-titel" data-testid="onderliggend-sectie">
    <div class="flex items-center gap-[var(--lk-space-md)] mb-[var(--lk-space-sm)]">
      <h2 id="onderliggend-titel" class="text-[length:var(--lk-text-lg)] font-semibold">Onderliggende processen</h2>
      <Button
        v-if="magBewerken"
        label="+ Deelproces toevoegen"
        severity="secondary"
        data-testid="deelproces-toevoegen"
        class="ml-auto"
        @click="emit('toevoegen')"
      />
    </div>

    <MeldingBanner v-if="fout" soort="danger" :tekst="fout" testid="rollup-fout" />

    <!-- Lege staat: een blad-proces — de toevoegknop staat in de blokkop. -->
    <p v-if="!kinderen.length" data-testid="deelprocessen-leeg" class="text-[var(--lk-color-text-muted)]">
      Nog geen deelprocessen.
      <template v-if="magBewerken">Voeg er een toe met "+ Deelproces toevoegen" — dit proces staat dan al als bovenliggend proces ingevuld.</template>
    </p>

    <template v-else>
      <!-- Open-tenzij-groot op het geheel; de kopjes hieronder blijven altijd staan. -->
      <button
        v-if="regels.length"
        type="button"
        data-testid="rollup-wissel"
        :aria-expanded="open"
        class="mb-[var(--lk-space-sm)] text-left font-medium text-[var(--lk-color-primary)] hover:underline focus:outline-2 focus:outline-offset-2 focus:outline-[var(--lk-color-primary)]"
        @click="wissel"
      >
        <template v-if="!open">Nog {{ aantalComponenten }} component(en) via {{ aantalHerkomst }} deelproces(sen) ▸</template>
        <template v-else>Verberg de {{ aantalComponenten }} component(en) via {{ aantalHerkomst }} deelproces(sen) ▾</template>
      </button>

      <ul class="divide-y divide-[var(--lk-color-border)]" data-testid="onderliggend-groepen">
        <li v-for="kind in groepen" :key="kind.id" class="py-[var(--lk-space-sm)]" :data-testid="`groep-${kind.id}`">
          <!-- Kopje: het deelproces zelf (klikbaar) + toelichting. -->
          <router-link
            :to="{ name: 'proces-detail', params: { id: kind.id } }"
            data-testid="deelproces-link"
            class="font-medium text-[var(--lk-color-primary)] hover:underline focus:outline-2 focus:outline-offset-2 focus:outline-[var(--lk-color-primary)]"
          >{{ kind.naam }}</router-link>
          <span v-if="kind.toelichting" class="block text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]">{{ kind.toelichting }}</span>

          <!-- De componentregels van deze tak — alleen in de open stand. -->
          <template v-if="open">
            <ul
              v-if="regelsPerTak.get(kind.id)?.length"
              class="mt-[var(--lk-space-xs)] pl-[var(--lk-space-md)]"
              :data-testid="`groep-regels-${kind.id}`"
            >
              <li
                v-for="regel in regelsPerTak.get(kind.id)"
                :key="regel.vervulling_id"
                class="py-[var(--lk-space-xs)]"
                :data-testid="`rollup-regel-${regel.vervulling_id}`"
              >
                <span class="min-w-0">
                  <router-link
                    :to="{ name: 'component-detail', params: { id: regel.component_id } }"
                    data-testid="rollup-component-link"
                    class="text-[var(--lk-color-primary)] hover:underline focus:outline-2 focus:outline-offset-2 focus:outline-[var(--lk-color-primary)]"
                  >{{ regel.component_naam }}</router-link>
                  <span v-if="regel.componenttype_label" class="text-[length:var(--lk-text-xs)] text-[var(--lk-color-text-muted)]"> ({{ regel.componenttype_label }})</span>
                  — <em>{{ regel.applicatiefunctie_label }}</em>
                </span>
                <!-- Alleen diepere lagen dragen een pad-bijschrift; op het niveau van het
                     kopje zelf ís de groepering de herkomst. -->
                <span
                  v-if="(regel.proces_pad?.length || 0) > 1"
                  class="block text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]"
                  data-testid="rollup-herkomst"
                >
                  via ›
                  <router-link
                    :to="{ name: 'proces-detail', params: { id: regel.proces_id } }"
                    data-testid="rollup-herkomst-link"
                    class="hover:underline focus:outline-2 focus:outline-offset-2 focus:outline-[var(--lk-color-primary)]"
                  >{{ regel.proces_pad.slice(1).join(' › ') }}</router-link>
                </span>
              </li>
            </ul>
            <p
              v-else
              class="mt-[var(--lk-space-xs)] pl-[var(--lk-space-md)] text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]"
              :data-testid="`groep-leeg-${kind.id}`"
            >Nog geen componenten.</p>
          </template>
        </li>
      </ul>
    </template>
  </section>
</template>
