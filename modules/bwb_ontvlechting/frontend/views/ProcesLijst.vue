<script setup>
/**
 * ProcesLijst — het procesregister als boom (ADR-042 slice 4a).
 *
 * Boomweergave: hoofdprocessen als regels, uitklapbaar naar deelprocessen (de plek in de
 * boom ís het niveau — geen niveau-label). De volledige (begrensde, organisatie-eigen)
 * processet wordt in pagina's opgehaald en client-side als boom gerenderd; zoeken filtert
 * soepel (partieel, hoofdletter-ongevoelig — zoekveld-norm) en klapt de paden naar de
 * treffers open. Aanmaken (top-level) + hernoemen gebeuren hier; deelprocessen maak je op
 * de proces-pagina (context voorgevuld — actie waar het onderwerp leeft).
 *
 * Lijststaat (useLijstStaat, lk-state-patroon): zoekterm + uitgeklapte takken overleven
 * een detailbezoek-en-terug én F5.
 */
import { computed, onMounted, reactive, ref } from 'vue'
import { Button, Dialog, useToast } from '@/primevue'
import { toastSucces } from '@/meldingen'
import { useAuthStore } from '@/store/auth'
import { useRouter } from '@/composables/router'
import { useLijstStaat } from '@/composables/useLijstStaat'
import { useToonInBoom } from '@/composables/useToonNieuweRij'
import { zetKaartHandoff } from '@/composables/kaartHandoff'
import { api } from '@/api'
import BevestigVerwijderDialog from '@/components/BevestigVerwijderDialog.vue'
import MeldingBanner from '@/components/MeldingBanner.vue'
import RijActies from '@/components/RijActies.vue'
import { procesBoomStructuur } from '../procesBoom'
import { bouwProcesKaartHandoff } from '../procesKaartIngang'
import ProcesDiagram from './ProcesDiagram.vue'
import VeldUitleg from './VeldUitleg.vue'
import ZoekSelect from './ZoekSelect.vue'

const auth = useAuthStore()
const toast = useToast()
const magBewerken = computed(() => auth.hasRole('medewerker', 'beheerder'))
// LI037 — verwijderen = het VERWIJDEREN-recht (beheerder-only per de RBAC-matrix; het endpoint
// eist PROCES.VERWIJDEREN). Vooraf weren i.p.v. een 403 pas in de dialoog — het bestaande
// detailscherm-patroon. Aanmaken/hernoemen/verhangen blijven op Wijzigen (magBewerken).
const magVerwijderen = computed(() => auth.hasRole('beheerder'))

const alle = ref([]) // platte set (alle pagina's); de boom is een client-side afgeleide
const laden = ref(false)
const fout = ref(null)

const zoekterm = ref('')
const openTakken = ref([]) // ids van uitgeklapte processen (array → serialiseerbare lijststaat)
// LI038 gate 1 — tweede weergave: 'boom' (register-tree) | 'diagram' (proces-only structuurbeeld).
const weergave = ref('boom')
// LI038 gate 3 — "Toon in procesbeeld" (rij-actie): het proces dat het Diagram bij openen als
// centrum krijgt (neutraal, oranje — geen inperking). Momentkeuze: bewust NIET in de lijststaat.
const diagramStart = ref(null)
function toonInProcesbeeld(p) {
  if (!p?.id) return
  diagramStart.value = p.id
  weergave.value = 'diagram' // in-place wissel; de Boom-staat blijft bewaard (lijststaat)
}

// Lijststaat behouden bij terugnavigeren/F5 (lk-state-patroon; zie useLijstStaat).
const _tekst = (w) => typeof w === 'string'
const { herstel: herstelLijstStaat } = useLijstStaat(
  'proces-lijst',
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
    // Alle pagina's ophalen (processen zijn een begrensd organisatie-vocabulaire; de
    // boom heeft de volledige set nodig om ouder→kind te kunnen leggen).
    const items = []
    let after
    do {
      const pagina = await api.processen.lijst({ limit: 100, after })
      items.push(...pagina.items)
      after = pagina.volgende_cursor
    } while (after)
    alle.value = items
    // Herstelde open-takken die niet (meer) bestaan stil laten vallen.
    const bekend = new Set(items.map((p) => p.id))
    openTakken.value = openTakken.value.filter((id) => bekend.has(id))
    laadGapCue() // LI037 — bewust niet ge-await: de cue laadt progressief ná de boom-render
  } catch (e) {
    fout.value = e?.status === 401 ? null : 'Laden van de processen is mislukt.'
  } finally {
    laden.value = false
  }
}

