<script setup>
/**
 * BedrijfsfunctieLijst — de bedrijfsfunctieboom (ADR-043 gate 1a, blok 2).
 *
 * De logische ruggengraat van de kaart als Boom | Diagram (het processen-scherm-recept;
 * Boom = beheren, Diagram = begrijpen/navigeren). Boom-structuur uit de gedeelde pure
 * module `procesBoomStructuur` (structuur-generiek — LI039-feitenrapport); het Diagram is
 * de gegeneraliseerde `ProcesDiagram`-bouwsteen met functie-taal (géén tweede kopie).
 *
 * ADR-043-regels, gespiegeld op de backend (de picker-/affordance-regel: toon nooit een
 * knop die bij opslaan een 422 geeft — de service blijft de handhaver):
 * - MODELINHOUD (functie mét bronsleutel): naam/definitie/plek read-only — géén
 *   bewerk-/verplaats-/verwijder-affordance; rustige herkomstvermelding "uit [model],
 *   versie X".
 * - EIGEN functie (geen bronsleutel): volledig bewerkbaar; toevoegen mag onder elke
 *   niet-vervallen functie én als wortel.
 * - VERVALLEN (besluit LI039-6): zichtbaar mét rustige markering (eerlijkheids-cue-taal),
 *   niet koppelbaar — geen "+ Deelfunctie" eronder.
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
import { procesBoomStructuur } from '../procesBoom'
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
const openTakken = ref([]) // ids van uitgeklapte functies (array → serialiseerbare lijststaat)
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
  toonRij(item.id)
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
    // Herstelde open-takken die niet (meer) bestaan stil laten vallen.
    const bekend = new Set(items.map((f) => f.id))
    openTakken.value = openTakken.value.filter((id) => bekend.has(id))
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
const _byId = computed(() => new Map(alle.value.map((f) => [f.id, f])))
const boom = computed(() => procesBoomStructuur(
  new Set(alle.value.map((f) => f.id)),
  alle.value.filter((f) => f.ouder_id).map((f) => ({ bron: f.id, doel: f.ouder_id })),
  (id) => _byId.value.get(id)?.naam || String(id),
))

const _matcht = (f) => f.naam.toLowerCase().includes(zoekterm.value.trim().toLowerCase())
// Bij een actieve zoekterm: toon de paden naar de treffers, opengeklapt (zoeken klapt open).
const matchOfNazaatMatcht = computed(() => {
  const term = zoekterm.value.trim()
  const set = new Set()
  if (!term) return set
  const heeftMatchIn = (id) => {
    let raak = false
    for (const kindId of boom.value.kinderenVan.get(id) || []) {
      const kind = _byId.value.get(kindId)
      if (heeftMatchIn(kindId) || (kind && _matcht(kind))) raak = true
    }
    if (raak) set.add(id)
    return raak
  }
  for (const wortelId of boom.value.wortels) {
    const wortel = _byId.value.get(wortelId)
    if (heeftMatchIn(wortelId) || (wortel && _matcht(wortel))) set.add(wortelId)
  }
  return set
})

function isOpen(id) {
  if (zoekterm.value.trim()) return matchOfNazaatMatcht.value.has(id)
  return openTakken.value.includes(id)
}
function toggle(id) {
  if (openTakken.value.includes(id)) openTakken.value = openTakken.value.filter((x) => x !== id)
  else openTakken.value = [...openTakken.value, id]
}

// Platte, zichtbare rijen + het tree-connector-lijnen-model (het LI037-recept van
// ProcesLijst 1-op-1 — wortels zaaien een lege prefix; `laatste` sluit af met └).
const rijen = computed(() => {
  const term = zoekterm.value.trim()
  const { wortels, kinderenVan } = boom.value
  const uit = []
  const zichtbare = (ids) => ids
    .map((id) => _byId.value.get(id))
    .filter(Boolean)
    .filter((f) => !term || _matcht(f) || matchOfNazaatMatcht.value.has(f.id))
  const loop = (ids, diepte, lijnen) => {
    const zichtbaar = zichtbare(ids)
    zichtbaar.forEach((f, i) => {
      const laatste = i === zichtbaar.length - 1
      const kids = kinderenVan.get(f.id) || []
      const heeftKinderen = kids.length > 0
      const open = heeftKinderen && isOpen(f.id)
      uit.push({ functie: f, diepte, heeftKinderen, open, laatste, lijnen })
      if (open) loop(kids, diepte + 1, diepte === 0 ? [] : [...lijnen, !laatste])
    })
  }
  loop(wortels, 0, [])
  return uit
})

const lijnX = (niveau) => `calc(var(--lk-space-md) + ${niveau * 1.5}rem + 0.625rem)`

// Vervallen-set — voedt de vervallen-markering in het Diagram via het EIGEN
// `vervallenIds`-kanaal (LI039 blok C; het `gapIds`-kanaal blijft vrij voor de echte
// gap-cue in gate 3 — beide toestanden kunnen straks tegelijk gelden).
const vervallenIds = computed(() => new Set(alle.value.filter((f) => f.vervallen).map((f) => f.id)))

// LI039 blok B — "wat je zojuist hebt vastgelegd, zie je altijd" (gedeelde bouwsteen;
// aanmaken én verplaatsen): pad openklappen + korte aanstip + zoekterm wijkt zichtbaar.
const { aangestiptId, wijkMelding, toonRij } = useToonInBoom({
  openTakken,
  zoekterm,
  matcht: (id) => {
    const f = _byId.value.get(String(id))
    return !!f && _matcht(f)
  },
  ouderVan: (id) => {
    const o = _byId.value.get(String(id))?.ouder_id
    return o == null ? null : String(o)
  },
  wijkTekst: 'Zoekterm opzij gezet om je nieuwe functie te tonen.',
})

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
    if (nieuwId != null) toonRij(nieuwId)
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
    openTakken.value = openTakken.value.filter((id) => id !== f.id)
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

// ── Verplaatsen (alleen eigen functies; doelen = geen subboom, geen vervallen functie) ──
const verplaatsFunctie = ref(null)
const verplaatsDoel = ref(null) // { type: 'geen' } of { type: 'functie', id, naam }
const verplaatsFout = ref(null)
const verplaatsBezig = ref(false)
const verplaatsKey = ref(0) // remount-sleutel per opening (stale-label-les LI032)
function openVerplaats(f) {
  verplaatsFunctie.value = f
  verplaatsDoel.value = null
  verplaatsFout.value = null
  verplaatsKey.value += 1
}
const verplaatsKinderen = computed(() =>
  (verplaatsFunctie.value ? subboomIds(verplaatsFunctie.value.id).size - 1 : 0))
// Geldige doelen: geen subboom (kring-preventie vóóraf) en geen vervallen functie (de
// backend weigert VERVALLEN_NIET_KOPPELBAAR — de picker spiegelt dat, LI032-regel 1).
async function zoekVerplaatsDoelen(params = {}) {
  const f = verplaatsFunctie.value
  if (!f) return { items: [], volgende_cursor: null }
  const verboden = subboomIds(f.id)
  const term = (params.zoek || '').trim().toLowerCase()
  const items = alle.value
    .filter((x) => !verboden.has(x.id) && !x.vervallen)
    .filter((x) => !term || x.naam.toLowerCase().includes(term))
    .map((x) => ({ ...x, ouder_naam: x.ouder_id ? (_byId.value.get(x.ouder_id)?.naam ?? null) : null }))
    .sort((a, b) => a.naam.localeCompare(b.naam, 'nl'))
  return { items, volgende_cursor: null }
}
const doelWeergave = (x) => (x?.ouder_naam ? `${x.naam} — ${x.ouder_naam}` : (x?.naam ?? ''))
function kiesVerplaatsDoel(item) {
  if (item?.id) verplaatsDoel.value = { type: 'functie', id: item.id, naam: item.naam }
  verplaatsFout.value = null
}
function kiesWortel() {
  verplaatsDoel.value = { type: 'geen' }
  verplaatsFout.value = null
}
const verplaatsZin = computed(() => {
  const f = verplaatsFunctie.value
  const d = verplaatsDoel.value
  if (!f || !d) return ''
  const n = verplaatsKinderen.value
  const mee = n > 0 ? ` en ${n} onderliggende functie${n === 1 ? '' : 's'}` : ''
  return d.type === 'geen'
    ? `Verplaats "${f.naam}"${mee} naar het hoogste niveau?`
    : `Verplaats "${f.naam}"${mee} naar "${d.naam}"?`
})
async function bevestigVerplaats() {
  const f = verplaatsFunctie.value
  const d = verplaatsDoel.value
  if (!f || !d) return
  verplaatsBezig.value = true
  verplaatsFout.value = null
  try {
    const doelId = d.type === 'geen' ? null : d.id
    await api.bedrijfsfuncties.werkBij(f.id, { ouder_id: doelId })
    toastSucces(toast, 'Verplaatst')
    verplaatsFunctie.value = null
    alle.value = alle.value.map((x) => (x.id === f.id ? { ...x, ouder_id: doelId } : x))
    // LI039 blok B — zelfde bouwsteen als bij aanmaken: de verhuisde rij is altijd
    // zichtbaar (nieuwe ouderketen open + aanstip + zoekterm wijkt zichtbaar).
    toonRij(f.id)
  } catch (e) {
    if (e?.status !== 401) verplaatsFout.value = e?.message || 'Verplaatsen is mislukt.'
  } finally {
    verplaatsBezig.value = false
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
          :key="rij.functie.id"
          :class="[
            'lk-rij relative flex items-center gap-[var(--lk-space-sm)] px-[var(--lk-space-md)] py-[var(--lk-space-sm)]',
            rij.functie.id === aangestiptId ? 'lk-aangestipt' : '',
            // LI039 blok C — vervallen: rustige waarschuwingstint over de hele rij
            // (kleur + icoon + tekst samen; zie de badge hieronder).
            rij.functie.vervallen ? 'bg-[color-mix(in_srgb,var(--lk-color-warning)_8%,transparent)]' : '',
          ]"
          :data-testid="`functie-rij-${rij.functie.id}`"
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
              :data-testid="`functie-lijn-${rij.functie.id}`"
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
              <button
                v-if="rij.heeftKinderen"
                type="button"
                :aria-expanded="rij.open"
                :aria-label="`${rij.open ? 'Klap in' : 'Klap uit'}: ${rij.functie.naam}`"
                :data-testid="`functie-toggle-${rij.functie.id}`"
                class="relative w-5 shrink-0 bg-[var(--lk-color-surface)] text-[var(--lk-color-text-muted)] hover:text-[var(--lk-color-primary)] focus:outline-2 focus:outline-offset-2 focus:outline-[var(--lk-color-primary)]"
                @click="toggle(rij.functie.id)"
              >{{ rij.open ? '▾' : '▸' }}</button>
              <span v-else class="w-5 shrink-0" aria-hidden="true"></span>
              <span class="min-w-0 font-medium text-[var(--lk-color-text)]" data-testid="functie-naam">{{ rij.functie.naam }}</span>
              <!-- Alleen wat afwijkt op de rij: "eigen" (eigenschap — gedempt randje, geen
                   knop-familie) en de vervallen-markering (LI039 blok C: warning-taal,
                   kleur + ⚠ + tekst; solid rand — gestippeld blijft van de gap-familie;
                   de gate-2-telling past er later in de tekst bij). -->
              <span
                v-if="isEigen(rij.functie)"
                :data-testid="`functie-eigen-${rij.functie.id}`"
                class="shrink-0 rounded-[var(--lk-radius-badge)] border border-[var(--lk-color-border)] px-1.5 text-[length:var(--lk-text-xs)] text-[var(--lk-color-text-muted)]"
              >eigen</span>
              <span
                v-if="rij.functie.vervallen"
                :data-testid="`functie-vervallen-${rij.functie.id}`"
                class="flex shrink-0 items-center gap-1 rounded-[var(--lk-radius-badge)] border border-[var(--lk-color-warning)] px-1.5 text-[length:var(--lk-text-xs)] text-[var(--lk-color-warning)]"
              ><span aria-hidden="true">⚠</span><span>vervallen in het referentiemodel</span></span>
            </div>
            <p
              v-if="rij.functie.definitie"
              class="lk-rij-definitie pl-7 text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]"
              :data-testid="`functie-definitie-${rij.functie.id}`"
            >{{ rij.functie.definitie }}</p>
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
              :data-testid="`functie-diagram-${rij.functie.id}`"
              :aria-label="`Toon ${rij.functie.naam} in het functiebeeld`"
              @click="toonInFunctiebeeld(rij.functie)"
            />
            <Button
              v-if="magBewerken && !rij.functie.vervallen"
              label="+ Deelfunctie"
              outlined
              :data-testid="`functie-deelfunctie-${rij.functie.id}`"
              :aria-label="`Nieuwe deelfunctie onder ${rij.functie.naam}`"
              @click="openNieuw(rij.functie)"
            />
            <Button
              v-if="magBewerken && isEigen(rij.functie)"
              label="Bewerken"
              outlined
              :data-testid="`functie-bewerk-${rij.functie.id}`"
              :aria-label="`Bewerk ${rij.functie.naam}`"
              @click="openBewerk(rij.functie)"
            />
            <Button
              v-if="magBewerken && isEigen(rij.functie)"
              label="Verplaats naar…"
              outlined
              :data-testid="`functie-verplaats-${rij.functie.id}`"
              :aria-label="`Verplaats ${rij.functie.naam}`"
              @click="openVerplaats(rij.functie)"
            />
            <Button
              v-if="magVerwijderen && isEigen(rij.functie)"
              label="Verwijderen"
              severity="danger"
              :data-testid="`functie-verwijder-${rij.functie.id}`"
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

    <!-- Verplaatsen (eigen functies): picker zonder ongeldige doelen (subboom + vervallen
         eruit — kring- en VERVALLEN-preventie vóóraf) + "Geen (hoogste niveau)". -->
    <Dialog :visible="!!verplaatsFunctie" modal :closable="false" :header="`Verplaats “${verplaatsFunctie?.naam ?? ''}”`" data-testid="functie-verplaats-dialog" @update:visible="(v) => { if (!v) verplaatsFunctie = null }">
      <div class="flex min-w-[24rem] flex-col gap-[var(--lk-space-md)]">
        <p v-if="verplaatsFout" role="alert" data-testid="functie-verplaats-fout" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ verplaatsFout }}</p>
        <button
          type="button"
          data-testid="functie-verplaats-geen"
          :disabled="!verplaatsFunctie?.ouder_id"
          :title="verplaatsFunctie?.ouder_id ? '' : 'Deze functie staat al op het hoogste niveau'"
          :class="['rounded-[var(--lk-radius-btn)] border px-[var(--lk-space-md)] py-[var(--lk-space-xs)] text-left text-[length:var(--lk-text-sm)] disabled:cursor-not-allowed disabled:opacity-50',
                   verplaatsDoel?.type === 'geen' ? 'border-[var(--lk-color-primary)] bg-[var(--lk-color-accent)] font-semibold' : 'border-[var(--lk-color-border)] hover:bg-[var(--lk-color-accent)]']"
          @click="kiesWortel"
        >Geen (hoogste niveau)</button>
        <label class="flex flex-col gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]">
          <span>Of kies een nieuwe ouder</span>
          <ZoekSelect
            :key="verplaatsKey"
            :zoek-functie="zoekVerplaatsDoelen"
            :weergave="doelWeergave"
            id-veld="id"
            placeholder="Zoek functie…"
            testid="functie-verplaats-doel"
            @keuze="kiesVerplaatsDoel"
          />
        </label>
        <p v-if="verplaatsZin" data-testid="functie-verplaats-zin" class="max-w-prose font-medium">{{ verplaatsZin }}</p>
        <div class="flex gap-[var(--lk-space-md)]">
          <Button type="button" label="Verplaatsen" data-testid="functie-verplaats-bevestig" :disabled="!verplaatsDoel || verplaatsBezig" @click="bevestigVerplaats" />
          <Button type="button" label="Annuleren" severity="secondary" @click="verplaatsFunctie = null" />
        </div>
      </div>
    </Dialog>
  </section>
</template>
