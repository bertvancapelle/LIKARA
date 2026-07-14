<script setup>
/**
 * WerkvoorraadPlekView — ADR-051 gate 3, VENSTER 2 (de centrale signalering).
 *
 * De consultant vraagt: "waar moet ik nog langs?" Dit venster leest EXACT dezelfde afleiding als
 * de boom-cue (`functievervullingen.standen` — `plek_standen`, besluit 5) en telt + lijst de
 * plek-werkvoorraad. Het VENSTER rekent zelf niets: de teller komt uit de gedeelde `tellers`, de
 * lijst uit dezelfde `plekken` — één filterwaarheid (de "3-van-19"-les LI040).
 *
 * Een plek is GEEN element-id maar een paar (functie, ouder); we persen hem niet in een element —
 * we tonen hem als het paar, met de functienaam en (voor via-boven) de dragende voorouder.
 *
 * "Nog niet beoordeeld" is een EIGEN, vindbare stand (eigen sectie/filter), geen afwezigheid; de
 * lijst bundelt per systeem ("G-schijf — draagt N plekken") — drie besluiten i.p.v. twaalf regels.
 */
import { computed, onMounted, ref } from 'vue'
import { api } from '@/api'

const standen = ref([])
const tellers = ref({})
const dekking = ref([])
const naamPerFunctie = ref(new Map())
const laden = ref(true)
const fout = ref(null)

async function laad() {
  laden.value = true
  fout.value = null
  try {
    // Namen (alle functies) + de gedeelde afleiding + de dekking (voor "zonder oordeel").
    const functies = []
    let after
    do {
      const p = await api.bedrijfsfuncties.lijst({ limit: 100, after })
      functies.push(...p.items)
      after = p.volgende_cursor
    } while (after)
    naamPerFunctie.value = new Map(functies.map((f) => [f.id, f.naam]))
    const r = await api.functievervullingen.standen()
    standen.value = r?.plekken ?? []
    tellers.value = r?.tellers ?? {}
    dekking.value = (await api.functievervullingen.dekking()) ?? []
  } catch (e) {
    fout.value = e?.status === 401 ? null : e?.message || 'Laden van de werkvoorraad is mislukt.'
  } finally {
    laden.value = false
  }
}
onMounted(laad)

const naam = (id) => naamPerFunctie.value.get(id) || '—'

// De plekken die aandacht vragen (nog geen systeem of alleen via boven), uit dezelfde afleiding.
const teVerwerken = computed(() =>
  standen.value
    .filter((p) => p.stand === 'gat' || p.stand === 'via_boven')
    .map((p) => ({
      key: `${p.functie_id}|${p.ouder_functie_id ?? ''}`,
      functie: naam(p.functie_id),
      onder: p.ouder_functie_id ? naam(p.ouder_functie_id) : null,
      stand: p.stand,
      via: p.via_functie_id ? naam(p.via_functie_id) : null,
      via_aantal: p.via_aantal,
    }))
    .sort((a, b) => a.functie.localeCompare(b.functie, 'nl')),
)
// Één filterwaarheid: de teller = gat + via_boven uit de gedeelde `tellers` (NIET zelf geteld).
const aantalAandacht = computed(() => (tellers.value.gat || 0) + (tellers.value.via_boven || 0))

// "Nog niet beoordeeld": koppelingen (uit de dekking) met een leeg oordeel — gebundeld per systeem.
const filterOnbeoordeeld = ref(false)
const onbeoordeeldPerSysteem = computed(() => {
  const per = new Map()
  for (const d of dekking.value) {
    for (const c of d.componenten || []) {
      if (c.oordeel == null) {
        const e = per.get(c.component_naam) || { naam: c.component_naam, aantal: 0 }
        e.aantal += 1
        per.set(c.component_naam, e)
      }
    }
  }
  return [...per.values()].sort((a, b) => b.aantal - a.aantal)
})
const aantalOnbeoordeeld = computed(() => tellers.value.zonder_oordeel || 0)
</script>

<template>
  <div data-testid="werkvoorraad-plek">
    <p v-if="fout" role="alert" data-testid="werkvoorraad-fout" class="text-[var(--lk-color-danger)]">{{ fout }}</p>
    <p v-else-if="laden" data-testid="werkvoorraad-laden" class="text-[var(--lk-color-text-muted)]">Laden…</p>
    <template v-else>
      <!-- De teller: waar moet ik nog langs? Deelt de filterwaarheid met de lijst eronder. -->
      <p data-testid="werkvoorraad-teller" class="mb-[var(--lk-space-md)] text-[length:var(--lk-text-lg)] font-semibold text-[var(--lk-color-primary)]">
        {{ aantalAandacht }} {{ aantalAandacht === 1 ? 'plek vraagt' : 'plekken vragen' }} aandacht
      </p>
      <ul v-if="teVerwerken.length" data-testid="werkvoorraad-lijst" class="flex flex-col gap-[var(--lk-space-xs)]">
        <li v-for="r in teVerwerken" :key="r.key" :data-testid="`werkvoorraad-rij-${r.key}`" class="flex items-center gap-[var(--lk-space-sm)] text-[length:var(--lk-text-sm)]">
          <span class="font-medium">{{ r.functie }}</span>
          <span v-if="r.onder" class="text-[var(--lk-color-text-muted)]">onder {{ r.onder }}</span>
          <span
            class="ml-auto rounded-[var(--lk-radius-badge)] border border-dashed px-1.5 text-[length:var(--lk-text-xs)] text-[var(--lk-color-text-muted)]"
          >{{ r.stand === 'gat' ? 'nog niet vastgelegd waarmee'
              : (r.via ? `ondersteund via ${r.via} — hier niet bevestigd` : `ondersteund via ${r.via_aantal} bovenliggende functies`) }}</span>
        </li>
      </ul>
      <p v-else data-testid="werkvoorraad-leeg" class="text-[var(--lk-color-text-muted)]">Elke plek is nagevraagd — geen openstaande werkvoorraad.</p>

      <!-- Nog niet beoordeeld — een eigen, vindbare stand (filter), gebundeld per systeem. -->
      <div class="mt-[var(--lk-space-lg)] border-t border-[var(--lk-color-border)] pt-[var(--lk-space-md)]">
        <label class="flex items-center gap-2 text-[length:var(--lk-text-sm)]">
          <input v-model="filterOnbeoordeeld" type="checkbox" data-testid="werkvoorraad-filter-onbeoordeeld" />
          <span>Toon koppelingen die nog niet beoordeeld zijn ({{ aantalOnbeoordeeld }})</span>
        </label>
        <ul v-if="filterOnbeoordeeld && onbeoordeeldPerSysteem.length" data-testid="werkvoorraad-onbeoordeeld-lijst" class="mt-[var(--lk-space-sm)] flex flex-col gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]">
          <li v-for="s in onbeoordeeldPerSysteem" :key="s.naam" :data-testid="`werkvoorraad-onbeoordeeld-${s.naam}`">
            <span class="font-medium">{{ s.naam }}</span>
            <span class="text-[var(--lk-color-text-muted)]"> — draagt {{ s.aantal }} {{ s.aantal === 1 ? 'plek' : 'plekken' }} zonder oordeel</span>
          </li>
        </ul>
      </div>
    </template>
  </div>
</template>