// LI037 tree-view gate 1 — de boom-STRUCTUUR komt uit de gedeelde pure module (procesBoom.js:
// zelfde opbouw/sortering/guards als de kaart-proceszone; geen derde boom-opbouw ernaast).
// Alleen de rendering (rijen + verbindingslijnen) is schermspecifiek.
const _byId = computed(() => new Map(alle.value.map((p) => [p.id, p])))
const boom = computed(() => procesBoomStructuur(
  new Set(alle.value.map((p) => p.id)),
  alle.value.filter((p) => p.ouder_id).map((p) => ({ bron: p.id, doel: p.ouder_id })),
  (id) => _byId.value.get(id)?.naam || String(id),
))

const _matcht = (p) => p.naam.toLowerCase().includes(zoekterm.value.trim().toLowerCase())
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

// Platte, zichtbare rijen (diepte-eerst over de boom; respecteert open-state en zoekterm).
// LI037 — per rij ook het lijnen-model voor de tree-connectoren: `lijnen[i]` = de VOOROUDER OP
// DIEPTE i+1 heeft nog zichtbare broers onder zich → op kolom i (exact de elleboog-kolom van
// díe voorouder) loopt de verticale lijn hier dóór; `laatste` = laatste zichtbare kind (sluit
// de verticale lijn af met een elleboog └, anders ├).
// Gate 1c — WORTELS zaaien een LEGE prefix (bomen zijn onafhankelijk; wortels dragen geen
// connector-kolom). De vroegere `[!wortel.laatste]`-seed schoof álle guides één kolom op:
// het doorloop-spoor rendeerde op de elleboog-kolom (T-stuk-look op laatste kinderen) en de
// échte doorloop-kolom bleef leeg (de gaten in de verticale lijnen).
const rijen = computed(() => {
  const term = zoekterm.value.trim()
  const { wortels, kinderenVan } = boom.value
  const uit = []
  const zichtbare = (ids) => ids
    .map((id) => _byId.value.get(id))
    .filter(Boolean)
    .filter((p) => !term || _matcht(p) || matchOfNazaatMatcht.value.has(p.id))
  const loop = (ids, diepte, lijnen) => {
    const zichtbaar = zichtbare(ids)
    zichtbaar.forEach((p, i) => {
      const laatste = i === zichtbaar.length - 1
      const kids = kinderenVan.get(p.id) || []
      const heeftKinderen = kids.length > 0
      const open = heeftKinderen && isOpen(p.id)
      uit.push({ proces: p, diepte, heeftKinderen, open, laatste, lijnen })
      // Dezelfde `laatste`-bron als de elleboog hierboven — geen aparte berekening.
      if (open) loop(kids, diepte + 1, diepte === 0 ? [] : [...lijnen, !laatste])
    })
  }
  loop(wortels, 0, [])
  return uit
})

// Lijn-x per inspring-niveau: het midden onder de ▸/▾-kolom van dat niveau (inspring-stap 1.5rem,
// toggle-kolom w-5 → midden op 0.625rem). Gedeeld door guides, ellebogen en de omlaag-stub.
const lijnX = (niveau) => `calc(var(--lk-space-md) + ${niveau * 1.5}rem + 0.625rem)`

// LI039 blok B — "wat je zojuist hebt vastgelegd, zie je altijd" (gedeelde bouwsteen,
// zelfde als het bedrijfsfuncties-scherm; aanmaken én verplaatsen): pad openklappen +
// korte aanstip + een verbergende zoekterm wijkt zichtbaar.
const { aangestiptId, wijkMelding, toonRij } = useToonInBoom({
  openTakken,
  zoekterm,
  matcht: (id) => {
    const p = _byId.value.get(String(id))
    return !!p && _matcht(p)
  },
  ouderVan: (id) => {
    const o = _byId.value.get(String(id))?.ouder_id
    return o == null ? null : String(o)
  },
  wijkTekst: 'Zoekterm opzij gezet om je nieuwe proces te tonen.',
})

