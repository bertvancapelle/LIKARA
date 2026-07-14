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
// Gate 1b — inlezen = beheerder (REFERENTIEMODEL.AANMAKEN is beheerder-only sinds de
// gate-1b-RBAC-correctie). Affordance vooraf weren; de backend blijft de handhaver.
const magInlezen = computed(() => auth.hasRole('beheerder'))

const alle = ref([]) // platte set (alle pagina's); de boom is een client-side afgeleide
const laden = ref(false)
const fout = ref(null)
// ADR-049 gate 2a — de GEDEELDE leesregel per plek (fijn verdringt grof), server-side
// afgeleid. De boom LEEST deze uitkomst; ze beslist grof/fijn nooit zelf (besluit 5).
const dekking = ref([])
// ADR-051 gate 3 — de gedeelde stand per plek (gat · via_boven · hier · niets).
const standen = ref([])

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
  laadDekking() // best-effort, parallel: de koppelingen kleuren de boom in
  laadStanden()
}

// ADR-049 — de gedeelde dekking ophalen (best-effort; faalt dit, dan toont de boom geen
// koppelingen maar blijft bruikbaar — geen dubbele rode ruis naast de laad-fout).
async function laadDekking() {
  try {
    dekking.value = (await api.functievervullingen.dekking()) ?? []
  } catch {
    dekking.value = []
  }
}
// ADR-051 gate 3 — de VIER standen per plek uit de GEDEELDE afleiding (`plek_standen`). De boom
// LEEST deze stand; ze beslist niets zelf (besluit 5). Best-effort.
async function laadStanden() {
  try {
    standen.value = (await api.functievervullingen.standen())?.plekken ?? []
  } catch {
    standen.value = []
  }
}
const standenPerPlek = computed(() => {
  const m = new Map()
  for (const p of standen.value) m.set(_dekkingSleutel(p.functie_id, p.ouder_functie_id), p)
  return m
})
const standVoorRij = (rij) => standenPerPlek.value.get(_dekkingSleutel(rij.functie.id, rij.ouderId)) || null
// De omhoog-cue in gebruikerstaal — de naam komt van de dichtstbijzijnde dragende voorouder
// (via_functie_id, door de boom opgezocht in naamVanId); bij meerdere op gelijke afstand telt
// de backend ze (via_aantal) en noemen we géén willekeurige naam.
function viaTekst(p) {
  if (!p) return ''
  if (p.via_functie_id) return `ondersteund via ${naamVanId(p.via_functie_id)} — hier niet bevestigd`
  return `ondersteund via ${p.via_aantal} bovenliggende functies — hier niet bevestigd`
}
// Plek-sleutel voor de leesregel-lookup: functie + ouder ('' = wortel/grof). Spiegelt exact
// de backend-sleutel (functie_id, ouder_functie_id) — de boom KIEST hier niets, ze zoekt op.
const _dekkingSleutel = (functieId, ouderId) => `${functieId}|${ouderId ?? ''}`
const dekkingPerPlek = computed(() => {
  const m = new Map()
  for (const d of dekking.value) {
    m.set(_dekkingSleutel(d.functie_id, d.ouder_functie_id), d)
  }
  return m
})
const dekkingVoorRij = (rij) => dekkingPerPlek.value.get(_dekkingSleutel(rij.functie.id, rij.ouderId)) || null
// LI041 — het getelde reikwijdte-label voor een grove plek. De TELLING komt uit de gedeelde
// leeslaag (`grof_totaal_plekken` N, `grof_geldt_op` M) — hier alleen de zin eromheen; de boom
// telt niets zelf. Op een fijne plek staat gewoon "alleen hier".
function dekkingLabel(d) {
  if (!d || d.herkomst === 'fijn') return 'alleen hier'
  const n = d.grof_totaal_plekken
  const m = d.grof_geldt_op
  if (n === 1) return 'geldt op deze plek'
  if (m === n) return `geldt op alle ${n} plekken`
  return `geldt nog op ${m} van de ${n} plekken`
}
// De namen van het grove antwoord dat op déze (fijne) plek verdrongen is (read-only; het
// bestaat nog — ADR-049 besluit 1). Leeg = niets verdrongen.
const verdrongenNamen = (d) => (d?.verdrongen || []).map((c) => c.component_naam).join(', ')

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

// ── Koppelen (ADR-049 gate 2a) — systeem aan functie/plek, grof of fijn ───────────
// Koppelen mag op ELKE functie (óók modelinhoud — "Toezicht" koppelen is de use-case);
// alleen vervallen functies zijn niet koppelbaar (backend 422 — de knop weren we vooraf).
// De picker toont alleen componenten die WERK ondersteunen (ADR-045; het server-side
// `ondersteunt_werk`-filter spiegelt de backend-regel — geen typenlijst in de frontend).
const koppelRij = ref(null)        // { functie, ouderId, plek }
const koppelComponent = ref(null)  // { id, naam }
const koppelScope = ref('overal')  // 'overal' (grof) | 'hier' (fijn) — 'hier' alleen mét plek
const koppelOordeel = ref('')      // ADR-051 — '' = nog niet beoordeeld (geen sentinel)
const koppelFout = ref(null)
const koppelBezig = ref(false)
const koppelKey = ref(0)           // remount-sleutel per opening (stale-label-les LI032)
const koppelHeeftPlek = computed(() => !!koppelRij.value?.ouderId)
function openKoppel(rij) {
  koppelRij.value = { functie: rij.functie, ouderId: rij.ouderId, plek: rij.plek }
  koppelComponent.value = null
  // "Geldt overal" staat voorop (ADR-044 besluit 2 / ADR-045 besluit 3); een wortel kent
  // maar één plek, dus daar valt grof en fijn samen → altijd grof.
  koppelScope.value = 'overal'
  koppelOordeel.value = ''  // leeg = nog niet beoordeeld
  koppelFout.value = null
  koppelKey.value += 1
}
// De picker spiegelt de backend: alleen werk-ondersteunende componenten (server-side filter).
async function zoekKoppelComponenten(params = {}) {
  try {
    return await api.componenten.lijst({ ondersteunt_werk: true, zoek: params.zoek || undefined, limit: 25 })
  } catch {
    return { items: [], volgende_cursor: null }
  }
}
const koppelComponentWeergave = (x) => x?.naam ?? ''
function kiesKoppelComponent(item) {
  if (item?.id) koppelComponent.value = { id: item.id, naam: item.naam }
  koppelFout.value = null
}
const koppelZin = computed(() => {
  const r = koppelRij.value
  const c = koppelComponent.value
  if (!r || !c) return ''
  if (koppelScope.value === 'hier' && r.ouderId) {
    return `"${c.naam}" ondersteunt "${r.functie.naam}" alleen op deze plek (onder "${naamVanId(r.ouderId)}"). Een grof antwoord op deze plek wordt hier vervangen.`
  }
  return `"${c.naam}" ondersteunt "${r.functie.naam}" — op elke plek waar deze functie staat. Verfijn later per plek als het ergens anders gaat.`
})
async function bevestigKoppel() {
  const r = koppelRij.value
  const c = koppelComponent.value
  if (!r || !c) return
  koppelBezig.value = true
  koppelFout.value = null
  try {
    const ouder = koppelScope.value === 'hier' && r.ouderId ? r.ouderId : null
    await api.functievervullingen.maak({
      component_id: c.id, functie_id: r.functie.id, ouder_functie_id: ouder,
      oordeel: koppelOordeel.value || null,
    })
    toastSucces(toast, 'Gekoppeld')
    koppelRij.value = null
    await laadDekking()
    await laadStanden()
    toonFunctie(r.functie.id, r.plek)
  } catch (e) {
    if (e?.status !== 401) koppelFout.value = e?.message || 'Koppelen is mislukt.'
  } finally {
    koppelBezig.value = false
  }
}

