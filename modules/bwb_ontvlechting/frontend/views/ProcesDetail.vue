<script setup>
/**
 * ProcesDetail — één proces met context (ADR-042 slice 4a).
 *
 * Kop: naam + toelichting + (i)-uitleg + klikbare broodkruimel naar boven
 * ("Vergunningverlening › Aanvraag behandelen" — context-in-header-patroon; de keten wordt
 * langs `ouder_id` omhoog gelezen, cyclus-veilig met een visited-set). Deelprocessen = de
 * directe kinderen, met "+ Deelproces toevoegen" op de plek zelf (ouder voorgevuld).
 * Sectie "Componenten in dit proces" = ProcesComponentenSectie (:key op props.id — remount
 * bij detail→detail-navigatie). Het roll-up-inzicht ("incl. onderliggende processen") is
 * bewust ADR-042 slice 5 — hier niet.
 */
import { computed, reactive, ref, watch } from 'vue'
import { Button, Dialog } from '@/primevue'
import { useAuthStore } from '@/store/auth'
import { useTerugNavigatie } from '@/composables/useTerugNavigatie'
import { api } from '@/api'
import ProcesComponentenSectie from './ProcesComponentenSectie.vue'
import VeldUitleg from './VeldUitleg.vue'

const props = defineProps({ id: { type: String, required: true } })

const auth = useAuthStore()
const magBewerken = computed(() => auth.hasRole('medewerker', 'beheerder'))
const { terugLabel, gaTerug } = useTerugNavigatie()

const proces = ref(null)
const voorouders = ref([]) // wortel → directe ouder (voor de broodkruimel)
const kinderen = ref([])
const laden = ref(false)
const fout = ref(null)

async function _laadVoorouders(ouderId) {
  // Keten omhoog langs ouder_id; visited-set = cyclus-veilig (boom is servicegeborgd,
  // maar een leestraversal mag nooit kunnen hangen).
  const keten = []
  const visited = new Set([props.id])
  let huidige = ouderId
  while (huidige && !visited.has(huidige)) {
    visited.add(huidige)
    const p = await api.processen.haal(huidige)
    keten.unshift(p)
    huidige = p.ouder_id
  }
  return keten
}

async function laad() {
  laden.value = true
  fout.value = null
  try {
    const p = await api.processen.haal(props.id)
    proces.value = p
    const [keten, deel] = await Promise.all([
      p.ouder_id ? _laadVoorouders(p.ouder_id) : Promise.resolve([]),
      api.processen.lijst({ ouder_id: props.id, limit: 100 }),
    ])
    voorouders.value = keten
    kinderen.value = deel.items
  } catch (e) {
    fout.value = e?.status === 401 ? null : e?.status === 404 ? 'Dit proces bestaat niet (meer).' : 'Laden van het proces is mislukt.'
  } finally {
    laden.value = false
  }
}

// ── Deelproces toevoegen (ouder voorgevuld = dit proces) ─────────────────────
const addOpen = ref(false)
const addForm = reactive({ naam: '', toelichting: '' })
const addFout = ref(null)
const bezig = ref(false)

function openToevoegen() {
  Object.assign(addForm, { naam: '', toelichting: '' })
  addFout.value = null
  addOpen.value = true
}
async function bevestigToevoegen() {
  addFout.value = null
  if (!addForm.naam.trim()) {
    addFout.value = 'Naam is verplicht.'
    return
  }
  bezig.value = true
  try {
    await api.processen.maak({
      naam: addForm.naam.trim(),
      toelichting: addForm.toelichting.trim() || null,
      ouder_id: props.id, // de context is voorgevuld — actie waar het onderwerp leeft
    })
    addOpen.value = false
    await laad()
  } catch (e) {
    if (e?.status !== 401) addFout.value = e?.message || 'Toevoegen is mislukt.'
  } finally {
    bezig.value = false
  }
}

// Detail-view-norm: props.id-watch i.p.v. onMounted (detail→detail-navigatie herlaadt).
watch(() => props.id, () => laad(), { immediate: true })
</script>