// ── LI037 — "geen ondersteunend systeem"-cue (zelfde subboom-semantiek + leespaden als de
// kaart-gap-cue: per wortel rollup (doorgerolde subboom-regels) + de wortel-eigen regels; een
// vervulling dekt óók de voorouders — één roll-up-bron, geen nieuwe definitie). PROGRESSIEF:
// de boom rendert direct; de cue verschijnt zodra de afleiding binnen is (2 calls per wortel,
// parallel — geen N+1 per rij, en de lijst-render blokkeert er niet op).
const gapIds = ref(null) // null = (nog) niet geladen → geen cue; Set = geladen
async function laadGapCue() {
  try {
    const { wortels, ouderVan } = boom.value
    const per = await Promise.all(wortels.map(async (w) => {
      const [rollup, eigen] = await Promise.all([
        api.processen.rollup(w),
        api.procesvervullingen.lijst({ proces_id: w }),
      ])
      const vervuld = (rollup || []).map((r) => String(r.proces_id))
      if ((eigen || []).length) vervuld.push(String(w))
      return vervuld
    }))
    const gedekt = new Set()
    for (const vervuld of per) {
      for (const startId of vervuld) {
        let cur = startId
        while (cur != null && !gedekt.has(cur)) { // cyclus-veilig (gedekt-guard)
          gedekt.add(cur)
          cur = boom.value.ouderVan.get(cur)
        }
      }
    }
    gapIds.value = new Set(alle.value.map((p) => p.id).filter((id) => !gedekt.has(id)))
  } catch {
    gapIds.value = null // cue is verrijking — een faal blokkeert of vervuilt de lijst niet
  }
}
const isGap = (id) => !!gapIds.value?.has(id)

// ── Aanmaken (top-level) + hernoemen ─────────────────────────────────────────
const dialogOpen = ref(false)
const dialogProces = ref(null) // null = nieuw top-level proces; anders hernoemen
const form = reactive({ naam: '', toelichting: '' })
const formFout = ref(null)
const bezig = ref(false)

function openNieuw() {
  dialogProces.value = null
  Object.assign(form, { naam: '', toelichting: '' })
  formFout.value = null
  dialogOpen.value = true
}
function openHernoem(p) {
  dialogProces.value = p
  Object.assign(form, { naam: p.naam, toelichting: p.toelichting || '' })
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
    const data = { naam: form.naam.trim(), toelichting: form.toelichting.trim() || null }
    let nieuwId = null
    if (dialogProces.value) {
      await api.processen.werkBij(dialogProces.value.id, data)
    } else {
      const res = await api.processen.maak(data)
      nieuwId = res?.id ?? null
    }
    toastSucces(toast, dialogProces.value ? 'Opgeslagen' : 'Proces aangemaakt')
    dialogOpen.value = false
    await laad()
    // LI039 blok B — het zojuist aangemaakte proces is ALTIJD zichtbaar (gedeelde bouwsteen).
    if (nieuwId != null) toonRij(nieuwId)
  } catch (e) {
    if (e?.status !== 401) formFout.value = e?.message || 'Opslaan is mislukt.'
  } finally {
    bezig.value = false
  }
}

// ── LI037 tree-view gate 2 — verwijderen + verhangen (backend kon het al; nu de UI) ─────────

// De subboom (zelf + alle nazaten) uit de GEDEELDE boom-structuur — voedt de verboden-set van
// de verhang-picker (kring-preventie vóóraf) én de N-kinderen-telling in de bevestiging.
function subboomIds(procesId) {
  const ids = new Set([procesId])
  let frontier = [procesId]
  while (frontier.length) {
    const volgende = []
    for (const p of frontier) {
      for (const k of boom.value.kinderenVan.get(p) || []) {
        if (!ids.has(k)) { ids.add(k); volgende.push(k) }
      }
    }
    frontier = volgende
  }
  return ids
}