// Ontkoppelen = een registratie-feit terugnemen → medewerker (magBewerken, ADR-050: wie koppelt,
// ontkoppelt). Een fijne koppeling weghalen maakt het grove antwoord op die plek wéér leesbaar;
// er is nooit iets weggeschreven (ADR-049 besluit 1).
const ontkoppelDoel = ref(null) // { vervulling_id, component_naam, functie_naam, herkomst, ouderId }
const ontkoppelFout = ref(null)
const ontkoppelBezig = ref(false)
function openOntkoppel(rij, comp, herkomst) {
  ontkoppelDoel.value = {
    vervulling_id: comp.vervulling_id,
    component_naam: comp.component_naam,
    functie_naam: rij.functie.naam,
    herkomst,
    ouderId: rij.ouderId,
  }
  ontkoppelFout.value = null
}
const ontkoppelZin = computed(() => {
  const d = ontkoppelDoel.value
  if (!d) return ''
  if (d.herkomst === 'geen_systeem') {
    return `De bevinding "hiervoor wordt niets gebruikt" op "${d.functie_naam}" weghalen? De plek komt dan weer op de navraag-lijst.`
  }
  if (d.herkomst === 'fijn') {
    return `De koppeling van "${d.component_naam}" aan "${d.functie_naam}" hier weghalen? Het antwoord dat overal geldt wordt op deze plek weer leesbaar.`
  }
  return `De koppeling van "${d.component_naam}" aan "${d.functie_naam}" weghalen? Deze geldt overal — hij verdwijnt op elke plek waar "${d.functie_naam}" staat.`
})
async function bevestigOntkoppel() {
  const d = ontkoppelDoel.value
  if (!d) return
  ontkoppelBezig.value = true
  ontkoppelFout.value = null
  try {
    await api.functievervullingen.verwijder(d.vervulling_id)
    toastSucces(toast, 'Koppeling weggehaald')
    ontkoppelDoel.value = null
    await laadDekking()
    await laadStanden()
  } catch (e) {
    if (e?.status !== 401) ontkoppelFout.value = e?.message || 'Weghalen is mislukt.'
  } finally {
    ontkoppelBezig.value = false
  }
}

// ── ADR-051 gate 3 — "hier draait geen systeem — vastgesteld" (een bevinding) ─────
// Een eigen actie op de plek, strikt onderscheiden van "nog niet gevraagd" (het gat). Medewerker-
// werk (registratie-feit, ADR-050). Weghalen laat de plek terugvallen op gat/via-boven.
const geenSysteemRij = ref(null)   // { functie, ouderId, plek }
const geenSysteemFout = ref(null)
const geenSysteemBezig = ref(false)
function openGeenSysteem(rij) {
  geenSysteemRij.value = { functie: rij.functie, ouderId: rij.ouderId, plek: rij.plek }
  geenSysteemFout.value = null
}
const geenSysteemZin = computed(() => {
  const r = geenSysteemRij.value
  return r ? `Vastleggen dat dit werk zonder hulpmiddel gaat (bijvoorbeeld op papier)? Dit is een bevinding — geen openstaande vraag meer, en niet meer op de navraag-lijst.` : ''
})
async function bevestigGeenSysteem() {
  const r = geenSysteemRij.value
  if (!r) return
  geenSysteemBezig.value = true
  geenSysteemFout.value = null
  try {
    // "Hier" (fijne plek) als er een ouder is; anders grof (de functie-brede bevinding).
    const ouder = r.ouderId || null
    await api.functievervullingen.geenSysteem({ functie_id: r.functie.id, ouder_functie_id: ouder })
    toastSucces(toast, 'Vastgelegd: hiervoor wordt niets gebruikt')
    geenSysteemRij.value = null
    await laadDekking()
    await laadStanden()
    toonFunctie(r.functie.id, r.plek)
  } catch (e) {
    if (e?.status !== 401) geenSysteemFout.value = e?.message || 'Vastleggen is mislukt.'
  } finally {
    geenSysteemBezig.value = false
  }
}

// Het oordeel op een bestaande koppeling zetten/wissen (naar_behoren / noodoplossing / '' = leeg).
async function zetOordeel(comp, oordeel) {
  try {
    await api.functievervullingen.zetOordeel(comp.vervulling_id, oordeel || null)
    await laadDekking()
    await laadStanden()
  } catch (e) {
    if (e?.status !== 401) toastSucces(toast, 'Bijgewerkt')  // fout is zeldzaam; geen rode ruis in de rij
  }
}

