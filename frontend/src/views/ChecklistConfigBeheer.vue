<script setup>
/**
 * ChecklistConfigBeheer — TENANT-beheer van de checklist-vragenset + antwoord-
 * configuratie (ADR-022 W1/W2/W3/W4, LI050). Schil op de tenant-endpoints
 * (`/checklistconfig`, lk_app): de server handhaaft álle regels.
 *
 * Indeling (LI050): bovenaan kies je het COMPONENTTYPE; links staan de categorieën
 * van dat type (naam + aantal vragen, één geselecteerd); rechts uitsluitend de
 * vragen van de gekozen categorie. De kolom ís het filter — het losse
 * categoriefilter is vervallen. Nergens staat een vraagcode: de code is intern
 * (identiteit-anker voor de deeplink) en wordt bij aanmaken door het systeem
 * toegekend (W4).
 *
 * Leesbaarheid (LI050-ergonomie): rechts staat één REGEL per vraag — tekst +
 * actieve staat; dicht is de rusttoestand. De onderbouwing (antwoordtype,
 * betekenis, antwoordopties) verschijnt pas na openklappen. Slepen werkt op de
 * ingeklapte regels; een geopende vraag is bewust niet sleepbaar (HTML5-drag op
 * een voorouder kaapt anders het selecteren/typen in de velden eronder).
 *
 * Rechten (W2): iedereen leest; alleen de beheerder ziet bewerk-affordances.
 */
import { computed, reactive, ref, watch } from 'vue'
import Dialog from 'primevue/dialog'
import { useToast } from 'primevue/usetoast'
import { api } from '@/api'
import { useAuthStore } from '@/store/auth'
import { SleepGreep, useSleepLijst } from '@/composables/useSleepLijst'
import VeldUitleg from '@modules/bwb_ontvlechting/frontend/views/VeldUitleg.vue'
import LijstKop from '@/components/LijstKop.vue'

const ANTWOORDTYPES = ['geen', 'enkelvoudige_keuze', 'meerkeuze', 'getal']
const TYPE_LABEL = {
  geen: 'Geen',
  enkelvoudige_keuze: 'Enkelvoudige keuze',
  meerkeuze: 'Meerkeuze',
  getal: 'Getal',
}

// ADR-022 W2 / LI050 — vraag- en categoriebeheer zijn beheerder-only; iedereen leest.
const auth = useAuthStore()
const magBeheren = computed(() => auth.hasRole('beheerder'))

const toast = useToast()
const vragen = ref([])
const componenttypeOpties = ref([]) // [{ optie_sleutel, label }]
const betekenisOpties = ref([]) // [{ optie_sleutel, label }] — ADR-023 Fase F (F-3)
const categorieen = ref([]) // [{ id, componenttype, naam, volgorde, aantal_vragen }]
const laden = ref(false)
const fout = ref(null)
const actieFout = ref(null)

// LI050 — de indeling: één componenttype tegelijk; de linkerkolom is het filter.
const typeKeuze = ref('')
const geselecteerdeCategorieId = ref(null)

const nieuweOptie = reactive({}) // vraag-id -> { optie_sleutel, label } — volgorde: achteraan, daarna slepen
// W4: geen code-invoer meer — het systeem kent de code toe.
const nieuweVraag = reactive({ vraag: '' })
const nieuweCategorie = reactive({ naam: '' })

// LI050-ergonomie: dicht is de rusttoestand, en ÉÉN vraag tegelijk open — openen
// sluit de vorige, zodat er nooit twijfel is welke velden bij welke vraag horen.
const openVraagId = ref(null)
function toggleVraag(vraag) {
  const opent = openVraagId.value !== vraag.id
  openVraagId.value = opent ? vraag.id : null
  // ADR-056 — verse tekst-buffer bij openen: bewerken muteert de vraag niet tot het
  // opslaan-venster bevestigd is.
  if (opent) vraagBewerk[vraag.id] = vraag.vraag
}

// ── ADR-056 besluit 13/16 — de vraagtekst bewerken met één opslaan-venster ──────
// De beheerder typt in een buffer; "Vraagtekst opslaan" opent het venster dat de
// wijziging benoemt, "dit raakt N antwoorden" voorspelt (besluit 12, uit dezelfde
// telling als het beeld erná) en de keuze verduidelijking/wijziging stelt — één
// keer, ZONDER voorselectie (besluit 16: een vinkje is een uitspraak).
const vraagBewerk = reactive({}) // vraag.id -> tekst-buffer
const opslaanVenster = ref(null) // { vraagId, oud, nieuw, aard: '', aantal: null|-1|N }
const vensterBezig = ref(false)

function tekstGewijzigd(vraag) {
  const buf = (vraagBewerk[vraag.id] ?? vraag.vraag).trim()
  return !!buf && buf !== vraag.vraag
}

async function openOpslaanVenster(vraag) {
  const nieuw = (vraagBewerk[vraag.id] ?? '').trim()
  if (!nieuw || nieuw === vraag.vraag) return
  actieFout.value = null
  opslaanVenster.value = { vraagId: vraag.id, oud: vraag.vraag, nieuw, aard: '', aantal: null }
  try {
    const { aantal_antwoorden } = await api.checklistconfig.impactAntwoorden(vraag.id)
    if (opslaanVenster.value?.vraagId === vraag.id) opslaanVenster.value.aantal = aantal_antwoorden
  } catch {
    // Best-effort voorspelling: het venster zegt dan eerlijk dat de telling ontbreekt.
    if (opslaanVenster.value?.vraagId === vraag.id) opslaanVenster.value.aantal = -1
  }
}

async function bevestigVraagtekst() {
  const v = opslaanVenster.value
  if (!v || !v.aard || vensterBezig.value) return
  vensterBezig.value = true
  try {
    const updated = await api.checklistconfig.werkVraagBij(v.vraagId, {
      vraag: v.nieuw,
      wijzigingsaard: v.aard,
    })
    _vervangVraag(updated)
    vraagBewerk[v.vraagId] = updated.vraag
    opslaanVenster.value = null
    toast.add({ severity: 'success', summary: 'Opgeslagen', detail: 'Vraagtekst opgeslagen.', life: 3000 })
  } catch (e) {
    _toonFout(e)
  } finally {
    vensterBezig.value = false
  }
}

// Meervoudsvorm voor de voorspelling ("1 antwoord" / "N antwoorden").
function antwoordTelling(aantal) {
  return aantal === 1 ? '1 antwoord' : `${aantal} antwoorden`
}

// Categorieën van het gekozen type, in hun volgorde.
const typeCategorieen = computed(() =>
  categorieen.value
    .filter((c) => c.componenttype === typeKeuze.value)
    .sort((a, b) => a.volgorde - b.volgorde || a.naam.localeCompare(b.naam)),
)

