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
import { computed, onMounted, ref, watch } from 'vue'
import { Button, Dialog, Tag, useToast } from '@/primevue'
import { useRoute, useRouter } from '@/composables/router'
import { useAuthStore } from '@/store/auth'
import { useTerugNavigatie } from '@/composables/useTerugNavigatie'
import { api } from '@/api'
import { HOSTINGMODEL, LIFECYCLE, LIFECYCLE_SEVERITY, REGISTER_FOUT, label } from '../labels'
import ObjectHistoriePaneel from './ObjectHistoriePaneel.vue'
import StructuurSectie from './StructuurSectie.vue'
import ContractSectie from './ContractSectie.vue'
import VerantwoordelijkheidSectie from './VerantwoordelijkheidSectie.vue'
import ImpactSectie from './ImpactSectie.vue'
// ADR-022 Fase E — checklist (scoring) voor checklist-dragende NIET-applicatie-typen.
import ChecklistscoreSectie from './ChecklistscoreSectie.vue'
// F-1-vervolg — blokkades + herkomst-doorklik, ook voor checklist-dragende niet-applicaties.
import BlokkadeSectie from './BlokkadeSectie.vue'
// ADR-027 — migratiegereedheid (component-klaarverklaring); component-generiek, ook hier.
import MigratiegereedheidSectie from './MigratiegereedheidSectie.vue'

const props = defineProps({ id: { type: String, required: true } })
const router = useRouter()
const route = useRoute()
const { terugLabel, gaTerug } = useTerugNavigatie()
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
// ADR-022 Fase E: "Start beoordeling" alleen bij checklist-dragend + status 'concept'
// + bewerk-rechten; verdwijnt zodra de lifecycle-status niet meer 'concept' is.
const magStarten = computed(
  () => magBewerken.value && component.value?.checklist_dragend === true && component.value?.lifecycle_status === 'concept',
)
// ADR-027 — migratiegereedheid tonen voor checklist-dragende óf reeds beoordeelde componenten
// (zelfde conditie als de checklist-/blokkadesectie). Knop verbergen zonder rol; backend handhaaft.
const scoreSectie = ref(null)
const gereedheidSectie = ref(null)
const magKlaarverklaren = computed(() => auth.hasRole('medewerker', 'beheerder'))
const gereedheidLabel = computed(() => (gereedheidSectie.value?.status === 'klaar' ? 'Heropenen' : 'Klaar verklaren'))
const toonGereedheid = computed(
  () => component.value?.checklist_dragend === true || !!component.value?.lifecycle_status,
)

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

async function startBeoordeling() {
  bezig.value = true
  try {
    await api.componenten.startBeoordeling(props.id)
    await laad()
    toast.add({ severity: 'success', summary: 'Beoordeling gestart', life: 3000 })
  } catch (e) {
    _toastFout(e)
  } finally {
    bezig.value = false
  }
}