// Verwijderen — gedeelde bevestigingsdialoog; 409 HEEFT_DEELPROCESSEN → leesbare warn-zin in
// de dialoog (geen technische fout, boom onveranderd; de backend-guard blijft de vangrail).
const verwijderProces = ref(null)
const verwijderFout = ref(null)
const verwijderBezig = ref(false)
function openVerwijder(p) {
  verwijderProces.value = p
  verwijderFout.value = null
}
async function bevestigVerwijder() {
  const p = verwijderProces.value
  if (!p) return
  verwijderBezig.value = true
  verwijderFout.value = null
  try {
    await api.processen.verwijder(p.id)
    toastSucces(toast, 'Verwijderd')
    verwijderProces.value = null
    // Lokaal bijwerken (geen herlaad-sprong): rij weg, expand-staat van de rest blijft; de
    // gap-cue herberekent (een voorouder kan door de cascade van dekking wisselen).
    alle.value = alle.value.filter((x) => x.id !== p.id)
    openTakken.value = openTakken.value.filter((id) => id !== p.id)
    laadGapCue()
  } catch (e) {
    if (e?.status === 409) {
      verwijderFout.value = `"${p.naam}" kan niet worden verwijderd omdat er nog onderliggende processen zijn. Verplaats of verwijder die eerst.`
    } else if (e?.status !== 401) {
      verwijderFout.value = e?.message || 'Verwijderen is mislukt.'
    }
  } finally {
    verwijderBezig.value = false
  }
}

// Verhangen — "Verplaats naar…": ouder-picker (ZoekSelect over de al-geladen set, verboden-set
// eruit gefilterd zodat een kring vooraf onmogelijk is) + expliciete optie "Geen (maak
// hoofdproces)". De bevestigingszin benoemt de meeverhuizende kinderen alleen als die er zijn.
const verplaatsProces = ref(null)
const verplaatsDoel = ref(null) // null = nog geen keuze; { type: 'geen' } of { type: 'proces', id, naam }
const verplaatsFout = ref(null)
const verplaatsBezig = ref(false)
const verplaatsKey = ref(0) // remount-sleutel voor de picker per opening (stale-label-les LI032)
function openVerplaats(p) {
  verplaatsProces.value = p
  verplaatsDoel.value = null
  verplaatsFout.value = null
  verplaatsKey.value += 1
}
const verplaatsKinderen = computed(() =>
  (verplaatsProces.value ? subboomIds(verplaatsProces.value.id).size - 1 : 0))
// Geldige doelen: alles behalve het proces zelf + zijn nazaten (kring-preventie vóóraf).
// Client-side zoeken over de al-geladen set (zoekveld-norm: partieel, hoofdletter-ongevoelig),
// treffers mét oudercontext (identiteitspatroon "naam — ouder", zoals de proces-pickers elders).
async function zoekVerplaatsDoelen(params = {}) {
  const p = verplaatsProces.value
  if (!p) return { items: [], volgende_cursor: null }
  const verboden = subboomIds(p.id)
  const term = (params.zoek || '').trim().toLowerCase()
  const items = alle.value
    .filter((x) => !verboden.has(x.id))
    .filter((x) => !term || x.naam.toLowerCase().includes(term))
    .map((x) => ({ ...x, ouder_naam: x.ouder_id ? (_byId.value.get(x.ouder_id)?.naam ?? null) : null }))
    .sort((a, b) => a.naam.localeCompare(b.naam, 'nl'))
  return { items, volgende_cursor: null }
}
const doelWeergave = (x) => (x?.ouder_naam ? `${x.naam} — ${x.ouder_naam}` : (x?.naam ?? ''))
function kiesVerplaatsDoel(item) {
  if (item?.id) verplaatsDoel.value = { type: 'proces', id: item.id, naam: item.naam }
  verplaatsFout.value = null
}
function kiesHoofdproces() {
  verplaatsDoel.value = { type: 'geen' }
  verplaatsFout.value = null
}
const verplaatsZin = computed(() => {
  const p = verplaatsProces.value
  const d = verplaatsDoel.value
  if (!p || !d) return ''
  const n = verplaatsKinderen.value
  const mee = n > 0 ? ` en ${n} onderliggend${n === 1 ? '' : 'e'} proces${n === 1 ? '' : 'sen'}` : ''
  return d.type === 'geen'
    ? `Verplaats "${p.naam}"${mee} naar hoofdprocesniveau?`
    : `Verplaats "${p.naam}"${mee} naar "${d.naam}"?`
})
async function bevestigVerplaats() {
  const p = verplaatsProces.value
  const d = verplaatsDoel.value
  if (!p || !d) return
  verplaatsBezig.value = true
  verplaatsFout.value = null
  try {
    const doelId = d.type === 'geen' ? null : d.id
    await api.processen.werkBij(p.id, { ouder_id: doelId })
    toastSucces(toast, 'Verplaatst')
    verplaatsProces.value = null
    // Lokaal bijwerken: de tak verhuist mee (ouder_id van de wortel wijzigt; kinderen hangen
    // eraan). LI039 blok B — de verhuisde rij is altijd zichtbaar (gedeelde bouwsteen:
    // nieuwe ouderketen open + aanstip + zoekterm wijkt zichtbaar — het vroegere losse
    // openklappen is hierin geconvergeerd); de gap-cue herberekent (de dekking verhuist mee).
    alle.value = alle.value.map((x) => (x.id === p.id ? { ...x, ouder_id: doelId } : x))
    toonRij(p.id)
    laadGapCue()
  } catch (e) {
    // Race op de backend-vangrail (kring/verdwenen doel) → rustige melding, boom onveranderd.
    if (e?.status !== 401) verplaatsFout.value = e?.message || 'Verplaatsen is mislukt.'
  } finally {
    verplaatsBezig.value = false
  }
}