const geopendeCategorie = computed(
  () => typeCategorieen.value.find((c) => c.id === geselecteerdeCategorieId.value) || null,
)

// Rechts: uitsluitend de vragen van de gekozen categorie (interne code = volgorde).
const zichtbareVragen = computed(() =>
  vragen.value
    .filter(
      (v) => v.componenttype === typeKeuze.value && v.categorie_id === geselecteerdeCategorieId.value,
    )
    // LI050 (W5): de beheerde sleep-volgorde, niet de code.
    .sort((a, b) => (a.volgorde ?? 0) - (b.volgorde ?? 0)),
)

// Uitstaande (gedeactiveerde) vragen per categorie — benoemd in de linkerkolom.
function aantalUit(catId) {
  return vragen.value.filter((v) => v.categorie_id === catId && !v.actief).length
}

// Typewissel → eerste categorie van dat type openen; categorielijst leeg → niets open.
watch([typeKeuze, typeCategorieen], () => {
  if (!typeCategorieen.value.some((c) => c.id === geselecteerdeCategorieId.value)) {
    geselecteerdeCategorieId.value = typeCategorieen.value[0]?.id ?? null
  }
})

function typeLabel(sleutel) {
  return componenttypeOpties.value.find((o) => o.optie_sleutel === sleutel)?.label || sleutel
}

function isAfgeleideSet(vraag) {
  return (vraag.opties || []).some((o) => o.afgeleid_bron)
}
function heeftOpties(vraag) {
  return vraag.antwoordtype === 'enkelvoudige_keuze' || vraag.antwoordtype === 'meerkeuze'
}

// LI050 (W4): bevestigingen benoemen de vraag op zijn TEKST (afgekort), niet op een code.
function kort(tekst, max = 60) {
  const t = String(tekst || '')
  return t.length > max ? `${t.slice(0, max)}…` : t
}

function _toonFout(e) {
  let detail
  if (e?.status === 409 || e?.code === 'CONFIGURATIE_CONFLICT' || e?.code === 'CHECKLISTVRAAG_BESTAAT')
    detail = e?.message || 'Niet toegestaan.'
  else if (e?.status === 422)
    detail = Array.isArray(e?.detail) ? e.detail[0]?.msg || 'Ongeldige invoer.' : 'Ongeldige invoer.'
  else if (e?.status === 404) detail = 'Item niet gevonden.'
  else detail = e?.message || 'Er ging iets mis.'
  actieFout.value = detail
  toast.add({ severity: e?.status === 409 ? 'warn' : 'error', summary: 'Configuratie', detail, life: 6000 })
}

function _vervangVraag(updated) {
  const i = vragen.value.findIndex((v) => v.id === updated.id)
  if (i >= 0) vragen.value[i] = updated
}
function _vervangOptie(vraag, optie) {
  const i = vraag.opties.findIndex((o) => o.id === optie.id)
  if (i >= 0) vraag.opties[i] = optie
  // De server-respons ís de opgeslagen staat — de dirty-referentie beweegt mee.
  optieLabelOpgeslagen[optie.id] = optie.label
}

// Correctie snede 1 (besluit Bert, meting-opslaanknop) — zelfde vorm als de vraagtekst:
// de optie-Opslaan is uit zolang het label gelijk is aan de laatst opgeslagen staat, en
// uit tijdens de vlucht (een tweede klik levert nooit een tweede verzoek). Het label wordt
// via v-model direct op de rij bewerkt; de laatst opgeslagen waarde leeft daarom in een
// eigen referentie, gevuld bij laden en bij elke server-respons.
const optieLabelOpgeslagen = reactive({}) // optie.id -> laatst opgeslagen label
const optieBezig = reactive({}) // optie.id -> bool (vluchtslot)

function _registreerOptieLabels(lijst) {
  for (const v of lijst) for (const o of v.opties || []) optieLabelOpgeslagen[o.id] = o.label
}

function optieGewijzigd(optie) {
  return (optie.label ?? '') !== (optieLabelOpgeslagen[optie.id] ?? '')
}

// "Raakt N componenten"-aankondiging vóór een tellende actie. Faalt de telling,
// dan blokkeren we de actie niet (best-effort melding).
async function _bevestigImpact(componenttype, aanhef) {
  try {
    const { aantal_componenten } = await api.checklistconfig.impact(componenttype)
    return window.confirm(`${aanhef}\n\nDit raakt ${aantal_componenten} componenten van type ${typeLabel(componenttype)}.`)
  } catch {
    return window.confirm(`${aanhef}\n\nDoorgaan?`)
  }
}

async function laad() {
  laden.value = true
  fout.value = null
  try {
    const [lijst, opties, betekenissen, cats] = await Promise.all([
      api.checklistconfig.lijst(),
      api.componenten.opties(),
      api.checklistconfig.betekenissen(),
      api.checklistconfig.categorieen(),
    ])
    vragen.value = lijst
    _registreerOptieLabels(lijst) // dirty-referentie: wat er nu staat ís opgeslagen
    componenttypeOpties.value = opties?.componenttype || []
    betekenisOpties.value = betekenissen || []
    categorieen.value = cats || []
    // Verse binnenkomst: het eerste type mét categorieën (catalogus-volgorde), zodat het
    // scherm nooit leeg opent; de watch opent daarna de eerste categorie.
    if (!typeKeuze.value) {
      const met = componenttypeOpties.value.find((o) =>
        categorieen.value.some((c) => c.componenttype === o.optie_sleutel),
      )
      typeKeuze.value = met?.optie_sleutel || componenttypeOpties.value[0]?.optie_sleutel || ''
    }
  } catch (e) {
    fout.value = e?.status === 401 ? null : e?.message || 'Laden van de configuratie mislukt.'
  } finally {
    laden.value = false
  }
}

async function _herlaadCategorieen() {
  try {
    categorieen.value = (await api.checklistconfig.categorieen()) || []
  } catch {
    /* best-effort — de volgende laad() herstelt */
  }
}

// ── Vragen (rechts, bij de geopende categorie) ─────────────────────────────────

async function maakVraag() {
  if (!nieuweVraag.vraag || !typeKeuze.value || !geselecteerdeCategorieId.value) return
  actieFout.value = null
  const akkoord = await _bevestigImpact(typeKeuze.value, 'Vraag toevoegen.')
  if (!akkoord) return
  try {
    const vraag = await api.checklistconfig.maakVraag({
      componenttype: typeKeuze.value,
      vraag: nieuweVraag.vraag,
      categorie_id: geselecteerdeCategorieId.value,
    })
    vragen.value.push(vraag)
    nieuweVraag.vraag = ''
    toast.add({ severity: 'success', summary: 'Toegevoegd', detail: 'Vraag toegevoegd.', life: 3000 })
    await _herlaadCategorieen() // de vraag-telling per categorie beweegt mee
  } catch (e) {
    _toonFout(e)
  }
}

