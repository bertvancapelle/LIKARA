<script setup>
/**
 * ComponentProcessenSectie — "Waarvoor gebruiken we het" / "Vervult een rol in"
 * (ADR-042 slice 4b; de component-zijde van de koppelregel — zelfde regel als op de
 * proces-pagina, twee ingangen).
 *
 * Regels als leesbare zinnen ("*registreren* in Aanvraag behandelen — Vergunningverlening",
 * proces klikbaar, procescontext via het identiteit-patroon). Regel-acties conform het
 * LI035-patroon: Bewerken = dialog op de kenmerk-velden (functie + toelichting; component
 * en proces zijn de ankers en staan read-only), Verwijderen = gedeelde bevestiging met de
 * regel leesbaar. Toevoegregel = proces-ZoekSelect over de hele boom mét context in elke
 * treffer (procesZoek.js) + functie-select + optionele toelichting — direct opslaan per
 * regel. 409 → MeldingBanner (warn); lege staat verwijst voor het aanmaken van processen
 * naar de Processen-pagina (bewust géén ter-plekke-proces-aanmaak). Backend handhaaft.
 */
import { computed, reactive, ref, watch } from 'vue'
import { Button, Dialog, useToast } from '@/primevue'
import { toastSucces } from '@/meldingen'
import { useAuthStore } from '@/store/auth'
import { api } from '@/api'
import BevestigVerwijderDialog from '@/components/BevestigVerwijderDialog.vue'
import MeldingBanner from '@/components/MeldingBanner.vue'
import { maakProcesZoeker } from '../procesZoek'
import ZoekSelect from './ZoekSelect.vue'
import VeldUitleg from './VeldUitleg.vue'

const props = defineProps({
  componentId: { type: String, required: true },
  // Voor de leesbare regel-omschrijving in bevestiging/bewerken.
  componentNaam: { type: String, default: '' },
})

const auth = useAuthStore()
const toast = useToast()
const magKoppelen = computed(() => auth.hasRole('medewerker', 'beheerder'))

const regels = ref([])
const functies = ref([])
const laden = ref(false)
const fout = ref(null)

const { zoekFunctie: zoekProcessen, weergave: procesWeergave } = maakProcesZoeker(api)

// Leesbare proces-identiteit van een regel ("Aanvraag behandelen — Vergunningverlening").
const procesIdentiteit = (regel) =>
  regel.proces_ouder_naam ? `${regel.proces_naam} — ${regel.proces_ouder_naam}` : regel.proces_naam

async function laad() {
  laden.value = true
  fout.value = null
  try {
    const [lijst, opties] = await Promise.all([
      api.procesvervullingen.lijst({ component_id: props.componentId }),
      api.procesvervullingen.functies(),
    ])
    regels.value = lijst
    functies.value = opties
  } catch (e) {
    fout.value = e?.status === 401 ? null : 'Laden van de procesinzet is mislukt.'
  } finally {
    laden.value = false
  }
}

// ── Toevoegregel — direct opslaan per regel ──────────────────────────────────
const nieuwProcesId = ref(null)
const nieuwFunctie = ref('')
const nieuwToelichting = ref('')
const bezig = ref(false)
const toevoegMelding = ref(null)
const veldFouten = ref({})
const pickerKey = ref(0)

function _resetToevoegregel() {
  nieuwProcesId.value = null
  nieuwFunctie.value = ''
  nieuwToelichting.value = ''
  pickerKey.value += 1
}

