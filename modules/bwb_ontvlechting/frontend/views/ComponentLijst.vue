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
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { Button, Column, DataTable, Dialog, Tag } from '@/primevue'
import { detailRoute } from '@/detailIngang'
import { useRoute, useRouter } from '@/composables/router'
import { useAuthStore } from '@/store/auth'
import { useLijstStaat } from '@/composables/useLijstStaat'
import { api } from '@/api'
import MultiSelectDropdown from '@/components/MultiSelectDropdown.vue'
import FilterResultaatRegel from '@/components/FilterResultaatRegel.vue'
import LijstKop from '@/components/LijstKop.vue'
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
  veldLabel,
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
// LI040 — oordelen ('' = alle; echte niveaus + het gat "nog niet vastgelegd").
const filterComplexiteit = ref('')
const filterPrioriteit = ref('')
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
// LI040 — gedeeld client-sentinel voor "nog niet vastgelegd" (server-side wordt dit een
// `*_ontbreekt`-param: filteren op AFWEZIGHEID/NULL, nooit op een sentinel-waarde).
const ZONDER = '__zonder__'
const filterBiv = ref('')
// ADR-045 besluit 5 — filter op de catalogus-eigenschap "ondersteunt werk"
// ('' = alle · 'ja' · 'nee'); de vraag vóór en na een vlag-flip in het beheer.
const filterWerk = ref('')
// ADR-043 gate 4 (G4) — werkvoorraad: '' = alle · ZONDER = "nog geen bedrijfsfunctie" (het gat).
const filterZonderBedrijfsfunctie = ref('')
const rolLabel = (sleutel) => rolOpties.value.find((o) => o.optie_sleutel === sleutel)?.label || sleutel
const bivLabel = (sleutel) => bivNiveaus.value.find((o) => o.optie_sleutel === sleutel)?.label || sleutel
// ADR-027 slice 3 — dashboard-doorklik-filters (geen dropdown; uit de route-query).
// LI040: zichtbaar + wisbaar via de resultaatregel-chips (geen losse chip meer).
const filterKlaarverklaring = ref('') // '' | 'klaar'
const filterAfwijking = ref(false)

// LI048 — de filters wonen in een venster. `VELDEN` is DE lijst van filters die daarheen reizen,
// `_refs` koppelt elke naam aan zijn ref. Eén plek: een nieuw filter dat hier ontbreekt staat wel
// in het venster maar doet niets bij Toepassen — en dat valt meteen op. Het zoekveld staat er
// bewust NIET bij: dat blijft bovenin en wordt direct toegepast.
const VELDEN = [
  'filterStatus', 'filterType', 'filterLaag', 'filterHosting', 'filterLevensfase',
  'filterBedoeling', 'filterComplexiteit', 'filterPrioriteit', 'filterEigenaarId',
  'filterEigenaarNaam', 'filterRol', 'filterBiv', 'filterWerk', 'filterZonderBedrijfsfunctie',
  'filterKlaarverklaring', 'filterAfwijking',
]
const _refs = {
  filterStatus, filterType, filterLaag, filterHosting, filterLevensfase, filterBedoeling,
  filterComplexiteit, filterPrioriteit, filterEigenaarId, filterEigenaarNaam, filterRol,
  filterBiv, filterWerk, filterZonderBedrijfsfunctie, filterKlaarverklaring, filterAfwijking,
}
const _kopie = (w) => (Array.isArray(w) ? [...w] : w)

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
    !!filterComplexiteit.value ||
    !!filterPrioriteit.value ||
    !!filterEigenaarId.value ||
    !!filterZoek.value.trim() ||
    filterRol.value.length > 0 ||
    !!filterBiv.value ||
    !!filterWerk.value ||
    !!filterZonderBedrijfsfunctie.value,
)