async function zetActief(vraag) {
  actieFout.value = null
  const aanhef = vraag.actief
    ? `Vraag "${kort(vraag.vraag)}" deactiveren.`
    : `Vraag "${kort(vraag.vraag)}" activeren.`
  const akkoord = await _bevestigImpact(vraag.componenttype, aanhef)
  if (!akkoord) return
  try {
    const updated = await api.checklistconfig.zetActief(vraag.id, !vraag.actief)
    _vervangVraag(updated)
  } catch (e) {
    _toonFout(e)
  }
}

async function zetType(vraag, nieuwType) {
  if (nieuwType === vraag.antwoordtype) return
  actieFout.value = null
  try {
    const updated = await api.checklistconfig.zetAntwoordtype(vraag.id, nieuwType)
    _vervangVraag(updated)
  } catch (e) {
    _toonFout(e)
    _vervangVraag({ ...vraag }) // forceer re-render → dropdown terug naar huidige type
  }
}

async function zetBetekenis(vraag, waarde) {
  const nieuw = waarde || null
  if (nieuw === (vraag.betekenis || null)) return
  actieFout.value = null
  try {
    const updated = await api.checklistconfig.zetBetekenis(vraag.id, nieuw)
    _vervangVraag(updated)
  } catch (e) {
    _toonFout(e)
    _vervangVraag({ ...vraag }) // forceer re-render → dropdown terug naar huidige waarde
  }
}

async function voegToe(vraag) {
  const buf = nieuweOptie[vraag.id]
  if (!buf?.optie_sleutel || !buf?.label) return
  actieFout.value = null
  try {
    // LI050-ergonomie: geen getalveld — een nieuwe optie komt achteraan; daarna slepen.
    const optie = await api.checklistconfig.voegOptieToe(vraag.id, {
      optie_sleutel: buf.optie_sleutel,
      label: buf.label,
      volgorde: Math.max(0, ...vraag.opties.map((o) => o.volgorde || 0)) + 1,
    })
    vraag.opties.push(optie)
    optieLabelOpgeslagen[optie.id] = optie.label // vers aangemaakt = opgeslagen staat
    nieuweOptie[vraag.id] = { optie_sleutel: '', label: '' }
  } catch (e) {
    _toonFout(e)
  }
}

async function bewaarOptie(vraag, optie) {
  // Vluchtslot + niets-te-doen-slot (de knop is dan óók uitgeschakeld; deze guard is
  // de vangrail voor elk pad dat de knop omzeilt).
  if (optieBezig[optie.id] || !optieGewijzigd(optie)) return
  actieFout.value = null
  optieBezig[optie.id] = true
  try {
    // Alleen het label — de volgorde is van de sleep-bouwsteen (LI050-ergonomie).
    const updated = await api.checklistconfig.wijzigOptie(optie.id, { label: optie.label })
    _vervangOptie(vraag, updated)
    toast.add({ severity: 'success', summary: 'Opgeslagen', detail: `Optie ${updated.optie_sleutel}.`, life: 3000 })
  } catch (e) {
    _toonFout(e)
  } finally {
    optieBezig[optie.id] = false
  }
}

async function deactiveer(vraag, optie) {
  actieFout.value = null
  try {
    const updated = await api.checklistconfig.deactiveerOptie(optie.id)
    _vervangOptie(vraag, updated)
  } catch (e) {
    _toonFout(e)
  }
}

function buffer(id) {
  if (!nieuweOptie[id]) nieuweOptie[id] = { optie_sleutel: '', label: '' }
  return nieuweOptie[id]
}

// ── Categorieën (links: toevoegen + volgorde; bij de geopende: hernoemen + verwijderen) ──

async function maakCategorie() {
  if (!nieuweCategorie.naam || !typeKeuze.value) return
  actieFout.value = null
  try {
    // LI050 (W5): geen volgorde-invoer — de categorie komt achteraan; daarna slepen.
    const cat = await api.checklistconfig.maakCategorie({
      componenttype: typeKeuze.value,
      naam: nieuweCategorie.naam,
    })
    nieuweCategorie.naam = ''
    toast.add({ severity: 'success', summary: 'Toegevoegd', detail: 'Categorie toegevoegd.', life: 3000 })
    await _herlaadCategorieen()
    geselecteerdeCategorieId.value = cat.id
  } catch (e) {
    _toonFout(e)
  }
}

// ── LI050 (W5): slepen — de ENIGE bediening voor volgorde (besluit Bert; geen
// getalveld, geen pijltjes). Beide lijsten hangen aan dezelfde gedeelde bouwsteen.

async function _herschikCategorieen(ids) {
  actieFout.value = null
  try {
    // Alleen de rijen wier plek wijzigt worden bewaard (1..n op de nieuwe posities).
    const huidige = new Map(typeCategorieen.value.map((c) => [c.id, c.volgorde]))
    for (const [i, id] of ids.entries()) {
      if (huidige.get(id) !== i + 1) await api.checklistconfig.wijzigCategorie(id, { volgorde: i + 1 })
    }
    await _herlaadCategorieen()
  } catch (e) {
    _toonFout(e)
  }
}

async function _herschikVragen(ids) {
  actieFout.value = null
  try {
    const huidige = new Map(zichtbareVragen.value.map((v) => [v.id, v.volgorde]))
    for (const [i, id] of ids.entries()) {
      if (huidige.get(id) !== i + 1) {
        const updated = await api.checklistconfig.werkVraagBij(id, { volgorde: i + 1 })
        _vervangVraag(updated)
      }
    }
  } catch (e) {
    _toonFout(e)
  }
}

const catSleep = useSleepLijst({
  haalIds: () => typeCategorieen.value.map((c) => c.id),
  herschik: _herschikCategorieen,
  naSucces: () => toast.add({ severity: 'success', summary: 'Volgorde', detail: 'Volgorde bewaard.', life: 3000 }),
})

const vraagSleep = useSleepLijst({
  haalIds: () => zichtbareVragen.value.map((v) => v.id),
  herschik: _herschikVragen,
  naSucces: () => toast.add({ severity: 'success', summary: 'Volgorde', detail: 'Volgorde bewaard.', life: 3000 }),
})

