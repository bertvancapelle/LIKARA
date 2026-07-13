<script setup>
/**
 * BedrijfsfunctieLijst — de bedrijfsfunctieboom (ADR-043 gate 1a blok 2; ADR-044 blok 2).
 *
 * De logische ruggengraat van de kaart als Boom | Diagram (het processen-scherm-recept;
 * Boom = beheren, Diagram = begrijpen/navigeren). Boom-structuur uit de gedeelde pure
 * module (ADR-044: `meervoudBoomStructuur` — de boom leeft in PLAATSINGEN, één functie
 * kan op meerdere plekken staan); het Diagram is de gegeneraliseerde `ProcesDiagram`-
 * bouwsteen met functie-taal (géén tweede kopie).
 *
 * ADR-044 — meervoudige plekken, in drie bewuste regels:
 * - Een functie VERSCHIJNT op elke plek waar ze hoort (elke plaatsing = een rij); elke
 *   verschijning vertelt "staat ook onder: …" (klikbaar naar de andere plek) — het is
 *   één functie, geen kopie. Geen "origineel"-taal, geen rangorde.
 * - Selectie/aanstip is FUNCTIE-breed (alle verschijningen lichten samen op — de
 *   goedkoopste manier om "één ding" te tonen; het instance-projectie-denken van de
 *   Lagen-weergave). Bewerken/verwijderen werken op de functie, één keer.
 * - De uitklap-staat is PLEK-gebonden (plek-sleutel = het pad van wortel naar rij):
 *   Toezicht openklappen onder de ene ouder laat 'm onder de andere dicht.
 *
 * ADR-043-regels, gespiegeld op de backend (de picker-/affordance-regel: toon nooit een
 * knop die bij opslaan een 422 geeft — de service blijft de handhaver):
 * - MODELINHOUD (functie mét bronsleutel): naam/definitie/plaatsingen read-only — géén
 *   bewerk-/plaatsings-/verwijder-affordance; rustige herkomstvermelding.
 * - EIGEN functie: volledig bewerkbaar; "Plaats ook onder…" (extra plek) en "Haal hier
 *   weg" (déze plek weg; de functie blijft — zonder plekken wordt ze een wortel).
 * - VERVALLEN (besluit LI039-6): zichtbaar mét rustige markering, niet koppelbaar —
 *   geen "+ Deelfunctie" eronder en geen plaatsing eronder.
 */
import { computed, onMounted, reactive, ref } from 'vue'
import { Button, Dialog, useToast } from '@/primevue'
import { toastSucces } from '@/meldingen'
import { useAuthStore } from '@/store/auth'
import { useLijstStaat } from '@/composables/useLijstStaat'
import { useToonInBoom } from '@/composables/useToonNieuweRij'
import { api } from '@/api'
import BevestigVerwijderDialog from '@/components/BevestigVerwijderDialog.vue'
import MeldingBanner from '@/components/MeldingBanner.vue'
import RijActies from '@/components/RijActies.vue'
import { meervoudBoomStructuur } from '../procesBoom'
import ProcesDiagram from './ProcesDiagram.vue'
import ZoekSelect from './ZoekSelect.vue'

const auth = useAuthStore()
const toast = useToast()
const magBewerken = computed(() => auth.hasRole('medewerker', 'beheerder'))
// LI037-regel — verwijderen = het VERWIJDEREN-recht (beheerder-only; het endpoint eist
// BEDRIJFSFUNCTIE.VERWIJDEREN). Vooraf weren i.p.v. een 403 pas in de dialoog.
const magVerwijderen = computed(() => auth.hasRole('beheerder'))

const alle = ref([]) // platte set (alle pagina's); de boom is een client-side afgeleide
const laden = ref(false)
const fout = ref(null)

const zoekterm = ref('')
// ADR-044 — uitklap-staat is PLEK-gebonden: sleutels zijn plek-paden ('wortel>…>functie',
// functie-ids '>'-gescheiden), niet functie-ids. Zo laat Toezicht openklappen onder de
// ene ouder de andere verschijning dicht. (Array → serialiseerbare lijststaat.)
const openTakken = ref([])
const weergave = ref('boom') // 'boom' (register-tree) | 'diagram' (functie-only structuurbeeld)
// "Toon in functiebeeld" (rij-actie): centrum bij openen. Momentkeuze — niet in de lijststaat.
const diagramStart = ref(null)
function toonInFunctiebeeld(f) {
  if (!f?.id) return
  diagramStart.value = f.id
  weergave.value = 'diagram'
}
// LI039 v3 — "Open functie →" uit de diagram-popup: er is (nog) geen detailscherm, dus
// de landing is de Boom-rij van deze functie — via dezelfde toonRij-bouwsteen (pad
// open + aanstip + in beeld scrollen) als bij aanmaken/verplaatsen.
function openUitDiagram(item) {
  if (!item?.id) return
  weergave.value = 'boom'
  toonFunctie(item.id)
}

// Lijststaat behouden bij terugnavigeren/F5 (lk-state-patroon; zie useLijstStaat).
const _tekst = (w) => typeof w === 'string'
const { herstel: herstelLijstStaat } = useLijstStaat(
  'bedrijfsfunctie-lijst',
  { zoekterm, openTakken, weergave },
  {
    valideer: {
      zoekterm: _tekst,
      openTakken: (w) => Array.isArray(w) && w.every(_tekst),
      weergave: (w) => w === 'boom' || w === 'diagram',
    },
  },
)

