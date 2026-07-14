<script setup>
/**
 * ProcesComponentenSectie — "Componenten in dit proces" (ADR-042 slice 4a).
 *
 * Koppelregels als leesbare zinnen ("Zaaksysteem — registreren"), component klikbaar.
 * Regel-acties conform het LI035-patroon (KoppelingSectie-vorm): **Bewerken** = dialog op
 * de kenmerk-velden (applicatiefunctie + toelichting; component en proces zijn de ankers
 * van het feit en staan read-only in de dialog), **Verwijderen** = altijd bevestiging via
 * de gedeelde BevestigVerwijderDialog, met de regel leesbaar in de vraag. Toevoegregel =
 * component-ZoekSelect (component-breed, élk type — het type-label staat in elke treffer)
 * + applicatiefunctie-select (alleen actieve opties kiesbaar; een inactieve huidige
 * waarde blijft in de bewerk-dialog als label zichtbaar) + optionele toelichting; direct
 * opslaan per regel. Succes = korte toast (LI035-standaard, zie meldingen.js — CD004
 * geldt alléén voor de hoogfrequente scoringslijst, niet hier).
 * 409 VERVULLING_BESTAAT → vriendelijke melding (geen fout-toast); 422-envelope-codes op
 * het juiste veld. Rol-gating = affordance; backend handhaaft.
 */
import { computed, reactive, ref, watch } from 'vue'
import { Button, Dialog, useToast } from '@/primevue'
import { toastSucces } from '@/meldingen'
import { useAuthStore } from '@/store/auth'
import { api } from '@/api'
import BevestigVerwijderDialog from '@/components/BevestigVerwijderDialog.vue'
import MeldingBanner from '@/components/MeldingBanner.vue'
import ZoekSelect from './ZoekSelect.vue'
import VeldUitleg from './VeldUitleg.vue'

const props = defineProps({
  procesId: { type: String, required: true },
  // Voor de leesbare regel-omschrijving in bevestiging/bewerken ("… in <procesnaam>").
  procesNaam: { type: String, default: '' },
})

const auth = useAuthStore()
const toast = useToast()
const magKoppelen = computed(() => auth.hasRole('medewerker', 'beheerder'))

const regels = ref([])
const functies = ref([]) // actieve catalogus-opties [{optie_sleutel, label}]
const laden = ref(false)
const fout = ref(null)

// Toevoegregel-staat (direct opslaan per regel).
const nieuwComponentId = ref(null)
const nieuwFunctie = ref('')
const nieuwToelichting = ref('')
const bezig = ref(false)
const toevoegMelding = ref(null) // vriendelijke melding (bv. "bestaat al") — geen fout-toast
const veldFouten = ref({})
// Remount-teller voor de ZoekSelect na een geslaagde toevoeging (label wissen, LI032-lijn).
const pickerKey = ref(0)

// Component-breed zoeken: /componenten (ILIKE), type-label in elke treffer.
const zoekComponenten = (params) => api.componenten.lijst({ ...params })
const componentWeergave = (c) =>
  c?.componenttype_label ? `${c.naam} — ${c.componenttype_label}` : (c?.naam ?? '')

async function laad() {
  laden.value = true
  fout.value = null
  try {
    const [lijst, opties] = await Promise.all([
      api.procesvervullingen.lijst({ proces_id: props.procesId }),
      api.procesvervullingen.functies(),
    ])
    regels.value = lijst
    functies.value = opties
  } catch (e) {
    fout.value = e?.status === 401 ? null : 'Laden van de componenten in dit proces is mislukt.'
  } finally {
    laden.value = false
  }
}

function _resetToevoegregel() {
  nieuwComponentId.value = null
  nieuwFunctie.value = ''
  nieuwToelichting.value = ''
  pickerKey.value += 1
}

async function voegToe() {
  toevoegMelding.value = null
  veldFouten.value = {}
  if (!nieuwComponentId.value) veldFouten.value.component = 'Kies een component.'
  if (!nieuwFunctie.value) veldFouten.value.functie = 'Kies een applicatiefunctie.'
  if (Object.keys(veldFouten.value).length) return
  bezig.value = true
  try {
    await api.procesvervullingen.maak({
      component_id: nieuwComponentId.value,
      proces_id: props.procesId,
      applicatiefunctie: nieuwFunctie.value,
      toelichting: nieuwToelichting.value.trim() || null,
    })
    toastSucces(toast, 'Toegevoegd')
    _resetToevoegregel()
    await laad()
  } catch (e) {
    if (e?.status === 409 && e?.code === 'VERVULLING_BESTAAT') {
      // Vriendelijk — geen fout-toast: de registratie bestaat al, niets kapot.
      toevoegMelding.value = 'Deze koppeling bestaat al: dit component vervult deze applicatiefunctie al in dit proces.'
    } else if (e?.status === 422) {
      if (e?.code === 'ONGELDIGE_APPLICATIEFUNCTIE') veldFouten.value.functie = e.message || 'Ongeldige applicatiefunctie.'
      else if (e?.code === 'ONGELDIG_COMPONENT') veldFouten.value.component = e.message || 'Ongeldig component.'
      else veldFouten.value.functie = 'Ongeldige invoer.'
    } else if (e?.status !== 401) {
      toevoegMelding.value = 'Toevoegen is mislukt. Probeer het opnieuw.'
    }
  } finally {
    bezig.value = false
  }
}

