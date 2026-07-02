<script setup>
/**
 * ComponentDetail — één rijk detailscherm voor ELK componenttype (LI059 Slice 4).
 *
 * De aparte ApplicatieDetail is hierin opgegaan: de 2-laags tab-indeling (AppTabs) toont
 * per type de relevante onderdelen. Applicatie-eigen tabs (Datatypes/Gebruikersgroepen/
 * Koppelingen) verschijnen alleen bij `heeft_applicatie_subtype`; Checklist/Blokkades alleen
 * bij checklist-dragende typen. Rol-gating is affordance; de backend handhaaft
 * (`vereist_permissie`). Lifecycle is read-only (Tag); "Start beoordeling" alleen bij
 * checklist-dragend + status `concept`. Verwijderen waarschuwt voor de cascade.
 */
import { computed, ref, watch } from 'vue'
import { Button, Dialog, Tag, useToast } from '@/primevue'
import { useRoute, useRouter } from '@/composables/router'
import { useAuthStore } from '@/store/auth'
import { useTerugNavigatie } from '@/composables/useTerugNavigatie'
import { api } from '@/api'
import {
  CONTRACTTYPE,
  HOSTINGMODEL,
  LIFECYCLE,
  LIFECYCLE_SEVERITY,
  MIGRATIEPAD,
  NIVEAU,
  REGISTER_FOUT,
  label,
} from '../labels'
import AppTabs from './AppTabs.vue'
import ObjectHistoriePaneel from './ObjectHistoriePaneel.vue'
import StructuurSectie from './StructuurSectie.vue'
import ContractSectie from './ContractSectie.vue'
import VerantwoordelijkheidSectie from './VerantwoordelijkheidSectie.vue'
import ImpactSectie from './ImpactSectie.vue'
import ChecklistscoreSectie from './ChecklistscoreSectie.vue'
import BlokkadeSectie from './BlokkadeSectie.vue'
import MigratiegereedheidSectie from './MigratiegereedheidSectie.vue'
import SignaleringBadge from './SignaleringBadge.vue'
// LI059 Slice 4 — applicatie-eigen kind-secties, conditioneel gemount (bij subtype).
import DatatypeSectie from './DatatypeSectie.vue'
import GebruikersgroepSectie from './GebruikersgroepSectie.vue'
import KoppelingSectie from './KoppelingSectie.vue'

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
// ADR-035 Slice 1 — registratiegaten-badge (read-only; faalt zacht, geen invloed op de detail-laad).
const signaleringBadge = ref({ kritiek: 0, aandacht: 0, signalen: [] })

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
// LI059 Slice 4 — élk type wordt via ComponentFormulier bewerkt (ook applicatie); geen subtype-uitzondering meer.
const magBewerken = computed(() => auth.hasRole('medewerker', 'beheerder'))
const magVerwijderen = computed(() => auth.hasRole('beheerder'))
// ADR-022 Fase E: "Start beoordeling" alleen bij checklist-dragend + status 'concept' + bewerk-rechten.
const magStarten = computed(
  () => magBewerken.value && component.value?.checklist_dragend === true && component.value?.lifecycle_status === 'concept',
)
// ADR-027 — migratiegereedheid tonen voor checklist-dragende óf reeds beoordeelde componenten.
const scoreSectie = ref(null)
const blokkadeSectie = ref(null)
const contractSectie = ref(null)
const gereedheidSectie = ref(null)
const magKlaarverklaren = computed(() => auth.hasRole('medewerker', 'beheerder'))
// ADR-025 — "Bekijk op kaart" = ARCHITECTUUR.LEZEN-affordance (elke tenant-rol; backend handhaaft).
const magKaartZien = computed(() => auth.hasRole('viewer', 'medewerker', 'beheerder', 'auditor'))
const gereedheidLabel = computed(() => (gereedheidSectie.value?.status === 'klaar' ? 'Heropenen' : 'Klaar verklaren'))
// Checklist/migratiegereedheid/blokkades gelden voor checklist-dragende (of reeds beoordeelde) componenten.
const isChecklistDragend = computed(
  () => component.value?.checklist_dragend === true || !!component.value?.lifecycle_status,
)
const contractenVoorContext = computed(() => contractSectie.value?.items ?? [])

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
  signaleringBadge.value = { kritiek: 0, aandacht: 0, signalen: [] }
  try {
    component.value = await api.componenten.haal(props.id)
    // Badge read-only + optioneel: een fout hierin mag de detail-laad niet breken.
    try {
      signaleringBadge.value = await api.signalering.badgeComponent(props.id)
    } catch { /* badge optioneel */ }
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

// ADR-025 — open de Landschapskaart in ego-view, gecentreerd op dit component.
function bekijkOpKaart() {
  router.push({ name: 'landschapskaart', query: { center: component.value.id } })
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

// ── 2-laags tabnavigatie (LI059 Slice 4, geport uit ApplicatieDetail) ────────
// Tabs conditioneel per type: applicatie-eigen tabs (datatypes/gebruikersgroepen/
// koppelingen) alleen bij een subtype; checklist/blokkades alleen bij checklist-dragend.
const topTabs = computed(() => {
  const t = [{ key: 'overzicht', label: 'Overzicht' }]
  if (isChecklistDragend.value) t.push({ key: 'checklist', label: 'Checklist' })
  if (isSubtype.value)
    t.push(
      { key: 'datatypes', label: 'Datatypes' },
      { key: 'gebruikersgroepen', label: 'Gebruikersgroepen' },
      { key: 'koppelingen', label: 'Koppelingen' },
    )
  t.push(
    { key: 'opbouw', label: 'Opbouw' },
    { key: 'impact', label: 'Impact' },
    { key: 'contracten', label: 'Contracten' },
    { key: 'verantwoordelijkheden', label: 'Verantwoordelijkheden' },
  )
  if (isChecklistDragend.value) t.push({ key: 'blokkades', label: 'Blokkades' })
  return t
})
const activeTop = ref('overzicht')
const activeCat = ref(null) // categorie_nr als string-key

// Zodra de tabset wijzigt (na laden): houd activeTop geldig (default = Overzicht).
watch(topTabs, (tabs) => {
  if (!tabs.some((t) => t.key === activeTop.value)) activeTop.value = 'overzicht'
})

// Categorie-sub-tabs: labels afgeleid uit de geladen vragen (geen seed-duplicatie).
const categorieTabs = computed(() =>
  (scoreSectie.value?.categorieen ?? []).map((c) => ({ key: String(c.nr), label: c.naam })),
)
const actieveCategorieNr = computed(() => (activeCat.value != null ? Number(activeCat.value) : null))

watch(categorieTabs, (tabs) => {
  if (tabs.length && !tabs.some((t) => t.key === activeCat.value)) activeCat.value = tabs[0].key
})

// Deep-link initialiseren uit de URL (na mount; de scoreSectie laadt async).
function _initVanafQuery() {
  const t = String(route.query.tab ?? '')
  if (topTabs.value.some((x) => x.key === t)) activeTop.value = t
  if (route.query.cat != null) activeCat.value = String(route.query.cat)
  // Deep-link vanuit de tenant-brede blokkadelijst markeert een checklistvraag.
  if (route.query.markeer != null) {
    if (isChecklistDragend.value) activeTop.value = 'checklist'
    markeerVraagCode.value = String(route.query.markeer)
  }
}

// Actieve tab(s) terugschrijven naar de URL. Overzicht = schone URL; `router.replace` (geen history-spam).
watch([activeTop, activeCat], () => {
  const query = {}
  if (activeTop.value !== 'overzicht') query.tab = activeTop.value
  if (activeTop.value === 'checklist' && activeCat.value != null) query.cat = activeCat.value
  const huidigTab = route.query.tab ?? undefined
  const huidigCat = route.query.cat != null ? String(route.query.cat) : undefined
  if (huidigTab === (query.tab ?? undefined) && huidigCat === (query.cat ?? undefined)) return
  router.replace({ query })
})

async function onScoreGewijzigd() {
  await laad() // lifecycle kan schuiven
  blokkadeSectie.value?.herlaad() // een score kan een blokkade laten ontstaan/oplossen
}
async function onBlokkadeGewijzigd() {
  await laad()
}

// Herkomst-doorklik vanuit BlokkadeSectie: schakel naar Checklist + de categorie van de vraag.
const markeerVraagCode = ref(null)
function onNaarVraag({ code, categorieNr }) {
  activeTop.value = 'checklist'
  if (categorieNr != null) activeCat.value = String(categorieNr)
  markeerVraagCode.value = code
}

// Navigatie component-detail → component-detail hergebruikt de instance; watch op props.id
// (immediate) herlaadt + her-initialiseert de deep-link bij elke id-wissel.
watch(() => props.id, async () => { await laad(); _initVanafQuery() }, { immediate: true })
</script>

<template>
  <section aria-labelledby="detail-titel">
    <button v-if="terugLabel" type="button" data-testid="terug-knop" class="mb-[var(--lk-space-md)] inline-flex items-center text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)] hover:text-[var(--lk-color-primary)] hover:underline focus:outline-2 focus:outline-offset-2 focus:outline-[var(--lk-color-primary)]" @click="gaTerug">{{ terugLabel }}</button>
    <p v-if="fout" role="alert" data-testid="detail-fout" class="text-[var(--lk-color-danger)]">{{ fout }}</p>

    <template v-if="component">
      <div class="flex items-center gap-[var(--lk-space-md)] mb-[var(--lk-space-md)]">
        <h1 id="detail-titel" class="text-[length:var(--lk-text-2xl)] font-semibold text-[var(--lk-color-primary)]">
          {{ component.naam }}
        </h1>
        <Tag data-testid="detail-type" :value="component.componenttype_label" :severity="isSubtype ? 'info' : 'secondary'" />
        <Tag
          v-if="component.lifecycle_status"
          data-testid="detail-status"
          :value="label(LIFECYCLE, component.lifecycle_status)"
          :severity="LIFECYCLE_SEVERITY[component.lifecycle_status] || 'info'"
        />
        <SignaleringBadge :kritiek="signaleringBadge.kritiek" :aandacht="signaleringBadge.aandacht" :signalen="signaleringBadge.signalen || []" />
      </div>

      <p v-if="isChecklistDragend" data-testid="detail-voortgang" class="mb-[var(--lk-space-md)] text-[var(--lk-color-text-muted)]">
        {{ scoreSectie?.aantalGescoord ?? 0 }}/{{ scoreSectie?.aantalVragen ?? 0 }} vragen gescoord ·
        {{ blokkadeSectie?.aantalOpen ?? 0 }} open blokkade(s)
      </p>

      <AppTabs
        v-model="activeTop"
        :tabs="topTabs"
        aria-label="Component-detail onderdelen"
        id-prefix="detailtabs"
        class="mt-[var(--lk-space-lg)] mb-[var(--lk-space-md)]"
      />

      <!-- Overzicht: metadata + acties -->
      <div
        v-show="activeTop === 'overzicht'"
        id="detailtabs-panel-overzicht"
        role="tabpanel"
        aria-labelledby="detailtabs-tab-overzicht"
        data-testid="panel-overzicht"
      >
        <div class="flex flex-col gap-[var(--lk-space-lg)] md:flex-row md:items-start">
          <dl class="card grid grid-cols-[max-content_1fr] gap-x-[var(--lk-space-lg)] gap-y-[var(--lk-space-sm)] md:flex-1">
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
                class="text-[var(--lk-color-primary)] hover:underline"
              >{{ component.eigenaar_organisatie_naam }}</router-link>
              <span v-else>—</span>
            </dd>
            <dt class="font-semibold">Migratiepad</dt>
            <dd>{{ label(MIGRATIEPAD, component.migratiepad) }}</dd>
            <dt class="font-semibold">Complexiteit</dt>
            <dd>{{ label(NIVEAU, component.complexiteit) }}</dd>
            <dt class="font-semibold">Prioriteit</dt>
            <dd>{{ label(NIVEAU, component.prioriteit) }}</dd>
            <dt class="font-semibold">Beschrijving</dt>
            <dd class="whitespace-pre-wrap">{{ component.beschrijving || '—' }}</dd>
            <!-- ADR-028 — componentclassificatie (registratief): rol + BIV. -->
            <dt class="font-semibold">Rol</dt>
            <dd data-testid="comp-rol">{{ component.rol_label }}</dd>
            <dt class="font-semibold">BIV-classificatie</dt>
            <dd data-testid="comp-biv">
              <div class="grid grid-cols-[max-content_1fr] gap-x-[var(--lk-space-md)] gap-y-[var(--lk-space-xs)]">
                <span class="text-[var(--lk-color-text-muted)]">Beschikbaarheid</span>
                <span data-testid="comp-biv-b">{{ component.biv_beschikbaarheid_label || 'Niet geclassificeerd' }}</span>
                <span class="text-[var(--lk-color-text-muted)]">Integriteit</span>
                <span data-testid="comp-biv-i">{{ component.biv_integriteit_label || 'Niet geclassificeerd' }}</span>
                <span class="text-[var(--lk-color-text-muted)]">Vertrouwelijkheid</span>
                <span data-testid="comp-biv-v">{{ component.biv_vertrouwelijkheid_label || 'Niet geclassificeerd' }}</span>
              </div>
            </dd>
          </dl>

          <MigratiegereedheidSectie
            v-if="isChecklistDragend"
            ref="gereedheidSectie"
            class="md:w-80 md:shrink-0"
            :component-id="component.id"
            :aantal-gescoord="scoreSectie?.aantalGescoord ?? 0"
            :aantal-vragen="scoreSectie?.aantalVragen ?? 0"
          />
        </div>

        <div class="mt-[var(--lk-space-lg)] flex flex-wrap gap-[var(--lk-space-md)]">
          <Button
            v-if="magKaartZien"
            label="Bekijk op kaart"
            severity="secondary"
            data-testid="bekijk-op-kaart-knop"
            @click="bekijkOpKaart"
          />
          <Button
            v-if="magKlaarverklaren && isChecklistDragend"
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
      </div>

      <!-- Checklist: 12 categorieën als sub-navigatie (checklist-dragende typen) -->
      <div
        v-if="isChecklistDragend"
        v-show="activeTop === 'checklist'"
        id="detailtabs-panel-checklist"
        role="tabpanel"
        aria-labelledby="detailtabs-tab-checklist"
        data-testid="panel-checklist"
        class="flex flex-col gap-[var(--lk-space-md)] md:flex-row md:gap-[var(--lk-space-lg)]"
      >
        <AppTabs
          v-model="activeCat"
          :tabs="categorieTabs"
          aria-label="Checklist-categorieën"
          orientation="vertical"
          id-prefix="checklisttabs"
          class="md:w-[16rem] md:shrink-0"
        />
        <div
          :id="`checklisttabs-panel-${activeCat}`"
          role="tabpanel"
          :aria-labelledby="`checklisttabs-tab-${activeCat}`"
          class="grow"
        >
          <!-- Read-only context-paneel bij categorie 8 (Contractuele positie). -->
          <aside
            v-if="actieveCategorieNr === 8"
            role="complementary"
            aria-label="Geregistreerde contracten bij dit component"
            data-testid="context-paneel-cat8"
            class="card mb-[var(--lk-space-md)] border-l-4 border-[var(--lk-color-primary)]"
          >
            <h3 class="font-semibold">Geregistreerde contracten (registratie)</h3>
            <p class="mb-[var(--lk-space-sm)] text-[length:var(--lk-text-xs)] text-[var(--lk-color-text-muted)]">
              Ter context bij het beoordelen — registratie, geen oordeel.
            </p>
            <ul
              v-if="contractenVoorContext.length"
              data-testid="context-paneel-lijst"
              class="flex flex-col gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]"
            >
              <li v-for="r in contractenVoorContext" :key="r.koppeling_id">
                <span class="font-medium">{{ r.contractnaam }}</span> — {{ r.leverancier_naam }} ·
                {{ label(CONTRACTTYPE, r.contracttype) }} · rol: {{ r.relatie_rol_label }} ·
                {{ r.begindatum || '—' }} t/m {{ r.einddatum || '—' }}
              </li>
            </ul>
            <p v-else data-testid="context-paneel-leeg" class="text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]">
              Geen contracten geregistreerd.
              <button
                type="button"
                data-testid="context-paneel-naar-sectie"
                class="text-[var(--lk-color-primary)] hover:underline focus:outline-2 focus:outline-offset-2 focus:outline-[var(--lk-color-primary)]"
                @click="activeTop = 'contracten'"
              >
                Naar de Contracten-sectie
              </button>
            </p>
          </aside>

          <ChecklistscoreSectie
            ref="scoreSectie"
            :applicatie-id="component.id"
            :componenttype="component.componenttype"
            :categorie-nr="actieveCategorieNr"
            :markeer-code="markeerVraagCode"
            :bewerkbaar="component.checklist_dragend === true"
            @gewijzigd="onScoreGewijzigd"
          />
        </div>
      </div>

      <!-- Applicatie-eigen kind-entiteiten (alleen bij een subtype) -->
      <template v-if="isSubtype">
        <div v-show="activeTop === 'datatypes'" id="detailtabs-panel-datatypes" role="tabpanel" aria-labelledby="detailtabs-tab-datatypes">
          <DatatypeSectie :applicatie-id="props.id" />
        </div>
        <div v-show="activeTop === 'gebruikersgroepen'" id="detailtabs-panel-gebruikersgroepen" role="tabpanel" aria-labelledby="detailtabs-tab-gebruikersgroepen">
          <GebruikersgroepSectie :applicatie-id="props.id" />
        </div>
        <div v-show="activeTop === 'koppelingen'" id="detailtabs-panel-koppelingen" role="tabpanel" aria-labelledby="detailtabs-tab-koppelingen">
          <KoppelingSectie :applicatie-id="props.id" />
        </div>
      </template>

      <div v-show="activeTop === 'opbouw'" id="detailtabs-panel-opbouw" role="tabpanel" aria-labelledby="detailtabs-tab-opbouw">
        <StructuurSectie :component-id="props.id" />
      </div>
      <div v-show="activeTop === 'impact'" id="detailtabs-panel-impact" role="tabpanel" aria-labelledby="detailtabs-tab-impact">
        <ImpactSectie :component-id="props.id" />
      </div>
      <div v-show="activeTop === 'contracten'" id="detailtabs-panel-contracten" role="tabpanel" aria-labelledby="detailtabs-tab-contracten">
        <ContractSectie ref="contractSectie" :applicatie-id="props.id" :app-naam="component?.naam || ''" />
      </div>
      <div v-show="activeTop === 'verantwoordelijkheden'" id="detailtabs-panel-verantwoordelijkheden" role="tabpanel" aria-labelledby="detailtabs-tab-verantwoordelijkheden">
        <VerantwoordelijkheidSectie :object-id="props.id" />
      </div>

      <!-- Blokkades (alleen checklist-dragende typen) -->
      <div
        v-if="isChecklistDragend"
        v-show="activeTop === 'blokkades'"
        id="detailtabs-panel-blokkades"
        role="tabpanel"
        aria-labelledby="detailtabs-tab-blokkades"
      >
        <BlokkadeSectie
          ref="blokkadeSectie"
          :applicatie-id="component.id"
          @gewijzigd="onBlokkadeGewijzigd"
          @naar-vraag="onNaarVraag"
        />
      </div>
    </template>

    <Dialog v-model:visible="verwijderDialog" modal header="Component verwijderen" data-testid="verwijder-dialog">
      <p class="mb-[var(--lk-space-md)] max-w-prose">
        Weet je zeker dat je <strong>{{ component?.naam }}</strong> wilt verwijderen? Dit
        verwijdert ook alle gekoppelde datatypes, gebruikersgroepen, koppelingen,
        checklistscores en blokkades. Dit kan niet ongedaan worden gemaakt.
      </p>
      <p
        v-if="verwijderHeeftData"
        data-testid="verwijder-samenvatting"
        class="mb-[var(--lk-space-md)] max-w-prose text-[length:var(--lk-text-sm)] text-[var(--lk-color-danger)]"
      >
        Dit verwijdert ook: {{ verwijderImpact.beantwoorde_scores }} beantwoorde score(s),
        {{ verwijderImpact.blokkades }} blokkade(s), {{ verwijderImpact.datatypes }} datatype(s) en
        {{ verwijderImpact.gebruikersgroepen }} gebruikersgroep(en).
      </p>
      <div class="flex justify-end gap-[var(--lk-space-md)]">
        <Button label="Annuleren" severity="secondary" data-testid="verwijder-annuleer" @click="verwijderDialog = false" />
        <Button label="Definitief verwijderen" severity="danger" data-testid="verwijder-bevestig" :disabled="bezig" @click="bevestigVerwijderen" />
      </div>
    </Dialog>
  </section>
</template>
