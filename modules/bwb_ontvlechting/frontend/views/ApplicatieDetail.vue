<script setup>
/**
 * ApplicatieDetail — detailweergave + acties (BWB-ontvlechtingsmodule).
 *
 * Rol-gating is affordance (knoppen tonen/verbergen); de backend handhaaft via
 * `vereist_permissie`. Een 403 wordt alsnog netjes in een Toast getoond.
 * `lifecycle_status` is read-only (Tag); "Start inventarisatie" alleen bij
 * status `concept`. Verwijderen waarschuwt voor de cascade.
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
  label,
} from '../labels'
// Herbruikbare toegankelijke tablist (CD022, #11 — 2-laags IA).
import AppTabs from './AppTabs.vue'
import ObjectHistoriePaneel from './ObjectHistoriePaneel.vue'
// Child-secties (subordinate aan de ouder, blijven in de detail-context).
import DatatypeSectie from './DatatypeSectie.vue'
import GebruikersgroepSectie from './GebruikersgroepSectie.vue'
import KoppelingSectie from './KoppelingSectie.vue'
import ContractSectie from './ContractSectie.vue'
import VerantwoordelijkheidSectie from './VerantwoordelijkheidSectie.vue'
// ADR-021 Fase D — de Opbouw-laag (structuurgraaf) van deze applicatie-component
// (shared-PK: applicatie-id ís component-id).
import StructuurSectie from './StructuurSectie.vue'
// ADR-021 Fase E — impactanalyse (een applicatie kan zelf onderlegger zijn).
import ImpactSectie from './ImpactSectie.vue'
import ChecklistscoreSectie from './ChecklistscoreSectie.vue'
import BlokkadeSectie from './BlokkadeSectie.vue'
import MigratiegereedheidSectie from './MigratiegereedheidSectie.vue'

const props = defineProps({ id: { type: String, required: true } })
const route = useRoute()
const router = useRouter()
const { terugLabel, gaTerug } = useTerugNavigatie()
const toast = useToast()
const auth = useAuthStore()

const applicatie = ref(null)
const laden = ref(false)
const fout = ref(null)
const verwijderDialog = ref(false)
const bezig = ref(false)
// ADR-022 Fase C: read-only "wat verdwijnt"-samenvatting (applicatie-id == component-id).
const verwijderImpact = ref(null)

async function openVerwijderDialog() {
  verwijderImpact.value = null
  verwijderDialog.value = true
  try {
    verwijderImpact.value = await api.componenten.verwijderImpact(props.id)
  } catch {
    verwijderImpact.value = null
  }
}

const verwijderHeeftData = computed(() => {
  const i = verwijderImpact.value
  return !!i && (i.beantwoorde_scores || i.blokkades || i.datatypes || i.gebruikersgroepen)
})

const magBewerken = computed(() => auth.hasRole('medewerker', 'beheerder'))
const magVerwijderen = computed(() => auth.hasRole('beheerder'))
const magStarten = computed(
  () => magBewerken.value && applicatie.value?.lifecycle_status === 'concept',
)
// ADR-027 — migratiegereedheid (component-klaarverklaring). Knop verbergen zonder rol (backend handhaaft).
const gereedheidSectie = ref(null)
const magKlaarverklaren = computed(() => auth.hasRole('medewerker', 'beheerder'))
const gereedheidLabel = computed(() => (gereedheidSectie.value?.status === 'klaar' ? 'Heropenen' : 'Klaar verklaren'))

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

// ADR-025: open de Landschapskaart in Ego-view, gecentreerd op deze applicatie.
function openInLandschapskaart() {
  router.push({ name: 'landschapskaart', query: { center: props.id, modus: 'ego' } })
}

// Lifecycle-coördinatie (ADR-013): de frontend berekent niets zelf — na een
// score/blokkade-mutatie wordt de status opnieuw bij de backend opgehaald.
const scoreSectie = ref(null)
const blokkadeSectie = ref(null)
// §5 — het context-paneel bij categorie 8 hergebruikt de al geladen koppeling-state
// uit ContractSectie (geen extra fetch, ADR-020 Besluit 9/10: read-only, niet besturend).
const contractSectie = ref(null)
const contractenVoorContext = computed(() => contractSectie.value?.items ?? [])

// ── 2-laags tabnavigatie (CD022, #11) ───────────────────────────────────────
// Top-niveau = applicatie-aspecten; "Checklist" bevat de 12 categorieën als
// sub-navigatie. Alle panelen blijven gemount (`v-show`) → geen state-verlies bij
// wisselen en de refs (`scoreSectie`/`blokkadeSectie`) blijven geldig voor de
// globale voortgangsregel. Geen mini-ADR: dit is frontend-IA, geen datamodel.
const TOP_TABS = [
  { key: 'overzicht', label: 'Overzicht' },
  { key: 'checklist', label: 'Checklist' },
  { key: 'datatypes', label: 'Datatypes' },
  { key: 'gebruikersgroepen', label: 'Gebruikersgroepen' },
  { key: 'koppelingen', label: 'Koppelingen' },
  { key: 'opbouw', label: 'Opbouw' },
  { key: 'impact', label: 'Impact' },
  { key: 'contracten', label: 'Contracten' },
  { key: 'verantwoordelijkheden', label: 'Verantwoordelijkheden' },
  { key: 'blokkades', label: 'Blokkades' },
]
const TOP_KEYS = TOP_TABS.map((t) => t.key)

const activeTop = ref('overzicht')
const activeCat = ref(null) // categorie_nr als string-key

// Categorie-sub-tabs: labels afgeleid uit de geladen vragen (geen seed-duplicatie).
const categorieTabs = computed(() =>
  (scoreSectie.value?.categorieen ?? []).map((c) => ({ key: String(c.nr), label: c.naam })),
)
const actieveCategorieNr = computed(() => (activeCat.value != null ? Number(activeCat.value) : null))

// Deep-link initialiseren uit de URL (na mount; de scoreSectie laadt async).
function _initVanafQuery() {
  const t = String(route.query.tab ?? '')
  if (TOP_KEYS.includes(t)) activeTop.value = t
  if (route.query.cat != null) activeCat.value = String(route.query.cat)
  // ADR-024-vervolg: deep-link vanuit de tenant-brede blokkadelijst markeert een vraag.
  // Hergebruikt hetzelfde markeerpad als de in-page `naar-vraag` (geen tweede mechaniek).
  if (route.query.markeer != null) {
    activeTop.value = 'checklist'
    markeerVraagCode.value = String(route.query.markeer)
  }
}

// Zodra de categorieën geladen zijn: zorg dat activeCat geldig is (default = eerste).
watch(categorieTabs, (tabs) => {
  if (tabs.length && !tabs.some((t) => t.key === activeCat.value)) activeCat.value = tabs[0].key
})

// Actieve tab(s) terugschrijven naar de URL. Overzicht = schone URL (geen query);
// `router.replace` (geen history-spam). Browser-back werkt via de query-historie.
watch([activeTop, activeCat], () => {
  const query = {}
  if (activeTop.value !== 'overzicht') query.tab = activeTop.value
  if (activeTop.value === 'checklist' && activeCat.value != null) query.cat = activeCat.value
  const huidigTab = route.query.tab ?? undefined
  const huidigCat = route.query.cat != null ? String(route.query.cat) : undefined
  if (huidigTab === (query.tab ?? undefined) && huidigCat === (query.cat ?? undefined)) return
  router.replace({ query })
})

async function herlaadApplicatie() {
  try {
    applicatie.value = await api.applicaties.haal(props.id)
  } catch (e) {
    /* status-refresh faalt stil; de fout van de mutatie zelf is al getoond */
  }
}