async function laad() {
  laden.value = true
  fout.value = null
  try {
    // Alle pagina's ophalen (de functieboom is een begrensd vocabulaire; de boom heeft de
    // volledige set nodig om ouder→kind te kunnen leggen — het ProcesLijst-recept).
    const items = []
    let after
    do {
      const pagina = await api.bedrijfsfuncties.lijst({ limit: 100, after })
      items.push(...pagina.items)
      after = pagina.volgende_cursor
    } while (after)
    alle.value = items
    // Herstelde open-plekken waarvan een segment niet (meer) bestaat stil laten vallen.
    const bekend = new Set(items.map((f) => f.id))
    openTakken.value = openTakken.value.filter(
      (plek) => String(plek).split(PLEK_SCHEIDER).every((s) => bekend.has(s)),
    )
  } catch (e) {
    fout.value = e?.status === 401 ? null : 'Laden van de bedrijfsfuncties is mislukt.'
  } finally {
    laden.value = false
  }
}

const isEigen = (f) => !f?.bron_sleutel
// LI039 UI-afronding v2 (punt 3) — herkomst ÉÉN KEER boven de boom, niet per rij
// (informatie die overal hetzelfde is, is geen informatie; toon alleen wat afwijkt).
// Data-gedreven uit de ingelezen-referentiemodel-verrijking op de rijen — niets
// hardcoded. MVP = één model (meervoud-per-rij is een latere, bewuste stap).
const modelHerkomst = computed(() => {
  const m = alle.value.find((f) => f.bron_model_naam)
  if (!m) return null
  const basis = `Uit ${m.bron_model_naam}${m.bron_model_versie ? `, ${m.bron_model_versie}` : ''}.`
  const heeftEigen = alle.value.some((f) => isEigen(f))
  return heeftEigen ? `${basis} Eigen functies zijn gemarkeerd.` : basis
})

// Boom-STRUCTUUR uit de gedeelde pure module (geen derde boom-opbouw; alleen de
// rendering — rijen + verbindingslijnen — is schermspecifiek, zoals bij ProcesLijst).
// ADR-044: de meervoud-variant — élke plaatsing (ouder_ids) is een edge; één functie
// kan onder meerdere ouders staan.
const _byId = computed(() => new Map(alle.value.map((f) => [f.id, f])))
const naamVanId = (id) => _byId.value.get(id)?.naam || String(id)
const boom = computed(() => meervoudBoomStructuur(
  new Set(alle.value.map((f) => f.id)),
  alle.value.flatMap((f) => (f.ouder_ids || []).map((o) => ({ bron: f.id, doel: o }))),
  naamVanId,
))

// ADR-044 — plek-sleutels: het pad van wortel naar rij ('a>b>c', functie-ids). De
// uitklap-staat en de rij-identiteit in de DOM zijn plek-gebonden; selectie/aanstip
// blijven functie-breed.
const PLEK_SCHEIDER = '>'
const plekVan = (ouderPlek, id) => (ouderPlek ? `${ouderPlek}${PLEK_SCHEIDER}${id}` : String(id))
// De "eerste" plek van een functie: keten omhoog langs steeds de eerste (gesorteerde)
// ouder — deterministisch; cyclus-veilig (visited-guard: nooit hangen op vuile data).
function _ketenNaarBoven(id) {
  const keten = [String(id)]
  const bezocht = new Set(keten)
  let cur = (boom.value.oudersVan.get(String(id)) || [])[0]
  while (cur != null && !bezocht.has(String(cur))) {
    keten.unshift(String(cur))
    bezocht.add(String(cur))
    cur = (boom.value.oudersVan.get(String(cur)) || [])[0]
  }
  return keten
}
const _eerstePlek = (id) => _ketenNaarBoven(id).reduce((p, s) => plekVan(p, s), '')
// De open-sleutels vóór een plek: alle echte prefixen (de rij zelf hoeft niet open).
function _prefixPlekken(plek) {
  const segs = String(plek).split(PLEK_SCHEIDER)
  const keys = []
  let p = ''
  for (let i = 0; i < segs.length - 1; i += 1) {
    p = plekVan(p, segs[i])
    keys.push(p)
  }
  return keys
}

const _matcht = (f) => f.naam.toLowerCase().includes(zoekterm.value.trim().toLowerCase())
// Bij een actieve zoekterm: toon de paden naar de treffers, opengeklapt (zoeken klapt
// open — functie-inhoudelijk, dus op ÁLLE verschijningen). ADR-044: de structuur is een
// DAG (gedeelde subbomen) → memo + kring-guard zodat de afleiding nooit hangt.
const matchOfNazaatMatcht = computed(() => {
  const term = zoekterm.value.trim()
  const set = new Set()
  if (!term) return set
  const memo = new Map()
  const heeftMatchIn = (id, pad) => {
    if (memo.has(id)) return memo.get(id)
    if (pad.has(id)) return false // kring-guard (mag niet bestaan; nooit hangen)
    pad.add(id)
    let raak = false
    for (const kindId of boom.value.kinderenVan.get(id) || []) {
      const kind = _byId.value.get(kindId)
      if (heeftMatchIn(kindId, pad) || (kind && _matcht(kind))) raak = true
    }
    pad.delete(id)
    memo.set(id, raak)
    if (raak) set.add(id)
    return raak
  }
  for (const wortelId of boom.value.wortels) {
    const wortel = _byId.value.get(wortelId)
    if (heeftMatchIn(wortelId, new Set()) || (wortel && _matcht(wortel))) set.add(wortelId)
  }
  return set
})

// ADR-044 — open/dicht is PLEK-gebonden (plek-sleutel), zoeken klapt functie-breed open.
function isOpen(plek, functieId) {
  if (zoekterm.value.trim()) return matchOfNazaatMatcht.value.has(functieId)
  return openTakken.value.includes(plek)
}
function toggle(plek) {
  if (openTakken.value.includes(plek)) openTakken.value = openTakken.value.filter((x) => x !== plek)
  else openTakken.value = [...openTakken.value, plek]
}

