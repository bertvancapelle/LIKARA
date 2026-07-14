<script setup>
/**
 * ComponentLijst — het verenigde werkscherm (ADR-021 W1 / CD054b). Eén ingang voor
 * de hele technische laag: applicatie-subtypen én kale infra (database, fileshare, …).
 *
 * Vaste kolommenset (voorspelbaar scherm): Naam · Type · Eigenaar · Hosting ·
 * Complexiteit · Prioriteit · Status — besturingsvelden tonen "—" voor typen zonder
 * beoordeling. Filterbalk gespiegeld aan de oude Applicaties-lijst: Status-checkboxes,
 * Type-select (catalogus), Hosting, Eigenaar-bevat, Naam-zoek. Keyset-"Meer laden".
 * Subtype-rijen linken naar ApplicatieDetail (rijk detail, één waarheid); overige naar
 * ComponentDetail. Een `?type=`-query (bv. via de /applicaties-redirect) preselecteert
 * het typefilter.
 */
import { computed, onMounted, ref } from 'vue'
import { Button, Column, DataTable, Tag } from '@/primevue'
import { useRoute, useRouter } from '@/composables/router'
import { useAuthStore } from '@/store/auth'
import { useLijstStaat } from '@/composables/useLijstStaat'
import { api } from '@/api'
import MultiSelectDropdown from '@/components/MultiSelectDropdown.vue'
import FilterResultaatRegel from '@/components/FilterResultaatRegel.vue'
import ComponentFormulier from '@modules/bwb_ontvlechting/frontend/views/ComponentFormulier.vue'
import ZoekSelect from '@modules/bwb_ontvlechting/frontend/views/ZoekSelect.vue'
import {
  ARCHIMATE_ELEMENT,
  ARCHIMATE_LAAG,
  HOSTINGMODEL,
  LEVENSFASE,
  LIFECYCLE,
  LIFECYCLE_SEVERITY,
  MIGRATIEPAD,
  NIVEAU,
  label,
} from '../labels'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const magAanmaken = computed(() => auth.hasRole('medewerker', 'beheerder'))

const items = ref([])
const cursor = ref(null)
const laden = ref(false)
const fout = ref(null)
const eersteGeladen = ref(false)
// LI040 — resultaatregel: gefilterd totaal + ongefilterd totaal (server-side, hele dataset).
const totaal = ref(null)
const totaalAlles = ref(null)

// Filters — gespiegeld aan de Applicaties-lijst (CD017), AND-gecombineerd.
const STATUS_OPTIES = ['concept', 'in_inventarisatie', 'geblokkeerd', 'migratieklaar']
const HOSTING_OPTIES = Object.keys(HOSTINGMODEL)
// ADR-046 — levensfase-filter ("welke systemen faseren uit?" = één klik).
const LEVENSFASE_OPTIES = Object.keys(LEVENSFASE)
const typeOpties = ref([]) // [{ optie_sleutel, label, laag, archimate_element }]
const filterStatus = ref([])
const filterType = ref('') // '' = alle; kan via ?type= worden voorgezet
const filterLaag = ref('') // ADR-023 Fase C: '' = alle ArchiMate-lagen
const filterHosting = ref('')
// ADR-046 — levensfase ('' = alle).
const filterLevensfase = ref('')
// LI040 — bedoeling ('' = alle; API-param `migratiepad`, UI-label "Bedoeling").
const filterBedoeling = ref('')
// UX-B6-b — eigenaar-filter is een organisatie-keuze (FK) i.p.v. vrije tekst.
const filterEigenaarId = ref(null)
// LI032-les: een hersteld eigenaar-id moet zijn label tonen (ZoekSelect kent alleen het
// id) → de gekozen naam meebewaren en als `initieel-weergave` teruggeven.
const filterEigenaarNaam = ref('')
const filterZoek = ref('')
// ADR-028 — rol (multi-select). LI040 — BIV is ÉÉN filter geworden: de hoogste van de
// drie assen ≥ drempel ('' = alle · catalogus-sleutel · '__zonder__' = nog niet
// vastgelegd, d.w.z. geen enkele as ingevuld). De waarden komen uit de beheerbare
// BIV-schaal-catalogus (opties-endpoint) — nooit hardcoded. De drie assen zelf blijven
// volledig bestaan op component/formulier/detail; alleen het per-as-filteren verviel.
const rolOpties = ref([]) // [{ optie_sleutel, label }]
const bivNiveaus = ref([]) // [{ optie_sleutel, label }] — ordinaal (laag → hoog)
const filterRol = ref([])
const BIV_ZONDER = '__zonder__'
const filterBiv = ref('')
// ADR-045 besluit 5 — filter op de catalogus-eigenschap "ondersteunt werk"
// ('' = alle · 'ja' · 'nee'); de vraag vóór en na een vlag-flip in het beheer.
const filterWerk = ref('')
const rolLabel = (sleutel) => rolOpties.value.find((o) => o.optie_sleutel === sleutel)?.label || sleutel
const bivLabel = (sleutel) => bivNiveaus.value.find((o) => o.optie_sleutel === sleutel)?.label || sleutel
// ADR-027 slice 3 — dashboard-doorklik-filters (geen dropdown; uit de route-query).
// LI040: zichtbaar + wisbaar via de resultaatregel-chips (geen losse chip meer).
const filterKlaarverklaring = ref('') // '' | 'klaar'
const filterAfwijking = ref(false)