async function voegToe() {
  toevoegMelding.value = null
  veldFouten.value = {}
  if (!nieuwProcesId.value) veldFouten.value.proces = 'Kies een proces.'
  if (!nieuwFunctie.value) veldFouten.value.functie = 'Kies een applicatiefunctie.'
  if (Object.keys(veldFouten.value).length) return
  bezig.value = true
  try {
    await api.procesvervullingen.maak({
      component_id: props.componentId,
      proces_id: nieuwProcesId.value,
      applicatiefunctie: nieuwFunctie.value,
      toelichting: nieuwToelichting.value.trim() || null,
    })
    toastSucces(toast, 'Toegevoegd')
    _resetToevoegregel()
    await laad()
  } catch (e) {
    if (e?.status === 409 && e?.code === 'VERVULLING_BESTAAT') {
      toevoegMelding.value = 'Deze koppeling bestaat al: dit component vervult deze applicatiefunctie al in dit proces.'
    } else if (e?.status === 422) {
      if (e?.code === 'ONGELDIGE_APPLICATIEFUNCTIE') veldFouten.value.functie = e.message || 'Ongeldige applicatiefunctie.'
      else if (e?.code === 'ONGELDIG_PROCES') veldFouten.value.proces = e.message || 'Ongeldig proces.'
      else veldFouten.value.functie = 'Ongeldige invoer.'
    } else if (e?.status !== 401) {
      toevoegMelding.value = 'Toevoegen is mislukt. Probeer het opnieuw.'
    }
  } finally {
    bezig.value = false
  }
}

function regelOmschrijving(regel) {
  const wie = props.componentNaam || 'dit component'
  return `"${regel.applicatiefunctie_label}" in ${procesIdentiteit(regel)} — ${wie}`
}

// ── Verwijderen — gedeelde bevestiging (LI035) ───────────────────────────────
const verwijderOpen = ref(false)
const teVerwijderen = ref(null)
const verwijderBezig = ref(false)
function vraagVerwijder(regel) {
  teVerwijderen.value = regel
  verwijderOpen.value = true
}
async function bevestigVerwijder() {
  verwijderBezig.value = true
  try {
    await api.procesvervullingen.verwijder(teVerwijderen.value.vervulling_id)
    toastSucces(toast, 'Verwijderd')
    verwijderOpen.value = false
    await laad()
  } catch (e) {
    if (e?.status !== 401) fout.value = 'Verwijderen van de koppeling is mislukt.'
    verwijderOpen.value = false
  } finally {
    verwijderBezig.value = false
  }
}

// ── Bewerken — dialog op de kenmerk-velden; ankers read-only (LI035) ─────────
const bewerkOpen = ref(false)
const bewerkRegel = ref(null)
const bewerkForm = reactive({ applicatiefunctie: '', toelichting: '' })
const bewerkMelding = ref(null)
const bewerkFouten = reactive({})
const bewerkBezig = ref(false)

const bewerkFunctieOpties = computed(() => {
  const basis = [...functies.value]
  const huidig = bewerkRegel.value
  if (huidig && !basis.some((f) => f.optie_sleutel === huidig.applicatiefunctie)) {
    basis.push({
      optie_sleutel: huidig.applicatiefunctie,
      label: `${huidig.applicatiefunctie_label} (niet meer actief)`,
    })
  }
  return basis
})

function openBewerken(regel) {
  bewerkRegel.value = regel
  Object.assign(bewerkForm, {
    applicatiefunctie: regel.applicatiefunctie,
    toelichting: regel.toelichting || '',
  })
  bewerkMelding.value = null
  Object.keys(bewerkFouten).forEach((k) => delete bewerkFouten[k])
  bewerkOpen.value = true
}
async function bevestigBewerken() {
  bewerkMelding.value = null
  Object.keys(bewerkFouten).forEach((k) => delete bewerkFouten[k])
  if (!bewerkForm.applicatiefunctie) {
    bewerkFouten.functie = 'Kies een applicatiefunctie.'
    return
  }
  bewerkBezig.value = true
  try {
    await api.procesvervullingen.werkBij(bewerkRegel.value.vervulling_id, {
      applicatiefunctie: bewerkForm.applicatiefunctie,
      toelichting: bewerkForm.toelichting.trim() || null,
    })
    toastSucces(toast, 'Opgeslagen')
    bewerkOpen.value = false
    await laad()
  } catch (e) {
    if (e?.status === 409 && e?.code === 'VERVULLING_BESTAAT') {
      bewerkMelding.value = 'Deze koppeling bestaat al: dit component vervult deze applicatiefunctie al in dit proces.'
    } else if (e?.status === 422) {
      bewerkFouten.functie = e?.message || 'Ongeldige applicatiefunctie.'
    } else if (e?.status !== 401) {
      bewerkMelding.value = 'Opslaan is mislukt. Probeer het opnieuw.'
    }
  } finally {
    bewerkBezig.value = false
  }
}