// Herkomst-doorklik: BlokkadeSectie → checklist. ComponentDetail is tabloos en toont
// de volledige checklist (alle categorieën) inline; de doorklik markeert dus alleen de
// vraag-rij (scroll/highlight) — zelfde event+prop-mechanisme als ApplicatieDetail,
// zonder tab/categorie-switch.
const blokkadeSectie = ref(null)
const markeerVraagCode = ref(null)
function onNaarVraag({ code }) {
  markeerVraagCode.value = code
}
async function onScoreGewijzigd() {
  await laad() // lifecycle kan schuiven
  blokkadeSectie.value?.herlaad() // een score kan een blokkade laten ontstaan/oplossen
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

onMounted(() => {
  // ADR-024-vervolg: deep-link vanuit de blokkadelijst markeert een checklistvraag.
  // Hergebruikt hetzelfde markeerpad als de in-page `naar-vraag` (component-detail is
  // tabloos → alleen de code, geen tab/categorie).
  if (route.query.markeer != null) markeerVraagCode.value = String(route.query.markeer)
})
// Navigatie component-detail → component-detail hergebruikt de instance; watch op props.id
// (immediate) herlaadt bij elke id-wissel (vervangt de onMounted-laad).
watch(() => props.id, () => laad(), { immediate: true })
</script>

<template>
  <section aria-labelledby="detail-titel">
    <button v-if="terugLabel" type="button" data-testid="terug-knop" class="mb-[var(--cd-space-md)] inline-flex items-center text-[length:var(--cd-text-sm)] text-[var(--cd-color-text-muted)] hover:text-[var(--cd-color-primary)] hover:underline focus:outline-2 focus:outline-offset-2 focus:outline-[var(--cd-color-primary)]" @click="gaTerug">{{ terugLabel }}</button>
    <p v-if="fout" role="alert" data-testid="detail-fout" class="text-[var(--cd-color-danger)]">{{ fout }}</p>

    <template v-if="component">
      <div class="flex items-center gap-[var(--cd-space-md)] mb-[var(--cd-space-md)]">
        <h1 id="detail-titel" class="text-[length:var(--cd-text-2xl)] font-semibold text-[var(--cd-color-primary)]">
          {{ component.naam }}
        </h1>
        <Tag data-testid="detail-type" :value="component.componenttype_label" :severity="isSubtype ? 'info' : 'secondary'" />
        <!-- ADR-022 Fase E: lifecycle-status voor checklist-dragende componenten. -->
        <Tag
          v-if="component.lifecycle_status"
          data-testid="detail-status"
          :value="label(LIFECYCLE, component.lifecycle_status)"
          :severity="LIFECYCLE_SEVERITY[component.lifecycle_status] || 'info'"
        />
      </div>

      <p
        v-if="isSubtype"
        data-testid="detail-subtype-hint"
        class="card mb-[var(--cd-space-md)] border-l-4 border-[var(--cd-color-primary)] text-[length:var(--cd-text-sm)]"
      >
        Dit component is een applicatie. Beheer de applicatie-velden op
        <router-link :to="{ name: 'applicatie-detail', params: { id: component.id } }" class="text-[var(--cd-color-primary)] hover:underline">de applicatie zelf</router-link>.
      </p>

      <div class="flex flex-col gap-[var(--cd-space-lg)] md:flex-row md:items-start">
      <dl class="card grid grid-cols-[max-content_1fr] gap-x-[var(--cd-space-lg)] gap-y-[var(--cd-space-sm)] md:flex-1">
        <dt class="font-semibold">Type</dt>
        <dd>{{ component.componenttype_label }}</dd>
        <dt class="font-semibold">Hostingmodel</dt>
        <dd>{{ label(HOSTINGMODEL, component.hostingmodel) }}</dd>
        <dt class="font-semibold">Eigenaar-organisatie</dt>
        <dd>
          <router-link
            v-if="component.eigenaar_organisatie_id"
            :to="{ name: 'partij-detail', params: { id: component.eigenaar_organisatie_id } }"
            data-testid="comp-eigenaar-org-link"
            class="text-[var(--cd-color-primary)] hover:underline"
          >{{ component.eigenaar_organisatie_naam }}</router-link>
          <span v-else>—</span>
        </dd>
        <dt class="font-semibold">Beschrijving</dt>
        <dd class="whitespace-pre-wrap">{{ component.beschrijving || '—' }}</dd>
      </dl>

        <!-- ADR-027 — migratiegereedheid (component-klaarverklaring), zelfde blok als ApplicatieDetail. -->
        <MigratiegereedheidSectie
          v-if="toonGereedheid"
          ref="gereedheidSectie"
          class="md:w-80 md:shrink-0"
          :component-id="component.id"
          :aantal-gescoord="scoreSectie?.aantalGescoord ?? 0"
          :aantal-vragen="scoreSectie?.aantalVragen ?? 0"
        />
      </div>

      <div class="mt-[var(--cd-space-lg)] flex flex-wrap gap-[var(--cd-space-md)]">
        <Button
          v-if="magKlaarverklaren && toonGereedheid"
          :label="gereedheidLabel"
          severity="secondary"
          data-testid="klaarverklaar-knop"
          @click="(e) => gereedheidSectie?.openDialog(e)"
        />
        <ObjectHistoriePaneel entiteit-type="component" :entiteit-id="props.id" />
        <Button v-if="magBewerken" label="Bewerken" data-testid="bewerken-knop" @click="naarBewerken" />
        <Button
          v-if="magStarten"
          label="Start beoordeling"
          severity="secondary"
          data-testid="start-beoordeling-knop"
          :disabled="bezig"
          @click="startBeoordeling"
        />
        <Button v-if="magVerwijderen" label="Verwijderen" severity="danger" data-testid="verwijder-knop" @click="openVerwijderDialog" />
      </div>

      <div class="mt-[var(--cd-space-lg)] flex flex-col gap-[var(--cd-space-lg)]">
        <StructuurSectie :component-id="props.id" />
        <ContractSectie :applicatie-id="props.id" :app-naam="component?.naam || ''" />
        <VerantwoordelijkheidSectie :object-id="props.id" />
        <ImpactSectie :component-id="props.id" />
        <!-- ADR-022 Fase E — checklist voor checklist-dragende typen; ADR-027 — óók read-only
             tonen voor een gesloten type dat al een profiel/scores heeft (lifecycle_status gezet). -->
        <ChecklistscoreSectie
          v-if="component.checklist_dragend === true || component.lifecycle_status"
          ref="scoreSectie"
          :applicatie-id="component.id"
          :componenttype="component.componenttype"
          :markeer-code="markeerVraagCode"
          :bewerkbaar="component.checklist_dragend === true"
          @gewijzigd="onScoreGewijzigd"
        />
        <!-- F-1-vervolg — blokkades met herkomst-kolom + doorklik, alleen voor
             checklist-dragende typen (alleen die kunnen blokkades hebben). -->
        <BlokkadeSectie
          v-if="component.checklist_dragend === true"
          ref="blokkadeSectie"
          :applicatie-id="component.id"
          @gewijzigd="laad"
          @naar-vraag="onNaarVraag"
        />
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