// ADR-051 correctie (LI041) — het oordeel wordt bediend vanaf de plek waar het OVER gaat: de
// leeslaag-zin ("Zaaksysteem — is een noodoplossing"). Klik → de drie keuzes op VOLLE grootte
// (een lichte dialoog), niet een krappe select in de actie-strook. Zo blijft de veldnorm heel
// (geen .lk-veld-override) en oogt de rij rustiger — het oordeel is een eigenschap, geen handeling.
const oordeelDoel = ref(null)   // { comp, functie_naam }
function openOordeel(comp, functie_naam) {
  oordeelDoel.value = { comp, functie_naam }
}
async function kiesOordeel(oordeel) {
  const d = oordeelDoel.value
  if (!d) return
  oordeelDoel.value = null
  await zetOordeel(d.comp, oordeel)
}
const oordeelLabel = (o) => (o === 'naar_behoren' ? 'draagt naar behoren' : o === 'noodoplossing' ? 'noodoplossing' : 'nog niet beoordeeld')
// ADR-051 correctie — de LEESLAAG-zin (hoe goed draagt dit component het werk): het oordeel
// staat hier één keer. "Component", niet "systeem" (klopt óók voor een fileshare/G-schijf).
const oordeelZin = (o) => (o === 'naar_behoren' ? 'draagt het werk naar behoren' : o === 'noodoplossing' ? 'is een noodoplossing' : 'nog niet beoordeeld')

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

// ── Gate 1b-afronding — onvoltooide inlees: nooit stil ───────────────────────────
// De import zet server-side een begin- (False) en eindmarkering (True) op het
// ingelezen model (`inlees_voltooid`). False bij het openen van het scherm = de
// vorige inlees is afgebroken: het model staat er mogelijk half en vervallen
// functies kunnen nog als geldig getoond worden. Iedereen ZIET dat signaal (je
// kijkt naar een boom die mogelijk niet klopt); alleen de beheerder krijgt de
// herstart-actie. Best-effort: faalt deze status-call, dan geen signaal — de
// dialog-flow heeft zijn eigen foutafhandeling (geen dubbele rode ruis).
const modelStatus = ref([])
async function laadModelStatus() {
  try {
    modelStatus.value = (await api.referentiemodellen.overzicht()) ?? []
  } catch {
    modelStatus.value = []
  }
}
const onvoltooidModel = computed(() =>
  modelStatus.value.find((m) => m.ingelezen && m.ingelezen.inlees_voltooid === false) ?? null,
)

// ── Gate 1b — referentiemodel inlezen: voorbeeld vóór bevestigen ─────────────────
// Vorm = een Dialog-overlay met expliciete bevestig-knop (het bestaande
// bevestigingsdialoog-patroon — KOPPELING_DUBBEL / BevestigVerwijderDialog; het
// resultaat als tweede dialog-staat is het GebruikersbeheerView-recept). Geen nieuw
// mechanisme. Niets landt stil: kiezen → voorbeeld (dry-run) → bevestigen → resultaat.
const inleesOpen = ref(false)
const inleesModellen = ref([])     // het aanbod (met ingelezen-status per model)
const inleesModel = ref(null)      // het gekozen model
const inleesVoorbeeld = ref(null)  // de dry-run-telling (het voorbeeld)
const inleesResultaat = ref(null)  // ná bevestigen (tweede dialog-staat)
const inleesLaden = ref(false)     // het VOORBEELD berekenen (dry-run)
const inleesBezig = ref(false)     // het inlezen zelf (kan tientallen seconden duren)
const inleesFout = ref(null)       // fout BINNEN de model-context (voorbeeld/inlezen)

// B2 (browsercheck-bevinding): een lege uitkomst is geen fout. De aanbod-staat is ÉÉN
// enum-ref die op precies één plek per pad wordt gezet — 'fout' (aanroep faalde, rood)
// en 'leeg' (aanroep slaagde, niets in het aanbod, rustig) kunnen daardoor structureel
// niet tegelijk bestaan (één variabele draagt één waarde; de template vertakt er
// exclusief op). De eerdere overlap (catch zette de fout, de leeg-tak keek alleen naar
// de lege lijst) is daarmee onmogelijk gemaakt — niet alleen verholpen.
const aanbodStaat = ref('laden')   // 'laden' | 'fout' | 'leeg' | 'ok'

async function openInlezen() {
  inleesOpen.value = true
  inleesModellen.value = []
  inleesModel.value = null
  inleesVoorbeeld.value = null
  inleesResultaat.value = null
  inleesFout.value = null
  aanbodStaat.value = 'laden'
  try {
    const alles = await api.referentiemodellen.overzicht()
    modelStatus.value = alles // het onvoltooid-signaal boven de boom beweegt mee
    const aanbod = alles.filter((m) => m.beschikbaar)
    inleesModellen.value = aanbod
    aanbodStaat.value = aanbod.length ? 'ok' : 'leeg'
    // Eén model in het aanbod (de MVP-realiteit): direct het voorbeeld tonen.
    if (aanbod.length === 1) await kiesInleesModel(aanbod[0])
  } catch (e) {
    if (e?.status === 401) {
      inleesOpen.value = false // de centrale sessie-vangrail redirect; geen rode ruis
      return
    }
    aanbodStaat.value = 'fout'
  }
}

async function kiesInleesModel(model) {
  inleesModel.value = model
  inleesVoorbeeld.value = null
  inleesFout.value = null
  inleesLaden.value = true
  try {
    inleesVoorbeeld.value = await api.referentiemodellen.voorbeeld(model.model_sleutel)
  } catch (e) {
    inleesFout.value =
      e?.status === 401 ? null : e?.message || 'Het voorbeeld kon niet berekend worden.'
  } finally {
    inleesLaden.value = false
  }
}