// ── LI038 gate 2 — "Bekijk op de kaart →" vanuit de Diagram-popup ────────────────────────────
// Bewuste doorschakeling naar de component-wereld: exact het ProcesDetail-pad (één gedeelde
// bouwer + consume-once handoff — geen route-query; zie procesKaartIngang.js). Het Diagram
// zelf blijft api-vrij en emit alleen het gekozen proces.
const router = useRouter()
const kaartBezig = ref(false)
async function bekijkOpKaart(p) {
  if (!p?.id || kaartBezig.value) return
  kaartBezig.value = true
  try {
    const payload = await bouwProcesKaartHandoff(api, p.id)
    if (!payload.componentIds.length) {
      toast.add({ severity: 'info', summary: 'Dit proceslandschap heeft nog geen ondersteunende systemen — er is niets te tonen op de kaart.', life: 3500 })
      return
    }
    zetKaartHandoff(payload)
    router.push({ name: 'landschapskaart' })
  } catch (e) {
    if (e?.status !== 401) toast.add({ severity: 'error', summary: 'Bekijk op kaart is mislukt.', life: 3000 })
  } finally {
    kaartBezig.value = false
  }
}

onMounted(() => {
  // Geen doorklik-query op Processen → de bewaarde staat mag altijd terug.
  herstelLijstStaat()
  laad()
})
</script>