// Platte, zichtbare rijen + het tree-connector-lijnen-model (het LI037-recept van
// ProcesLijst 1-op-1 — wortels zaaien een lege prefix; `laatste` sluit af met └).
// ADR-044: één functie kan meermaals verschijnen (één rij per plaatsing/pad); elke rij
// draagt haar plek-sleutel + de ANDERE ouders ("staat ook onder"). De pad-guard slaat
// een functie over die al in het huidige pad zit (kring-veilig, nooit hangen).
const rijen = computed(() => {
  const term = zoekterm.value.trim()
  const { wortels, oudersVan, kinderenVan } = boom.value
  const uit = []
  const zichtbare = (ids) => ids
    .map((id) => _byId.value.get(id))
    .filter(Boolean)
    .filter((f) => !term || _matcht(f) || matchOfNazaatMatcht.value.has(f.id))
  const loop = (ids, diepte, lijnen, ouderPlek, ouderId, pad) => {
    const zichtbaar = zichtbare(ids.filter((id) => !pad.has(id)))
    zichtbaar.forEach((f, i) => {
      const plek = plekVan(ouderPlek, f.id)
      const laatste = i === zichtbaar.length - 1
      const kids = (kinderenVan.get(f.id) || []).filter((k) => !pad.has(k))
      const heeftKinderen = kids.length > 0
      const open = heeftKinderen && isOpen(plek, f.id)
      const andereOuders = (oudersVan.get(f.id) || []).filter((o) => o !== ouderId)
      uit.push({ functie: f, plek, ouderId, andereOuders, diepte, heeftKinderen, open, laatste, lijnen })
      if (open) {
        const kindPad = new Set(pad)
        kindPad.add(f.id)
        loop(kids, diepte + 1, diepte === 0 ? [] : [...lijnen, !laatste], plek, f.id, kindPad)
      }
    })
  }
  loop(wortels, 0, [], '', null, new Set())
  return uit
})

const lijnX = (niveau) => `calc(var(--lk-space-md) + ${niveau * 1.5}rem + 0.625rem)`

// Vervallen-set — voedt de vervallen-markering in het Diagram via het EIGEN
// `vervallenIds`-kanaal (LI039 blok C; het `gapIds`-kanaal blijft vrij voor de echte
// gap-cue in gate 3 — beide toestanden kunnen straks tegelijk gelden).
const vervallenIds = computed(() => new Set(alle.value.filter((f) => f.vervallen).map((f) => f.id)))

// LI039 blok B — "wat je zojuist hebt vastgelegd, zie je altijd" (gedeelde bouwsteen;
// aanmaken én plaatsen): pad openklappen + korte aanstip + zoekterm wijkt zichtbaar.
// ADR-044: open-sleutels zijn plek-paden → de bouwsteen krijgt `padVan`; de aanstip
// blijft functie-breed (alle verschijningen lichten op), de scroll mikt op de doel-plek.
const { aangestiptId, wijkMelding, toonRij } = useToonInBoom({
  openTakken,
  zoekterm,
  matcht: (id) => {
    const f = _byId.value.get(String(id))
    return !!f && _matcht(f)
  },
  ouderVan: (id) => (boom.value.oudersVan.get(String(id)) || [])[0] ?? null,
  padVan: (id, doelPlek) => _prefixPlekken(doelPlek ?? _eerstePlek(id)),
  wijkTekst: 'Zoekterm opzij gezet om je nieuwe functie te tonen.',
})
// Altijd met een expliciete doel-plek aanroepen (default: de eerste verschijning),
// zodat de scroll de juiste rij vindt — ook als een ándere verschijning al in beeld is.
function toonFunctie(functieId, doelPlek = null) {
  if (functieId == null) return
  toonRij(String(functieId), doelPlek ?? _eerstePlek(String(functieId)))
}
// "staat ook onder"-doorklik: naar de verschijning van déze functie onder díé ouder.
function gaNaarAnderePlek(rij, ouderId) {
  toonFunctie(rij.functie.id, plekVan(_eerstePlek(ouderId), rij.functie.id))
}

// ── Toevoegen (wortel of deelfunctie) + bewerken (alleen eigen functies) ──────────
const dialogOpen = ref(false)
const dialogFunctie = ref(null) // null = nieuw; anders bewerken (alleen eigen functies)
const dialogOuder = ref(null) // bij nieuw: de functie waaronder ("+ Deelfunctie"); null = wortel
const form = reactive({ naam: '', definitie: '' })
const formFout = ref(null)
const bezig = ref(false)

function openNieuw(ouder = null) {
  dialogFunctie.value = null
  dialogOuder.value = ouder
  Object.assign(form, { naam: '', definitie: '' })
  formFout.value = null
  dialogOpen.value = true
}
function openBewerk(f) {
  dialogFunctie.value = f
  dialogOuder.value = null
  Object.assign(form, { naam: f.naam, definitie: f.definitie || '' })
  formFout.value = null
  dialogOpen.value = true
}
async function bevestig() {
  formFout.value = null
  if (!form.naam.trim()) {
    formFout.value = 'Naam is verplicht.'
    return
  }
  bezig.value = true
  try {
    const data = { naam: form.naam.trim(), definitie: form.definitie.trim() || null }
    let nieuwId = null
    if (dialogFunctie.value) {
      await api.bedrijfsfuncties.werkBij(dialogFunctie.value.id, data)
    } else {
      const res = await api.bedrijfsfuncties.maak({ ...data, ouder_id: dialogOuder.value?.id ?? null })
      nieuwId = res?.id ?? null
    }
    toastSucces(toast, dialogFunctie.value ? 'Opgeslagen' : 'Functie aangemaakt')
    dialogOpen.value = false
    await laad()
    // LI039 blok B — de zojuist aangemaakte rij is ALTIJD zichtbaar: pad open, korte
    // aanstip, en een verbergende zoekterm wijkt zichtbaar (gedeelde bouwsteen).
    if (nieuwId != null) toonFunctie(nieuwId)
  } catch (e) {
    if (e?.status !== 401) formFout.value = e?.message || 'Opslaan is mislukt.'
  } finally {
    bezig.value = false
  }
}