async function onScoreGewijzigd() {
  // Een score kan een blokkade laten ontstaan/oplossen → blokkadelijst + status.
  await herlaadApplicatie()
  blokkadeSectie.value?.herlaad()
}

async function onBlokkadeGewijzigd() {
  await herlaadApplicatie()
}

// Herkomst-doorklik vanuit BlokkadeSectie: schakel naar het Checklist-tabblad +
// de categorie van de veroorzakende vraag, en markeer die vraag (scroll/highlight
// in ChecklistscoreSectie). Read-only navigatie.
const markeerVraagCode = ref(null)
function onNaarVraag({ code, categorieNr }) {
  activeTop.value = 'checklist'
  if (categorieNr != null) activeCat.value = String(categorieNr)
  markeerVraagCode.value = code
}

// Navigatie applicatie-detail → applicatie-detail hergebruikt de instance; watch op props.id
// (immediate) herlaadt + her-initialiseert de deep-link bij elke id-wissel (vervangt onMounted).
watch(() => props.id, async () => { await laad(); _initVanafQuery() }, { immediate: true })
</script>

<template>
  <section aria-labelledby="detail-titel">
    <button v-if="terugLabel" type="button" data-testid="terug-knop" class="mb-[var(--cd-space-md)] inline-flex items-center text-[length:var(--cd-text-sm)] text-[var(--cd-color-text-muted)] hover:text-[var(--cd-color-primary)] hover:underline focus:outline-2 focus:outline-offset-2 focus:outline-[var(--cd-color-primary)]" @click="gaTerug">{{ terugLabel }}</button>
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

      <p data-testid="detail-voortgang" class="mb-[var(--cd-space-md)] text-[var(--cd-color-text-muted)]">
        {{ scoreSectie?.aantalGescoord ?? 0 }}/{{ scoreSectie?.aantalVragen ?? 0 }} vragen gescoord ·
        {{ blokkadeSectie?.aantalOpen ?? 0 }} open blokkade(s)
      </p>

      <AppTabs
        v-model="activeTop"
        :tabs="TOP_TABS"
        aria-label="Applicatie-detail onderdelen"
        id-prefix="detailtabs"
        class="mt-[var(--cd-space-lg)] mb-[var(--cd-space-md)]"
      />

      <!-- Overzicht: metadata + acties -->
      <div
        v-show="activeTop === 'overzicht'"
        id="detailtabs-panel-overzicht"
        role="tabpanel"
        aria-labelledby="detailtabs-tab-overzicht"
        data-testid="panel-overzicht"
      >
        <div class="flex flex-col gap-[var(--cd-space-lg)] md:flex-row md:items-start">
        <dl class="card grid grid-cols-[max-content_1fr] gap-x-[var(--cd-space-lg)] gap-y-[var(--cd-space-sm)] md:flex-1">
          <dt class="font-semibold">Eigenaar-organisatie</dt>
          <dd>
            <router-link
              v-if="applicatie.eigenaar_organisatie_id"
              :to="{ name: 'partij-detail', params: { id: applicatie.eigenaar_organisatie_id } }"
              data-testid="app-eigenaar-org-link"
              class="text-[var(--cd-color-primary)] hover:underline"
            >{{ applicatie.eigenaar_organisatie_naam }}</router-link>
            <span v-else>—</span>
          </dd>
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

        <MigratiegereedheidSectie
          ref="gereedheidSectie"
          class="md:w-80 md:shrink-0"
          :component-id="applicatie.id"
          :aantal-gescoord="scoreSectie?.aantalGescoord ?? 0"
          :aantal-vragen="scoreSectie?.aantalVragen ?? 0"
        />
        </div>

        <div class="mt-[var(--cd-space-lg)] flex flex-wrap gap-[var(--cd-space-md)]">
          <Button
            label="Open in Landschapskaart"
            severity="secondary"
            data-testid="open-landschapskaart-knop"
            @click="openInLandschapskaart"
          />
          <Button
            v-if="magKlaarverklaren"
            :label="gereedheidLabel"
            severity="secondary"
            data-testid="klaarverklaar-knop"
            @click="(e) => gereedheidSectie?.openDialog(e)"
          />
          <ObjectHistoriePaneel entiteit-type="applicatie" :entiteit-id="props.id" />
          <Button v-if="magBewerken" label="Bewerken" data-testid="bewerken-knop" @click="naarBewerken" />
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
            @click="openVerwijderDialog"
          />
        </div>
      </div>

      <!-- Checklist: 12 categorieën als sub-navigatie (één gedeelde score-instantie) -->
      <div
        v-show="activeTop === 'checklist'"
        id="detailtabs-panel-checklist"
        role="tabpanel"
        aria-labelledby="detailtabs-tab-checklist"
        data-testid="panel-checklist"
        class="flex flex-col gap-[var(--cd-space-md)] md:flex-row md:gap-[var(--cd-space-lg)]"
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
          <!-- §5 — read-only context-paneel bij categorie 8 (Contractuele positie).
               Strikt eenrichtings: registratie, geen oordeel, geen schrijf-affordances. -->
          <aside
            v-if="actieveCategorieNr === 8"
            role="complementary"
            aria-label="Geregistreerde contracten bij deze applicatie"
            data-testid="context-paneel-cat8"
            class="card mb-[var(--cd-space-md)] border-l-4 border-[var(--cd-color-primary)]"
          >
            <h3 class="font-semibold">Geregistreerde contracten (registratie)</h3>
            <p class="mb-[var(--cd-space-sm)] text-[length:var(--cd-text-xs)] text-[var(--cd-color-text-muted)]">
              Ter context bij het beoordelen — registratie, geen oordeel.
            </p>
            <ul
              v-if="contractenVoorContext.length"
              data-testid="context-paneel-lijst"
              class="flex flex-col gap-[var(--cd-space-xs)] text-[length:var(--cd-text-sm)]"
            >
              <li v-for="r in contractenVoorContext" :key="r.koppeling_id">
                <span class="font-medium">{{ r.contractnaam }}</span> — {{ r.leverancier_naam }} ·
                {{ label(CONTRACTTYPE, r.contracttype) }} · rol: {{ r.relatie_rol_label }} ·
                {{ r.begindatum || '—' }} t/m {{ r.einddatum || '—' }}
              </li>
            </ul>
            <p v-else data-testid="context-paneel-leeg" class="text-[length:var(--cd-text-sm)] text-[var(--cd-color-text-muted)]">
              Geen contracten geregistreerd.
              <button
                type="button"
                data-testid="context-paneel-naar-sectie"
                class="text-[var(--cd-color-primary)] hover:underline focus:outline-2 focus:outline-offset-2 focus:outline-[var(--cd-color-primary)]"
                @click="activeTop = 'contracten'"
              >
                Naar de Contracten-sectie
              </button>
            </p>
          </aside>

          <ChecklistscoreSectie
            ref="scoreSectie"
            :applicatie-id="props.id"
            :componenttype="'applicatie'"
            :categorie-nr="actieveCategorieNr"
            :markeer-code="markeerVraagCode"
            :bewerkbaar="applicatie.checklist_dragend !== false"
            @gewijzigd="onScoreGewijzigd"
          />
        </div>
      </div>

      <!-- Child-entiteiten als eigen top-level tabs -->
      <div
        v-show="activeTop === 'datatypes'"
        id="detailtabs-panel-datatypes"
        role="tabpanel"
        aria-labelledby="detailtabs-tab-datatypes"
      >
        <DatatypeSectie :applicatie-id="props.id" />
      </div>
      <div
        v-show="activeTop === 'gebruikersgroepen'"
        id="detailtabs-panel-gebruikersgroepen"
        role="tabpanel"
        aria-labelledby="detailtabs-tab-gebruikersgroepen"
      >
        <GebruikersgroepSectie :applicatie-id="props.id" />
      </div>
      <div
        v-show="activeTop === 'koppelingen'"
        id="detailtabs-panel-koppelingen"
        role="tabpanel"
        aria-labelledby="detailtabs-tab-koppelingen"
      >
        <KoppelingSectie :applicatie-id="props.id" />
      </div>
      <div
        v-show="activeTop === 'opbouw'"
        id="detailtabs-panel-opbouw"
        role="tabpanel"
        aria-labelledby="detailtabs-tab-opbouw"
      >
        <StructuurSectie :component-id="props.id" />
      </div>
      <div
        v-show="activeTop === 'impact'"
        id="detailtabs-panel-impact"
        role="tabpanel"
        aria-labelledby="detailtabs-tab-impact"
      >
        <ImpactSectie :component-id="props.id" />
      </div>
      <div
        v-show="activeTop === 'contracten'"
        id="detailtabs-panel-contracten"
        role="tabpanel"
        aria-labelledby="detailtabs-tab-contracten"
      >
        <ContractSectie ref="contractSectie" :applicatie-id="props.id" :app-naam="applicatie?.naam || ''" />
      </div>
      <div
        v-show="activeTop === 'verantwoordelijkheden'"
        id="detailtabs-panel-verantwoordelijkheden"
        role="tabpanel"
        aria-labelledby="detailtabs-tab-verantwoordelijkheden"
      >
        <VerantwoordelijkheidSectie :object-id="props.id" />
      </div>
      <div
        v-show="activeTop === 'blokkades'"
        id="detailtabs-panel-blokkades"
        role="tabpanel"
        aria-labelledby="detailtabs-tab-blokkades"
      >
        <BlokkadeSectie
          ref="blokkadeSectie"
          :applicatie-id="props.id"
          @gewijzigd="onBlokkadeGewijzigd"
          @naar-vraag="onNaarVraag"
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
      <p
        v-if="verwijderHeeftData"
        data-testid="verwijder-samenvatting"
        class="mb-[var(--cd-space-md)] max-w-prose text-[length:var(--cd-text-sm)] text-[var(--cd-color-danger)]"
      >
        Dit verwijdert: {{ verwijderImpact.beantwoorde_scores }} beantwoorde score(s),
        {{ verwijderImpact.blokkades }} blokkade(s), {{ verwijderImpact.datatypes }} datatype(s) en
        {{ verwijderImpact.gebruikersgroepen }} gebruikersgroep(en).
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