// LI050-ergonomie: de antwoordopties zijn de DERDE consument van de bouwsteen —
// elke opties-lijst (per vraag) een eigen instantie, zonder de bouwsteen te verbuigen.
// Afgeleide sets slepen niet (structuur vast); dat gate de template, zoals rol-gating.
async function _herschikOpties(vraagId, ids) {
  actieFout.value = null
  const vraag = vragen.value.find((v) => v.id === vraagId)
  if (!vraag) return
  try {
    const huidige = new Map(vraag.opties.map((o) => [o.id, o.volgorde]))
    for (const [i, id] of ids.entries()) {
      if (huidige.get(id) !== i + 1) {
        const updated = await api.checklistconfig.wijzigOptie(id, { volgorde: i + 1 })
        _vervangOptie(vraag, updated)
      }
    }
    vraag.opties.sort((a, b) => (a.volgorde ?? 0) - (b.volgorde ?? 0))
  } catch (e) {
    _toonFout(e)
  }
}

const _optieSleepPerVraag = new Map()
function optieSleep(vraag) {
  if (!_optieSleepPerVraag.has(vraag.id)) {
    _optieSleepPerVraag.set(vraag.id, useSleepLijst({
      haalIds: () => (vragen.value.find((v) => v.id === vraag.id)?.opties || []).map((o) => o.id),
      herschik: (ids) => _herschikOpties(vraag.id, ids),
      naSucces: () => toast.add({ severity: 'success', summary: 'Volgorde', detail: 'Volgorde bewaard.', life: 3000 }),
    }))
  }
  return _optieSleepPerVraag.get(vraag.id)
}

// Hernoemen is een HANDELING (LI050): de knop opent het veld, opslaan of annuleren
// sluit het weer — geen permanent invoerveld dat als bewerkstand leest.
const hernoemNaam = ref('')
const hernoemActief = ref(false)
watch(geopendeCategorie, (cat) => {
  hernoemNaam.value = cat?.naam ?? ''
  hernoemActief.value = false // categorie-wissel sluit een openstaande hernoem-handeling
})

function startHernoem() {
  hernoemNaam.value = geopendeCategorie.value?.naam ?? ''
  hernoemActief.value = true
}

async function hernoemCategorie() {
  const cat = geopendeCategorie.value
  if (!cat || !hernoemNaam.value || hernoemNaam.value === cat.naam) return
  actieFout.value = null
  try {
    await api.checklistconfig.wijzigCategorie(cat.id, { naam: hernoemNaam.value })
    toast.add({ severity: 'success', summary: 'Opgeslagen', detail: `Categorie ${hernoemNaam.value}.`, life: 3000 })
    hernoemActief.value = false
    // Hernoemen raakt de categorie-naam op élke vraag-read → beide herladen.
    await laad()
  } catch (e) {
    _toonFout(e)
  }
}

async function verwijderCategorie() {
  const cat = geopendeCategorie.value
  if (!cat) return
  actieFout.value = null
  if (!window.confirm(`Categorie "${cat.naam}" verwijderen?`)) return
  try {
    await api.checklistconfig.verwijderCategorie(cat.id)
    toast.add({ severity: 'success', summary: 'Verwijderd', detail: `Categorie ${cat.naam}.`, life: 3000 })
    geselecteerdeCategorieId.value = null
    await _herlaadCategorieen()
  } catch (e) {
    // 409 CATEGORIE_HEEFT_VRAGEN → de weigering mét telling verschijnt als warn-melding.
    _toonFout(e)
  }
}

laad()
</script>