// ── Verwijderen (alleen eigen functies zonder kinderen; backend blijft de vangrail) ──
function subboomIds(functieId) {
  const ids = new Set([functieId])
  let frontier = [functieId]
  while (frontier.length) {
    const volgende = []
    for (const f of frontier) {
      for (const k of boom.value.kinderenVan.get(f) || []) {
        if (!ids.has(k)) { ids.add(k); volgende.push(k) }
      }
    }
    frontier = volgende
  }
  return ids
}

const verwijderFunctie = ref(null)
const verwijderFout = ref(null)
const verwijderBezig = ref(false)
function openVerwijder(f) {
  verwijderFunctie.value = f
  verwijderFout.value = null
}
async function bevestigVerwijder() {
  const f = verwijderFunctie.value
  if (!f) return
  verwijderBezig.value = true
  verwijderFout.value = null
  try {
    await api.bedrijfsfuncties.verwijder(f.id)
    toastSucces(toast, 'Verwijderd')
    verwijderFunctie.value = null
    alle.value = alle.value.filter((x) => x.id !== f.id)
    // Plek-sleutels die deze functie bevatten (als segment) zijn niet meer geldig.
    openTakken.value = openTakken.value.filter(
      (plek) => !String(plek).split(PLEK_SCHEIDER).includes(f.id),
    )
  } catch (e) {
    if (e?.status === 409) {
      verwijderFout.value = `"${f.naam}" kan niet worden verwijderd omdat er nog onderliggende functies zijn. Verplaats of verwijder die eerst.`
    } else if (e?.status !== 401) {
      verwijderFout.value = e?.message || 'Verwijderen is mislukt.'
    }
  } finally {
    verwijderBezig.value = false
  }
}

// ── Plaatsen (ADR-044) — "Plaats ook onder…" + "Haal hier weg", alleen eigen functies ──
// De handeling is een plaatsing (feit "hoort onder"), geen verplaatsing: toevoegen zet
// de functie op een EXTRA plek; weghalen haalt alleen déze plek weg. Modelinhoud krijgt
// geen van beide affordances (haar plekken komen uit de bron — MODELINHOUD_BESCHERMD).
const plaatsFunctie = ref(null)
const plaatsDoel = ref(null) // { id, naam }
const plaatsFout = ref(null)
const plaatsBezig = ref(false)
const plaatsKey = ref(0) // remount-sleutel per opening (stale-label-les LI032)
function openPlaats(f) {
  plaatsFunctie.value = f
  plaatsDoel.value = null
  plaatsFout.value = null
  plaatsKey.value += 1
}
// Geldige doelen spiegelen de backend (LI032-regel 1): geen huidige ouder (zou
// PLAATSING_BESTAAT geven), geen subboom/zelf (kring), geen vervallen functie.
async function zoekPlaatsDoelen(params = {}) {
  const f = plaatsFunctie.value
  if (!f) return { items: [], volgende_cursor: null }
  const verboden = subboomIds(f.id)
  const huidige = new Set(boom.value.oudersVan.get(f.id) || [])
  const term = (params.zoek || '').trim().toLowerCase()
  const items = alle.value
    .filter((x) => !verboden.has(x.id) && !huidige.has(x.id) && !x.vervallen)
    .filter((x) => !term || x.naam.toLowerCase().includes(term))
    .map((x) => ({ ...x, ouder_naam: (x.ouder_ids || []).map(naamVanId).join(' + ') || null }))
    .sort((a, b) => a.naam.localeCompare(b.naam, 'nl'))
  return { items, volgende_cursor: null }
}
const doelWeergave = (x) => (x?.ouder_naam ? `${x.naam} — ${x.ouder_naam}` : (x?.naam ?? ''))
function kiesPlaatsDoel(item) {
  if (item?.id) plaatsDoel.value = { id: item.id, naam: item.naam }
  plaatsFout.value = null
}
const plaatsZin = computed(() => {
  const f = plaatsFunctie.value
  const d = plaatsDoel.value
  if (!f || !d) return ''
  return `"${f.naam}" komt óók onder "${d.naam}" te staan — het blijft één en dezelfde functie.`
})
async function bevestigPlaats() {
  const f = plaatsFunctie.value
  const d = plaatsDoel.value
  if (!f || !d) return
  plaatsBezig.value = true
  plaatsFout.value = null
  try {
    const res = await api.bedrijfsfuncties.plaats(f.id, { ouder_id: d.id })
    toastSucces(toast, 'Geplaatst')
    plaatsFunctie.value = null
    if (res?.id) alle.value = alle.value.map((x) => (x.id === res.id ? res : x))
    // De NIEUWE verschijning zichtbaar maken (pad open + aanstip op álle plekken +
    // scroll naar de nieuwe plek) — zelfde bouwsteen als bij aanmaken.
    toonFunctie(f.id, plekVan(_eerstePlek(d.id), f.id))
  } catch (e) {
    if (e?.status !== 401) plaatsFout.value = e?.message || 'Plaatsen is mislukt.'
  } finally {
    plaatsBezig.value = false
  }
}