// Het voorbeeld in gebruikerstaal — geen jargon, de eerlijke telling.
const inleesIsEerste = computed(() => {
  const v = inleesVoorbeeld.value
  return !!v && v.ongewijzigd === 0 && !v.bijgewerkt.length && !v.vervallen.length
})
const inleesGeenWijzigingen = computed(() => {
  const v = inleesVoorbeeld.value
  return !!v && !v.nieuw.length && !v.bijgewerkt.length && !v.vervallen.length
})
// Onvoltooid geldt óók binnen de dialog: de afronding moet mogelijk zijn zelfs als
// het plan leeg is (alle functies staan er al, alleen de eindmarkering ontbreekt) —
// anders is de melding nooit weg te werken.
const inleesOnvoltooid = computed(
  () => inleesModel.value?.ingelezen?.inlees_voltooid === false,
)
const inleesVoorbeeldZin = computed(() => {
  const v = inleesVoorbeeld.value
  if (!v) return null
  if (inleesGeenWijzigingen.value) {
    return inleesOnvoltooid.value
      ? 'Alle functies staan er al — alleen de afronding van de vorige inlees ontbreekt nog.'
      : 'Het model is al actueel — er verandert niets.'
  }
  const overgeslagen = v.overgeslagen_totaal
    ? ` ${v.overgeslagen_totaal} elementen van andere typen worden overgeslagen.`
    : ''
  if (inleesIsEerste.value) {
    return `${v.nieuw.length} functies worden toegevoegd. ${v.plaatsingen_totaal} plaatsingen.${overgeslagen}`
  }
  const vervallenDeel = v.vervallen.length
    ? ` · ${v.vervallen.length} vervallen — waarvan ${v.vervallen.filter((f) => f.in_gebruik).length} nog in gebruik`
    : ''
  return `${v.nieuw.length} nieuw · ${v.bijgewerkt.length} bijgewerkt${vervallenDeel}.${overgeslagen}`
})

async function bevestigInlezen() {
  if (!inleesModel.value || inleesBezig.value) return
  inleesBezig.value = true
  inleesFout.value = null
  try {
    inleesResultaat.value = await api.referentiemodellen.inlezen(inleesModel.value.model_sleutel)
    toastSucces(toast, 'Ingelezen')
    await laad() // de boom toont direct de nieuwe stand
    await laadModelStatus() // het onvoltooid-signaal verdwijnt (of verschijnt eerlijk)
  } catch (e) {
    inleesFout.value =
      e?.status === 401 ? null : e?.message || 'Het inlezen is mislukt. Probeer het opnieuw.'
  } finally {
    inleesBezig.value = false
  }
}

