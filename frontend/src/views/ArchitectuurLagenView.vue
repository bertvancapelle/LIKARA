<script setup>
/**
 * ArchitectuurLagenView — visuele gelaagde ArchiMate-weergave (ADR-023 Fase F / F-2, LI025).
 *
 * Leest álle elementen uit `GET /architectuur/elementen` (alle pagina's), groepeert client-side
 * op `laag` en toont per laag een gekleurde band met klikbare element-pills. Aspect-stijl op de
 * pill: active = doorgetrokken border, passive = dashed border, behavior = ronde pill. Read-only;
 * leunt volledig op het bestaande endpoint (geen client-side typing-logica).
 */
import { computed, onMounted, ref } from 'vue'
import { api } from '@/api'
import { ARCHIMATE_LAAG, humaniseer } from '@modules/bwb_ontvlechting/frontend/labels'

// Bandvolgorde (boven → onder) + kleur per laag (conform de PNA-demo).
const BANDEN = [
  { laag: 'implementation_migration', kleur: '#993C1D', migratie: true },
  { laag: 'business', kleur: '#185FA5', migratie: false },
  { laag: 'application', kleur: '#0F6E56', migratie: false },
  { laag: 'technology', kleur: '#5F5E5A', migratie: false },
]
// Doorklik per element-type (typen zonder eigen detailpagina → geen link).
const ROUTE_PER_TYPE = {
  component: 'component-detail', contract: 'contract-detail', partij: 'partij-detail',
  plateau: 'plateau-detail', gap: 'gap-detail', work_package: 'work-package-detail', deliverable: 'deliverable-detail',
}
const elementRoute = (el) =>
  ROUTE_PER_TYPE[el.element_type] ? { name: ROUTE_PER_TYPE[el.element_type], params: { id: el.id } } : null

const ASPECT_KNOPPEN = [
  { waarde: '', tekst: 'Alle' },
  { waarde: 'active', tekst: 'Actief' },
  { waarde: 'passive', tekst: 'Passief' },
  { waarde: 'behavior', tekst: 'Gedrag' },
]

const elementen = ref([])
const laden = ref(false)
const fout = ref(null)
const toonMigratie = ref(true)
const aspectFilter = ref('') // '' | active | passive | behavior

async function laadAlles() {
  laden.value = true
  fout.value = null
  try {
    const acc = []
    let after
    // Alle pagina's ophalen — de lagenweergave kent geen paginering (max enkele honderden elementen).
    for (let i = 0; i < 50; i++) {
      const p = await api.architectuur.elementen({ limit: 100, after })
      acc.push(...(p.items || []))
      after = p.volgende_cursor
      if (!after) break
    }
    elementen.value = acc
  } catch (e) {
    fout.value = e?.status === 401 ? null : e?.message || 'Er ging iets mis bij het laden van het architectuuroverzicht.'
  } finally {
    laden.value = false
  }
}

const zichtbaar = computed(() =>
  elementen.value.filter((e) => !aspectFilter.value || e.aspect === aspectFilter.value),
)
const perLaag = computed(() => {
  const map = {}
  for (const e of zichtbaar.value) (map[e.laag] ||= []).push(e)
  for (const k of Object.keys(map)) map[k].sort((a, b) => String(a.naam).localeCompare(String(b.naam), 'nl'))
  return map
})
const zichtbareBanden = computed(() => BANDEN.filter((b) => (b.migratie ? toonMigratie.value : true)))
const laagLabel = (l) => ARCHIMATE_LAAG[l] || humaniseer(l)
// Aspect → pill-vorm/border: behavior = ronde pill, passive = dashed, active = solid.
const aspectClass = (a) =>
  a === 'behavior' ? 'rounded-full border-solid' : a === 'passive' ? 'border-dashed' : 'border-solid'

onMounted(laadAlles)
</script>