// Organisatie-keuze (filter): server-side zoeken, beperkt tot aard=organisatie.
const zoekOrganisaties = (params) => api.partijen.lijst({ ...params, aard: 'organisatie' })

// Server-side sortering (ADR-017) — null = server-default (created_at asc), niet
// meegestuurd. Spiegelt BlokkadeOverzichtView: @sort → sort/order + cursor-reset + refetch.
const sortVeld = ref(null)
const sortRichting = ref(null) // 'asc' | 'desc'
const primeSortOrder = computed(() =>
  sortRichting.value === 'asc' ? 1 : sortRichting.value === 'desc' ? -1 : 0,
)
// ArchiMate-laag-filteropties afgeleid uit de catalogus-typing (distinct lagen).
const laagOpties = computed(() => {
  const seen = new Map()
  for (const o of typeOpties.value) {
    if (o.laag && !seen.has(o.laag)) seen.set(o.laag, label(ARCHIMATE_LAAG, o.laag))
  }
  return [...seen.entries()].map(([waarde, tekst]) => ({ waarde, label: tekst }))
})
const heeftFilters = computed(
  () =>
    filterStatus.value.length > 0 ||
    !!filterType.value ||
    !!filterLaag.value ||
    !!filterHosting.value ||
    !!filterLevensfase.value ||
    !!filterBedoeling.value ||
    !!filterEigenaarId.value ||
    !!filterZoek.value.trim() ||
    filterRol.value.length > 0 ||
    !!filterBiv.value ||
    !!filterWerk.value,
)

// LI040 — de resultaatregel-chips: elk actief filter uitgeschreven (label + waarde),
// los wisbaar. Dit is het antwoord op "waarom is dit leeg?" — naast de melding, niet
// verstopt in de dropdowns. Eén chip per filterveld (multi-select → waarden gejoined).
const filterChips = computed(() => {
  const chips = []
  if (filterStatus.value.length)
    chips.push({ sleutel: 'status', label: 'Status', waarde: filterStatus.value.map(lifecycleLabel).join(', ') })
  if (filterType.value)
    chips.push({ sleutel: 'type', label: 'Type', waarde: typeOpties.value.find((o) => o.optie_sleutel === filterType.value)?.label || filterType.value })
  if (filterLaag.value) chips.push({ sleutel: 'laag', label: 'Laag', waarde: laagLabel(filterLaag.value) })
  if (filterHosting.value) chips.push({ sleutel: 'hosting', label: 'Hosting', waarde: hosting(filterHosting.value) })
  if (filterLevensfase.value)
    chips.push({ sleutel: 'levensfase', label: 'Levensfase', waarde: levensfaseLabel(filterLevensfase.value) })
  if (filterBedoeling.value)
    chips.push({ sleutel: 'bedoeling', label: 'Bedoeling', waarde: label(MIGRATIEPAD, filterBedoeling.value) })
  if (filterWerk.value)
    chips.push({ sleutel: 'werk', label: 'Ondersteunt werk', waarde: filterWerk.value === 'ja' ? 'Ja' : 'Nee' })
  if (filterRol.value.length)
    chips.push({ sleutel: 'rol', label: 'Rol', waarde: filterRol.value.map(rolLabel).join(', ') })
  if (filterBiv.value)
    chips.push({
      sleutel: 'biv', label: 'BIV',
      waarde: filterBiv.value === BIV_ZONDER ? 'nog niet vastgelegd' : `≥ ${bivLabel(filterBiv.value)}`,
    })
  if (filterEigenaarId.value)
    chips.push({ sleutel: 'eigenaar', label: 'Eigenaar', waarde: filterEigenaarNaam.value || 'gekozen organisatie' })
  if (filterZoek.value.trim()) chips.push({ sleutel: 'zoek', label: 'Naam', waarde: `“${filterZoek.value.trim()}”` })
  // ADR-027 — de dashboard-doorklik-filters horen óók uitgeschreven in de regel.
  if (filterAfwijking.value)
    chips.push({ sleutel: 'afwijking', label: 'Klaarverklaring', waarde: 'klaar verklaard, checklist nog niet compleet' })
  else if (filterKlaarverklaring.value)
    chips.push({ sleutel: 'klaarverklaring', label: 'Klaarverklaring', waarde: 'klaar verklaard' })
  return chips
})