// "Haal hier weg" — per verschijning: verwijdert alléén déze plaatsing; de functie
// blijft bestaan (zonder plekken wordt ze een wortel — de zin zegt dat vooraf).
const haalWegRij = ref(null) // { functie, ouderId }
const haalWegFout = ref(null)
const haalWegBezig = ref(false)
function openHaalWeg(rij) {
  haalWegRij.value = { functie: rij.functie, ouderId: rij.ouderId }
  haalWegFout.value = null
}
const haalWegZin = computed(() => {
  const r = haalWegRij.value
  if (!r) return ''
  const overige = (boom.value.oudersVan.get(r.functie.id) || []).filter((o) => o !== r.ouderId)
  const gevolg = overige.length
    ? `De functie blijft ook staan onder: ${overige.map(naamVanId).join(', ')}.`
    : 'De functie blijft bestaan en komt op het hoogste niveau te staan.'
  return `"${r.functie.naam}" hier weghalen (onder "${naamVanId(r.ouderId)}")? ${gevolg}`
})
async function bevestigHaalWeg() {
  const r = haalWegRij.value
  if (!r) return
  haalWegBezig.value = true
  haalWegFout.value = null
  try {
    const res = await api.bedrijfsfuncties.verwijderPlaatsing(r.functie.id, r.ouderId)
    toastSucces(toast, 'Hier weggehaald')
    haalWegRij.value = null
    if (res?.id) alle.value = alle.value.map((x) => (x.id === res.id ? res : x))
    // Laat zien waar de functie nu staat (resterende plek of het hoogste niveau).
    toonFunctie(r.functie.id)
  } catch (e) {
    if (e?.status !== 401) haalWegFout.value = e?.message || 'Weghalen is mislukt.'
  } finally {
    haalWegBezig.value = false
  }
}

// Functie-taal voor het gedeelde Diagram (de gegeneraliseerde bouwsteen). De
// vervallen-markering loopt via het eigen `vervallenIds`-kanaal met zijn eigen
// warning-taal; het gap-kanaal blijft ongebruikt tot gate 3.
const DIAGRAM_TEKSTEN = {
  zoekTitel: 'Zoek een bedrijfsfunctie',
  zoekPlaceholder: 'Zoek functie…',
  leeg: 'Zoek een bedrijfsfunctie om te beginnen.',
  wortel: 'Topgroepering',
  landschap: 'Toon hele functieboom',
  vervallen: 'vervallen in het referentiemodel',
}

onMounted(() => {
  herstelLijstStaat()
  laad()
})
</script>