onMounted(() => {
  herstelLijstStaat()
  laad()
  laadModelStatus() // onvoltooid-signaal (best-effort, parallel aan de boom-laad)
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
      <Button v-if="magInlezen" label="Model inlezen" severity="secondary" data-testid="model-inlezen" @click="openInlezen" />
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
          class="lk-veld"
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

    <!-- Gate 1b-afronding — onvoltooide inlees: rustig maar onmiskenbaar (kleur +
         icoon + tekst, de bestaande waarschuwingstaal). Iedereen ziet het signaal
         (de boom klopt mogelijk niet); alleen de beheerder krijgt de herstart-actie.
         Geen automatische herstart — opnieuw inlezen blijft een bewuste handeling. -->
    <MeldingBanner
      v-if="onvoltooidModel"
      soort="warn"
      testid="functie-inlees-onvoltooid"
      class="mb-[var(--lk-space-md)]"
    >
      De vorige inlees van "{{ onvoltooidModel.label }}" is niet afgerond — het model is
      mogelijk onvolledig.<template v-if="magInlezen"> Start opnieuw om hem af te maken.
        <Button
          label="Inlezen afronden"
          outlined
          data-testid="onvoltooid-hervat"
          class="ml-[var(--lk-space-sm)]"
          @click="openInlezen"
        /></template>
    </MeldingBanner>

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
            <!-- ADR-049 gate 2a — welke componenten dragen déze plek. De boom LEEST de
                 gedeelde leesregel (fijn verdringt grof): 'herkomst' komt van de server,
                 de boom beslist niets zelf. "geldt overal" = grof, "alleen hier" = fijn.
                 Weghalen loopt via de bevestigingsdialoog (nooit een kaal kruisje op een
                 registratie-feit); alleen de beheerder ziet die affordance. -->
            <!-- ADR-051 correctie — twee lagen (likara-ux), zoals de functierij zelf: SCAN
                 (wáármee) en daaronder LEES (hoe goed + hoe breed, gedempt). Het oordeel staat
                 ÉÉN keer (leeslaag); de bediening (oordeel/weghalen) verschijnt pas op de actieve
                 rij (.lk-rij-acties). "Component" i.p.v. "systeem" — klopt óók voor een fileshare. -->
            <template v-if="dekkingVoorRij(rij) && dekkingVoorRij(rij).componenten.length">
              <!-- Scanlaag: waarmee wordt dit werk gedaan -->
              <p class="pl-7 text-[length:var(--lk-text-sm)]" :data-testid="`functie-dekking-${rij.plek}`">
                <span class="text-[var(--lk-color-text-muted)]">Gedaan met: </span>
                <template v-for="(c, i) in dekkingVoorRij(rij).componenten" :key="c.vervulling_id">
                  <span v-if="i" aria-hidden="true"> · </span>
                  <span
                    class="font-medium"
                    :class="c.oordeel === 'noodoplossing' ? 'text-[var(--lk-color-warning)]' : 'text-[var(--lk-color-text)]'"
                    :data-testid="`functie-dekking-comp-${rij.plek}--${c.component_id}`"
                  >{{ c.component_naam }}</span>
                </template>
              </p>
              <!-- Leeslaag: hoe goed (oordeel — ÉÉN keer) + hoe breed (reikwijdte). Gedempt.
                   Het oordeel is KLIKBAAR (LI041) — de zin waar het over gaat opent de drie keuzes
                   op volle grootte; geen krappe select. Voor een viewer een gewone (niet-klikbare) span. -->
              <p class="pl-7 text-[length:var(--lk-text-xs)] text-[var(--lk-color-text-muted)]" :data-testid="`functie-dekking-lees-${rij.plek}`">
                <template v-for="(c, i) in dekkingVoorRij(rij).componenten" :key="c.vervulling_id">
                  <span v-if="i"> · </span>
                  <button
                    v-if="magBewerken"
                    type="button"
                    :class="['underline decoration-dotted underline-offset-2 hover:decoration-solid focus:outline-2 focus:outline-offset-2 focus:outline-[var(--lk-color-primary)]', c.oordeel === 'noodoplossing' ? 'text-[var(--lk-color-warning)]' : 'text-[var(--lk-color-text-muted)]']"
                    :data-testid="`functie-oordeel-${rij.plek}--${c.component_id}`"
                    :aria-label="`Oordeel over ${c.component_naam} wijzigen — nu: ${oordeelZin(c.oordeel)}`"
                    @click="openOordeel(c, rij.functie.naam)"
                  >{{ c.component_naam }} {{ oordeelZin(c.oordeel) }}</button>
                  <span
                    v-else
                    :class="c.oordeel === 'noodoplossing' ? 'text-[var(--lk-color-warning)]' : ''"
                    :data-testid="`functie-oordeel-${rij.plek}--${c.component_id}`"
                  >{{ c.component_naam }} {{ oordeelZin(c.oordeel) }}</span>
                </template>
                <span :data-testid="`functie-dekking-herkomst-${rij.plek}`"> · {{ dekkingLabel(dekkingVoorRij(rij)) }}</span>
              </p>
              <!-- Bediening — pas op de actieve rij (.lk-rij-acties: hover/focus, permanent op touch).
                   Alleen HANDELINGEN horen hier (weghalen). Het oordeel is een EIGENSCHAP van de
                   koppeling en wordt bediend vanaf de leeslaag-zin hierboven (LI041 — de veldnorm
                   blijft heel; geen krappe select in de strook). Wie registreert, corrigeert (ADR-050). -->
              <div v-if="magBewerken" class="lk-rij-acties pl-7 mt-0.5 flex flex-wrap gap-x-3 gap-y-0.5 text-[length:var(--lk-text-xs)]">
                <span v-for="c in dekkingVoorRij(rij).componenten" :key="c.vervulling_id" class="inline-flex items-center gap-1">
                  <span class="text-[var(--lk-color-text-muted)]">{{ c.component_naam }}:</span>
                  <button
                    type="button"
                    class="text-[var(--lk-color-danger)] hover:underline focus:outline-2 focus:outline-offset-2 focus:outline-[var(--lk-color-primary)]"
                    :data-testid="`functie-ontkoppel-${rij.plek}--${c.component_id}`"
                    :aria-label="`Koppeling van ${c.component_naam} weghalen`"
                    @click="openOntkoppel(rij, c, dekkingVoorRij(rij).herkomst)"
                  >weghalen</button>
                </span>
              </div>
            </template>
            <!-- ADR-051 gate 3 — de plek-standen die géén eigen koppeling zijn: 'niets' (bevinding),
                 'via_boven' (omhoog-cue), 'gat'. De boom LEEST de server-stand; ze beslist niets zelf.
                 Rustig — dit is werkvoorraad, geen fout; gescheiden van het amber vervallen-signaal. -->
            <p
              v-if="!(dekkingVoorRij(rij) && dekkingVoorRij(rij).componenten.length)"
              class="pl-7 text-[length:var(--lk-text-sm)]"
              :data-testid="`functie-stand-${rij.plek}`"
            >
              <template v-if="dekkingVoorRij(rij) && dekkingVoorRij(rij).herkomst === 'geen_systeem'">
                <span
                  class="rounded-[var(--lk-radius-badge)] border border-dashed border-[var(--lk-color-text-muted)] px-1.5 text-[length:var(--lk-text-xs)] font-medium text-[var(--lk-color-text)]"
                  :data-testid="`functie-stand-niets-${rij.plek}`"
                >Hiervoor wordt niets gebruikt — vastgesteld</span>
                <button
                  v-if="magBewerken"
                  type="button"
                  class="lk-rij-acties ml-2 text-[length:var(--lk-text-xs)] text-[var(--lk-color-danger)] hover:underline"
                  :data-testid="`functie-bevinding-weg-${rij.plek}`"
                  @click="openOntkoppel(rij, { vervulling_id: dekkingVoorRij(rij).bevinding_id, component_naam: 'niets' }, 'geen_systeem')"
                >weghalen</button>
              </template>
              <span
                v-else-if="standVoorRij(rij) && standVoorRij(rij).stand === 'via_boven'"
                class="text-[var(--lk-color-text-muted)]"
                :data-testid="`functie-stand-viaboven-${rij.plek}`"
              >{{ viaTekst(standVoorRij(rij)) }}</span>
              <span
                v-else-if="standVoorRij(rij) && standVoorRij(rij).stand === 'gat'"
                class="rounded-[var(--lk-radius-badge)] border border-dashed border-[var(--lk-color-text-muted)] px-1.5 text-[length:var(--lk-text-xs)] text-[var(--lk-color-text-muted)]"
                :data-testid="`functie-stand-gat-${rij.plek}`"
              >nog niet vastgelegd waarmee dit werk gedaan wordt</span>
            </p>
            <!-- LI041 — de verdringing benoemt zichzelf: op een verfijnde plek blijft het grove
                 antwoord LEESBAAR, gedempt (leeslaag, geen scanlaag) en zónder eigen actie (de
                 "weghalen"-actie woont bij de herkomst, niet hier). Rustige taal — niets kapot. -->
            <p
              v-if="dekkingVoorRij(rij) && dekkingVoorRij(rij).verdrongen.length"
              class="pl-7 text-[length:var(--lk-text-xs)] italic text-[var(--lk-color-text-muted)]"
              :data-testid="`functie-verdrongen-${rij.plek}`"
            >{{ verdrongenNamen(dekkingVoorRij(rij)) }} geldt overal, maar is hier vervangen door de verfijning</p>
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
            <!-- ADR-049 gate 2a — koppelen mag op ELKE functie (óók modelinhoud: "Toezicht"
                 koppelen is de use-case); alleen vervallen functies niet (backend 422). -->
            <Button
              v-if="magBewerken && !rij.functie.vervallen"
              label="Koppel component"
              outlined
              :data-testid="`functie-koppel-${rij.plek}`"
              :aria-label="`Koppel een component aan ${rij.functie.naam}`"
              @click="openKoppel(rij)"
            />
            <!-- ADR-051 — "hier draait geen systeem — vastgesteld": een bevinding. Alleen zinvol
                 waar nog geen koppeling/bevinding staat (stand 'gat' of 'via_boven'). -->
            <Button
              v-if="magBewerken && !rij.functie.vervallen && standVoorRij(rij) && ['gat','via_boven'].includes(standVoorRij(rij).stand)"
              label="Niets"
              outlined
              :data-testid="`functie-geen-systeem-${rij.plek}`"
              :aria-label="`Leg vast dat dit werk zonder hulpmiddel gaat`"
              @click="openGeenSysteem(rij)"
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
      <!-- Lege staat mét route naar de actie (gate 1b §2.2): de beheerder kan hier
           direct inlezen; anderen zien waar de actie wél ligt. -->
      <p v-else-if="!laden" data-testid="lijst-leeg" class="p-[var(--lk-space-md)] text-[var(--lk-color-text-muted)]">
        Er is nog geen functieboom.
        <template v-if="magInlezen">
          Lees het referentiemodel in of begin met "Nieuwe functie".
          <Button label="Referentiemodel inlezen" class="ml-[var(--lk-space-sm)]" data-testid="lijst-leeg-inlezen" @click="openInlezen" />
        </template>
        <template v-else-if="magBewerken">Begin met "Nieuwe functie", of vraag een beheerder het referentiemodel in te lezen.</template>
        <template v-else>Een beheerder leest het referentiemodel in; een medewerker kan functies toevoegen.</template>
      </p>
      <p v-else data-testid="lijst-laden" class="p-[var(--lk-space-md)] text-[var(--lk-color-text-muted)]">Laden…</p>
    </div>

    <!-- Nieuwe (deel)functie / eigen functie bewerken -->
    <Dialog v-model:visible="dialogOpen" modal :closable="false" :header="dialogFunctie ? 'Functie bewerken' : (dialogOuder ? `Nieuwe deelfunctie onder “${dialogOuder.naam}”` : 'Nieuwe functie')" data-testid="functie-dialog">
      <form class="flex min-w-[22rem] flex-col gap-[var(--lk-space-md)]" @submit.prevent="bevestig">
        <p v-if="formFout" role="alert" data-testid="functie-dialog-fout" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ formFout }}</p>
        <div class="flex flex-col gap-[var(--lk-space-xs)]">
          <label for="functie-naam" class="font-semibold">Naam *</label>
          <input id="functie-naam" v-model="form.naam" type="text" maxlength="255" data-testid="functie-form-naam" class="lk-veld" />
        </div>
        <div class="flex flex-col gap-[var(--lk-space-xs)]">
          <label for="functie-definitie" class="font-semibold">Definitie</label>
          <textarea id="functie-definitie" v-model="form.definitie" rows="3" data-testid="functie-form-definitie" class="lk-veld-tekstvlak"></textarea>
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

    <!-- ADR-049 gate 2a — Koppel een systeem: picker toont alleen werk-ondersteunende
         componenten (server-side ondersteunt_werk-filter); scope grof/fijn (alleen als de
         rij een plek heeft — een wortel valt samen op grof). Eén primary ("Koppelen"). -->
    <Dialog
      :visible="!!koppelRij"
      modal
      :closable="false"
      :header="`Waarmee wordt “${koppelRij?.functie.naam ?? ''}” gedaan?`"
      data-testid="functie-koppel-dialog"
      @update:visible="(v) => { if (!v) koppelRij = null }"
    >
      <div class="flex min-w-[26rem] max-w-xl flex-col gap-[var(--lk-space-md)]">
        <p v-if="koppelFout" role="alert" data-testid="functie-koppel-fout" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ koppelFout }}</p>
        <label class="flex flex-col gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]">
          <span>Kies waarmee dit werk gedaan wordt</span>
          <ZoekSelect
            :key="koppelKey"
            :zoek-functie="zoekKoppelComponenten"
            :weergave="koppelComponentWeergave"
            id-veld="id"
            placeholder="Zoek een component…"
            testid="functie-koppel-component"
            @keuze="kiesKoppelComponent"
          />
          <!-- Scope-regel (ADR-045 besluit 3): benoemt de scope, verklaart geen afwezigheid. -->
          <span class="text-[length:var(--lk-text-xs)] text-[var(--lk-color-text-muted)]" data-testid="functie-koppel-scoperegel">Componenten waarmee werk gedaan wordt.</span>
        </label>
        <fieldset v-if="koppelHeeftPlek" class="flex flex-col gap-[var(--lk-space-xs)]" data-testid="functie-koppel-scope">
          <label class="flex items-center gap-2 text-[length:var(--lk-text-sm)]">
            <input v-model="koppelScope" type="radio" value="overal" data-testid="functie-koppel-scope-overal" />
            <span>Geldt overal — op elke plek waar “{{ koppelRij?.functie.naam }}” staat</span>
          </label>
          <label class="flex items-center gap-2 text-[length:var(--lk-text-sm)]">
            <input v-model="koppelScope" type="radio" value="hier" data-testid="functie-koppel-scope-hier" />
            <span>Alleen hier — onder “{{ naamVanId(koppelRij?.ouderId) }}”</span>
          </label>
        </fieldset>
        <!-- ADR-051 besluit 3/4 — het oordeel bij de koppeling (optioneel; leeg = nog niet
             beoordeeld, geen sentinel). Het oordeel hoort bij de plek, niet bij het type. -->
        <fieldset class="flex flex-col gap-[var(--lk-space-xs)]" data-testid="functie-koppel-oordeel">
          <span class="text-[length:var(--lk-text-xs)] font-semibold uppercase tracking-wide text-[var(--lk-color-text-muted)]">Draagt het het werk?</span>
          <label class="flex items-center gap-2 text-[length:var(--lk-text-sm)]">
            <input v-model="koppelOordeel" type="radio" value="" data-testid="functie-koppel-oordeel-leeg" />
            <span>Weet ik nog niet — beoordeel later</span>
          </label>
          <label class="flex items-center gap-2 text-[length:var(--lk-text-sm)]">
            <input v-model="koppelOordeel" type="radio" value="naar_behoren" data-testid="functie-koppel-oordeel-naarbehoren" />
            <span>Draagt het werk naar behoren</span>
          </label>
          <label class="flex items-center gap-2 text-[length:var(--lk-text-sm)]">
            <input v-model="koppelOordeel" type="radio" value="noodoplossing" data-testid="functie-koppel-oordeel-noodoplossing" />
            <span>Noodoplossing — draagt het werk niet volwaardig</span>
          </label>
        </fieldset>
        <p v-if="koppelZin" data-testid="functie-koppel-zin" class="max-w-prose font-medium">{{ koppelZin }}</p>
        <div class="flex gap-[var(--lk-space-md)]">
          <Button type="button" label="Koppelen" data-testid="functie-koppel-bevestig" :disabled="!koppelComponent || koppelBezig" @click="bevestigKoppel" />
          <Button type="button" label="Annuleren" severity="secondary" @click="koppelRij = null" />
        </div>
      </div>
    </Dialog>

    <!-- ADR-051 — "hiervoor wordt niets gebruikt — vastgesteld": een BEVINDING, geen vernietiging.
         Bewust GÉÉN BevestigVerwijderDialog (die heeft een rode danger-knop) — een neutrale dialoog
         met een gewone (primary) bevestig-knop, zodat het interessantste feit van de workshop niet
         als een gevaar oogt. -->
    <Dialog
      :visible="!!geenSysteemRij"
      modal
      :closable="false"
      header="Hiervoor wordt niets gebruikt"
      data-testid="functie-geen-systeem-dialog"
      @update:visible="(v) => { if (!v) geenSysteemRij = null }"
    >
      <div class="flex min-w-[24rem] max-w-prose flex-col gap-[var(--lk-space-md)]">
        <span v-if="geenSysteemFout" role="alert" data-testid="functie-geen-systeem-fout" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ geenSysteemFout }}</span>
        <p v-else data-testid="functie-geen-systeem-zin">{{ geenSysteemZin }}</p>
        <div class="flex gap-[var(--lk-space-md)]">
          <Button type="button" label="Vastleggen" data-testid="functie-geen-systeem-bevestig" :disabled="geenSysteemBezig" @click="bevestigGeenSysteem" />
          <Button type="button" label="Annuleren" severity="secondary" @click="geenSysteemRij = null" />
        </div>
      </div>
    </Dialog>

    <!-- ADR-051/LI041 — het oordeel over een koppeling, bediend vanaf de leeslaag-zin op VOLLE
         grootte (geen krappe select — de veldnorm blijft heel). Drie gelijkwaardige keuzes;
         "weet ik nog niet" wist het oordeel terug naar leeg. Registratie-feit → medewerker (ADR-050). -->
    <Dialog
      :visible="!!oordeelDoel"
      modal
      :closable="false"
      :header="oordeelDoel ? `Hoe draagt ${oordeelDoel.comp.component_naam} dit werk?` : ''"
      data-testid="functie-oordeel-dialog"
      @update:visible="(v) => { if (!v) oordeelDoel = null }"
    >
      <div v-if="oordeelDoel" class="flex min-w-[22rem] max-w-prose flex-col gap-[var(--lk-space-sm)]">
        <p class="text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]" data-testid="functie-oordeel-context">
          Voor "{{ oordeelDoel.functie_naam }}".
        </p>
        <Button type="button" label="Draagt het werk naar behoren" severity="secondary" data-testid="functie-oordeel-kies-naar_behoren" @click="kiesOordeel('naar_behoren')" />
        <Button type="button" label="Noodoplossing — draagt het werk niet volwaardig" severity="secondary" data-testid="functie-oordeel-kies-noodoplossing" @click="kiesOordeel('noodoplossing')" />
        <Button type="button" label="Weet ik nog niet — beoordeel later" severity="secondary" data-testid="functie-oordeel-kies-leeg" @click="kiesOordeel('')" />
        <Button type="button" label="Annuleren" severity="text" class="mt-[var(--lk-space-sm)]" @click="oordeelDoel = null" />
      </div>
    </Dialog>

    <!-- ADR-049 gate 2a — koppeling weghalen (beheerder): gedeelde bevestigingsdialoog met de
         regel leesbaar; een fijne weghalen maakt het grove antwoord op die plek weer leesbaar. -->
    <BevestigVerwijderDialog
      :visible="!!ontkoppelDoel"
      kop="Koppeling weghalen"
      bevestig-label="Weghalen"
      :bezig="ontkoppelBezig"
      testid="functie-ontkoppel"
      @update:visible="(v) => { if (!v) ontkoppelDoel = null }"
      @bevestig="bevestigOntkoppel"
    >
      <span v-if="ontkoppelFout" data-testid="functie-ontkoppel-fout" class="text-[var(--lk-color-warning)]">{{ ontkoppelFout }}</span>
      <span v-else data-testid="functie-ontkoppel-zin">{{ ontkoppelZin }}</span>
    </BevestigVerwijderDialog>

    <!-- Gate 1b — referentiemodel inlezen: VOORBEELD vóór bevestigen (dialog-overlay
         met expliciete bevestig-knop; het resultaat als tweede dialog-staat). -->
    <Dialog
      v-model:visible="inleesOpen"
      modal
      :closable="false"
      header="Referentiemodel inlezen"
      data-testid="inlees-dialog"
    >
      <div class="flex min-w-[26rem] max-w-xl flex-col gap-[var(--lk-space-md)]" :aria-busy="inleesBezig">

        <!-- Staat 3 — resultaat (na bevestigen): wat er is gebeurd, leesbaar. -->
        <template v-if="inleesResultaat">
          <p data-testid="inlees-resultaat" class="max-w-prose font-medium">
            Het model "{{ inleesResultaat.model.naam }}" ({{ inleesResultaat.model.versie }}) is ingelezen.
          </p>
          <ul class="list-disc pl-[var(--lk-space-lg)] text-[length:var(--lk-text-sm)]">
            <li v-if="inleesResultaat.nieuw.length">{{ inleesResultaat.nieuw.length }} functies toegevoegd</li>
            <li v-if="inleesResultaat.bijgewerkt.length">{{ inleesResultaat.bijgewerkt.length }} functies bijgewerkt</li>
            <li v-if="inleesResultaat.vervallen.length">{{ inleesResultaat.vervallen.length }} functies vervallen gemarkeerd</li>
            <li v-if="!inleesResultaat.nieuw.length && !inleesResultaat.bijgewerkt.length && !inleesResultaat.vervallen.length">geen wijzigingen — het model was al actueel</li>
          </ul>
          <div class="flex gap-[var(--lk-space-md)]">
            <Button type="button" label="Klaar" data-testid="inlees-klaar" @click="inleesOpen = false" />
          </div>
        </template>

        <!-- Staat 2 — bezig: expliciete indicatie (het inlezen kan tientallen seconden duren). -->
        <template v-else-if="inleesBezig">
          <p data-testid="inlees-bezig" role="status" class="max-w-prose">
            Het model wordt ingelezen — dit kan een halve minuut duren. Sluit dit venster niet.
          </p>
        </template>

        <!-- Staat 1 — kiezen + voorbeeld (dry-run) vóór bevestigen. De aanbod-staat
             vertakt EXCLUSIEF op het ene `aanbodStaat`-enum (B2): 'fout' (aanroep
             faalde → rood) en 'leeg' (aanroep slaagde, niets beschikbaar → rustig)
             kunnen elkaar structureel niet overlappen. -->
        <template v-else>
          <p v-if="aanbodStaat === 'laden'" data-testid="inlees-aanbod-laden" class="text-[var(--lk-color-text-muted)]">Aanbod laden…</p>

          <!-- Aanroep FAALDE — er is echt iets kapot: rood. -->
          <template v-else-if="aanbodStaat === 'fout'">
            <MeldingBanner soort="danger" tekst="Het aanbod kon niet geladen worden. Probeer het later opnieuw." testid="inlees-fout" />
            <div class="flex gap-[var(--lk-space-md)]">
              <Button type="button" label="Sluiten" severity="secondary" data-testid="inlees-sluiten" @click="inleesOpen = false" />
            </div>
          </template>

          <!-- Aanroep SLAAGDE, aanbod leeg — een toestand, geen fout: rustig. -->
          <template v-else-if="aanbodStaat === 'leeg'">
            <p data-testid="inlees-geen-aanbod" class="max-w-prose text-[var(--lk-color-text-muted)]">
              Er zijn nog geen referentiemodellen beschikbaar. Modellen worden door de
              platformbeheerder aangeboden en komen mee met een release van LIKARA.
            </p>
            <div class="flex gap-[var(--lk-space-md)]">
              <Button type="button" label="Sluiten" severity="secondary" data-testid="inlees-sluiten" @click="inleesOpen = false" />
            </div>
          </template>

          <!-- Aanbod gevuld ('ok'): kiezen → voorbeeld → bevestigen. -->
          <template v-else>
            <MeldingBanner v-if="inleesFout" soort="danger" :tekst="inleesFout" testid="inlees-fout" />
            <MeldingBanner
              v-if="inleesOnvoltooid"
              soort="warn"
              tekst="De vorige inlees is niet afgerond — het model is mogelijk onvolledig. Inlezen maakt hem af."
              testid="inlees-onvoltooid-melding"
            />
            <p v-if="inleesLaden" data-testid="inlees-laden" class="text-[var(--lk-color-text-muted)]">Voorbeeld berekenen…</p>

            <!-- Meerdere modellen in het aanbod: eerst kiezen (MVP-aanbod = één → auto). -->
            <ul v-if="!inleesModel && inleesModellen.length > 1" class="flex flex-col gap-[var(--lk-space-xs)]" data-testid="inlees-modellen">
              <li v-for="m in inleesModellen" :key="m.model_sleutel">
                <Button :label="`${m.label} — ${m.versie}`" severity="secondary" :data-testid="`inlees-kies-${m.model_sleutel}`" @click="kiesInleesModel(m)" />
              </li>
            </ul>
            <div v-if="!inleesModel" class="flex gap-[var(--lk-space-md)]">
              <Button type="button" label="Sluiten" severity="secondary" data-testid="inlees-sluiten" @click="inleesOpen = false" />
            </div>

            <template v-if="inleesModel">
            <div class="text-[length:var(--lk-text-sm)]">
              <p class="font-semibold">{{ inleesModel.label }} — {{ inleesModel.versie }}</p>
              <p class="mt-1 max-w-prose text-[length:var(--lk-text-xs)] text-[var(--lk-color-text-muted)]" data-testid="inlees-herkomst">{{ inleesModel.herkomst }}</p>
              <p v-if="inleesModel.ingelezen" class="mt-1 text-[length:var(--lk-text-xs)] text-[var(--lk-color-text-muted)]" data-testid="inlees-eerder">
                Eerder ingelezen; dit is een herinlees — bestaande registratie blijft staan.
              </p>
            </div>

            <template v-if="inleesVoorbeeld">
              <p data-testid="inlees-voorbeeld" class="max-w-prose font-medium">{{ inleesVoorbeeldZin }}</p>
              <!-- De werklijst: vervallen functies bij naam (alleen bij een herinlees). -->
              <ul v-if="inleesVoorbeeld.vervallen.length" data-testid="inlees-vervallen-lijst" class="list-disc pl-[var(--lk-space-lg)] text-[length:var(--lk-text-sm)]">
                <li v-for="f in inleesVoorbeeld.vervallen" :key="f.naam">
                  {{ f.naam }}<span v-if="f.in_gebruik" class="text-[var(--lk-color-warning)]"> — nog in gebruik</span>
                </li>
              </ul>
              <p class="max-w-prose text-[length:var(--lk-text-xs)] text-[var(--lk-color-text-muted)]">
                Er verandert pas iets na je bevestiging.
              </p>
            </template>

            <div class="flex gap-[var(--lk-space-md)]">
              <Button
                type="button"
                label="Inlezen"
                data-testid="inlees-bevestig"
                :disabled="!inleesVoorbeeld || (inleesGeenWijzigingen && !inleesOnvoltooid) || inleesLaden"
                :title="inleesGeenWijzigingen && !inleesOnvoltooid ? 'Het model is al actueel.' : undefined"
                @click="bevestigInlezen"
              />
              <Button type="button" label="Annuleren" severity="secondary" data-testid="inlees-annuleer" @click="inleesOpen = false" />
            </div>
            </template>
          </template>
        </template>
      </div>
    </Dialog>
  </section>
</template>