// Eén chip wissen = ALLEEN dat filterveld terug naar de default (+ herfilter).
function wisChip(sleutel) {
  const reset = {
    status: () => (filterStatus.value = []),
    type: () => (filterType.value = ''),
    laag: () => (filterLaag.value = ''),
    hosting: () => (filterHosting.value = ''),
    levensfase: () => (filterLevensfase.value = ''),
    bedoeling: () => (filterBedoeling.value = ''),
    werk: () => (filterWerk.value = ''),
    rol: () => (filterRol.value = []),
    biv: () => (filterBiv.value = ''),
    eigenaar: () => { filterEigenaarId.value = null; filterEigenaarNaam.value = '' },
    zoek: () => (filterZoek.value = ''),
    afwijking: () => (filterAfwijking.value = false),
    klaarverklaring: () => (filterKlaarverklaring.value = ''),
  }[sleutel]
  reset?.()
  herfilter()
}

// Lijststaat behouden bij terugnavigeren/F5 (lk-state-patroon; zie useLijstStaat).
// Gevalideerd herstel: onbekende waarden vallen stil terug op de default; catalogus-
// gedreven sleutels (type/laag/rol/BIV) worden ná het laden van de opties geprund.
const SORTEERBARE_VELDEN = ['naam', 'componenttype', 'eigenaar', 'hostingmodel', 'complexiteit', 'prioriteit', 'levensfase', 'migratiepad', 'lifecycle_status']
const _tekst = (w) => typeof w === 'string'
const { herstel: herstelLijstStaat } = useLijstStaat(
  'component-lijst',
  {
    filterStatus, filterType, filterLaag, filterHosting, filterLevensfase, filterBedoeling,
    filterEigenaarId, filterEigenaarNaam,
    filterZoek, filterRol, filterBiv, filterWerk,
    filterKlaarverklaring, filterAfwijking, sortVeld, sortRichting,
  },
  {
    valideer: {
      filterStatus: (w) => Array.isArray(w) && w.every((s) => STATUS_OPTIES.includes(s)),
      filterType: _tekst,
      filterLaag: _tekst,
      filterHosting: (w) => w === '' || HOSTING_OPTIES.includes(w),
      filterLevensfase: (w) => w === '' || LEVENSFASE_OPTIES.includes(w),
      filterBedoeling: (w) => w === '' || Object.keys(MIGRATIEPAD).includes(w),
      filterEigenaarId: (w) => w === null || _tekst(w),
      filterEigenaarNaam: _tekst,
      filterZoek: _tekst,
      filterRol: (w) => Array.isArray(w) && w.every(_tekst),
      filterBiv: _tekst, // catalogus-sleutel of '__zonder__'; prune tegen de catalogus na laden
      filterWerk: (w) => w === '' || w === 'ja' || w === 'nee',
      filterKlaarverklaring: (w) => w === '' || w === 'klaar',
      filterAfwijking: (w) => typeof w === 'boolean',
      sortVeld: (w) => w === null || SORTEERBARE_VELDEN.includes(w),
      sortRichting: (w) => w === null || w === 'asc' || w === 'desc',
    },
  },
)