// Conflict-banners verdwijnen zodra de invoer wijzigt.
watch([nieuwProcesId, nieuwFunctie, nieuwToelichting], () => {
  toevoegMelding.value = null
})
watch(bewerkForm, () => {
  bewerkMelding.value = null
})

watch(() => props.componentId, () => laad(), { immediate: true })
</script>

<template>
  <section class="card" aria-labelledby="comp-processen-titel" data-testid="component-processen-sectie">
    <div class="mb-[var(--lk-space-sm)] flex items-center gap-[var(--lk-space-xs)]">
      <h2 id="comp-processen-titel" class="text-[length:var(--lk-text-lg)] font-semibold">
        Waarvoor gebruiken we het
      </h2>
      <VeldUitleg veld="applicatiefunctie" testid="uitleg-applicatiefunctie-comp" />
    </div>

    <p v-if="fout" role="alert" data-testid="cps-fout" class="mb-[var(--lk-space-sm)] text-[var(--lk-color-danger)]">{{ fout }}</p>
    <p v-else-if="laden && !regels.length" data-testid="cps-laden" class="text-[var(--lk-color-text-muted)]">Laden…</p>

    <ul v-if="regels.length" class="mb-[var(--lk-space-md)] divide-y divide-[var(--lk-color-border)]" data-testid="cps-regels">
      <li
        v-for="regel in regels"
        :key="regel.vervulling_id"
        class="flex items-baseline gap-[var(--lk-space-sm)] py-[var(--lk-space-sm)]"
        :data-testid="`cps-regel-${regel.vervulling_id}`"
      >
        <span class="min-w-0">
          <em data-testid="cps-functie">{{ regel.applicatiefunctie_label }}</em>
          in
          <router-link
            :to="{ name: 'proces-detail', params: { id: regel.proces_id } }"
            data-testid="cps-proces-link"
            class="font-medium text-[var(--lk-color-primary)] hover:underline focus:outline-2 focus:outline-offset-2 focus:outline-[var(--lk-color-primary)]"
          >{{ procesIdentiteit(regel) }}</router-link>
          <span v-if="regel.toelichting" class="block text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]">{{ regel.toelichting }}</span>
        </span>
        <div v-if="magKoppelen" class="ml-auto flex shrink-0 items-center gap-[var(--lk-space-xs)]">
          <Button label="Bewerken" severity="secondary" :data-testid="`cps-bewerk-${regel.vervulling_id}`" @click="openBewerken(regel)" />
          <Button label="Verwijderen" severity="danger" :data-testid="`cps-verwijder-${regel.vervulling_id}`" @click="vraagVerwijder(regel)" />
        </div>
      </li>
    </ul>
    <p v-else-if="!laden && !fout" data-testid="cps-leeg" class="mb-[var(--lk-space-md)] text-[var(--lk-color-text-muted)]">
      Nog niet vastgelegd in welke processen dit component een rol vervult.
      <template v-if="magKoppelen">
        Leg de eerste koppeling hieronder. Bestaat het proces nog niet? Maak het eerst aan op de
        <router-link :to="{ name: 'proces-lijst' }" data-testid="cps-naar-processen" class="text-[var(--lk-color-primary)] hover:underline">Processen-pagina</router-link>.
      </template>
    </p>

    <!-- Toevoegregel — direct opslaan per regel; banner boven de velden (LI035). -->
    <form v-if="magKoppelen" class="flex flex-wrap items-end gap-[var(--lk-space-md)]" data-testid="cps-toevoegregel" @submit.prevent="voegToe">
      <MeldingBanner v-if="toevoegMelding" class="w-full" soort="warn" :tekst="toevoegMelding" testid="cps-melding" />
      <label class="flex min-w-[16rem] flex-1 flex-col gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]">
        <span class="text-[length:var(--lk-text-xs)] font-semibold uppercase tracking-wide text-[var(--lk-color-text-muted)]">Proces</span>
        <ZoekSelect
          :key="pickerKey"
          v-model="nieuwProcesId"
          :zoek-functie="zoekProcessen"
          :weergave="procesWeergave"
          placeholder="Zoek een proces…"
          testid="cps-proces"
          :invalid="!!veldFouten.proces"
        />
        <span v-if="veldFouten.proces" role="alert" data-testid="cps-fout-proces" class="text-[var(--lk-color-danger)]">{{ veldFouten.proces }}</span>
      </label>
      <label class="flex flex-col gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]">
        <span class="text-[length:var(--lk-text-xs)] font-semibold uppercase tracking-wide text-[var(--lk-color-text-muted)]">Applicatiefunctie</span>
        <select
          v-model="nieuwFunctie"
          data-testid="cps-functie-select"
          :aria-invalid="!!veldFouten.functie"
          class="lk-veld"
        >
          <option value="">— kies —</option>
          <option v-for="f in functies" :key="f.optie_sleutel" :value="f.optie_sleutel">{{ f.label }}</option>
        </select>
        <span v-if="veldFouten.functie" role="alert" data-testid="cps-fout-functie" class="text-[var(--lk-color-danger)]">{{ veldFouten.functie }}</span>
      </label>
      <label class="flex min-w-[14rem] flex-1 flex-col gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]">
        <span class="text-[length:var(--lk-text-xs)] font-semibold uppercase tracking-wide text-[var(--lk-color-text-muted)]">Toelichting (optioneel)</span>
        <input
          v-model="nieuwToelichting"
          type="text"
          maxlength="500"
          data-testid="cps-toelichting"
          class="lk-veld"
        />
      </label>
      <Button type="submit" label="Toevoegen" data-testid="cps-opslaan" :disabled="bezig" />
    </form>

    <BevestigVerwijderDialog
      v-model:visible="verwijderOpen"
      kop="Koppeling verwijderen"
      :omschrijving="teVerwijderen ? `${regelOmschrijving(teVerwijderen)} verwijderen?` : ''"
      :bezig="verwijderBezig"
      testid="cps-verwijder"
      @bevestig="bevestigVerwijder"
    />

    <Dialog v-model:visible="bewerkOpen" modal :closable="false" header="Koppeling bewerken" data-testid="cps-bewerk-dialog">
      <form class="flex min-w-[24rem] flex-col gap-[var(--lk-space-md)]" @submit.prevent="bevestigBewerken">
        <p class="text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]" data-testid="cps-bewerk-identiteit">
          <strong>{{ componentNaam || 'Dit component' }}</strong>
          in <strong>{{ bewerkRegel ? procesIdentiteit(bewerkRegel) : '' }}</strong> — component en proces liggen
          vast; wat het systeem hier dóét en de toelichting zijn wijzigbaar.
        </p>
        <MeldingBanner v-if="bewerkMelding" soort="warn" :tekst="bewerkMelding" testid="cps-bewerk-melding" />
        <div class="flex flex-col gap-[var(--lk-space-xs)]">
          <label for="cps-bewerk-functie" class="font-semibold">Applicatiefunctie *</label>
          <select
            id="cps-bewerk-functie"
            v-model="bewerkForm.applicatiefunctie"
            data-testid="cps-bewerk-functie"
            :aria-invalid="!!bewerkFouten.functie"
            class="lk-veld"
          >
            <option v-for="f in bewerkFunctieOpties" :key="f.optie_sleutel" :value="f.optie_sleutel">{{ f.label }}</option>
          </select>
          <span v-if="bewerkFouten.functie" role="alert" data-testid="cps-bewerk-fout-functie" class="text-[length:var(--lk-text-sm)] text-[var(--lk-color-danger)]">{{ bewerkFouten.functie }}</span>
        </div>
        <div class="flex flex-col gap-[var(--lk-space-xs)]">
          <label for="cps-bewerk-toelichting" class="font-semibold">Toelichting</label>
          <input
            id="cps-bewerk-toelichting"
            v-model="bewerkForm.toelichting"
            type="text"
            maxlength="500"
            data-testid="cps-bewerk-toelichting"
            class="lk-veld"
          />
        </div>
        <div class="flex gap-[var(--lk-space-md)]">
          <Button type="submit" label="Opslaan" data-testid="cps-bewerk-opslaan" :disabled="bewerkBezig" />
          <Button type="button" label="Annuleren" severity="secondary" @click="bewerkOpen = false" />
        </div>
      </form>
    </Dialog>
  </section>
</template>
