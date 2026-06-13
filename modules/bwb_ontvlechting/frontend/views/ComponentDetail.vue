<script setup>
/**
 * ComponentDetail — detailweergave van één component (ADR-021 Fase D).
 *
 * Bereikt voor NIET-applicatie-componenten (subtypen linken vanuit de lijst naar
 * ApplicatieDetail). Toont velden + type-label, de Opbouw-sectie (structuurgraaf,
 * beide richtingen) en de Contracten-sectie (de in CD054a gegeneraliseerde
 * ContractSectie — component_id == het applicatie-id bij subtypen). Bewerken/
 * verwijderen alleen bij niet-subtypen; verwijderen waarschuwt en mapt 409 IN_GEBRUIK.
 */
import { computed, onMounted, ref } from 'vue'
import { Button, Dialog, Tag, useToast } from '@/primevue'
import { useRouter } from '@/composables/router'
import { useAuthStore } from '@/store/auth'
import { api } from '@/api'
import { HOSTINGMODEL, REGISTER_FOUT, label } from '../labels'
import StructuurSectie from './StructuurSectie.vue'
import ContractSectie from './ContractSectie.vue'
import ImpactSectie from './ImpactSectie.vue'

const props = defineProps({ id: { type: String, required: true } })
const router = useRouter()
const toast = useToast()
const auth = useAuthStore()

const component = ref(null)
const laden = ref(false)
const fout = ref(null)
const verwijderDialog = ref(false)
const bezig = ref(false)
// ADR-022 Fase C: read-only "wat verdwijnt"-samenvatting in de bevestiging.
const verwijderImpact = ref(null)

async function openVerwijderDialog() {
  verwijderImpact.value = null
  verwijderDialog.value = true
  try {
    verwijderImpact.value = await api.componenten.verwijderImpact(props.id)
  } catch {
    verwijderImpact.value = null // samenvatting is optioneel; dialoog blijft bruikbaar
  }
}

const verwijderHeeftData = computed(() => {
  const i = verwijderImpact.value
  return !!i && (i.beantwoorde_scores || i.blokkades || i.datatypes || i.gebruikersgroepen)
})

const isSubtype = computed(() => !!component.value?.heeft_applicatie_subtype)
const magBewerken = computed(() => auth.hasRole('medewerker', 'beheerder') && !isSubtype.value)
const magVerwijderen = computed(() => auth.hasRole('beheerder') && !isSubtype.value)

function _toastFout(e) {
  const detail =
    e?.code && REGISTER_FOUT[e.code]
      ? e?.message || REGISTER_FOUT[e.code]
      : { 403: 'Je hebt geen rechten voor deze actie.', 404: 'Niet gevonden.', 409: e?.message || 'Conflict.' }[e?.status] ||
        e?.message ||
        'Er ging iets mis.'
  toast.add({ severity: 'error', summary: 'Fout', detail, life: 5000 })
}

async function laad() {
  laden.value = true
  fout.value = null
  try {
    component.value = await api.componenten.haal(props.id)
  } catch (e) {
    fout.value = e?.status === 404 ? 'Dit component bestaat niet (meer).' : e?.message || 'Er ging iets mis.'
    _toastFout(e)
  } finally {
    laden.value = false
  }
}

function naarBewerken() {
  router.push({ name: 'component-bewerken', params: { id: props.id } })
}

async function bevestigVerwijderen() {
  bezig.value = true
  try {
    await api.componenten.verwijder(props.id)
    verwijderDialog.value = false
    toast.add({ severity: 'success', summary: 'Component verwijderd', life: 3000 })
    router.push({ name: 'component-lijst' })
  } catch (e) {
    _toastFout(e)
  } finally {
    bezig.value = false
  }
}

onMounted(laad)
</script>

