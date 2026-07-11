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
import { useLijstStaat } from '@/composables/useLijstStaat'
import { api } from '@/api'
import { procesBoomStructuur } from '../procesBoom'
import VeldUitleg from './VeldUitleg.vue'

const auth = useAuthStore()
const toast = useToast()
const magBewerken = computed(() => auth.hasRole('medewerker', 'beheerder'))

const alle = ref([]) // platte set (alle pagina's); de boom is een client-side afgeleide
const laden = ref(false)
const fout = ref(null)

const zoekterm = ref('')
const openTakken = ref([]) // ids van uitgeklapte processen (array → serialiseerbare lijststaat)

// Lijststaat behouden bij terugnavigeren/F5 (lk-state-patroon; zie useLijstStaat).
const _tekst = (w) => typeof w === 'string'
const { herstel: herstelLijstStaat } = useLijstStaat(
  'proces-lijst',
  { zoekterm, openTakken },
  {
    valideer: {
      zoekterm: _tekst,
      openTakken: (w) => Array.isArray(w) && w.every(_tekst),
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
    if (dialogProces.value) await api.processen.werkBij(dialogProces.value.id, data)
    else await api.processen.maak(data)
    toastSucces(toast, dialogProces.value ? 'Opgeslagen' : 'Proces aangemaakt')
    dialogOpen.value = false
    await laad()
  } catch (e) {
    if (e?.status !== 401) formFout.value = e?.message || 'Opslaan is mislukt.'
  } finally {
    bezig.value = false
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
      <Button v-if="magBewerken" label="Nieuw proces" data-testid="nieuw-proces" class="ml-auto" @click="openNieuw" />
    </div>

    <div
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

    <div class="rounded-[var(--lk-radius-card)] bg-[var(--lk-color-surface)] shadow-[var(--lk-shadow-sm)]" data-testid="processen-boom">
      <!-- LI037 tree-view — géén rij-scheidingslijnen meer (divide-y): de verbindingslijnen lopen
           verticaal dóór over rijgrenzen en zouden anders door de separators gekruist worden. -->
      <ul v-if="rijen.length">
        <li
          v-for="rij in rijen"
          :key="rij.proces.id"
          class="relative flex items-center gap-[var(--lk-space-sm)] px-[var(--lk-space-md)] py-[var(--lk-space-sm)]"
          :style="{ paddingLeft: `calc(var(--lk-space-md) + ${rij.diepte * 1.5}rem)` }"
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
            class="font-medium text-[var(--lk-color-primary)] hover:underline focus:outline-2 focus:outline-offset-2 focus:outline-[var(--lk-color-primary)]"
          >{{ rij.proces.naam }}</router-link>
          <!-- LI037 — "geen ondersteunend systeem" (zelfde subboom-semantiek als de kaart-gap-cue;
               rustige tag in de eerlijkheids-cue-taal: gestreepte rand, geen alarmkleur). -->
          <span
            v-if="isGap(rij.proces.id)"
            :data-testid="`proces-gap-${rij.proces.id}`"
            class="shrink-0 rounded-[var(--lk-radius-badge)] border border-dashed border-[var(--lk-color-border)] px-1.5 text-[length:var(--lk-text-xs)] text-[var(--lk-color-text-muted)]"
          >geen ondersteunend systeem</span>
          <span v-if="rij.proces.toelichting" class="min-w-0 truncate text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]">{{ rij.proces.toelichting }}</span>
          <button
            v-if="magBewerken"
            type="button"
            :data-testid="`proces-hernoem-${rij.proces.id}`"
            :aria-label="`Hernoem ${rij.proces.naam}`"
            class="ml-auto shrink-0 text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)] hover:text-[var(--lk-color-primary)] hover:underline focus:outline-2 focus:outline-offset-2 focus:outline-[var(--lk-color-primary)]"
            @click="openHernoem(rij.proces)"
          >Hernoemen</button>
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
  </section>
</template>