<template>
  <section aria-labelledby="proces-titel">
    <button
      v-if="terugLabel"
      type="button"
      data-testid="terug-knop"
      class="mb-[var(--lk-space-md)] text-[length:var(--lk-text-sm)] text-[var(--lk-color-primary)] hover:underline focus:outline-2 focus:outline-offset-2 focus:outline-[var(--lk-color-primary)]"
      @click="gaTerug"
    >{{ terugLabel }}</button>

    <p v-if="fout" role="alert" data-testid="proces-fout" class="text-[var(--lk-color-danger)]">{{ fout }}</p>
    <p v-else-if="laden && !proces" data-testid="proces-laden" class="text-[var(--lk-color-text-muted)]">Laden…</p>

    <template v-if="proces">
      <div class="mb-[var(--lk-space-md)]">
        <div class="flex items-center gap-[var(--lk-space-xs)]">
          <h1 id="proces-titel" class="text-[length:var(--lk-text-2xl)] font-semibold text-[var(--lk-color-primary)]">
            {{ proces.naam }}
          </h1>
          <VeldUitleg veld="proces" testid="uitleg-proces" />
        </div>
        <!-- Broodkruimel (context-in-header): klikbare keten naar boven. -->
        <p v-if="voorouders.length" class="mt-1 text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]" data-testid="proces-broodkruimel">
          <template v-for="(v, i) in voorouders" :key="v.id">
            <router-link
              :to="{ name: 'proces-detail', params: { id: v.id } }"
              class="text-[var(--lk-color-primary)] hover:underline focus:outline-2 focus:outline-offset-2 focus:outline-[var(--lk-color-primary)]"
            >{{ v.naam }}</router-link>
            <span aria-hidden="true"> › </span>
          </template>
          <span>{{ proces.naam }}</span>
        </p>
        <p v-if="proces.toelichting" class="mt-[var(--lk-space-sm)] max-w-prose" data-testid="proces-toelichting">
          {{ proces.toelichting }}
        </p>
      </div>

      <!-- Deelprocessen — de directe kinderen; actie op de plek zelf (ouder voorgevuld). -->
      <section class="card mb-[var(--lk-space-md)]" aria-labelledby="deelprocessen-titel" data-testid="deelprocessen-sectie">
        <div class="flex items-center gap-[var(--lk-space-md)] mb-[var(--lk-space-sm)]">
          <h2 id="deelprocessen-titel" class="text-[length:var(--lk-text-lg)] font-semibold">Deelprocessen</h2>
          <Button v-if="magBewerken" label="+ Deelproces toevoegen" severity="secondary" data-testid="deelproces-toevoegen" class="ml-auto" @click="openToevoegen" />
        </div>
        <ul v-if="kinderen.length" class="divide-y divide-[var(--lk-color-border)]" data-testid="deelprocessen-lijst">
          <li v-for="kind in kinderen" :key="kind.id" class="py-[var(--lk-space-sm)]">
            <router-link
              :to="{ name: 'proces-detail', params: { id: kind.id } }"
              data-testid="deelproces-link"
              class="font-medium text-[var(--lk-color-primary)] hover:underline focus:outline-2 focus:outline-offset-2 focus:outline-[var(--lk-color-primary)]"
            >{{ kind.naam }}</router-link>
            <span v-if="kind.toelichting" class="block text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]">{{ kind.toelichting }}</span>
          </li>
        </ul>
        <p v-else data-testid="deelprocessen-leeg" class="text-[var(--lk-color-text-muted)]">
          Nog geen deelprocessen.
          <template v-if="magBewerken">Voeg er een toe met "+ Deelproces toevoegen" — dit proces staat dan al als bovenliggend proces ingevuld.</template>
        </p>
      </section>

      <!-- Koppelregels — :key remount bij detail→detail-navigatie (vaste norm). -->
      <ProcesComponentenSectie :key="props.id" :proces-id="props.id" :proces-naam="proces.naam" />
    </template>

    <!-- Deelproces toevoegen -->
    <Dialog v-model:visible="addOpen" modal :closable="false" header="Deelproces toevoegen" data-testid="deelproces-dialog">
      <form class="flex min-w-[22rem] flex-col gap-[var(--lk-space-md)]" @submit.prevent="bevestigToevoegen">
        <p class="text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]">
          Wordt een deelproces van <strong data-testid="deelproces-ouder">{{ proces?.naam }}</strong>.
        </p>
        <p v-if="addFout" role="alert" data-testid="deelproces-fout" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ addFout }}</p>
        <div class="flex flex-col gap-[var(--lk-space-xs)]">
          <label for="deelproces-naam" class="font-semibold">Naam *</label>
          <input id="deelproces-naam" v-model="addForm.naam" type="text" maxlength="255" data-testid="deelproces-naam" class="rounded-[var(--lk-radius-btn)] border border-[var(--lk-color-border)] bg-[var(--lk-color-surface)] px-[var(--lk-space-sm)] py-[var(--lk-space-xs)]" />
        </div>
        <div class="flex flex-col gap-[var(--lk-space-xs)]">
          <label for="deelproces-toelichting" class="font-semibold">Toelichting</label>
          <textarea id="deelproces-toelichting" v-model="addForm.toelichting" rows="3" data-testid="deelproces-toelichting" class="rounded-[var(--lk-radius-btn)] border border-[var(--lk-color-border)] bg-[var(--lk-color-surface)] px-[var(--lk-space-sm)] py-[var(--lk-space-xs)]"></textarea>
        </div>
        <div class="flex gap-[var(--lk-space-md)]">
          <Button type="submit" label="Toevoegen" data-testid="deelproces-opslaan" :disabled="bezig" />
          <Button type="button" label="Annuleren" severity="secondary" @click="addOpen = false" />
        </div>
      </form>
    </Dialog>
  </section>
</template>