// LI040 — de resultaatregel-chips: elk actief filter uitgeschreven (label + waarde),
// los wisbaar. Dit is het antwoord op "waarom is dit leeg?" — naast de melding, niet
// verstopt in de dropdowns. Eén chip per filterveld (multi-select → waarden gejoined).
const filterChips = computed(() => {
  const chips = []
  if (filterStatus.value.length)
    chips.push({ sleutel: 'status', label: veldLabel('lifecycle_status'), waarde: filterStatus.value.map(lifecycleLabel).join(', ') })
  if (filterType.value)
    chips.push({ sleutel: 'type', label: 'Type', waarde: typeOpties.value.find((o) => o.optie_sleutel === filterType.value)?.label || filterType.value })
  if (filterLaag.value) chips.push({ sleutel: 'laag', label: 'Laag', waarde: laagLabel(filterLaag.value) })
  if (filterHosting.value) chips.push({ sleutel: 'hosting', label: 'Hosting', waarde: hosting(filterHosting.value) })
  if (filterLevensfase.value)
    chips.push({
      sleutel: 'levensfase', label: 'Levensfase',
      waarde: filterLevensfase.value === ZONDER ? 'nog niet vastgelegd' : levensfaseLabel(filterLevensfase.value),
    })
  if (filterBedoeling.value)
    chips.push({
      sleutel: 'bedoeling', label: 'Bedoeling',
      waarde: filterBedoeling.value === ZONDER ? 'nog niet vastgelegd' : label(MIGRATIEPAD, filterBedoeling.value),
    })
  if (filterComplexiteit.value)
    chips.push({
      sleutel: 'complexiteit', label: 'Complexiteit',
      waarde: filterComplexiteit.value === ZONDER ? 'nog niet vastgelegd' : niveau(filterComplexiteit.value),
    })
  if (filterPrioriteit.value)
    chips.push({
      sleutel: 'prioriteit', label: 'Prioriteit',
      waarde: filterPrioriteit.value === ZONDER ? 'nog niet vastgelegd' : niveau(filterPrioriteit.value),
    })
  if (filterWerk.value)
    chips.push({ sleutel: 'werk', label: 'Ondersteunt werk', waarde: filterWerk.value === 'ja' ? 'Ja' : 'Nee' })
  if (filterZonderBedrijfsfunctie.value)
    chips.push({ sleutel: 'bedrijfsfunctie', label: 'Bedrijfsfunctie', waarde: 'nog geen' })
  if (filterRol.value.length)
    chips.push({ sleutel: 'rol', label: 'Rol', waarde: filterRol.value.map(rolLabel).join(', ') })
  if (filterBiv.value)
    chips.push({
      sleutel: 'biv', label: 'BIV',
      waarde: filterBiv.value === ZONDER ? 'nog niet vastgelegd' : `≥ ${bivLabel(filterBiv.value)}`,
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
    complexiteit: () => (filterComplexiteit.value = ''),
    prioriteit: () => (filterPrioriteit.value = ''),
    werk: () => (filterWerk.value = ''),
    bedrijfsfunctie: () => (filterZonderBedrijfsfunctie.value = ''),
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
    filterComplexiteit, filterPrioriteit,
    filterEigenaarId, filterEigenaarNaam,
    filterZoek, filterRol, filterBiv, filterWerk, filterZonderBedrijfsfunctie,
    filterKlaarverklaring, filterAfwijking, sortVeld, sortRichting,
  },
  {
    valideer: {
      filterStatus: (w) => Array.isArray(w) && w.every((s) => STATUS_OPTIES.includes(s)),
      filterType: _tekst,
      filterLaag: _tekst,
      filterHosting: (w) => w === '' || HOSTING_OPTIES.includes(w),
      filterLevensfase: (w) => w === '' || w === ZONDER || LEVENSFASE_OPTIES.includes(w),
      filterBedoeling: (w) => w === '' || w === ZONDER || Object.keys(MIGRATIEPAD).includes(w),
      filterComplexiteit: (w) => w === '' || w === ZONDER || Object.keys(NIVEAU).includes(w),
      filterPrioriteit: (w) => w === '' || w === ZONDER || Object.keys(NIVEAU).includes(w),
      filterEigenaarId: (w) => w === null || _tekst(w),
      filterEigenaarNaam: _tekst,
      filterZoek: _tekst,
      filterRol: (w) => Array.isArray(w) && w.every(_tekst),
      filterBiv: _tekst, // catalogus-sleutel of '__zonder__'; prune tegen de catalogus na laden
      filterWerk: (w) => w === '' || w === 'ja' || w === 'nee',
      filterZonderBedrijfsfunctie: (w) => w === '' || w === ZONDER,
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
    bivNiveaus.value.length && filterBiv.value && filterBiv.value !== ZONDER &&
    !bivNiveaus.value.some((n) => n.optie_sleutel === filterBiv.value)
  ) {
    filterBiv.value = ''
  }
}

/**
 * Filterwaarden → API-parameters. ÉÉN plek (LI048): zowel de lijst als de live-teller in het
 * filtervenster bouwen hier hun params, alleen met een andere bron (`_refs` = de toegepaste
 * stand, `concept` = wat de gebruiker aan het kiezen is). Een tweede opbouw zou betekenen dat
 * het venster "7" zegt terwijl de lijst er acht toont — dezelfde faalmodus als een tweede
 * telling, maar dan een laag eerder.
 *
 * `bron` levert per veldnaam de waarde; `_refs`-waarden komen via `.value`, concept-waarden
 * direct. Vandaar de kleine helper i.p.v. twee varianten van deze functie.
 */
function _paramsUit(bron) {
  const w = (naam) => (bron === _refs ? _refs[naam].value : bron[naam])
  const params = {}
  if (w('filterStatus')?.length) params.status = w('filterStatus')
  if (w('filterType')) params.componenttype = w('filterType')
  if (w('filterLaag')) params.laag = w('filterLaag')
  if (w('filterHosting')) params.hostingmodel = w('filterHosting')
  // ADR-046/LI040 — levensfase; "nog niet vastgelegd" filtert op afwezigheid (NULL).
  if (w('filterLevensfase') === ZONDER) params.levensfase_ontbreekt = 1
  else if (w('filterLevensfase')) params.levensfase = w('filterLevensfase')
  // LI040 — bedoeling (API-param `migratiepad`); idem voor het gat.
  if (w('filterBedoeling') === ZONDER) params.migratiepad_ontbreekt = 1
  else if (w('filterBedoeling')) params.migratiepad = w('filterBedoeling')
  // LI040 — oordelen: echte niveaus of het gat ("nooit naar gekeken" ≠ "vastgesteld").
  if (w('filterComplexiteit') === ZONDER) params.complexiteit_ontbreekt = 1
  else if (w('filterComplexiteit')) params.complexiteit = w('filterComplexiteit')
  if (w('filterPrioriteit') === ZONDER) params.prioriteit_ontbreekt = 1
  else if (w('filterPrioriteit')) params.prioriteit = w('filterPrioriteit')
  if (w('filterEigenaarId')) params.eigenaar_organisatie_id = w('filterEigenaarId')
  // ADR-028 — rol (array → herhaalde param). LI040 — één BIV-filter: hoogste as ≥
  // drempel (`biv_min`) of het registratiegat (`biv_ontbreekt`).
  if (w('filterRol')?.length) params.componentrol = w('filterRol')
  if (w('filterBiv') === ZONDER) params.biv_ontbreekt = 1
  else if (w('filterBiv')) params.biv_min = w('filterBiv')
  // ADR-045 — server-side op de catalogus-eigenschap (leeg = geen clause).
  if (w('filterWerk')) params.ondersteunt_werk = w('filterWerk') === 'ja'
  // ADR-043 gate 4 (G4) — werkvoorraad: alleen werk-ondersteunende systemen zonder koppeling.
  if (w('filterZonderBedrijfsfunctie') === ZONDER) params.zonder_bedrijfsfunctie = 1
  if (w('filterAfwijking')) params.afwijking = 1
  else if (w('filterKlaarverklaring')) params.klaarverklaring = w('filterKlaarverklaring')
  return params
}

async function laad({ reset = false } = {}) {
  laden.value = true
  fout.value = null
  try {
    const params = { limit: 25, after: reset ? undefined : cursor.value, ..._paramsUit(_refs) }
    // Het zoeken staat BUITEN het filtervenster (het blijft bovenin) en reist dus niet mee in
    // de conceptstaat — vandaar hier, niet in `_paramsUit`.
    if (filterZoek.value.trim()) params.zoek = filterZoek.value.trim()
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
  filterComplexiteit.value = ''
  filterPrioriteit.value = ''
  filterEigenaarId.value = null
  filterEigenaarNaam.value = ''
  filterZoek.value = ''
  filterRol.value = []
  filterBiv.value = ''
  filterWerk.value = ''
  filterZonderBedrijfsfunctie.value = ''
  herfilter()
}

// ── LI048 — de filters wonen in een venster; het zoeken blijft bovenin ──────────────────────
// Dertien filtervelden namen drie rijen in beslag, dus de lijst — waar de consultant voor komt —
// begon pas daaronder. Zijn werkvolgorde is een andere: eerst een naam zoeken, dáárna soms
// filteren. Alle velden verhuizen, niet een selectie van "de meest gebruikte": dan hoeft niemand
// te raden welke hij het vaakst nodig heeft, en mist hij nooit een filter omdat het verstopt zit.
//
// CONCEPTSTAAT (besluit 4): kiezen in het venster wijzigt de lijst nog niet. De echte filter-refs
// blijven staan tot hij op "Toon N componenten" drukt, zodat hij van gedachten kan veranderen
// zonder dat de lijst al is omgegooid. Escape en het kruisje gooien het concept weg.
const filterVensterOpen = ref(false)
const concept = reactive({})
const conceptTotaal = ref(null)
const conceptBezig = ref(false)
let _filterKnop = null
let _telTimer = null

function openFilterVenster(e) {
  _filterKnop = e?.currentTarget ?? null
  for (const naam of VELDEN) concept[naam] = _kopie(_refs[naam].value)
  conceptTotaal.value = totaal.value // tot de eerste telling: de huidige stand, geen leeg vak
  filterVensterOpen.value = true
}

/** Sluiten ZONDER toepassen (Annuleren) — het concept wordt weggegooid. */
function sluitFilterVenster() {
  filterVensterOpen.value = false
}

/**
 * Ná élke manier van sluiten — Annuleren, het kruisje, Escape én Toepassen. De focus keert
 * terug naar de Filter-knop, zodat wie met het toetsenbord werkt niet bovenaan de pagina
 * belandt. Aan `@hide` gehangen en niet aan de knoppen: Escape en het kruisje lopen niet door
 * onze eigen handlers, dus een focus-herstel per knop zou juist die twee missen.
 */
function naVensterSluiten() {
  clearTimeout(_telTimer) // een lopende telling hoeft niet meer te landen
  conceptBezig.value = false
  nextTick(() => _filterKnop?.focus?.())
}

/** Toepassen: het concept wordt de echte stand, en pas dán herlaadt de lijst. */
function pasFiltersToe() {
  for (const naam of VELDEN) _refs[naam].value = _kopie(concept[naam])
  filterVensterOpen.value = false
  herfilter()
}

// Besluit 3 — LIVE meetellen terwijl hij kiest, zodat hij vóór het sluiten weet wat hij krijgt en
// niet pas achteraf ontdekt dat hij op nul is uitgekomen. Met dertien filters gebeurt dat makkelijk.
// ÉÉN BRON: dit is exact het lijst-endpoint dat ook de teller naast de chips voedt — de server telt
// via `svc.tel`, dat `_pas_filters_toe` deelt met `lijst` (LI040: één filterwaarheid). Alleen de
// PARAMETERS verschillen (concept vs. toegepast); er is geen tweede berekening.
watch(concept, () => {
  if (!filterVensterOpen.value) return
  clearTimeout(_telTimer)
  conceptBezig.value = true
  _telTimer = setTimeout(async () => {
    // Nogmaals kijken of het venster nog openstaat: tussen het plannen en het vuren kan hij
    // gesloten zijn. Zonder deze poort doet een late timer alsnog een aanroep op een venster dat
    // niemand meer ziet — en die aanroep landt dan als "laatste api-call", wat in de suite de
    // volgende toets omver duwde. De timer wordt óók opgeruimd (bij sluiten en bij unmount); dit
    // is de vangrail die niet afhangt van of dat opruimen op tijd gebeurt.
    if (!filterVensterOpen.value) return
    try {
      const pagina = await api.componenten.lijst({ ..._paramsUit(concept), limit: 1 })
      conceptTotaal.value = pagina.totaal ?? null
    } catch {
      conceptTotaal.value = null // telling is een hulpje; een fout hier mag het venster niet breken
    } finally {
      conceptBezig.value = false
    }
  }, 250)
}, { deep: true })

// Beide debounce-timers opruimen bij het verlaten van het scherm. Zonder dit vuurt een lopende
// telling ná unmount — in de app een overbodige call op een scherm dat niemand meer ziet, en in
// de suite testvervuiling: de late call landt in de VOLGENDE test, waar `calls.at(-1)` dan de
// teller aanwijst i.p.v. de lijst. Dat gebeurde ook echt: de toets slaagde geïsoleerd en viel om
// in de volle run.
onBeforeUnmount(() => {
  clearTimeout(_telTimer)
  clearTimeout(_zoekTimer)
})

// Het aantal actieve filters op de knop. ÉÉN BRON met de chiprij: beide lezen `filterChips`, dus
// een filter kan niet wél tellen en géén chip krijgen (of andersom) — precies het defect waar deze
// opdracht voor bestaat: een verstopt filter is een onzichtbaar filter.
const aantalFilters = computed(() => filterChips.value.length)

function rijRoute(rij) {
  // LI059 Slice 4 — één detailscherm voor élk type.
  return detailRoute('component', rij.id)
}

// ADR-042 4b — aanmaken als overlay boven de lijst; na opslaan door naar het detail
// (bestaand gedrag). De oude route `component-nieuw` redirect hierheen met ?nieuw=1.
const nieuwOverlayOpen = ref(false)
function onAangemaakt(resultaat) {
  router.push(detailRoute('component', resultaat.id))
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
    <!-- LI048 — één kop voor élk lijstscherm (LijstKop): naam · zoeken · filteren · aanmaken, in
         die volgorde en op dezelfde plek. De consultant hoeft per scherm niet opnieuw te zoeken
         waar hij zoekt. Het zoekveld en de Filter-knop stonden hier in een apart blok eronder;
         ze zijn nu de slots van de kop. -->
    <LijstKop titel="Componenten" titel-id="componenten-titel">
      <template #zoek>
        <label class="flex items-center gap-[var(--lk-space-sm)]">
          <span class="sr-only">Naam</span>
          <input
            v-model="filterZoek"
            type="search"
            maxlength="100"
            data-testid="filter-zoek"
            aria-label="Zoek op componentnaam"
            placeholder="Zoek op naam…"
            class="lk-veld w-full"
            @input="herfilterDebounced"
          />
        </label>
      </template>
      <template #filter>
        <button
          type="button"
          data-testid="filter-knop"
          :aria-label="aantalFilters ? `Filter — ${aantalFilters} actief` : 'Filter'"
          class="lk-veld inline-flex items-center gap-[var(--lk-space-xs)] hover:bg-[var(--lk-color-primary-50)] focus:outline-2 focus:outline-offset-2 focus:outline-[var(--lk-color-primary)]"
          @click="openFilterVenster"
        >
          <span>Filter</span>
          <!-- Bij nul geen getal: de rust ís het signaal dat er niets gefilterd wordt (likara-ux). -->
          <span
            v-if="aantalFilters"
            data-testid="filter-knop-teller"
            class="font-semibold text-[var(--lk-color-primary)]"
          >({{ aantalFilters }})</span>
        </button>
      </template>
      <template v-if="magAanmaken" #actie>
        <Button
          label="Nieuw component"
          data-testid="nieuw-component"
          @click="nieuwOverlayOpen = true"
        />
      </template>
    </LijstKop>

    <!-- ADR-042 4b — aanmaak-overlay: de lijst blijft eronder zichtbaar. Lazy gemount
         (v-if): pas bij openen laden de opties; sluiten unmount hem weer. -->
    <ComponentFormulier v-if="nieuwOverlayOpen" v-model:visible="nieuwOverlayOpen" :id="null" @opgeslagen="onAangemaakt" />

    <!-- "Filters wissen" hoort bij de UITKOMST, niet bij de besturing: hij verschijnt pas als er
         iets te wissen is en staat daarom bij de chiprij, niet in de kop (regel 1 — in de kop
         staat wat de lijst bepaalt, en dit ruimt op wat al bepaald ís). -->
    <div v-if="heeftFilters" class="mb-[var(--lk-space-md)] flex">
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


    <!-- Het filtervenster (CD017-filters, AND-gecombineerd). ALLE velden staan hier — niet een
         selectie van "de meest gebruikte": dan hoeft niemand te raden welke de consultant het
         vaakst nodig heeft, en mist hij nooit een filter omdat het achter een "toon meer" zit.
         Kiezen past nog niets toe (besluit 4): pas de knop onderin commit het concept, zodat hij
         van gedachten kan veranderen zonder dat de lijst al is omgegooid. -->
    <Dialog
      v-model:visible="filterVensterOpen"
      modal
      header="Filter componenten"
      data-testid="filter-venster"
      class="!w-[48rem] !max-w-[95vw]"
      @hide="naVensterSluiten"
    >
      <div
        data-testid="filterbalk"
        class="flex flex-wrap items-end gap-[var(--lk-space-md)]"
      >
      <label class="flex flex-col gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]">
        <span class="text-[length:var(--lk-text-xs)] font-semibold uppercase tracking-wide text-[var(--lk-color-text-muted)]">{{ veldLabel('lifecycle_status') }}</span>
        <!-- Multi-select dropdown (zelfde stijl als Type/Laag/Hosting); meervoudige
             selectie behouden (filterStatus blijft een array → server-side IN). -->
        <MultiSelectDropdown
          v-model="concept.filterStatus"
          :opties="STATUS_OPTIES"
          :weergave="lifecycleLabel"
          placeholder="Alle"
          aria-label="Filter op status"
          testid="filter-status"
        />
      </label>

      <label class="flex flex-col gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]">
        <span class="text-[length:var(--lk-text-xs)] font-semibold uppercase tracking-wide text-[var(--lk-color-text-muted)]">Type</span>
        <select
          v-model="concept.filterType"
          data-testid="filter-type"
          aria-label="Filter op componenttype"
          class="lk-veld"
        >
          <option value="">Alle</option>
          <option v-for="o in typeOpties" :key="o.optie_sleutel" :value="o.optie_sleutel">{{ o.label }}</option>
        </select>
      </label>

      <label class="flex flex-col gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]">
        <span class="text-[length:var(--lk-text-xs)] font-semibold uppercase tracking-wide text-[var(--lk-color-text-muted)]">Laag</span>
        <select
          v-model="concept.filterLaag"
          data-testid="filter-laag"
          aria-label="Filter op ArchiMate-laag"
          class="lk-veld"
        >
          <option value="">Alle</option>
          <option v-for="o in laagOpties" :key="o.waarde" :value="o.waarde">{{ o.label }}</option>
        </select>
      </label>

      <label class="flex flex-col gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]">
        <span class="text-[length:var(--lk-text-xs)] font-semibold uppercase tracking-wide text-[var(--lk-color-text-muted)]">Hosting</span>
        <select
          v-model="concept.filterHosting"
          data-testid="filter-hosting"
          aria-label="Filter op hostingmodel"
          class="lk-veld"
        >
          <option value="">Alle</option>
          <option v-for="h in HOSTING_OPTIES" :key="h" :value="h">{{ hosting(h) }}</option>
        </select>
      </label>

      <!-- ADR-046 — levensfase-filter: "welke systemen faseren uit?" is één klik. -->
      <label class="flex flex-col gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]">
        <span class="text-[length:var(--lk-text-xs)] font-semibold uppercase tracking-wide text-[var(--lk-color-text-muted)]">Levensfase</span>
        <select
          v-model="concept.filterLevensfase"
          data-testid="filter-levensfase"
          aria-label="Filter op levensfase"
          class="lk-veld"
        >
          <option value="">Alle</option>
          <option v-for="f in LEVENSFASE_OPTIES" :key="f" :value="f">{{ levensfaseLabel(f) }}</option>
          <option :value="ZONDER">nog niet vastgelegd</option>
        </select>
      </label>

      <!-- LI040 — bedoeling-filter: "welke systemen gaan we vervangen?" is één klik
           (de tweede vraag naast de levensfase — ADR-046). -->
      <label class="flex flex-col gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]">
        <span class="text-[length:var(--lk-text-xs)] font-semibold uppercase tracking-wide text-[var(--lk-color-text-muted)]">Bedoeling</span>
        <select
          v-model="concept.filterBedoeling"
          data-testid="filter-bedoeling"
          aria-label="Filter op bedoeling"
          class="lk-veld"
        >
          <option value="">Alle</option>
          <option v-for="code in Object.keys(MIGRATIEPAD)" :key="code" :value="code">{{ label(MIGRATIEPAD, code) }}</option>
          <option :value="ZONDER">nog niet vastgelegd</option>
        </select>
      </label>

      <!-- LI040 — oordeel-filters: niveaus + het gat (geen verzonnen 'Midden' meer). -->
      <label class="flex flex-col gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]">
        <span class="text-[length:var(--lk-text-xs)] font-semibold uppercase tracking-wide text-[var(--lk-color-text-muted)]">Complexiteit</span>
        <select
          v-model="concept.filterComplexiteit"
          data-testid="filter-complexiteit"
          aria-label="Filter op complexiteit"
          class="lk-veld"
        >
          <option value="">Alle</option>
          <option v-for="n in Object.keys(NIVEAU)" :key="n" :value="n">{{ niveau(n) }}</option>
          <option :value="ZONDER">nog niet vastgelegd</option>
        </select>
      </label>

      <label class="flex flex-col gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]">
        <span class="text-[length:var(--lk-text-xs)] font-semibold uppercase tracking-wide text-[var(--lk-color-text-muted)]">Prioriteit</span>
        <select
          v-model="concept.filterPrioriteit"
          data-testid="filter-prioriteit"
          aria-label="Filter op prioriteit"
          class="lk-veld"
        >
          <option value="">Alle</option>
          <option v-for="n in Object.keys(NIVEAU)" :key="n" :value="n">{{ niveau(n) }}</option>
          <option :value="ZONDER">nog niet vastgelegd</option>
        </select>
      </label>

      <label class="flex flex-col gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]">
        <span class="text-[length:var(--lk-text-xs)] font-semibold uppercase tracking-wide text-[var(--lk-color-text-muted)]">Ondersteunt werk</span>
        <select
          v-model="concept.filterWerk"
          data-testid="filter-ondersteunt-werk"
          aria-label="Filter op ondersteunt werk"
          class="lk-veld"
        >
          <option value="">Alle</option>
          <option value="ja">Ja</option>
          <option value="nee">Nee</option>
        </select>
      </label>

      <label class="flex flex-col gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]">
        <span class="text-[length:var(--lk-text-xs)] font-semibold uppercase tracking-wide text-[var(--lk-color-text-muted)]">Bedrijfsfunctie</span>
        <select
          v-model="concept.filterZonderBedrijfsfunctie"
          data-testid="filter-zonder-bedrijfsfunctie"
          aria-label="Filter op componenten zonder bedrijfsfunctie"
          class="lk-veld"
        >
          <option value="">Alle</option>
          <option :value="ZONDER">nog geen bedrijfsfunctie</option>
        </select>
      </label>

      <label class="flex flex-col gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]">
        <span class="text-[length:var(--lk-text-xs)] font-semibold uppercase tracking-wide text-[var(--lk-color-text-muted)]">Rol</span>
        <MultiSelectDropdown
          v-model="concept.filterRol"
          :opties="rolOpties.map((o) => o.optie_sleutel)"
          :weergave="rolLabel"
          placeholder="Alle"
          aria-label="Filter op componentrol"
          testid="filter-rol"
        />
      </label>

      <!-- LI040 — één BIV-filter (de zwaarste as bepaalt): ≥ drempel op de hoogste van de
           drie assen, of "nog niet vastgelegd" (geen enkele as ingevuld — het gat vindbaar).
           Waarden uit de beheerbare BIV-schaal-catalogus, nooit hardcoded. -->
      <label class="flex flex-col gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]">
        <span class="text-[length:var(--lk-text-xs)] font-semibold uppercase tracking-wide text-[var(--lk-color-text-muted)]">BIV ≥</span>
        <select
          v-model="concept.filterBiv"
          data-testid="filter-biv"
          aria-label="Filter op BIV-classificatie (hoogste as)"
          class="lk-veld"
        >
          <option value="">Alle</option>
          <option v-for="n in bivNiveaus" :key="n.optie_sleutel" :value="n.optie_sleutel">{{ n.label }}</option>
          <option :value="ZONDER">nog niet vastgelegd</option>
        </select>
      </label>

      <label class="flex flex-col gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]">
        <span class="text-[length:var(--lk-text-xs)] font-semibold uppercase tracking-wide text-[var(--lk-color-text-muted)]">Eigenaar</span>
        <ZoekSelect
          testid="filter-eigenaar"
          v-model="concept.filterEigenaarId"
          :zoek-functie="zoekOrganisaties"
          :initieel-weergave="filterEigenaarNaam"
          placeholder="Kies een organisatie…"
          @keuze="(p) => (concept.filterEigenaarNaam = p?.naam || '')"
        />
      </label>

      </div>

      <!-- Besluit 3 — de teller telt LIVE mee terwijl hij kiest, zodat hij vóór het sluiten weet
           wat hij krijgt en niet pas achteraf ontdekt dat hij op nul is uitgekomen. Met dertien
           filters gebeurt dat makkelijk. Dezelfde bron als de teller naast de chips: het
           lijst-endpoint (`svc.tel` deelt `_pas_filters_toe` met `lijst`), alleen met de
           concept-parameters. -->
      <template #footer>
        <div class="flex w-full items-center gap-[var(--lk-space-md)]">
          <span
            data-testid="filter-venster-telling"
            aria-live="polite"
            class="text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]"
          >
            <template v-if="conceptBezig">tellen…</template>
            <template v-else-if="conceptTotaal === 0">Geen componenten — verruim een filter.</template>
            <template v-else-if="conceptTotaal !== null">
              {{ conceptTotaal }} van {{ totaalAlles ?? conceptTotaal }} componenten
            </template>
          </span>
          <Button
            label="Annuleren"
            severity="secondary"
            data-testid="filter-annuleer"
            class="ml-auto"
            @click="sluitFilterVenster"
          />
          <Button
            :label="conceptTotaal === null ? 'Toon componenten' : `Toon ${conceptTotaal} ${conceptTotaal === 1 ? 'component' : 'componenten'}`"
            data-testid="filter-toepassen"
            @click="pasFiltersToe"
          />
        </div>
      </template>
    </Dialog>

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
            :to="detailRoute('partij', data.eigenaar_organisatie_id)"
            :data-testid="`comp-eigenaar-org-link-${data.id}`"
            class="text-[var(--lk-color-primary)] hover:underline"
          >{{ data.eigenaar_organisatie_naam }}</router-link>
          <span v-else>—</span>
        </template>
      </Column>
      <Column header="Hosting" sort-field="hostingmodel" sortable>
        <template #body="{ data }">{{ hosting(data.hostingmodel) }}</template>
      </Column>
      <!-- LI040 — oordelen zonder waarde: gedempt "nog niet vastgelegd" (één leegte-
           taal; nooit een verzonnen 'Midden'). -->
      <Column header="Complexiteit" sort-field="complexiteit" sortable>
        <template #body="{ data }">
          <span v-if="data.complexiteit" data-testid="rij-complexiteit">{{ niveau(data.complexiteit) }}</span>
          <span v-else data-testid="complexiteit-leeg" class="text-[var(--lk-color-text-muted)]">nog niet vastgelegd</span>
        </template>
      </Column>
      <Column header="Prioriteit" sort-field="prioriteit" sortable>
        <template #body="{ data }">
          <span v-if="data.prioriteit" data-testid="rij-prioriteit">{{ niveau(data.prioriteit) }}</span>
          <span v-else data-testid="prioriteit-leeg" class="text-[var(--lk-color-text-muted)]">nog niet vastgelegd</span>
        </template>
      </Column>
      <!-- ADR-046 — levensfase-kolom: ontbrekend = gedempt "nog niet vastgelegd" (nooit rood). -->
      <Column header="Levensfase" sort-field="levensfase" sortable>
        <template #body="{ data }">
          <span v-if="data.levensfase" data-testid="rij-levensfase">{{ levensfaseLabel(data.levensfase) }}</span>
          <span v-else data-testid="levensfase-leeg" class="text-[var(--lk-color-text-muted)]">nog niet vastgelegd</span>
        </template>
      </Column>
      <!-- LI040 — bedoeling-kolom (sorteerbaar); ontbrekend = gedempt "nog niet
           vastgelegd", identiek aan levensfase (één leegte-taal, nooit "Onbekend"). -->
      <Column header="Bedoeling" sort-field="migratiepad" sortable>
        <template #body="{ data }">
          <span v-if="data.migratiepad" data-testid="rij-bedoeling">{{ label(MIGRATIEPAD, data.migratiepad) }}</span>
          <span v-else data-testid="bedoeling-leeg" class="text-[var(--lk-color-text-muted)]">nog niet vastgelegd</span>
        </template>
      </Column>
      <Column :header="veldLabel('lifecycle_status')" sort-field="lifecycle_status" sortable>
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