<template>
  <section aria-labelledby="bedrijfsfuncties-titel">
    <div class="mb-[var(--lk-space-md)] flex items-center gap-[var(--lk-space-md)]">
      <h1 id="bedrijfsfuncties-titel" class="text-[length:var(--lk-text-2xl)] font-semibold text-[var(--lk-color-primary)]">
        Bedrijfsfuncties
      </h1>
      <div
        class="ml-auto inline-flex overflow-hidden rounded-[var(--lk-radius-btn)] border border-[var(--lk-color-border)]"
        role="group"
        aria-label="Weergave"
        data-testid="functie-weergave-schakelaar"
      >
        <button
          type="button" data-testid="weergave-boom"
          :aria-pressed="weergave === 'boom'"
          :class="['px-[var(--lk-space-md)] py-1 text-[length:var(--lk-text-sm)] font-semibold', weergave === 'boom' ? 'bg-[var(--lk-color-primary)] text-white' : 'bg-white text-[var(--lk-color-primary)] hover:bg-[var(--lk-color-accent)]']"
          @click="weergave = 'boom'"
        >Boom</button>
        <button
          type="button" data-testid="weergave-diagram"
          :aria-pressed="weergave === 'diagram'"
          title="Functie-structuurbeeld"
          :class="['border-l border-[var(--lk-color-border)] px-[var(--lk-space-md)] py-1 text-[length:var(--lk-text-sm)] font-semibold', weergave === 'diagram' ? 'bg-[var(--lk-color-primary)] text-white' : 'bg-white text-[var(--lk-color-primary)] hover:bg-[var(--lk-color-accent)]']"
          @click="weergave = 'diagram'"
        >Diagram</button>
      </div>
      <Button v-if="magBewerken" label="Nieuwe functie" data-testid="nieuwe-functie" @click="openNieuw(null)" />
    </div>

    <!-- Diagram-weergave: de gegeneraliseerde ProcesDiagram-bouwsteen met functie-taal;
         geen kaart-uitgang (functies hebben in de MVP geen kaartprojectie) en geen
         detail-route (bewerken gebeurt in de Boom). Vervallen loopt via het EIGEN
         kanaal (warning-taal); het gap-kanaal blijft vrij voor gate 3. -->
    <ProcesDiagram
      v-if="weergave === 'diagram'"
      :items="alle"
      :vervallen-ids="vervallenIds"
      :teksten="DIAGRAM_TEKSTEN"
      :detail-route="null"
      open-label="Open functie →"
      :met-kaart-uitgang="false"
      testid="functie-diagram"
      :initieel-centrum-id="diagramStart"
      @centrum-gewijzigd="(id) => (diagramStart = id)"
      @open-item="openUitDiagram"
    >
      <!-- Scherm-eigen popup-inhoud (LI039 v3): de DEFINITIE is de kern — precies wat
           het diagram zelf niet toont; verder alleen wat afwijkt ("eigen functie";
           de ⚠-vervallen-markering levert de bouwsteen-popup zelf). -->
      <template #popup-extra="{ item }">
        <p v-if="item?.definitie" data-testid="functie-popup-definitie" class="mt-2 text-[length:var(--lk-text-sm)] text-[var(--lk-color-text)]">{{ item.definitie }}</p>
        <p v-if="isEigen(item)" data-testid="functie-popup-eigen" class="mt-1 text-[length:var(--lk-text-xs)] text-[var(--lk-color-text-muted)]">eigen functie (staat niet in het referentiemodel)</p>
      </template>
    </ProcesDiagram>

    <div
      v-if="weergave === 'boom'"
      data-testid="filterbalk"
      class="mb-[var(--lk-space-md)] flex flex-wrap items-end gap-[var(--lk-space-md)] rounded-[var(--lk-radius-card)] bg-[var(--lk-color-surface)] p-[var(--lk-space-md)] shadow-[var(--lk-shadow-sm)]"
    >
      <label class="flex flex-col gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]">
        <span class="text-[length:var(--lk-text-xs)] font-semibold uppercase tracking-wide text-[var(--lk-color-text-muted)]">Zoeken</span>
        <input
          v-model="zoekterm"
          type="search"
          maxlength="255"
          data-testid="filter-zoek"
          aria-label="Zoek op functienaam"
          placeholder="zoeken…"
          class="rounded-[var(--lk-radius-btn)] border border-[var(--lk-color-border)] bg-[var(--lk-color-surface)] px-[var(--lk-space-sm)] py-1 focus:outline-2 focus:outline-offset-2 focus:outline-[var(--lk-color-primary)]"
        />
      </label>
    </div>

    <p v-if="fout" role="alert" data-testid="lijst-fout" class="mb-[var(--lk-space-md)] rounded-[var(--lk-radius-badge)] border border-[var(--lk-color-danger)] bg-[var(--lk-color-danger)]/10 px-[var(--lk-space-md)] py-[var(--lk-space-sm)] text-[var(--lk-color-danger)]">{{ fout }}</p>

    <!-- LI039 blok B — de zoekterm week zichtbaar opzij voor de zojuist vastgelegde rij
         (nooit stil); verdwijnt zodra de gebruiker het zoekveld weer aanraakt. -->
    <MeldingBanner
      v-if="weergave === 'boom' && wijkMelding"
      soort="info"
      :tekst="wijkMelding"
      testid="functie-wijk-melding"
      class="mb-[var(--lk-space-md)]"
    />

    <!-- LI039 UI-afronding v2 (punt 3) — de herkomst van het ingelezen model, één keer,
         uit de data (geen herhaling per rij; op de rij staat alleen wat afwijkt). -->
    <p
      v-if="weergave === 'boom' && modelHerkomst"
      data-testid="functie-model-herkomst"
      class="mb-[var(--lk-space-sm)] text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]"
    >{{ modelHerkomst }}</p>

    <div v-if="weergave === 'boom'" class="rounded-[var(--lk-radius-card)] bg-[var(--lk-color-surface)] shadow-[var(--lk-shadow-sm)]" data-testid="functies-boom">
      <ul v-if="rijen.length">
        <li
          v-for="rij in rijen"
          :key="rij.plek"
          :data-plek="rij.plek"
          :class="[
            'lk-rij relative flex items-center gap-[var(--lk-space-sm)] px-[var(--lk-space-md)] py-[var(--lk-space-sm)]',
            // ADR-044 — aanstip is FUNCTIE-breed: álle verschijningen lichten samen op
            // (één functie, geen kopie); de rij-identiteit (key/testid) is de plek.
            rij.functie.id === aangestiptId ? 'lk-aangestipt' : '',
            // LI039 blok C — vervallen: rustige waarschuwingstint over de hele rij
            // (kleur + icoon + tekst samen; zie de badge hieronder).
            rij.functie.vervallen ? 'bg-[color-mix(in_srgb,var(--lk-color-warning)_8%,transparent)]' : '',
          ]"
          :data-testid="`functie-rij-${rij.plek}`"
        >
          <!-- Tree-connectoren — het LI037-recept (puur decoratief, aria-hidden). -->
          <template v-if="rij.diepte">
            <template v-for="(door, i) in rij.lijnen" :key="`lijn-${i}`">
              <span
                v-if="door"
                data-boomlijn
                aria-hidden="true"
                class="pointer-events-none absolute inset-y-0 w-[1.5px] bg-[var(--lk-color-text-muted)]"
                :style="{ left: lijnX(i) }"
              ></span>
            </template>
            <span
              data-boomlijn
              :data-testid="`functie-lijn-${rij.plek}`"
              aria-hidden="true"
              class="pointer-events-none absolute top-0 w-[1.5px] bg-[var(--lk-color-text-muted)]"
              :class="rij.laatste ? 'bottom-1/2' : 'bottom-0'"
              :style="{ left: lijnX(rij.diepte - 1) }"
            ></span>
            <span
              data-boomlijn
              aria-hidden="true"
              class="pointer-events-none absolute top-1/2 h-[1.5px] w-3 bg-[var(--lk-color-text-muted)]"
              :style="{ left: lijnX(rij.diepte - 1) }"
            ></span>
          </template>
          <span
            v-if="rij.open"
            data-boomlijn
            aria-hidden="true"
            class="pointer-events-none absolute bottom-0 top-1/2 w-[1.5px] bg-[var(--lk-color-text-muted)]"
            :style="{ left: lijnX(rij.diepte) }"
          ></span>
          <!-- LI039 UI-afronding v2 — tweelaags rij-inhoud: SCAN-laag (naam + alleen wat
               afwijkt) en daaronder de LEES-laag (de definitie is het product — volledig
               leesbaar, max twee regels; geen tooltip, geen uitklap). -->
          <div class="lk-rij-inhoud" :style="{ paddingLeft: `${rij.diepte * 1.5}rem` }">
            <div class="lk-rij-kop">
              <!-- ADR-044 — uitklappen is PLEK-gebonden: deze toggle raakt alleen déze
                   verschijning; dezelfde functie elders blijft zoals ze stond. -->
              <button
                v-if="rij.heeftKinderen"
                type="button"
                :aria-expanded="rij.open"
                :aria-label="`${rij.open ? 'Klap in' : 'Klap uit'}: ${rij.functie.naam}`"
                :data-testid="`functie-toggle-${rij.plek}`"
                class="relative w-5 shrink-0 bg-[var(--lk-color-surface)] text-[var(--lk-color-text-muted)] hover:text-[var(--lk-color-primary)] focus:outline-2 focus:outline-offset-2 focus:outline-[var(--lk-color-primary)]"
                @click="toggle(rij.plek)"
              >{{ rij.open ? '▾' : '▸' }}</button>
              <span v-else class="w-5 shrink-0" aria-hidden="true"></span>
              <span class="min-w-0 font-medium text-[var(--lk-color-text)]" data-testid="functie-naam">{{ rij.functie.naam }}</span>
              <!-- Alleen wat afwijkt op de rij: "eigen" (eigenschap — gedempt randje, geen
                   knop-familie) en de vervallen-markering (LI039 blok C: warning-taal,
                   kleur + ⚠ + tekst; solid rand — gestippeld blijft van de gap-familie;
                   de gate-2-telling past er later in de tekst bij). -->
              <span
                v-if="isEigen(rij.functie)"
                :data-testid="`functie-eigen-${rij.plek}`"
                class="shrink-0 rounded-[var(--lk-radius-badge)] border border-[var(--lk-color-border)] px-1.5 text-[length:var(--lk-text-xs)] text-[var(--lk-color-text-muted)]"
              >eigen</span>
              <span
                v-if="rij.functie.vervallen"
                :data-testid="`functie-vervallen-${rij.plek}`"
                class="flex shrink-0 items-center gap-1 rounded-[var(--lk-radius-badge)] border border-[var(--lk-color-warning)] px-1.5 text-[length:var(--lk-text-xs)] text-[var(--lk-color-warning)]"
              ><span aria-hidden="true">⚠</span><span>vervallen in het referentiemodel</span></span>
            </div>
            <p
              v-if="rij.functie.definitie"
              class="lk-rij-definitie pl-7 text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]"
              :data-testid="`functie-definitie-${rij.plek}`"
            >{{ rij.functie.definitie }}</p>
            <!-- ADR-044 — "staat ook onder": dezelfde functie staat óók op andere
                 plekken (gelijkwaardig — geen kopie, geen rangorde). Klik = die andere
                 verschijning in beeld (pad open + functie-brede aanstip + scroll). -->
            <p
              v-if="rij.andereOuders.length"
              class="pl-7 text-[length:var(--lk-text-xs)] text-[var(--lk-color-text-muted)]"
              :data-testid="`functie-ookonder-${rij.plek}`"
            >
              staat ook onder:
              <template v-for="(o, i) in rij.andereOuders" :key="o">
                <span v-if="i">, </span>
                <button
                  type="button"
                  class="text-[var(--lk-color-primary)] hover:underline focus:outline-2 focus:outline-offset-2 focus:outline-[var(--lk-color-primary)]"
                  :data-testid="`functie-ookonder-link-${rij.plek}--${o}`"
                  :aria-label="`Toon ${rij.functie.naam} onder ${naamVanId(o)}`"
                  @click="gaNaarAnderePlek(rij, o)"
                >{{ naamVanId(o) }}</button>
              </template>
            </p>
          </div>
          <!-- Rij-acties — rustig (LI039 C0, gedeelde RijActies-bouwsteen: tertiair,
               zichtbaar op de actieve rij/via focus). De affordances spiegelen de
               backend-regels: modelinhoud kent geen bewerk-/verplaats-/verwijder-knop
               (422-bescherming), een vervallen functie geen "+ Deelfunctie"
               (VERVALLEN_NIET_KOPPELBAAR). Verwijderen HOUDT de danger-vorm (LI037). -->
          <RijActies>
            <!-- Doorklik (navigatie) = text/ghost mét pijl; mutaties = outlined (rustige
                 knop-vorm: omlijning, gedempte tekst) — het verschil is zichtbaar (punt 1). -->
            <Button
              label="Toon in functiebeeld →"
              text
              :data-testid="`functie-diagram-${rij.plek}`"
              :aria-label="`Toon ${rij.functie.naam} in het functiebeeld`"
              @click="toonInFunctiebeeld(rij.functie)"
            />
            <Button
              v-if="magBewerken && !rij.functie.vervallen"
              label="+ Deelfunctie"
              outlined
              :data-testid="`functie-deelfunctie-${rij.plek}`"
              :aria-label="`Nieuwe deelfunctie onder ${rij.functie.naam}`"
              @click="openNieuw(rij.functie)"
            />
            <Button
              v-if="magBewerken && isEigen(rij.functie)"
              label="Bewerken"
              outlined
              :data-testid="`functie-bewerk-${rij.plek}`"
              :aria-label="`Bewerk ${rij.functie.naam}`"
              @click="openBewerk(rij.functie)"
            />
            <!-- ADR-044 — plaatsings-acties (alleen eigen functies; modelinhoud krijgt
                 de affordance niet: haar plekken komen uit de bron). "Plaats ook
                 onder…" = extra plek; "Haal hier weg" = alléén déze plek (danger — het
                 verwijdert een registratie-feit; de functie zelf blijft). -->
            <Button
              v-if="magBewerken && isEigen(rij.functie)"
              label="Plaats ook onder…"
              outlined
              :data-testid="`functie-plaats-${rij.plek}`"
              :aria-label="`Plaats ${rij.functie.naam} ook onder een andere functie`"
              @click="openPlaats(rij.functie)"
            />
            <Button
              v-if="magBewerken && isEigen(rij.functie) && rij.ouderId"
              label="Haal hier weg"
              severity="danger"
              :data-testid="`functie-haalweg-${rij.plek}`"
              :aria-label="`Haal ${rij.functie.naam} weg onder ${naamVanId(rij.ouderId)}`"
              @click="openHaalWeg(rij)"
            />
            <Button
              v-if="magVerwijderen && isEigen(rij.functie)"
              label="Verwijderen"
              severity="danger"
              :data-testid="`functie-verwijder-${rij.plek}`"
              :aria-label="`Verwijder ${rij.functie.naam}`"
              @click="openVerwijder(rij.functie)"
            />
          </RijActies>
        </li>
      </ul>
      <p v-else-if="!laden && zoekterm.trim()" data-testid="lijst-geen-match" class="p-[var(--lk-space-md)] text-[var(--lk-color-text-muted)]">
        Geen bedrijfsfuncties komen overeen met de zoekterm.
      </p>
      <p v-else-if="!laden" data-testid="lijst-leeg" class="p-[var(--lk-space-md)] text-[var(--lk-color-text-muted)]">
        Er is nog geen functieboom.
        <template v-if="magBewerken">Lees een referentiemodel in (volgt in een volgende stap) of begin met "Nieuwe functie".</template>
        <template v-else>Een beheerder of medewerker leest het referentiemodel in of voegt functies toe.</template>
      </p>
      <p v-else data-testid="lijst-laden" class="p-[var(--lk-space-md)] text-[var(--lk-color-text-muted)]">Laden…</p>
    </div>

    <!-- Nieuwe (deel)functie / eigen functie bewerken -->
    <Dialog v-model:visible="dialogOpen" modal :closable="false" :header="dialogFunctie ? 'Functie bewerken' : (dialogOuder ? `Nieuwe deelfunctie onder “${dialogOuder.naam}”` : 'Nieuwe functie')" data-testid="functie-dialog">
      <form class="flex min-w-[22rem] flex-col gap-[var(--lk-space-md)]" @submit.prevent="bevestig">
        <p v-if="formFout" role="alert" data-testid="functie-dialog-fout" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ formFout }}</p>
        <div class="flex flex-col gap-[var(--lk-space-xs)]">
          <label for="functie-naam" class="font-semibold">Naam *</label>
          <input id="functie-naam" v-model="form.naam" type="text" maxlength="255" data-testid="functie-form-naam" class="rounded-[var(--lk-radius-btn)] border border-[var(--lk-color-border)] bg-[var(--lk-color-surface)] px-[var(--lk-space-sm)] py-[var(--lk-space-xs)]" />
        </div>
        <div class="flex flex-col gap-[var(--lk-space-xs)]">
          <label for="functie-definitie" class="font-semibold">Definitie</label>
          <textarea id="functie-definitie" v-model="form.definitie" rows="3" data-testid="functie-form-definitie" class="rounded-[var(--lk-radius-btn)] border border-[var(--lk-color-border)] bg-[var(--lk-color-surface)] px-[var(--lk-space-sm)] py-[var(--lk-space-xs)]"></textarea>
        </div>
        <div class="flex gap-[var(--lk-space-md)]">
          <Button type="submit" :label="dialogFunctie ? 'Opslaan' : 'Toevoegen'" data-testid="functie-dialog-opslaan" :disabled="bezig" />
          <Button type="button" label="Annuleren" severity="secondary" @click="dialogOpen = false" />
        </div>
      </form>
    </Dialog>

    <!-- Verwijderen: gedeelde bevestigingsdialoog; 409 (HEEFT_DEELFUNCTIES) → leesbare zin. -->
    <BevestigVerwijderDialog
      :visible="!!verwijderFunctie"
      kop="Bedrijfsfunctie verwijderen"
      :bezig="verwijderBezig"
      testid="functie-verwijder"
      @update:visible="(v) => { if (!v) verwijderFunctie = null }"
      @bevestig="bevestigVerwijder"
    >
      <span v-if="verwijderFout" data-testid="functie-verwijder-fout" class="text-[var(--lk-color-warning)]">{{ verwijderFout }}</span>
      <span v-else>Verwijder "{{ verwijderFunctie?.naam }}"?</span>
    </BevestigVerwijderDialog>

    <!-- ADR-044 — "Plaats ook onder…" (eigen functies): picker zonder ongeldige doelen
         (huidige ouders + subboom + vervallen eruit — PLAATSING_BESTAAT-, kring- en
         VERVALLEN-preventie vóóraf, LI032-regel 1). -->
    <Dialog :visible="!!plaatsFunctie" modal :closable="false" :header="`Plaats “${plaatsFunctie?.naam ?? ''}” ook onder…`" data-testid="functie-plaats-dialog" @update:visible="(v) => { if (!v) plaatsFunctie = null }">
      <div class="flex min-w-[24rem] flex-col gap-[var(--lk-space-md)]">
        <p v-if="plaatsFout" role="alert" data-testid="functie-plaats-fout" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ plaatsFout }}</p>
        <label class="flex flex-col gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]">
          <span>Kies de functie waaronder deze óók komt te staan</span>
          <ZoekSelect
            :key="plaatsKey"
            :zoek-functie="zoekPlaatsDoelen"
            :weergave="doelWeergave"
            id-veld="id"
            placeholder="Zoek functie…"
            testid="functie-plaats-doel"
            @keuze="kiesPlaatsDoel"
          />
        </label>
        <p v-if="plaatsZin" data-testid="functie-plaats-zin" class="max-w-prose font-medium">{{ plaatsZin }}</p>
        <div class="flex gap-[var(--lk-space-md)]">
          <Button type="button" label="Plaatsen" data-testid="functie-plaats-bevestig" :disabled="!plaatsDoel || plaatsBezig" @click="bevestigPlaats" />
          <Button type="button" label="Annuleren" severity="secondary" @click="plaatsFunctie = null" />
        </div>
      </div>
    </Dialog>

    <!-- ADR-044 — "Haal hier weg": verwijdert alléén déze plaatsing (gedeelde
         bevestigingsdialoog met de regel leesbaar; de functie zelf blijft bestaan). -->
    <BevestigVerwijderDialog
      :visible="!!haalWegRij"
      kop="Functie hier weghalen"
      bevestig-label="Haal hier weg"
      :bezig="haalWegBezig"
      testid="functie-haalweg"
      @update:visible="(v) => { if (!v) haalWegRij = null }"
      @bevestig="bevestigHaalWeg"
    >
      <span v-if="haalWegFout" data-testid="functie-haalweg-fout" class="text-[var(--lk-color-warning)]">{{ haalWegFout }}</span>
      <span v-else data-testid="functie-haalweg-zin">{{ haalWegZin }}</span>
    </BevestigVerwijderDialog>
  </section>
</template>