<template>
  <section aria-labelledby="beheer-titel">
    <!-- LI050: de typekeuze bepaalt WELKE vragenlijst je inricht en hoort dus in de kop
         (zelfde plek als filters elders). Het losse categoriefilter is vervallen — de
         linkerkolom ís het filter. -->
    <LijstKop titel="Checklistvragen" titel-id="beheer-titel">
      <template #filter>
        <label class="flex items-center gap-[var(--lk-space-sm)] text-[length:var(--lk-text-sm)]">
          Componenttype
          <select v-model="typeKeuze" data-testid="cfg-type-keuze" class="lk-veld">
            <option v-for="o in componenttypeOpties" :key="o.optie_sleutel" :value="o.optie_sleutel">
              {{ o.label }}
            </option>
          </select>
        </label>
      </template>
    </LijstKop>

    <!-- W2 — wie niet mag bewerken ziet geen knoppen, wél waarom (NormBeheer-patroon). -->
    <p
      v-if="!magBeheren"
      data-testid="cfg-alleen-lezen-hint"
      class="mb-[var(--lk-space-md)] max-w-prose text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]"
    >
      De vragenlijst wordt bepaald door de beheerder van uw organisatie.
    </p>

    <p v-if="fout" role="alert" data-testid="cfg-fout" class="text-[var(--lk-color-danger)] mb-[var(--lk-space-sm)]">{{ fout }}</p>
    <p v-if="actieFout" role="alert" data-testid="cfg-actie-fout" class="text-[var(--lk-color-danger)] mb-[var(--lk-space-sm)]">{{ actieFout }}</p>
    <p v-if="laden" data-testid="cfg-laden" class="text-[var(--lk-color-text-muted)]">Laden…</p>

    <div class="flex gap-[var(--lk-space-md)] items-start">
      <!-- ── Linkerkolom: de categorieën van het gekozen type ─────────────────── -->
      <!-- LI048-regel: de BUITENrand van een werkvlak is de sterkste lijn op het scherm;
           alles daarbinnen is lichter. Beide buitenvlakken dragen daarom de sterke rand. -->
      <aside
        data-testid="cfg-categorie-kolom"
        aria-label="Categorieën"
        class="card border border-[var(--lk-color-border-sterk)] w-72 shrink-0 flex flex-col gap-[var(--lk-space-xs)]"
      >
        <!-- Kopstijl uit de basislaag (css-build-scan): geen eigen maat/gewicht per scherm. -->
        <h2>Categorieën</h2>
        <ul class="flex flex-col gap-[2px]">
          <!-- LI050 (W5): volgorde verzet je door te SLEPEN — de enige bediening
               (besluit Bert; het getalveld is bewust vervallen). Gedeelde bouwsteen. -->
          <li
            v-for="cat in typeCategorieen"
            :key="cat.id"
            :draggable="magBeheren ? 'true' : undefined"
            :data-testid="`cfg-cat-rij-${cat.id}`"
            :class="['flex items-center gap-[var(--lk-space-xs)]', catSleep.sleepId.value === cat.id ? 'opacity-50' : '', magBeheren ? 'cursor-grab' : '']"
            @dragstart="magBeheren && catSleep.pak(cat.id)"
            @dragover.prevent
            @drop.prevent="magBeheren && catSleep.laatLos(cat.id)"
          >
            <!-- ADR-056/LI051 — de greep maakt het slepen zichtbaar in rust; alleen voor
                 wie mag slepen (zelfde conditie als `draggable`), en op de geselecteerde
                 rij kleurt hij mee zodat de selectie één geheel blijft. -->
            <SleepGreep v-if="magBeheren" :mee="cat.id === geselecteerdeCategorieId" />
            <!-- Selectie = een EIGEN kanaal (LI050): gevulde accent-achtergrond + 4px
                 linkermarkering in primary — geen omtrek-rand (de randen dragen op dit
                 scherm al betekenis: zwaar = werkvlak, licht = kader). Aanwijzen gebruikt
                 het bestaande neutrale hover-grijs van tabelrijen (main.css) — duidelijk
                 lichter dan de selectie; de oude hover was hetzelfde blauw als de selectie
                 en dáárdoor lazen meerdere rijen als geselecteerd. -->
            <button
              type="button"
              :data-testid="`cfg-cat-${cat.id}`"
              :aria-current="cat.id === geselecteerdeCategorieId ? 'true' : undefined"
              :class="[
                'flex-1 text-left rounded-[var(--lk-radius-input)] px-[var(--lk-space-sm)] py-[var(--lk-space-xs)] border-l-4',
                cat.id === geselecteerdeCategorieId
                  ? 'border-[var(--lk-color-primary)] bg-[var(--lk-color-accent)] font-semibold'
                  : 'border-transparent hover:bg-[var(--lk-color-bg-hover,#f3f4f6)]',
              ]"
              @click="geselecteerdeCategorieId = cat.id"
            >
              {{ cat.naam }}
              <span class="block text-[length:var(--lk-text-xs)] text-[var(--lk-color-text-muted)]">
                {{ cat.aantal_vragen }} {{ cat.aantal_vragen === 1 ? 'vraag' : 'vragen' }}<template v-if="aantalUit(cat.id)"> · {{ aantalUit(cat.id) }} uitgezet</template>
              </span>
            </button>
          </li>
        </ul>

        <!-- Toevoegen hoort bij de lijst (beheerder). -->
        <form
          v-if="magBeheren"
          data-testid="cfg-nieuwe-categorie"
          class="flex flex-col gap-[var(--lk-space-xs)] border-t border-[var(--lk-color-border)] pt-[var(--lk-space-sm)] mt-[var(--lk-space-xs)]"
          @submit.prevent="maakCategorie"
        >
          <label class="flex flex-col gap-[2px] text-[length:var(--lk-text-xs)]">
            Nieuwe categorie
            <input
              v-model="nieuweCategorie.naam"
              data-testid="cfg-nieuwe-categorie-naam"
              type="text"
              placeholder="naam"
              class="lk-veld"
            />
          </label>
          <div class="flex items-end gap-[var(--lk-space-xs)]">
            <!-- LI050 (W5): geen volgorde-invoer — de categorie komt achteraan; daarna slepen. -->
            <button
              type="submit"
              data-testid="cfg-nieuwe-categorie-knop"
              class="rounded-[var(--lk-radius-input)] bg-[var(--lk-color-primary)] text-white px-[var(--lk-space-md)] py-[var(--lk-space-xs)] hover:bg-[#2D6DB5]"
            >
              Toevoegen
            </button>
          </div>
        </form>
      </aside>

      <!-- ── Rechterkolom: de geopende categorie + haar vragen ────────────────── -->
      <div class="flex-1 min-w-0 flex flex-col gap-[var(--lk-space-md)]">
        <div v-if="geopendeCategorie" class="card border border-[var(--lk-color-border-sterk)] flex flex-col gap-[var(--lk-space-sm)]">
          <!-- De koppeling met links is expliciet (LI050): de naam staat hier als KOP —
               "je kijkt naar de vragen van déze categorie" — niet in een permanent
               invoerveld (dat las als bewerkveld). Hernoemen is een HANDELING. -->
          <div class="flex flex-wrap items-start gap-[var(--lk-space-sm)]">
            <div class="min-w-0 flex-1">
              <p class="text-[length:var(--lk-text-xs)] text-[var(--lk-color-text-muted)]">Vragen van categorie</p>
              <h2 data-testid="cfg-cat-open-titel" class="mb-0">{{ geopendeCategorie.naam }}</h2>
              <p data-testid="cfg-cat-open-aantal" class="text-[length:var(--lk-text-xs)] text-[var(--lk-color-text-muted)]">
                {{ geopendeCategorie.aantal_vragen }} {{ geopendeCategorie.aantal_vragen === 1 ? 'vraag' : 'vragen' }}<template v-if="aantalUit(geopendeCategorie.id)"> · {{ aantalUit(geopendeCategorie.id) }} uitgezet</template>
              </p>
            </div>
            <template v-if="magBeheren">
              <button
                type="button"
                data-testid="cfg-cat-hernoem"
                class="rounded-[var(--lk-radius-input)] border border-[var(--lk-color-border)] px-[var(--lk-space-sm)] py-[var(--lk-space-xs)] bg-white"
                @click="startHernoem"
              >
                Hernoemen
              </button>
              <!-- Destructief in een EIGEN, gescheiden zone (DetailKop #destructief-patroon:
                   rand + afstand) — nooit naast waar de beheerder werkt. -->
              <div
                data-testid="cfg-cat-destructief"
                class="ml-auto border-l border-[var(--lk-color-border)] pl-[var(--lk-space-md)]"
              >
                <button
                  type="button"
                  data-testid="cfg-cat-verwijderen"
                  class="rounded-[var(--lk-radius-input)] bg-[var(--lk-color-danger)] text-white px-[var(--lk-space-sm)] py-[var(--lk-space-xs)]"
                  @click="verwijderCategorie"
                >
                  Verwijderen
                </button>
              </div>
            </template>
          </div>

          <!-- De hernoem-handeling: pas ná de knop verschijnt het veld; annuleren sluit. -->
          <form
            v-if="magBeheren && hernoemActief"
            data-testid="cfg-cat-hernoem-form"
            class="flex flex-wrap items-end gap-[var(--lk-space-sm)]"
            @submit.prevent="hernoemCategorie"
          >
            <label class="flex flex-col gap-[2px] text-[length:var(--lk-text-xs)]">
              Nieuwe naam
              <input
                v-model="hernoemNaam"
                data-testid="cfg-cat-open-naam"
                type="text"
                class="lk-veld min-w-[14rem]"
                :aria-label="`Nieuwe naam voor categorie ${geopendeCategorie.naam}`"
              />
            </label>
            <button
              type="submit"
              data-testid="cfg-cat-opslaan"
              class="rounded-[var(--lk-radius-input)] bg-[var(--lk-color-primary)] text-white px-[var(--lk-space-md)] py-[var(--lk-space-xs)] hover:bg-[#2D6DB5]"
            >
              Opslaan
            </button>
            <button
              type="button"
              data-testid="cfg-cat-annuleren"
              class="rounded-[var(--lk-radius-input)] border border-[var(--lk-color-border)] px-[var(--lk-space-sm)] py-[var(--lk-space-xs)] bg-white"
              @click="hernoemActief = false"
            >
              Annuleren
            </button>
          </form>

          <!-- Lege categorie: geen leegte maar een regel mét de route (likara-ux §4). -->
          <p
            v-if="!zichtbareVragen.length"
            data-testid="cfg-leeg"
            class="text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]"
          >
            Er staan nog geen vragen in deze categorie.
            <template v-if="magBeheren"> Voeg hieronder de eerste vraag toe.</template>
            <template v-else> De beheerder van uw organisatie kan er een toevoegen.</template>
          </p>

          <!-- ADR-056/LI051 — waaróm de volgorde ertoe doet, boven de lijst: dit is wat
               de consultant te zien krijgt; de greep zegt hóé je haar wijzigt. -->
          <p
            v-if="magBeheren && zichtbareVragen.length"
            data-testid="cfg-volgorde-uitleg"
            class="text-[length:var(--lk-text-xs)] text-[var(--lk-color-text-muted)]"
          >
            Dit is de volgorde waarin de consultant de vragen te zien krijgt — pak een rij
            bij de greep en versleep haar om de volgorde te wijzigen.
          </p>

          <ul class="flex flex-col gap-[var(--lk-space-sm)]">
            <!-- LI050-ergonomie: élke vraag is een OMRAND blok — het bestaande
                 lk-inhoudskader-patroon (het kader BINNEN een werkvlak: échte 1px-rand,
                 lichter dan de sterke buitenrand van de categoriekaart — LI048-regel).
                 `card` droeg hier geen rand (alleen 5%-schaduw, wit-op-wit) én een eigen
                 marge bovenop de lijst-gap; de tussenruimte komt nu alleen uit de gap.
                 Compact: verticale padding sm — één regel tekst vraagt geen 24px lucht. -->
            <li
              v-for="vraag in zichtbareVragen"
              :key="vraag.id"
              :data-testid="`cfg-vraag-${vraag.code}`"
              :draggable="magBeheren && openVraagId !== vraag.id ? 'true' : undefined"
              :class="['lk-inhoudskader py-[var(--lk-space-sm)] flex flex-col gap-[var(--lk-space-sm)]', vraag.actief ? '' : 'opacity-60', vraagSleep.sleepId.value === vraag.id ? 'opacity-50' : '', magBeheren && openVraagId !== vraag.id ? 'cursor-grab' : '']"
              @dragstart="magBeheren && openVraagId !== vraag.id && vraagSleep.pak(vraag.id)"
              @dragover.prevent
              @drop.prevent="magBeheren && vraagSleep.laatLos(vraag.id)"
            >
              <!-- De vraagtekst is de KOP van het blok; de staat en het uitklapteken staan
                   er direct naast — niet tegen de verre rechterrand. -->
              <div class="flex items-start gap-[var(--lk-space-sm)]">
                <!-- ADR-056/LI051 — de greep, alleen op een sleepbare rij (dicht + beheerder). -->
                <SleepGreep v-if="magBeheren && openVraagId !== vraag.id" />
                <!-- LI050 (W4): geen vraagcode meer op het scherm — de tekst ís de vraag. -->
                <h3 class="min-w-0 text-[length:var(--lk-text-lg)] font-semibold">{{ vraag.vraag }}</h3>
                <span
                  :data-testid="`cfg-vraag-status-${vraag.code}`"
                  :class="['shrink-0 text-[length:var(--lk-text-xs)]', vraag.actief ? 'text-[var(--lk-color-success)]' : 'text-[var(--lk-color-danger)]']"
                >{{ vraag.actief ? 'actief' : 'uitgezet' }}</span>
                <button
                  type="button"
                  :data-testid="`cfg-vraag-toggle-${vraag.code}`"
                  :aria-expanded="openVraagId === vraag.id"
                  :aria-controls="`cfg-vraag-detail-${vraag.code}`"
                  :aria-label="`Details van vraag ${kort(vraag.vraag, 40)}`"
                  class="shrink-0 rounded-[var(--lk-radius-input)] border border-[var(--lk-color-border)] px-[var(--lk-space-sm)] py-[var(--lk-space-xs)] bg-white"
                  @click="toggleVraag(vraag)"
                >
                  {{ openVraagId === vraag.id ? '▾' : '▸' }}
                </button>
              </div>

              <!-- Open: wat bij de vraag hoort — antwoordtype, betekenis, opties.
                   De veldenrij BREEKT AF (flex-wrap): niets valt buiten beeld. -->
              <div
                v-if="openVraagId === vraag.id"
                :id="`cfg-vraag-detail-${vraag.code}`"
                :data-testid="`cfg-vraag-detail-${vraag.code}`"
                class="flex flex-col gap-[var(--lk-space-sm)]"
              >
                <!-- ADR-056 besluit 1/13 — de vraagtekst is bewerkbaar in het scherm; het
                     opslaan loopt via het éne venster dat de wijziging benoemt en de
                     keuze verduidelijking/wijziging stelt. -->
                <form
                  v-if="magBeheren"
                  :data-testid="`cfg-vraagtekst-form-${vraag.code}`"
                  class="flex flex-wrap items-end gap-[var(--lk-space-sm)]"
                  @submit.prevent="openOpslaanVenster(vraag)"
                >
                  <label class="flex flex-col gap-[2px] text-[length:var(--lk-text-xs)] flex-1 min-w-[16rem]">
                    Vraagtekst
                    <input
                      v-model="vraagBewerk[vraag.id]"
                      :data-testid="`cfg-vraagtekst-${vraag.code}`"
                      type="text"
                      class="lk-veld"
                    />
                  </label>
                  <button
                    type="submit"
                    :data-testid="`cfg-vraagtekst-opslaan-${vraag.code}`"
                    :disabled="!tekstGewijzigd(vraag)"
                    class="rounded-[var(--lk-radius-input)] bg-[var(--lk-color-primary)] text-white px-[var(--lk-space-md)] py-[var(--lk-space-xs)] hover:bg-[#2D6DB5] disabled:opacity-50"
                  >
                    Vraagtekst opslaan
                  </button>
                </form>
                <div class="flex flex-wrap items-center gap-[var(--lk-space-md)]">
                  <button
                    v-if="magBeheren"
                    type="button"
                    :data-testid="`cfg-vraag-actief-${vraag.code}`"
                    class="rounded-[var(--lk-radius-input)] border border-[var(--lk-color-border)] px-[var(--lk-space-sm)] py-[var(--lk-space-xs)] bg-white"
                    @click="zetActief(vraag)"
                  >
                    {{ vraag.actief ? 'Deactiveren' : 'Activeren' }}
                  </button>
                  <span class="inline-flex items-center gap-[var(--lk-space-xs)]">
                    <label class="flex items-center gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]">
                      Antwoordtype
                      <select
                        v-if="magBeheren"
                        :data-testid="`cfg-type-${vraag.code}`"
                        :value="vraag.antwoordtype"
                        class="lk-veld"
                        @change="zetType(vraag, $event.target.value)"
                      >
                        <option v-for="t in ANTWOORDTYPES" :key="t" :value="t">{{ TYPE_LABEL[t] }}</option>
                      </select>
                      <span v-else :data-testid="`cfg-type-tekst-${vraag.code}`">{{ TYPE_LABEL[vraag.antwoordtype] }}</span>
                    </label>
                    <VeldUitleg veld="antwoordtype" opties="antwoordtype" :testid="`uitleg-antwoordtype-${vraag.code}`" />
                  </span>
                  <span class="inline-flex items-center gap-[var(--lk-space-xs)]">
                    <label class="flex items-center gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]">
                      Betekenis
                      <select
                        v-if="magBeheren"
                        :data-testid="`cfg-betekenis-${vraag.code}`"
                        :value="vraag.betekenis || ''"
                        class="lk-veld"
                        @change="zetBetekenis(vraag, $event.target.value)"
                      >
                        <option value="">— geen —</option>
                        <option v-for="b in betekenisOpties" :key="b.optie_sleutel" :value="b.optie_sleutel">{{ b.label }}</option>
                      </select>
                      <span v-else :data-testid="`cfg-betekenis-tekst-${vraag.code}`">{{ betekenisOpties.find((b) => b.optie_sleutel === vraag.betekenis)?.label || '— geen —' }}</span>
                    </label>
                    <VeldUitleg veld="betekenis" :testid="`uitleg-betekenis-${vraag.code}`" />
                  </span>
                </div>
                <p v-if="magBeheren && vraag.antwoordtype !== 'geen'" class="text-[length:var(--lk-text-xs)] text-[var(--lk-color-text-muted)]">
                  Een reeds geconfigureerde vraag kan niet van antwoordtype wisselen (de server weigert dat).
                </p>

                <!-- Opties-editor (alleen keuze-types) -->
                <div v-if="heeftOpties(vraag)" class="flex flex-col gap-[var(--lk-space-xs)]">
                <div
                  v-if="isAfgeleideSet(vraag)"
                  :data-testid="`cfg-afgeleid-${vraag.code}`"
                  class="text-[length:var(--lk-text-xs)] text-[var(--lk-color-text-muted)]"
                >
                  Afgeleide optieset — structuur is vast; alleen labels zijn aanpasbaar.
                </div>

                <!-- LI050: de opties in dezelfde LIJSTVORM als de categorieën en de vragen —
                     geen tabelrijen: een <tr> draagt het browser-slepen niet betrouwbaar
                     (bewezen met het audit-spoor; de bronscan verbiedt drag op tabel-
                     elementen). Geen Volgorde-getalkolom: slepen is de enige bediening. -->
                <ul
                  class="flex flex-col gap-[var(--lk-space-xs)]"
                  :aria-label="`Antwoordopties van vraag ${kort(vraag.vraag, 40)}`"
                >
                  <li
                    v-for="optie in vraag.opties"
                    :key="optie.id"
                    :data-testid="`cfg-optie-${vraag.code}-${optie.optie_sleutel}`"
                    :draggable="magBeheren && !isAfgeleideSet(vraag) ? 'true' : undefined"
                    :class="['flex flex-wrap items-center gap-[var(--lk-space-sm)]', optie.actief ? '' : 'opacity-50', optieSleep(vraag).sleepId.value === optie.id ? 'opacity-50' : '', magBeheren && !isAfgeleideSet(vraag) ? 'cursor-grab' : '']"
                    @dragstart.stop="magBeheren && !isAfgeleideSet(vraag) && optieSleep(vraag).pak(optie.id)"
                    @dragover.prevent
                    @drop.prevent.stop="magBeheren && !isAfgeleideSet(vraag) && optieSleep(vraag).laatLos(optie.id)"
                  >
                    <!-- ADR-056/LI051 — greep alleen waar écht gesleept kan worden
                         (niet bij een afgeleide set: structuur vast). -->
                    <SleepGreep v-if="magBeheren && !isAfgeleideSet(vraag)" />
                    <span class="font-mono w-32 shrink-0 text-[length:var(--lk-text-sm)]">{{ optie.optie_sleutel }}</span>
                    <input
                      v-if="magBeheren"
                      :data-testid="`cfg-optie-label-${optie.id}`"
                      v-model="optie.label"
                      type="text"
                      class="lk-veld flex-1 min-w-[10rem]"
                    />
                    <span v-else class="flex-1 min-w-0">{{ optie.label }}</span>
                    <span v-if="optie.afgeleid_bron" :data-testid="`cfg-bron-${optie.id}`" class="shrink-0 text-[length:var(--lk-text-xs)]">afgeleid · {{ optie.afgeleid_bron }}</span>
                    <span v-else-if="!optie.actief" class="shrink-0 text-[length:var(--lk-text-xs)] text-[var(--lk-color-danger)]">gedeactiveerd</span>
                    <span v-else class="shrink-0 text-[length:var(--lk-text-xs)] text-[var(--lk-color-success)]">actief</span>
                    <!-- Correctie snede 1 — zelfde vorm als "Vraagtekst opslaan": uit tijdens
                         de vlucht én uit zolang het label gelijk is aan de opgeslagen staat. -->
                    <button
                      v-if="magBeheren"
                      type="button"
                      :data-testid="`cfg-optie-opslaan-${optie.id}`"
                      :disabled="optieBezig[optie.id] || !optieGewijzigd(optie)"
                      class="shrink-0 rounded-[var(--lk-radius-input)] border border-[var(--lk-color-border)] px-[var(--lk-space-sm)] py-[var(--lk-space-xs)] bg-white disabled:opacity-50 disabled:cursor-not-allowed"
                      @click="bewaarOptie(vraag, optie)"
                    >
                      Opslaan
                    </button>
                    <button
                      v-if="magBeheren && !optie.afgeleid_bron && optie.actief"
                      type="button"
                      :data-testid="`cfg-optie-deactiveren-${optie.id}`"
                      class="shrink-0 rounded-[var(--lk-radius-input)] border border-[var(--lk-color-border)] px-[var(--lk-space-sm)] py-[var(--lk-space-xs)] bg-white"
                      @click="deactiveer(vraag, optie)"
                    >
                      Deactiveren
                    </button>
                  </li>
                </ul>

                <!-- Optie toevoegen (niet bij afgeleide sets; beheerder-only).
                     Geen getalveld: de optie komt achteraan, daarna slepen. -->
                <form
                  v-if="magBeheren && !isAfgeleideSet(vraag)"
                  :data-testid="`cfg-toevoegen-${vraag.code}`"
                  class="flex flex-wrap items-end gap-[var(--lk-space-sm)] mt-[var(--lk-space-xs)]"
                  @submit.prevent="voegToe(vraag)"
                >
                  <input
                    :data-testid="`cfg-nieuw-sleutel-${vraag.code}`"
                    v-model="buffer(vraag.id).optie_sleutel"
                    type="text"
                    placeholder="sleutel"
                    class="lk-veld"
                  />
                  <input
                    :data-testid="`cfg-nieuw-label-${vraag.code}`"
                    v-model="buffer(vraag.id).label"
                    type="text"
                    placeholder="label"
                    class="lk-veld"
                  />
                  <button
                    type="submit"
                    :data-testid="`cfg-toevoegen-knop-${vraag.code}`"
                    class="rounded-[var(--lk-radius-input)] bg-[var(--lk-color-primary)] text-white px-[var(--lk-space-md)] py-[var(--lk-space-xs)] hover:bg-[#2D6DB5]"
                  >
                    Optie toevoegen
                  </button>
                </form>
                </div>
              </div>
            </li>
          </ul>

          <!-- Vraag toevoegen bij de geopende categorie (W4: zonder code — het systeem kent hem toe). -->
          <form
            v-if="magBeheren"
            data-testid="cfg-nieuwe-vraag"
            class="flex flex-wrap items-end gap-[var(--lk-space-sm)]"
            @submit.prevent="maakVraag"
          >
            <label class="flex flex-col gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)] flex-1 min-w-[16rem]">
              Nieuwe vraag in {{ geopendeCategorie.naam }}
              <input
                v-model="nieuweVraag.vraag"
                data-testid="cfg-nieuwe-vraag-tekst"
                type="text"
                class="lk-veld"
              />
            </label>
            <button
              type="submit"
              data-testid="cfg-nieuwe-vraag-knop"
              class="rounded-[var(--lk-radius-input)] bg-[var(--lk-color-primary)] text-white px-[var(--lk-space-md)] py-[var(--lk-space-xs)] hover:bg-[#2D6DB5]"
            >
              Vraag toevoegen
            </button>
          </form>
        </div>

        <p
          v-else-if="!laden"
          data-testid="cfg-geen-categorie"
          class="text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]"
        >
          Dit componenttype heeft nog geen categorieën.
          <template v-if="magBeheren"> Voeg er links een toe.</template>
        </p>
      </div>
    </div>

    <!-- ADR-056 besluit 13/16 — HET opslaan-venster: benoemt wat er wijzigt, voorspelt
         hoeveel antwoorden eronder liggen (besluit 12) en stelt de keuze één keer,
         ZONDER voorselectie. Beide opties benoemen hun gevolg in gewone taal; er wordt
         niets gewist en niets geblokkeerd. -->
    <Dialog
      :visible="!!opslaanVenster"
      modal
      :closable="false"
      :draggable="false"
      header="Wat is deze wijziging?"
      data-testid="cfg-opslaan-venster"
      @update:visible="opslaanVenster = null"
    >
      <div v-if="opslaanVenster" class="flex flex-col gap-[var(--lk-space-sm)] max-w-prose">
        <p data-testid="cfg-venster-opsomming" class="text-[length:var(--lk-text-sm)]">
          De vraagtekst wijzigt van<br />
          <span class="text-[var(--lk-color-text-muted)]">“{{ opslaanVenster.oud }}”</span><br />
          naar<br />
          <span class="font-medium">“{{ opslaanVenster.nieuw }}”</span>
        </p>
        <p data-testid="cfg-venster-aantal" class="text-[length:var(--lk-text-sm)]">
          <template v-if="opslaanVenster.aantal === null">Het aantal geraakte antwoorden wordt geteld…</template>
          <template v-else-if="opslaanVenster.aantal === -1">Het aantal geraakte antwoorden kon niet worden opgehaald.</template>
          <template v-else>Dit raakt {{ antwoordTelling(opslaanVenster.aantal) }}.</template>
        </p>

        <label class="flex items-start gap-[var(--lk-space-xs)]">
          <input
            v-model="opslaanVenster.aard"
            type="radio"
            value="verduidelijking"
            data-testid="cfg-aard-verduidelijking"
            class="mt-1"
          />
          <span class="text-[length:var(--lk-text-sm)]">
            <span class="font-medium">Verduidelijking</span> — de betekenis blijft gelijk.
            Wie al antwoordde hoeft niets te doen; bij het antwoord komt een stille notitie
            dat de formulering is bijgewerkt.
          </span>
        </label>
        <label class="flex items-start gap-[var(--lk-space-xs)]">
          <input
            v-model="opslaanVenster.aard"
            type="radio"
            value="wijziging"
            data-testid="cfg-aard-wijziging"
            class="mt-1"
          />
          <span class="text-[length:var(--lk-text-sm)]">
            <span class="font-medium">Dit verandert de vraag</span> — bestaande antwoorden gaan
            als verouderd lezen en komen terug op de werklijst van wie antwoordde; zij geven
            hun antwoord opnieuw.
          </span>
        </label>

        <p data-testid="cfg-venster-geruststelling" class="text-[length:var(--lk-text-xs)] text-[var(--lk-color-text-muted)]">
          Er wordt niets gewist en niets geblokkeerd: bestaande antwoorden blijven staan en
          tellen mee tot ze opnieuw gegeven zijn.
        </p>
      </div>
      <template #footer>
        <button
          type="button"
          data-testid="cfg-venster-annuleren"
          class="rounded-[var(--lk-radius-input)] border border-[var(--lk-color-border)] px-[var(--lk-space-sm)] py-[var(--lk-space-xs)] bg-white"
          @click="opslaanVenster = null"
        >
          Annuleren
        </button>
        <button
          type="button"
          data-testid="cfg-venster-opslaan"
          :disabled="!opslaanVenster?.aard || vensterBezig"
          class="rounded-[var(--lk-radius-input)] bg-[var(--lk-color-primary)] text-white px-[var(--lk-space-md)] py-[var(--lk-space-xs)] hover:bg-[#2D6DB5] disabled:opacity-50"
          @click="bevestigVraagtekst"
        >
          Opslaan
        </button>
      </template>
    </Dialog>
  </section>
</template>