// Catalogus-gevalideerd herstel: een bewaarde sleutel die niet (meer) in de geladen
// catalogus bestaat valt stil terug op de default — een stale BIV-sleutel zou anders
// server-side een 422 geven (nooit een kapot scherm door een stale opgeslagen stand).
// Alleen op het herstel-pad; doorklik-query's houden hun bestaande (ongewijzigde) gedrag.
function _pruneTegenCatalogus() {
  if (typeOpties.value.length) {
    if (filterType.value && !typeOpties.value.some((o) => o.optie_sleutel === filterType.value)) filterType.value = ''
    if (filterLaag.value && !typeOpties.value.some((o) => o.laag === filterLaag.value)) filterLaag.value = ''
  }
  if (rolOpties.value.length && filterRol.value.length) {
    filterRol.value = filterRol.value.filter((r) => rolOpties.value.some((o) => o.optie_sleutel === r))
  }
  // LI040 — één BIV-filter: catalogus-sleutel of de vaste '__zonder__'-optie.
  if (
    bivNiveaus.value.length && filterBiv.value && filterBiv.value !== BIV_ZONDER &&
    !bivNiveaus.value.some((n) => n.optie_sleutel === filterBiv.value)
  ) {
    filterBiv.value = ''
  }
}

async function laad({ reset = false } = {}) {
  laden.value = true
  fout.value = null
  try {
    const params = { limit: 25, after: reset ? undefined : cursor.value }
    if (filterStatus.value.length) params.status = filterStatus.value
    if (filterType.value) params.componenttype = filterType.value
    if (filterLaag.value) params.laag = filterLaag.value
    if (filterHosting.value) params.hostingmodel = filterHosting.value
    // ADR-046 — levensfase (leeg = geen clause).
    if (filterLevensfase.value) params.levensfase = filterLevensfase.value
    // LI040 — bedoeling (API-param `migratiepad`).
    if (filterBedoeling.value) params.migratiepad = filterBedoeling.value
    if (filterEigenaarId.value) params.eigenaar_organisatie_id = filterEigenaarId.value
    if (filterZoek.value.trim()) params.zoek = filterZoek.value.trim()
    // ADR-028 — rol (array → herhaalde param). LI040 — één BIV-filter: hoogste as ≥
    // drempel (`biv_min`) of het registratiegat (`biv_ontbreekt`).
    if (filterRol.value.length) params.componentrol = filterRol.value
    if (filterBiv.value === BIV_ZONDER) params.biv_ontbreekt = 1
    else if (filterBiv.value) params.biv_min = filterBiv.value
    // ADR-045 — server-side op de catalogus-eigenschap (leeg = geen clause).
    if (filterWerk.value) params.ondersteunt_werk = filterWerk.value === 'ja'
    if (filterAfwijking.value) params.afwijking = 1
    else if (filterKlaarverklaring.value) params.klaarverklaring = filterKlaarverklaring.value
    if (sortVeld.value) {
      params.sort = sortVeld.value
      params.order = sortRichting.value
    }
    const pagina = await api.componenten.lijst(params)
    items.value = reset ? pagina.items : items.value.concat(pagina.items)
    cursor.value = pagina.volgende_cursor
    // LI040 — resultaatregel-aantallen (server-side, hele dataset; ook bij "Meer laden").
    totaal.value = pagina.totaal ?? null
    totaalAlles.value = pagina.totaal_ongefilterd ?? null
  } catch (e) {
    fout.value = e?.status === 401 ? null : e?.message || 'Er ging iets mis bij het laden van de componenten.'
  } finally {
    laden.value = false
    eersteGeladen.value = true
  }
}

function onSort(event) {
  sortVeld.value = event.sortField
  sortRichting.value = event.sortOrder === 1 ? 'asc' : 'desc'
  cursor.value = null
  laad({ reset: true })
}

function herfilter() {
  cursor.value = null
  laad({ reset: true })
}
let _zoekTimer = null
function herfilterDebounced() {
  clearTimeout(_zoekTimer)
  _zoekTimer = setTimeout(herfilter, 300)
}
function wisFilters() {
  filterStatus.value = []
  filterType.value = ''
  filterLaag.value = ''
  filterHosting.value = ''
  filterLevensfase.value = ''
  filterBedoeling.value = ''
  filterEigenaarId.value = null
  filterEigenaarNaam.value = ''
  filterZoek.value = ''
  filterRol.value = []
  filterBiv.value = ''
  filterWerk.value = ''
  herfilter()
}

function rijRoute(rij) {
  // LI059 Slice 4 — één detailscherm voor élk type.
  return { name: 'component-detail', params: { id: rij.id } }
}