// Leesbare regel-omschrijving voor bevestiging/bewerken (regel-acties-patroon).
function regelOmschrijving(regel) {
  const waar = props.procesNaam || 'dit proces'
  return `"${regel.applicatiefunctie_label}" in ${waar} — ${regel.component_naam}`
}

// ── Verwijderen — altijd met bevestiging (gedeelde BevestigVerwijderDialog) ───
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

// ── Bewerken — dialog op de kenmerk-velden; ankers read-only ─────────────────
const bewerkOpen = ref(false)
const bewerkRegel = ref(null)
const bewerkForm = reactive({ applicatiefunctie: '', toelichting: '' })
const bewerkMelding = ref(null)
const bewerkFouten = reactive({})
const bewerkBezig = ref(false)

// Actieve opties + (indien inactief) de huidige waarde van de regel, zodat die
// zichtbaar blijft als label (soft-deactivate-leespad).
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
      // Rustig — de gewijzigde combinatie bestaat al als eigen regel.
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

// De conflict-banner verdwijnt zodra de invoer wijzigt (de melding hoort bij de
// geweigerde poging, niet bij de nieuwe invoer).
watch([nieuwComponentId, nieuwFunctie, nieuwToelichting], () => {
  toevoegMelding.value = null
})
watch(bewerkForm, () => {
  bewerkMelding.value = null
})

// props.id-watch-norm (detail→detail-navigatie herlaadt de sectie).
watch(() => props.procesId, () => laad(), { immediate: true })
</script>