<template>
  <section aria-labelledby="detail-titel">
    <p v-if="fout" role="alert" data-testid="detail-fout" class="text-[var(--cd-color-danger)]">{{ fout }}</p>

    <template v-if="component">
      <div class="flex items-center gap-[var(--cd-space-md)] mb-[var(--cd-space-md)]">
        <h1 id="detail-titel" class="text-[length:var(--cd-text-2xl)] font-semibold text-[var(--cd-color-primary)]">
          {{ component.naam }}
        </h1>
        <Tag data-testid="detail-type" :value="component.componenttype_label" :severity="isSubtype ? 'info' : 'secondary'" />
      </div>

      <p
        v-if="isSubtype"
        data-testid="detail-subtype-hint"
        class="card mb-[var(--cd-space-md)] border-l-4 border-[var(--cd-color-primary)] text-[length:var(--cd-text-sm)]"
      >
        Dit component is een applicatie. Beheer de applicatie-velden op
        <router-link :to="{ name: 'applicatie-detail', params: { id: component.id } }" class="text-[var(--cd-color-primary)] hover:underline">de applicatie zelf</router-link>.
      </p>

      <dl class="card grid grid-cols-[max-content_1fr] gap-x-[var(--cd-space-lg)] gap-y-[var(--cd-space-sm)]">
        <dt class="font-semibold">Type</dt>
        <dd>{{ component.componenttype_label }}</dd>
        <dt class="font-semibold">Hostingmodel</dt>
        <dd>{{ label(HOSTINGMODEL, component.hostingmodel) }}</dd>
        <dt class="font-semibold">Eigenaar-organisatie</dt>
        <dd>{{ component.eigenaar_organisatie || '—' }}</dd>
        <dt class="font-semibold">Eigenaar (naam)</dt>
        <dd>{{ component.eigenaar_naam || '—' }}</dd>
        <dt class="font-semibold">Leverancier</dt>
        <dd>{{ component.leverancier || '—' }}</dd>
        <dt class="font-semibold">Beschrijving</dt>
        <dd class="whitespace-pre-wrap">{{ component.beschrijving || '—' }}</dd>
      </dl>

      <div class="mt-[var(--cd-space-lg)] flex flex-wrap gap-[var(--cd-space-md)]">
        <Button v-if="magBewerken" label="Bewerken" data-testid="bewerken-knop" @click="naarBewerken" />
        <Button v-if="magVerwijderen" label="Verwijderen" severity="danger" data-testid="verwijder-knop" @click="openVerwijderDialog" />
      </div>

      <div class="mt-[var(--cd-space-lg)] flex flex-col gap-[var(--cd-space-lg)]">
        <StructuurSectie :component-id="props.id" />
        <ContractSectie :applicatie-id="props.id" />
        <ImpactSectie :component-id="props.id" />
      </div>
    </template>

    <Dialog v-model:visible="verwijderDialog" modal header="Component verwijderen" data-testid="verwijder-dialog">
      <p class="mb-[var(--cd-space-md)] max-w-prose">
        Weet je zeker dat je <strong>{{ component?.naam }}</strong> wilt verwijderen? Een component
        met nog bestaande relaties (structuur of contracten) kan niet worden verwijderd.
      </p>
      <p
        v-if="verwijderHeeftData"
        data-testid="verwijder-samenvatting"
        class="mb-[var(--cd-space-md)] max-w-prose text-[length:var(--cd-text-sm)] text-[var(--cd-color-danger)]"
      >
        Dit verwijdert ook: {{ verwijderImpact.beantwoorde_scores }} beantwoorde score(s),
        {{ verwijderImpact.blokkades }} blokkade(s), {{ verwijderImpact.datatypes }} datatype(s) en
        {{ verwijderImpact.gebruikersgroepen }} gebruikersgroep(en).
      </p>
      <div class="flex justify-end gap-[var(--cd-space-md)]">
        <Button label="Annuleren" severity="secondary" data-testid="verwijder-annuleer" @click="verwijderDialog = false" />
        <Button label="Definitief verwijderen" severity="danger" data-testid="verwijder-bevestig" :disabled="bezig" @click="bevestigVerwijderen" />
      </div>
    </Dialog>
  </section>
</template>