// ADR-042 4b — aanmaken als overlay boven de lijst; na opslaan door naar het detail
// (bestaand gedrag). De oude route `component-nieuw` redirect hierheen met ?nieuw=1.
const nieuwOverlayOpen = ref(false)
function onAangemaakt(resultaat) {
  router.push({ name: 'component-detail', params: { id: resultaat.id } })
}

const hosting = (c) => label(HOSTINGMODEL, c)
const niveau = (c) => (c ? label(NIVEAU, c) : '—')
const levensfaseLabel = (c) => label(LEVENSFASE, c)
const laagLabel = (c) => (c ? label(ARCHIMATE_LAAG, c) : '—')
const elementLabel = (c) => (c ? label(ARCHIMATE_ELEMENT, c) : '')
const lifecycleLabel = (c) => label(LIFECYCLE, c)
const lifecycleSeverity = (c) => LIFECYCLE_SEVERITY[c] || 'info'

onMounted(async () => {
  // Precedentie (kaart-lijn LI034): doorklik-query > bewaarde staat > kale defaults.
  // Een doorklik-query VERVANGT de bewaarde staat volledig — de gebruiker krijgt exact
  // wat hij aanklikte, zonder dat een oude zoekterm/filter de selectie stil uitdunt.
  // Bij het verlaten wordt de dan-actieve staat vanzelf de nieuwe bewaarde staat.
  const q = String(route.query.type ?? '')
  // Statusfilter via de URL voorzetten (dashboard-doorklik), zelfde patroon als ?type=.
  // Accepteert één of meerdere `status`-params; alleen geldige lifecycle-statussen.
  const statusQ = route.query.status
  const statussen = (Array.isArray(statusQ) ? statusQ : statusQ != null ? [statusQ] : [])
    .map(String)
    .filter((s) => STATUS_OPTIES.includes(s))
  const afwijkingQ = String(route.query.afwijking ?? '') === '1'
  const klaarQ = String(route.query.klaarverklaring ?? '') === 'klaar'
  // ADR-042 4b — deep-link /componenten/nieuw (redirect) opent de aanmaak-overlay.
  if (String(route.query.nieuw ?? '') === '1' && magAanmaken.value) nieuwOverlayOpen.value = true
  let hersteld = false
  if (q || statussen.length || afwijkingQ || klaarQ) {
    if (q) filterType.value = q
    if (statussen.length) filterStatus.value = statussen
    // ADR-027 slice 3 — klaarverklaring-doorklik vanaf het dashboard.
    if (afwijkingQ) filterAfwijking.value = true
    else if (klaarQ) filterKlaarverklaring.value = 'klaar'
  } else {
    hersteld = herstelLijstStaat()
  }
  try {
    const opties = await api.componenten.opties()
    typeOpties.value = opties.componenttype || []
    // ADR-028 — rol-opties + ordinale BIV-niveaus voor de filterbalk.
    rolOpties.value = opties.componentrol_opties || []
    bivNiveaus.value = opties.biv_niveaus || []
    if (hersteld) _pruneTegenCatalogus()
  } catch {
    /* filterlijst optioneel — het overzicht laadt sowieso */
  }
  laad({ reset: true })
})
</script>