<template>
  <section class="card" aria-labelledby="proces-componenten-titel" data-testid="proces-componenten-sectie">
    <div class="flex items-center gap-[var(--lk-space-xs)] mb-[var(--lk-space-sm)]">
      <h2 id="proces-componenten-titel" class="text-[length:var(--lk-text-lg)] font-semibold">
        Componenten in dit proces
      </h2>
      <VeldUitleg veld="applicatiefunctie" testid="uitleg-applicatiefunctie" />
    </div>

    <p v-if="fout" role="alert" data-testid="pcs-fout" class="mb-[var(--lk-space-sm)] text-[var(--lk-color-danger)]">{{ fout }}</p>
    <p v-else-if="laden && !regels.length" data-testid="pcs-laden" class="text-[var(--lk-color-text-muted)]">Laden…</p>

    <ul v-if="regels.length" class="mb-[var(--lk-space-md)] divide-y divide-[var(--lk-color-border)]" data-testid="pcs-regels">
      <li
        v-for="regel in regels"
        :key="regel.vervulling_id"
        class="flex items-baseline gap-[var(--lk-space-sm)] py-[var(--lk-space-sm)]"
        :data-testid="`pcs-regel-${regel.vervulling_id}`"
      >
        <span class="min-w-0">
          <router-link
            :to="{ name: 'component-detail', params: { id: regel.component_id } }"
            data-testid="pcs-component-link"
            class="font-medium text-[var(--lk-color-primary)] hover:underline focus:outline-2 focus:outline-offset-2 focus:outline-[var(--lk-color-primary)]"
          >{{ regel.component_naam }}</router-link>
          <span v-if="regel.componenttype_label" class="text-[length:var(--lk-text-xs)] text-[var(--lk-color-text-muted)]"> ({{ regel.componenttype_label }})</span>
          — <em data-testid="pcs-functie">{{ regel.applicatiefunctie_label }}</em>
          <span v-if="regel.toelichting" class="block text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]">{{ regel.toelichting }}</span>
        </span>
        <div v-if="magKoppelen" class="ml-auto flex shrink-0 items-center gap-[var(--lk-space-xs)]">
          <Button
            label="Bewerken"
            severity="secondary"
            :data-testid="`pcs-bewerk-${regel.vervulling_id}`"
            @click="openBewerken(regel)"
          />
          <Button
            label="Verwijderen"
            severity="danger"
            :data-testid="`pcs-verwijder-${regel.vervulling_id}`"
            @click="vraagVerwijder(regel)"
          />
        </div>
      </li>
    </ul>
    <p v-else-if="!laden && !fout" data-testid="pcs-leeg" class="mb-[var(--lk-space-md)] text-[var(--lk-color-text-muted)]">
      Nog geen componenten aan dit proces gekoppeld.
      <template v-if="magKoppelen">Leg de eerste koppeling hieronder — élk componenttype kan.</template>
    </p>

    <!-- Toevoegregel — direct opslaan per regel. De conflict-banner staat BOVEN de
         invoervelden (leesvolgorde vóór de te corrigeren velden, LI035-positie-fix). -->
    <form v-if="magKoppelen" class="flex flex-wrap items-end gap-[var(--lk-space-md)]" data-testid="pcs-toevoegregel" @submit.prevent="voegToe">
      <MeldingBanner v-if="toevoegMelding" class="w-full" soort="warn" :tekst="toevoegMelding" testid="pcs-melding" />
      <label class="flex min-w-[16rem] flex-1 flex-col gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]">
        <span class="text-[length:var(--lk-text-xs)] font-semibold uppercase tracking-wide text-[var(--lk-color-text-muted)]">Component</span>
        <ZoekSelect
          :key="pickerKey"
          v-model="nieuwComponentId"
          :zoek-functie="zoekComponenten"
          :weergave="componentWeergave"
          placeholder="Zoek een component…"
          testid="pcs-component"
          :invalid="!!veldFouten.component"
        />
        <span v-if="veldFouten.component" role="alert" data-testid="pcs-fout-component" class="text-[var(--lk-color-danger)]">{{ veldFouten.component }}</span>
      </label>
      <label class="flex flex-col gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]">
        <span class="text-[length:var(--lk-text-xs)] font-semibold uppercase tracking-wide text-[var(--lk-color-text-muted)]">Applicatiefunctie</span>
        <select
          v-model="nieuwFunctie"
          data-testid="pcs-functie-select"
          :aria-invalid="!!veldFouten.functie"
          class="lk-veld"
        >
          <option value="">— kies —</option>
          <option v-for="f in functies" :key="f.optie_sleutel" :value="f.optie_sleutel">{{ f.label }}</option>
        </select>
        <span v-if="veldFouten.functie" role="alert" data-testid="pcs-fout-functie" class="text-[var(--lk-color-danger)]">{{ veldFouten.functie }}</span>
      </label>
      <label class="flex min-w-[14rem] flex-1 flex-col gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]">
        <span class="text-[length:var(--lk-text-xs)] font-semibold uppercase tracking-wide text-[var(--lk-color-text-muted)]">Toelichting (optioneel)</span>
        <input
          v-model="nieuwToelichting"
          type="text"
          maxlength="500"
          data-testid="pcs-toelichting"
          class="lk-veld"
        />
      </label>
      <Button type="submit" label="Toevoegen" data-testid="pcs-opslaan" :disabled="bezig" />
    </form>

    <!-- Verwijderen — gedeelde bevestiging met de regel leesbaar in de vraag (LI035). -->
    <BevestigVerwijderDialog
      v-model:visible="verwijderOpen"
      kop="Koppeling verwijderen"
      :omschrijving="teVerwijderen ? `${regelOmschrijving(teVerwijderen)} verwijderen?` : ''"
      :bezig="verwijderBezig"
      testid="pcs-verwijder"
      @bevestig="bevestigVerwijder"
    />

    <!-- Bewerken — kenmerk-velden; de ankers (component + proces) read-only. -->
    <Dialog v-model:visible="bewerkOpen" modal :closable="false" header="Koppeling bewerken" data-testid="pcs-bewerk-dialog">
      <form class="flex min-w-[24rem] flex-col gap-[var(--lk-space-md)]" @submit.prevent="bevestigBewerken">
        <p class="text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]" data-testid="pcs-bewerk-identiteit">
          <strong>{{ bewerkRegel?.component_naam }}</strong>
          <span v-if="bewerkRegel?.componenttype_label"> ({{ bewerkRegel.componenttype_label }})</span>
          in <strong>{{ procesNaam || 'dit proces' }}</strong> — component en proces liggen vast; wat het systeem
          hier dóét en de toelichting zijn wijzigbaar.
        </p>
        <MeldingBanner v-if="bewerkMelding" soort="warn" :tekst="bewerkMelding" testid="pcs-bewerk-melding" />
        <div class="flex flex-col gap-[var(--lk-space-xs)]">
          <label for="pcs-bewerk-functie" class="font-semibold">Applicatiefunctie *</label>
          <select
            id="pcs-bewerk-functie"
            v-model="bewerkForm.applicatiefunctie"
            data-testid="pcs-bewerk-functie"
            :aria-invalid="!!bewerkFouten.functie"
            class="lk-veld"
          >
            <option v-for="f in bewerkFunctieOpties" :key="f.optie_sleutel" :value="f.optie_sleutel">{{ f.label }}</option>
          </select>
          <span v-if="bewerkFouten.functie" role="alert" data-testid="pcs-bewerk-fout-functie" class="text-[length:var(--lk-text-sm)] text-[var(--lk-color-danger)]">{{ bewerkFouten.functie }}</span>
        </div>
        <div class="flex flex-col gap-[var(--lk-space-xs)]">
          <label for="pcs-bewerk-toelichting" class="font-semibold">Toelichting</label>
          <input
            id="pcs-bewerk-toelichting"
            v-model="bewerkForm.toelichting"
            type="text"
            maxlength="500"
            data-testid="pcs-bewerk-toelichting"
            class="lk-veld"
          />
        </div>
        <div class="flex gap-[var(--lk-space-md)]">
          <Button type="submit" label="Opslaan" data-testid="pcs-bewerk-opslaan" :disabled="bewerkBezig" />
          <Button type="button" label="Annuleren" severity="secondary" @click="bewerkOpen = false" />
        </div>
      </form>
    </Dialog>
  </section>
</template>