<template>
  <div data-testid="arch-lagen">
    <!-- Controls: migratie-toggle + aspect-filter -->
    <div class="mb-[var(--lk-space-md)] flex flex-wrap items-center gap-[var(--lk-space-lg)] rounded-[var(--lk-radius-card)] bg-[var(--lk-color-surface)] p-[var(--lk-space-md)] shadow-[var(--lk-shadow-sm)]">
      <label class="flex items-center gap-2 text-[length:var(--lk-text-sm)]">
        <input type="checkbox" :checked="toonMigratie" data-testid="arch-lagen-migratie" @change="toonMigratie = !toonMigratie" />
        Migratie-laag tonen
      </label>
      <div class="flex items-center gap-1" role="group" aria-label="Aspect-filter">
        <span class="text-[length:var(--lk-text-xs)] font-semibold uppercase tracking-wide text-[var(--lk-color-text-muted)]">Aspect</span>
        <button
          v-for="o in ASPECT_KNOPPEN"
          :key="o.waarde"
          type="button"
          :data-testid="`arch-lagen-aspect-${o.waarde || 'alle'}`"
          :aria-pressed="aspectFilter === o.waarde"
          :class="['rounded-[var(--lk-radius-btn)] px-[var(--lk-space-sm)] py-0.5 text-[length:var(--lk-text-sm)]', aspectFilter === o.waarde ? 'bg-[var(--lk-color-primary)] text-white' : 'bg-[var(--lk-color-accent)]']"
          @click="aspectFilter = o.waarde"
        >
          {{ o.tekst }}
        </button>
      </div>
    </div>

    <p v-if="fout" role="alert" data-testid="arch-lagen-fout" class="mb-[var(--lk-space-md)] rounded-[var(--lk-radius-badge)] border border-[var(--lk-color-danger)] bg-[var(--lk-color-danger)]/10 px-[var(--lk-space-md)] py-[var(--lk-space-sm)] text-[var(--lk-color-danger)]">
      {{ fout }}
    </p>

    <!-- Lagen-bands (boven → onder) -->
    <div
      v-for="b in zichtbareBanden"
      :key="b.laag"
      :data-testid="`arch-band-${b.laag}`"
      class="mb-[var(--lk-space-sm)] rounded-[var(--lk-radius-card)] border-l-4 p-[var(--lk-space-md)]"
      :style="{ borderLeftColor: b.kleur, backgroundColor: b.kleur + '12' }"
    >
      <p class="mb-[var(--lk-space-sm)] text-[length:var(--lk-text-xs)] font-semibold uppercase tracking-wide" :style="{ color: b.kleur }">
        {{ laagLabel(b.laag) }}
      </p>
      <div class="flex flex-wrap gap-2">
        <component
          :is="elementRoute(el) ? 'router-link' : 'span'"
          v-for="el in (perLaag[b.laag] || [])"
          :key="el.id"
          :to="elementRoute(el) || undefined"
          :data-testid="`arch-pill-${el.id}`"
          :title="el.naam_secundair || el.naam"
          class="inline-flex items-center border-2 bg-[var(--lk-color-surface)] px-[var(--lk-space-sm)] py-0.5 text-[length:var(--lk-text-sm)] focus:outline-2 focus:outline-offset-2 focus:outline-[var(--lk-color-primary)]"
          :class="[aspectClass(el.aspect), elementRoute(el) ? 'hover:underline cursor-pointer' : '', el.aspect === 'behavior' ? '' : 'rounded-[var(--lk-radius-btn)]']"
          :style="{ borderColor: b.kleur }"
        >
          {{ el.naam }}
        </component>
        <span v-if="!(perLaag[b.laag] || []).length" class="text-[length:var(--lk-text-xs)] text-[var(--lk-color-text-muted)]">— geen elementen</span>
      </div>
    </div>

    <!-- Legenda (één keer) -->
    <div data-testid="arch-lagen-legenda" class="mt-[var(--lk-space-md)] flex flex-wrap items-center gap-[var(--lk-space-lg)] text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]">
      <span class="flex items-center gap-2"><span class="inline-block rounded-[var(--lk-radius-btn)] border-2 border-solid border-[var(--lk-color-text-muted)] px-2">Aa</span> Actieve structuur</span>
      <span class="flex items-center gap-2"><span class="inline-block rounded-[var(--lk-radius-btn)] border-2 border-dashed border-[var(--lk-color-text-muted)] px-2">Aa</span> Passieve structuur</span>
      <span class="flex items-center gap-2"><span class="inline-block rounded-full border-2 border-solid border-[var(--lk-color-text-muted)] px-2">Aa</span> Gedrag</span>
    </div>

    <p v-if="laden" data-testid="arch-lagen-laden" class="mt-[var(--lk-space-md)] text-[var(--lk-color-text-muted)]">Laden…</p>
  </div>
</template>