<template>
  <section aria-labelledby="componenten-titel">
    <div class="flex items-center gap-[var(--lk-space-md)] mb-[var(--lk-space-md)]">
      <h1
        id="componenten-titel"
        class="text-[length:var(--lk-text-2xl)] font-semibold text-[var(--lk-color-primary)]"
      >
        Componenten
      </h1>
      <Button
        v-if="magAanmaken"
        label="Nieuw component"
        data-testid="nieuw-component"
        class="ml-auto"
        @click="nieuwOverlayOpen = true"
      />
    </div>

    <!-- ADR-042 4b — aanmaak-overlay: de lijst blijft eronder zichtbaar. Lazy gemount
         (v-if): pas bij openen laden de opties; sluiten unmount hem weer. -->
    <ComponentFormulier v-if="nieuwOverlayOpen" v-model:visible="nieuwOverlayOpen" :id="null" @opgeslagen="onAangemaakt" />

    <!-- Filterbalk (CD017) — AND-gecombineerd; elke wijziging reset de cursor. -->
    <div
      data-testid="filterbalk"
      class="mb-[var(--lk-space-md)] flex flex-wrap items-end gap-[var(--lk-space-md)] rounded-[var(--lk-radius-card)] bg-[var(--lk-color-surface)] p-[var(--lk-space-md)] shadow-[var(--lk-shadow-sm)]"
    >
      <label class="flex flex-col gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]">
        <span class="text-[length:var(--lk-text-xs)] font-semibold uppercase tracking-wide text-[var(--lk-color-text-muted)]">Status</span>
        <!-- Multi-select dropdown (zelfde stijl als Type/Laag/Hosting); meervoudige
             selectie behouden (filterStatus blijft een array → server-side IN). -->
        <MultiSelectDropdown
          v-model="filterStatus"
          :opties="STATUS_OPTIES"
          :weergave="lifecycleLabel"
          placeholder="Alle"
          aria-label="Filter op status"
          testid="filter-status"
          @change="herfilter"
        />
      </label>

      <label class="flex flex-col gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]">
        <span class="text-[length:var(--lk-text-xs)] font-semibold uppercase tracking-wide text-[var(--lk-color-text-muted)]">Type</span>
        <select
          v-model="filterType"
          data-testid="filter-type"
          aria-label="Filter op componenttype"
          class="lk-veld"
          @change="herfilter"
        >
          <option value="">Alle</option>
          <option v-for="o in typeOpties" :key="o.optie_sleutel" :value="o.optie_sleutel">{{ o.label }}</option>
        </select>
      </label>

      <label class="flex flex-col gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]">
        <span class="text-[length:var(--lk-text-xs)] font-semibold uppercase tracking-wide text-[var(--lk-color-text-muted)]">Laag</span>
        <select
          v-model="filterLaag"
          data-testid="filter-laag"
          aria-label="Filter op ArchiMate-laag"
          class="lk-veld"
          @change="herfilter"
        >
          <option value="">Alle</option>
          <option v-for="o in laagOpties" :key="o.waarde" :value="o.waarde">{{ o.label }}</option>
        </select>
      </label>

      <label class="flex flex-col gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]">
        <span class="text-[length:var(--lk-text-xs)] font-semibold uppercase tracking-wide text-[var(--lk-color-text-muted)]">Hosting</span>
        <select
          v-model="filterHosting"
          data-testid="filter-hosting"
          aria-label="Filter op hostingmodel"
          class="lk-veld"
          @change="herfilter"
        >
          <option value="">Alle</option>
          <option v-for="h in HOSTING_OPTIES" :key="h" :value="h">{{ hosting(h) }}</option>
        </select>
      </label>

      <!-- ADR-046 — levensfase-filter: "welke systemen faseren uit?" is één klik. -->
      <label class="flex flex-col gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]">
        <span class="text-[length:var(--lk-text-xs)] font-semibold uppercase tracking-wide text-[var(--lk-color-text-muted)]">Levensfase</span>
        <select
          v-model="filterLevensfase"
          data-testid="filter-levensfase"
          aria-label="Filter op levensfase"
          class="lk-veld"
          @change="herfilter"
        >
          <option value="">Alle</option>
          <option v-for="f in LEVENSFASE_OPTIES" :key="f" :value="f">{{ levensfaseLabel(f) }}</option>
        </select>
      </label>

      <!-- LI040 — bedoeling-filter: "welke systemen gaan we vervangen?" is één klik
           (de tweede vraag naast de levensfase — ADR-046). -->
      <label class="flex flex-col gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]">
        <span class="text-[length:var(--lk-text-xs)] font-semibold uppercase tracking-wide text-[var(--lk-color-text-muted)]">Bedoeling</span>
        <select
          v-model="filterBedoeling"
          data-testid="filter-bedoeling"
          aria-label="Filter op bedoeling"
          class="lk-veld"
          @change="herfilter"
        >
          <option value="">Alle</option>
          <option v-for="code in Object.keys(MIGRATIEPAD)" :key="code" :value="code">{{ label(MIGRATIEPAD, code) }}</option>
        </select>
      </label>

      <label class="flex flex-col gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]">
        <span class="text-[length:var(--lk-text-xs)] font-semibold uppercase tracking-wide text-[var(--lk-color-text-muted)]">Ondersteunt werk</span>
        <select
          v-model="filterWerk"
          data-testid="filter-ondersteunt-werk"
          aria-label="Filter op ondersteunt werk"
          class="lk-veld"
          @change="herfilter"
        >
          <option value="">Alle</option>
          <option value="ja">Ja</option>
          <option value="nee">Nee</option>
        </select>
      </label>

      <label class="flex flex-col gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]">
        <span class="text-[length:var(--lk-text-xs)] font-semibold uppercase tracking-wide text-[var(--lk-color-text-muted)]">Rol</span>
        <MultiSelectDropdown
          v-model="filterRol"
          :opties="rolOpties.map((o) => o.optie_sleutel)"
          :weergave="rolLabel"
          placeholder="Alle"
          aria-label="Filter op componentrol"
          testid="filter-rol"
          @change="herfilter"
        />
      </label>

      <!-- LI040 — één BIV-filter (de zwaarste as bepaalt): ≥ drempel op de hoogste van de
           drie assen, of "nog niet vastgelegd" (geen enkele as ingevuld — het gat vindbaar).
           Waarden uit de beheerbare BIV-schaal-catalogus, nooit hardcoded. -->
      <label class="flex flex-col gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]">
        <span class="text-[length:var(--lk-text-xs)] font-semibold uppercase tracking-wide text-[var(--lk-color-text-muted)]">BIV ≥</span>
        <select
          v-model="filterBiv"
          data-testid="filter-biv"
          aria-label="Filter op BIV-classificatie (hoogste as)"
          class="lk-veld"
          @change="herfilter"
        >
          <option value="">Alle</option>
          <option v-for="n in bivNiveaus" :key="n.optie_sleutel" :value="n.optie_sleutel">{{ n.label }}</option>
          <option :value="BIV_ZONDER">nog niet vastgelegd</option>
        </select>
      </label>

      <label class="flex flex-col gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]">
        <span class="text-[length:var(--lk-text-xs)] font-semibold uppercase tracking-wide text-[var(--lk-color-text-muted)]">Eigenaar</span>
        <ZoekSelect
          testid="filter-eigenaar"
          v-model="filterEigenaarId"
          :zoek-functie="zoekOrganisaties"
          :initieel-weergave="filterEigenaarNaam"
          placeholder="Kies een organisatie…"
          @keuze="(p) => (filterEigenaarNaam = p?.naam || '')"
          @update:model-value="herfilter"
        />
      </label>

      <label class="flex flex-col gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]">
        <span class="text-[length:var(--lk-text-xs)] font-semibold uppercase tracking-wide text-[var(--lk-color-text-muted)]">Naam</span>
        <input
          v-model="filterZoek"
          type="search"
          maxlength="100"
          data-testid="filter-zoek"
          aria-label="Zoek op componentnaam"
          placeholder="zoeken…"
          class="lk-veld"
          @input="herfilterDebounced"
        />
      </label>

      <button
        v-if="heeftFilters"
        type="button"
        data-testid="filters-wissen"
        class="ml-auto rounded-[var(--lk-radius-btn)] border border-[var(--lk-color-border)] px-[var(--lk-space-md)] py-1 text-[length:var(--lk-text-sm)] hover:bg-[var(--lk-color-accent)] focus:outline-2 focus:outline-offset-2 focus:outline-[var(--lk-color-primary)]"
        @click="wisFilters"
      >
        Filters wissen
      </button>
    </div>

    <p
      v-if="fout"
      role="alert"
      data-testid="lijst-fout"
      class="mb-[var(--lk-space-md)] rounded-[var(--lk-radius-badge)] border border-[var(--lk-color-danger)] bg-[var(--lk-color-danger)]/10 px-[var(--lk-space-md)] py-[var(--lk-space-sm)] text-[var(--lk-color-danger)]"
    >
      {{ fout }}
    </p>

    <!-- LI040 — de resultaatregel: aantal (altijd) + elk actief filter uitgeschreven en
         los wisbaar. De lege-melding in de tabel staat zo náást zijn eigen reden.
         (De vroegere losse klaarverklaring-chip is hierin opgegaan.) -->
    <FilterResultaatRegel
      :totaal="totaal"
      :totaal-alles="totaalAlles"
      :chips="filterChips"
      eenheid="componenten"
      eenheid-enkelvoud="component"
      @wis="wisChip"
    />

    <!-- Server-side sortering (ADR-017): lazy + @sort → sort/order + cursor-reset.
         Laag is bewust NIET sorteerbaar (afgeleide ArchiMate-projectie, geen kolom). -->
    <DataTable
      :value="items"
      lazy
      :sort-field="sortVeld"
      :sort-order="primeSortOrder"
      data-testid="componenten-tabel"
      class="bg-[var(--lk-color-surface)] rounded-[var(--lk-radius-card)] shadow-[var(--lk-shadow-sm)]"
      @sort="onSort"
    >
      <Column field="naam" header="Naam" sortable>
        <template #body="{ data }">
          <router-link
            :to="rijRoute(data)"
            data-testid="rij-link"
            class="text-[var(--lk-color-primary)] font-medium hover:underline focus:outline-2 focus:outline-offset-2 focus:outline-[var(--lk-color-primary)]"
          >
            {{ data.naam }}
          </router-link>
        </template>
      </Column>
      <Column header="Type" sort-field="componenttype" sortable>
        <template #body="{ data }">
          <Tag :value="data.componenttype_label" :severity="data.heeft_applicatie_subtype ? 'info' : 'secondary'" />
        </template>
      </Column>
      <Column header="Laag">
        <template #body="{ data }">
          <span data-testid="rij-laag">{{ laagLabel(data.laag) }}</span>
          <span
            v-if="elementLabel(data.archimate_element)"
            class="block text-[length:var(--lk-text-xs)] text-[var(--lk-color-text-muted)]"
          >
            {{ elementLabel(data.archimate_element) }}
          </span>
        </template>
      </Column>
      <Column header="Eigenaar" sort-field="eigenaar" sortable>
        <template #body="{ data }">
          <router-link
            v-if="data.eigenaar_organisatie_id"
            :to="{ name: 'partij-detail', params: { id: data.eigenaar_organisatie_id } }"
            :data-testid="`comp-eigenaar-org-link-${data.id}`"
            class="text-[var(--lk-color-primary)] hover:underline"
          >{{ data.eigenaar_organisatie_naam }}</router-link>
          <span v-else>—</span>
        </template>
      </Column>
      <Column header="Hosting" sort-field="hostingmodel" sortable>
        <template #body="{ data }">{{ hosting(data.hostingmodel) }}</template>
      </Column>
      <Column header="Complexiteit" sort-field="complexiteit" sortable>
        <template #body="{ data }">{{ niveau(data.complexiteit) }}</template>
      </Column>
      <Column header="Prioriteit" sort-field="prioriteit" sortable>
        <template #body="{ data }">{{ niveau(data.prioriteit) }}</template>
      </Column>
      <!-- ADR-046 — levensfase-kolom: ontbrekend = gedempt "nog niet vastgelegd" (nooit rood). -->
      <Column header="Levensfase" sort-field="levensfase" sortable>
        <template #body="{ data }">
          <span v-if="data.levensfase" data-testid="rij-levensfase">{{ levensfaseLabel(data.levensfase) }}</span>
          <span v-else data-testid="levensfase-leeg" class="text-[var(--lk-color-text-muted)]">nog niet vastgelegd</span>
        </template>
      </Column>
      <!-- LI040 — bedoeling-kolom (sorteerbaar, zoals levensfase — de twee vragen samen). -->
      <Column header="Bedoeling" sort-field="migratiepad" sortable>
        <template #body="{ data }">
          <span data-testid="rij-bedoeling">{{ label(MIGRATIEPAD, data.migratiepad) }}</span>
        </template>
      </Column>
      <Column header="Status" sort-field="lifecycle_status" sortable>
        <template #body="{ data }">
          <Tag v-if="data.lifecycle_status" :value="lifecycleLabel(data.lifecycle_status)" :severity="lifecycleSeverity(data.lifecycle_status)" />
          <span v-else data-testid="status-leeg">—</span>
        </template>
      </Column>
      <template #empty>
        <span v-if="eersteGeladen && !laden && heeftFilters" data-testid="lijst-geen-match">
          Geen componenten komen overeen met de filters.
        </span>
        <span v-else-if="eersteGeladen && !laden" data-testid="lijst-leeg">
          Er zijn nog geen componenten in deze tenant.
        </span>
        <span v-else data-testid="lijst-laden-leeg">Laden…</span>
      </template>
    </DataTable>

    <div class="mt-[var(--lk-space-md)] flex items-center gap-[var(--lk-space-md)]">
      <Button
        v-if="cursor"
        label="Meer laden"
        severity="secondary"
        data-testid="meer-laden"
        :disabled="laden"
        @click="laad()"
      />
      <span v-if="laden && items.length" data-testid="lijst-laden" class="text-[var(--lk-color-text-muted)] text-[length:var(--lk-text-sm)]">
        Laden…
      </span>
    </div>
  </section>
</template>
