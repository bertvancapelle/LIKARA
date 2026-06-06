<script setup>
/**
 * ApplicatieDetail — detailweergave + acties (BWB-ontvlechtingsmodule).
 *
 * Rol-gating is affordance (knoppen tonen/verbergen); de backend handhaaft via
 * `vereist_permissie`. Een 403 wordt alsnog netjes in een Toast getoond.
 * `lifecycle_status` is read-only (Tag); "Start inventarisatie" alleen bij
 * status `concept`. Verwijderen waarschuwt voor de cascade.
 */
import { computed, onMounted, ref } from 'vue'
import { Button, Dialog, Tag, useToast } from '@/primevue'
import { useRouter } from '@/composables/router'
import { useAuthStore } from '@/store/auth'
import { api } from '@/api'
import {
  HOSTINGMODEL,
  LIFECYCLE,
  LIFECYCLE_SEVERITY,
  MIGRATIEPAD,
  NIVEAU,
  label,
} from '../labels'

const props = defineProps({ id: { type: String, required: true } })
const router = useRouter()
const toast = useToast()
const auth = useAuthStore()

const applicatie = ref(null)
const laden = ref(false)
const fout = ref(null)
const verwijderDialog = ref(false)
const bezig = ref(false)

const magBewerken = computed(() => auth.hasRole('medewerker', 'beheerder'))
const magVerwijderen = computed(() => auth.hasRole('beheerder'))
const magStarten = computed(
  () => magBewerken.value && applicatie.value?.lifecycle_status === 'concept',
)

function _toastFout(e) {
  const perStatus = {
    403: 'Je hebt geen rechten voor deze actie.',
    404: 'De applicatie is niet (meer) gevonden.',
    409: e?.message || 'Deze actie is in de huidige status niet toegestaan.',
  }
  toast.add({
    severity: 'error',
    summary: 'Fout',
    detail: perStatus[e?.status] || e?.message || 'Er ging iets mis.',
    life: 5000,
  })
}

async function laad() {
  laden.value = true
  fout.value = null
  try {
    applicatie.value = await api.applicaties.haal(props.id)
  } catch (e) {
    fout.value =
      e?.status === 404 ? 'Deze applicatie bestaat niet (meer).' : e?.message || 'Er ging iets mis.'
    _toastFout(e)
  } finally {
    laden.value = false
  }
}

async function startInventarisatie() {
  bezig.value = true
  try {
    applicatie.value = await api.applicaties.startInventarisatie(props.id)
    toast.add({ severity: 'success', summary: 'Inventarisatie gestart', life: 3000 })
  } catch (e) {
    _toastFout(e)
  } finally {
    bezig.value = false
  }
}

async function bevestigVerwijderen() {
  bezig.value = true
  try {
    await api.applicaties.verwijder(props.id)
    verwijderDialog.value = false
    toast.add({ severity: 'success', summary: 'Applicatie verwijderd', life: 3000 })
    router.push({ name: 'applicatie-lijst' })
  } catch (e) {
    _toastFout(e)
  } finally {
    bezig.value = false
  }
}

function naarBewerken() {
  router.push({ name: 'applicatie-bewerken', params: { id: props.id } })
}

onMounted(laad)
</script>

<template>
  <section aria-labelledby="detail-titel">
    <p v-if="fout" role="alert" data-testid="detail-fout" class="text-[var(--cd-color-danger)]">
      {{ fout }}
    </p>

    <template v-if="applicatie">
      <div class="flex items-center gap-[var(--cd-space-md)] mb-[var(--cd-space-md)]">
        <h1
          id="detail-titel"
          class="text-[length:var(--cd-text-2xl)] font-semibold text-[var(--cd-color-primary)]"
        >
          {{ applicatie.naam }}
        </h1>
        <Tag
          data-testid="detail-status"
          :value="label(LIFECYCLE, applicatie.lifecycle_status)"
          :severity="LIFECYCLE_SEVERITY[applicatie.lifecycle_status] || 'info'"
        />
      </div>

      <dl class="card grid grid-cols-[max-content_1fr] gap-x-[var(--cd-space-lg)] gap-y-[var(--cd-space-sm)]">
        <dt class="font-semibold">Eigenaar-organisatie</dt>
        <dd>{{ applicatie.eigenaar_organisatie }}</dd>
        <dt class="font-semibold">Eigenaar (naam)</dt>
        <dd>{{ applicatie.eigenaar_naam || '—' }}</dd>
        <dt class="font-semibold">Leverancier</dt>
        <dd>{{ applicatie.leverancier || '—' }}</dd>
        <dt class="font-semibold">Hostingmodel</dt>
        <dd>{{ label(HOSTINGMODEL, applicatie.hostingmodel) }}</dd>
        <dt class="font-semibold">Migratiepad</dt>
        <dd>{{ label(MIGRATIEPAD, applicatie.migratiepad) }}</dd>
        <dt class="font-semibold">Complexiteit</dt>
        <dd>{{ label(NIVEAU, applicatie.complexiteit) }}</dd>
        <dt class="font-semibold">Prioriteit</dt>
        <dd>{{ label(NIVEAU, applicatie.prioriteit) }}</dd>
        <dt class="font-semibold">Beschrijving</dt>
        <dd class="whitespace-pre-wrap">{{ applicatie.beschrijving || '—' }}</dd>
      </dl>

      <div class="mt-[var(--cd-space-lg)] flex flex-wrap gap-[var(--cd-space-md)]">
        <Button
          v-if="magBewerken"
          label="Bewerken"
          data-testid="bewerken-knop"
          @click="naarBewerken"
        />
        <Button
          v-if="magStarten"
          label="Start inventarisatie"
          severity="secondary"
          data-testid="start-knop"
          :disabled="bezig"
          @click="startInventarisatie"
        />
        <Button
          v-if="magVerwijderen"
          label="Verwijderen"
          severity="danger"
          data-testid="verwijder-knop"
          @click="verwijderDialog = true"
        />
      </div>
    </template>

    <Dialog
      v-model:visible="verwijderDialog"
      modal
      header="Applicatie verwijderen"
      data-testid="verwijder-dialog"
    >
      <p class="mb-[var(--cd-space-md)] max-w-prose">
        Weet je zeker dat je <strong>{{ applicatie?.naam }}</strong> wilt verwijderen? Dit
        verwijdert ook alle gekoppelde datatypes, gebruikersgroepen, koppelingen,
        checklistscores en blokkades. Dit kan niet ongedaan worden gemaakt.
      </p>
      <div class="flex justify-end gap-[var(--cd-space-md)]">
        <Button
          label="Annuleren"
          severity="secondary"
          data-testid="verwijder-annuleer"
          @click="verwijderDialog = false"
        />
        <Button
          label="Definitief verwijderen"
          severity="danger"
          data-testid="verwijder-bevestig"
          :disabled="bezig"
          @click="bevestigVerwijderen"
        />
      </div>
    </Dialog>
  </section>
</template>