<template>
  <section aria-labelledby="processen-titel">
    <div class="mb-[var(--lk-space-md)] flex items-center gap-[var(--lk-space-md)]">
      <div class="flex items-center gap-[var(--lk-space-xs)]">
        <h1 id="processen-titel" class="text-[length:var(--lk-text-2xl)] font-semibold text-[var(--lk-color-primary)]">
          Processen
        </h1>
        <VeldUitleg veld="proces" testid="uitleg-proces" />
      </div>
      <!-- LI038 gate 1 — expliciete weergave-schakelaar (Boom | Diagram), in de kaart-schakelaar-taal:
           de Boom is het register (beheer + uitklappen), het Diagram het proces-only structuurbeeld. -->
      <div
        class="ml-auto inline-flex overflow-hidden rounded-[var(--lk-radius-btn)] border border-[var(--lk-color-border)]"
        role="group"
        aria-label="Weergave"
        data-testid="proces-weergave-schakelaar"
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
          title="Proces-only structuurbeeld"
          :class="['border-l border-[var(--lk-color-border)] px-[var(--lk-space-md)] py-1 text-[length:var(--lk-text-sm)] font-semibold', weergave === 'diagram' ? 'bg-[var(--lk-color-primary)] text-white' : 'bg-white text-[var(--lk-color-primary)] hover:bg-[var(--lk-color-accent)]']"
          @click="weergave = 'diagram'"
        >Diagram</button>
      </div>
      <Button v-if="magBewerken" label="Nieuw proces" data-testid="nieuw-proces" @click="openNieuw" />
    </div>

    <!-- LI038 gate 1 — Diagram-weergave: proces-only structuurbeeld op de al-geladen set (zelfde
         bron als de Boom; de gap-cue-afleiding reist als prop mee — geen tweede fetch/definitie).
         Gate 2: de kaart-doorschakeling uit de popup landt hier (api-werk hoort bij de ouder). -->
    <ProcesDiagram
      v-if="weergave === 'diagram'"
      :processen="alle"
      :gap-ids="gapIds"
      :initieel-centrum-id="diagramStart"
      @bekijk-op-kaart="bekijkOpKaart"
      @centrum-gewijzigd="(id) => (diagramStart = id)"
    />

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
          aria-label="Zoek op procesnaam"
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
      testid="proces-wijk-melding"
      class="mb-[var(--lk-space-md)]"
    />

    <div v-if="weergave === 'boom'" class="rounded-[var(--lk-radius-card)] bg-[var(--lk-color-surface)] shadow-[var(--lk-shadow-sm)]" data-testid="processen-boom">
      <!-- LI037 tree-view — géén rij-scheidingslijnen meer (divide-y): de verbindingslijnen lopen
           verticaal dóór over rijgrenzen en zouden anders door de separators gekruist worden. -->
      <ul v-if="rijen.length">
        <li
          v-for="rij in rijen"
          :key="rij.proces.id"
          :class="[
            'lk-rij relative flex items-center gap-[var(--lk-space-sm)] px-[var(--lk-space-md)] py-[var(--lk-space-sm)]',
            rij.proces.id === aangestiptId ? 'lk-aangestipt' : '',
          ]"
          :data-testid="`proces-rij-${rij.proces.id}`"
        >
          <!-- LI037 tree-view — verbindingslijnen (PUUR DECORATIEF, aria-hidden: de structuur
               blijft de lijst + aria-expanded; kleur = het bestaande --lk-color-text-muted-token
               (gate 1b: --lk-color-border viel weg als haarlijn; 1.5px, zelfde kleur als de
               ▸/▾-affordances), rustig, de namen blijven de hoofdzaak). Per voorouder-niveau een doorlopende
               verticale lijn zolang die voorouder nog zichtbare broers onder zich heeft; op het
               eigen niveau een elleboog (├ , laatste kind └) + horizontale stub naar de rij. -->
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
              :data-testid="`proces-lijn-${rij.proces.id}`"
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
          <!-- Omlaag-stub onder een opengeklapte ouder: verbindt de ouder met zijn kind-lijnen. -->
          <span
            v-if="rij.open"
            data-boomlijn
            aria-hidden="true"
            class="pointer-events-none absolute bottom-0 top-1/2 w-[1.5px] bg-[var(--lk-color-text-muted)]"
            :style="{ left: lijnX(rij.diepte) }"
          ></span>
          <!-- LI039 UI-afronding v2 — tweelaags rij-inhoud (gedeelde vorm met de
               functieboom): SCAN-laag (naam + alleen wat afwijkt) en daaronder de
               LEES-laag (de toelichting, volledig leesbaar, max twee regels). -->
          <div class="lk-rij-inhoud" :style="{ paddingLeft: `${rij.diepte * 1.5}rem` }">
            <div class="lk-rij-kop">
              <button
                v-if="rij.heeftKinderen"
                type="button"
                :aria-expanded="rij.open"
                :aria-label="`${rij.open ? 'Klap in' : 'Klap uit'}: ${rij.proces.naam}`"
                :data-testid="`proces-toggle-${rij.proces.id}`"
                class="relative w-5 shrink-0 bg-[var(--lk-color-surface)] text-[var(--lk-color-text-muted)] hover:text-[var(--lk-color-primary)] focus:outline-2 focus:outline-offset-2 focus:outline-[var(--lk-color-primary)]"
                @click="toggle(rij.proces.id)"
              >{{ rij.open ? '▾' : '▸' }}</button>
              <span v-else class="w-5 shrink-0" aria-hidden="true"></span>
              <router-link
                :to="{ name: 'proces-detail', params: { id: rij.proces.id } }"
                data-testid="proces-link"
                class="min-w-0 font-medium text-[var(--lk-color-primary)] hover:underline focus:outline-2 focus:outline-offset-2 focus:outline-[var(--lk-color-primary)]"
              >{{ rij.proces.naam }}</router-link>
              <!-- LI037 — "geen ondersteunend systeem" (zelfde subboom-semantiek als de kaart-gap-cue;
                   rustige tag in de eerlijkheids-cue-taal: gestreepte rand, geen alarmkleur). -->
              <span
                v-if="isGap(rij.proces.id)"
                :data-testid="`proces-gap-${rij.proces.id}`"
                class="shrink-0 rounded-[var(--lk-radius-badge)] border border-dashed border-[var(--lk-color-border)] px-1.5 text-[length:var(--lk-text-xs)] text-[var(--lk-color-text-muted)]"
              >geen ondersteunend systeem</span>
            </div>
            <p
              v-if="rij.proces.toelichting"
              class="lk-rij-definitie pl-7 text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]"
              :data-testid="`proces-toelichting-${rij.proces.id}`"
            >{{ rij.proces.toelichting }}</p>
          </div>
          <!-- Rij-acties — rustig (LI039 C0, gedeelde RijActies-bouwsteen: tertiair, zichtbaar
               op de actieve rij/via focus). Rechtenverdeling ongewijzigd (LI037): Hernoemen/
               Verplaatsen op Wijzigen, Verwijderen alléén met het Verwijderen-recht en mét de
               danger-vorm (de gevaarlijkste actie mag er niet het minst gevaarlijk uitzien).
               "Toon in procesbeeld" is een LEES-actie (elke rol). -->
          <RijActies>
            <!-- Doorklik (navigatie) = text/ghost mét pijl; mutaties = outlined (rustige
                 knop-vorm) — het verschil is zichtbaar (LI039 UI-afronding punt 1). -->
            <Button
              label="Toon in procesbeeld →"
              text
              :data-testid="`proces-diagram-${rij.proces.id}`"
              :aria-label="`Toon ${rij.proces.naam} in het procesbeeld`"
              @click="toonInProcesbeeld(rij.proces)"
            />
            <Button
              v-if="magBewerken"
              label="Hernoemen"
              outlined
              :data-testid="`proces-hernoem-${rij.proces.id}`"
              :aria-label="`Hernoem ${rij.proces.naam}`"
              @click="openHernoem(rij.proces)"
            />
            <Button
              v-if="magBewerken"
              label="Verplaats naar…"
              outlined
              :data-testid="`proces-verplaats-${rij.proces.id}`"
              :aria-label="`Verplaats ${rij.proces.naam}`"
              @click="openVerplaats(rij.proces)"
            />
            <Button
              v-if="magVerwijderen"
              label="Verwijderen"
              severity="danger"
              :data-testid="`proces-verwijder-${rij.proces.id}`"
              :aria-label="`Verwijder ${rij.proces.naam}`"
              @click="openVerwijder(rij.proces)"
            />
          </RijActies>
        </li>
      </ul>
      <p v-else-if="!laden && zoekterm.trim()" data-testid="lijst-geen-match" class="p-[var(--lk-space-md)] text-[var(--lk-color-text-muted)]">
        Geen processen komen overeen met de zoekterm.
      </p>
      <p v-else-if="!laden" data-testid="lijst-leeg" class="p-[var(--lk-space-md)] text-[var(--lk-color-text-muted)]">
        Er zijn nog geen processen.
        <template v-if="magBewerken">Begin met "Nieuw proces" — deelprocessen voeg je daarna toe op de procespagina zelf.</template>
      </p>
      <p v-else data-testid="lijst-laden" class="p-[var(--lk-space-md)] text-[var(--lk-color-text-muted)]">Laden…</p>
    </div>

    <!-- Nieuw top-level proces / hernoemen -->
    <Dialog v-model:visible="dialogOpen" modal :closable="false" :header="dialogProces ? 'Proces hernoemen' : 'Nieuw proces'" data-testid="proces-dialog">
      <form class="flex min-w-[22rem] flex-col gap-[var(--lk-space-md)]" @submit.prevent="bevestig">
        <p v-if="formFout" role="alert" data-testid="proces-dialog-fout" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ formFout }}</p>
        <div class="flex flex-col gap-[var(--lk-space-xs)]">
          <label for="proces-naam" class="font-semibold">Naam *</label>
          <input id="proces-naam" v-model="form.naam" type="text" maxlength="255" data-testid="proces-naam" class="rounded-[var(--lk-radius-btn)] border border-[var(--lk-color-border)] bg-[var(--lk-color-surface)] px-[var(--lk-space-sm)] py-[var(--lk-space-xs)]" />
        </div>
        <div class="flex flex-col gap-[var(--lk-space-xs)]">
          <label for="proces-toelichting" class="font-semibold">Toelichting</label>
          <textarea id="proces-toelichting" v-model="form.toelichting" rows="3" data-testid="proces-toelichting" class="rounded-[var(--lk-radius-btn)] border border-[var(--lk-color-border)] bg-[var(--lk-color-surface)] px-[var(--lk-space-sm)] py-[var(--lk-space-xs)]"></textarea>
        </div>
        <div class="flex gap-[var(--lk-space-md)]">
          <Button type="submit" :label="dialogProces ? 'Opslaan' : 'Toevoegen'" data-testid="proces-dialog-opslaan" :disabled="bezig" />
          <Button type="button" label="Annuleren" severity="secondary" @click="dialogOpen = false" />
        </div>
      </form>
    </Dialog>

    <!-- LI037 gate 2 — verwijderen: gedeelde bevestigingsdialoog; een 409 (HEEFT_DEELPROCESSEN)
         wordt een leesbare warn-zin ín de dialoog — de boom blijft ongewijzigd. -->
    <BevestigVerwijderDialog
      :visible="!!verwijderProces"
      kop="Proces verwijderen"
      :bezig="verwijderBezig"
      testid="proces-verwijder"
      @update:visible="(v) => { if (!v) verwijderProces = null }"
      @bevestig="bevestigVerwijder"
    >
      <span v-if="verwijderFout" data-testid="proces-verwijder-fout" class="text-[var(--lk-color-warning)]">{{ verwijderFout }}</span>
      <span v-else>Verwijder "{{ verwijderProces?.naam }}"?</span>
    </BevestigVerwijderDialog>

    <!-- LI037 gate 2 — verhangen: ouder-picker zonder ongeldige doelen (kring-preventie vóóraf:
         het proces zelf + zijn nazaten zijn eruit gefilterd) + "Geen (maak hoofdproces)"; de
         bevestigingszin benoemt de meeverhuizende onderliggende processen alleen als die er zijn. -->
    <Dialog :visible="!!verplaatsProces" modal :closable="false" :header="`Verplaats “${verplaatsProces?.naam ?? ''}”`" data-testid="proces-verplaats-dialog" @update:visible="(v) => { if (!v) verplaatsProces = null }">
      <div class="flex min-w-[24rem] flex-col gap-[var(--lk-space-md)]">
        <p v-if="verplaatsFout" role="alert" data-testid="proces-verplaats-fout" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ verplaatsFout }}</p>
        <button
          type="button"
          data-testid="proces-verplaats-geen"
          :disabled="!verplaatsProces?.ouder_id"
          :title="verplaatsProces?.ouder_id ? '' : 'Dit is al een hoofdproces'"
          :class="['rounded-[var(--lk-radius-btn)] border px-[var(--lk-space-md)] py-[var(--lk-space-xs)] text-left text-[length:var(--lk-text-sm)] disabled:cursor-not-allowed disabled:opacity-50',
                   verplaatsDoel?.type === 'geen' ? 'border-[var(--lk-color-primary)] bg-[var(--lk-color-accent)] font-semibold' : 'border-[var(--lk-color-border)] hover:bg-[var(--lk-color-accent)]']"
          @click="kiesHoofdproces"
        >Geen (maak hoofdproces)</button>
        <label class="flex flex-col gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]">
          <span>Of kies een nieuwe ouder</span>
          <ZoekSelect
            :key="verplaatsKey"
            :zoek-functie="zoekVerplaatsDoelen"
            :weergave="doelWeergave"
            id-veld="id"
            placeholder="Zoek proces…"
            testid="proces-verplaats-doel"
            @keuze="kiesVerplaatsDoel"
          />
        </label>
        <p v-if="verplaatsZin" data-testid="proces-verplaats-zin" class="max-w-prose font-medium">{{ verplaatsZin }}</p>
        <div class="flex gap-[var(--lk-space-md)]">
          <Button type="button" label="Verplaatsen" data-testid="proces-verplaats-bevestig" :disabled="!verplaatsDoel || verplaatsBezig" @click="bevestigVerplaats" />
          <Button type="button" label="Annuleren" severity="secondary" @click="verplaatsProces = null" />
        </div>
      </div>
    </Dialog>
  </section>
</template>
