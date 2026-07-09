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
import { Button, Dialog } from '@/primevue'
import { useAuthStore } from '@/store/auth'
import { useLijstStaat } from '@/composables/useLijstStaat'
import { api } from '@/api'
import VeldUitleg from './VeldUitleg.vue'

const auth = useAuthStore()
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
  } catch (e) {
    fout.value = e?.status === 401 ? null : 'Laden van de processen is mislukt.'
  } finally {
    laden.value = false
  }
}

const kinderenVan = computed(() => {
  const map = new Map()
  for (const p of alle.value) {
    const sleutel = p.ouder_id || '__wortel__'
    if (!map.has(sleutel)) map.set(sleutel, [])
    map.get(sleutel).push(p)
  }
  for (const lijst of map.values()) lijst.sort((a, b) => a.naam.localeCompare(b.naam, 'nl'))
  return map
})

const _matcht = (p) => p.naam.toLowerCase().includes(zoekterm.value.trim().toLowerCase())
// Bij een actieve zoekterm: toon de paden naar de treffers, opengeklapt (zoeken klapt open).
const matchOfNazaatMatcht = computed(() => {
  const term = zoekterm.value.trim()
  const set = new Set()
  if (!term) return set
  const heeftMatchIn = (id) => {
    let raak = false
    for (const kind of kinderenVan.value.get(id) || []) {
      if (heeftMatchIn(kind.id) || _matcht(kind)) raak = true
    }
    if (raak) set.add(id)
    return raak
  }
  for (const wortel of kinderenVan.value.get('__wortel__') || []) {
    if (heeftMatchIn(wortel.id) || _matcht(wortel)) set.add(wortel.id)
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
const rijen = computed(() => {
  const term = zoekterm.value.trim()
  const uit = []
  const loop = (ouderSleutel, diepte) => {
    for (const p of kinderenVan.value.get(ouderSleutel) || []) {
      const relevant = !term || _matcht(p) || matchOfNazaatMatcht.value.has(p.id)
      if (!relevant) continue
      const heeftKinderen = (kinderenVan.value.get(p.id) || []).length > 0
      uit.push({ proces: p, diepte, heeftKinderen, open: heeftKinderen && isOpen(p.id) })
      if (heeftKinderen && isOpen(p.id)) loop(p.id, diepte + 1)
    }
  }
  loop('__wortel__', 0)
  return uit
})

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
      <ul v-if="rijen.length" class="divide-y divide-[var(--lk-color-border)]">
        <li
          v-for="rij in rijen"
          :key="rij.proces.id"
          class="flex items-center gap-[var(--lk-space-sm)] px-[var(--lk-space-md)] py-[var(--lk-space-sm)]"
          :style="{ paddingLeft: `calc(var(--lk-space-md) + ${rij.diepte * 1.5}rem)` }"
          :data-testid="`proces-rij-${rij.proces.id}`"
        >
          <button
            v-if="rij.heeftKinderen"
            type="button"
            :aria-expanded="rij.open"
            :aria-label="`${rij.open ? 'Klap in' : 'Klap uit'}: ${rij.proces.naam}`"
            :data-testid="`proces-toggle-${rij.proces.id}`"
            class="w-5 shrink-0 text-[var(--lk-color-text-muted)] hover:text-[var(--lk-color-primary)] focus:outline-2 focus:outline-offset-2 focus:outline-[var(--lk-color-primary)]"
            @click="toggle(rij.proces.id)"
          >{{ rij.open ? '▾' : '▸' }}</button>
          <span v-else class="w-5 shrink-0" aria-hidden="true"></span>
          <router-link
            :to="{ name: 'proces-detail', params: { id: rij.proces.id } }"
            data-testid="proces-link"
            class="font-medium text-[var(--lk-color-primary)] hover:underline focus:outline-2 focus:outline-offset-2 focus:outline-[var(--lk-color-primary)]"
          >{{ rij.proces.naam }}</router-link>
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
