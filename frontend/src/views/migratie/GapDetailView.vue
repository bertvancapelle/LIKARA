<script setup>
/**
 * GapDetailView — migratielaag (ADR-023 Fase F / F-1): gap-detail.
 * Read-only; leunt op `GET /gaps/{id}` (GapDetail incl. de twee readiness-cijfers),
 * `GET /gaps/{id}/leden`, en `GET /plateaus/{id}` voor de baseline-/doel-plateaunamen.
 * De twee readiness-cijfers (technisch + contractueel) worden gescheiden getoond; een
 * lege noemer (percentage = null) als "n.v.t.", niet als 0%.
 */
import { onMounted, ref } from 'vue'
import { Column, DataTable } from '@/primevue'
import { api } from '@/api'

const props = defineProps({ id: { type: String, required: true } })

const gap = ref(null)
const leden = ref([])
const baselineNaam = ref(null)
const doelNaam = ref(null)
const laden = ref(true)
const fout = ref(null)

const TYPE_LABEL = { component: 'Component', contract: 'Contract' }

function readinessTekst(cijfer) {
  if (!cijfer || cijfer.percentage === null || cijfer.percentage === undefined) {
    return 'n.v.t. (geen leden in de noemer)'
  }
  return `${cijfer.aantal_klaar} van ${cijfer.aantal_totaal} (${cijfer.percentage}%)`
}

onMounted(async () => {
  try {
    gap.value = await api.gaps.haal(props.id)
    leden.value = await api.gaps.leden(props.id)
    // Plateaunamen los ophalen (bestaande plateau-read); faalt er één, toon de id niet.
    const [b, d] = await Promise.all([
      api.plateaus.haal(gap.value.baseline_plateau_id).catch(() => null),
      api.plateaus.haal(gap.value.doel_plateau_id).catch(() => null),
    ])
    baselineNaam.value = b?.naam || null
    doelNaam.value = d?.naam || null
  } catch (e) {
    fout.value = e?.message || 'De gap kon niet worden geladen.'
  } finally {
    laden.value = false
  }
})
</script>

<template>
  <section aria-labelledby="gap-detail-titel">
    <router-link
      :to="{ name: 'gap-lijst' }"
      class="text-[length:var(--cd-text-sm)] text-[var(--cd-color-primary)] hover:underline"
    >
      ← Gaps
    </router-link>

    <p v-if="fout" role="alert" data-testid="gap-detail-fout" class="my-[var(--cd-space-md)] text-[var(--cd-color-danger)]">
      {{ fout }}
    </p>
    <p v-else-if="laden" data-testid="gap-detail-laden" class="my-[var(--cd-space-md)] text-[var(--cd-color-text-muted)]">Laden…</p>

    <template v-else-if="gap">
      <h1
        id="gap-detail-titel"
        data-testid="gap-naam"
        class="mt-[var(--cd-space-sm)] mb-[var(--cd-space-sm)] text-[length:var(--cd-text-2xl)] font-semibold text-[var(--cd-color-primary)]"
      >
        {{ gap.naam }}
      </h1>
      <p v-if="gap.toelichting" class="mb-[var(--cd-space-md)] text-[var(--cd-color-text)]">{{ gap.toelichting }}</p>

      <p data-testid="gap-overgang" class="mb-[var(--cd-space-lg)] text-[var(--cd-color-text)]">
        <span class="font-medium">Overgang:</span>
        {{ baselineNaam || 'baseline-plateau' }} → {{ doelNaam || 'doel-plateau' }}
      </p>

      <div class="mb-[var(--cd-space-lg)] grid gap-[var(--cd-space-md)] sm:grid-cols-2">
        <div
          data-testid="readiness-technisch"
          class="rounded-[var(--cd-radius-card)] border border-[var(--cd-color-border)] bg-[var(--cd-color-surface)] p-[var(--cd-space-md)] shadow-[var(--cd-shadow-sm)]"
        >
          <h2 class="mb-1 text-[length:var(--cd-text-sm)] font-semibold uppercase tracking-wide text-[var(--cd-color-text-muted)]">
            Technische readiness
          </h2>
          <p class="text-[length:var(--cd-text-lg)]">{{ readinessTekst(gap.readiness_technisch) }}</p>
        </div>
        <div
          data-testid="readiness-contractueel"
          class="rounded-[var(--cd-radius-card)] border border-[var(--cd-color-border)] bg-[var(--cd-color-surface)] p-[var(--cd-space-md)] shadow-[var(--cd-shadow-sm)]"
        >
          <h2 class="mb-1 text-[length:var(--cd-text-sm)] font-semibold uppercase tracking-wide text-[var(--cd-color-text-muted)]">
            Contractuele readiness
          </h2>
          <p class="text-[length:var(--cd-text-lg)]">{{ readinessTekst(gap.readiness_contractueel) }}</p>
        </div>
      </div>

      <h2 class="mb-[var(--cd-space-sm)] text-[length:var(--cd-text-lg)] font-semibold">Leden</h2>
      <DataTable
        :value="leden"
        data-testid="gap-leden-tabel"
        class="bg-[var(--cd-color-surface)] rounded-[var(--cd-radius-card)] shadow-[var(--cd-shadow-sm)]"
      >
        <Column header="Type">
          <template #body="{ data }">{{ TYPE_LABEL[data.lid_element_type] || data.lid_element_type }}</template>
        </Column>
        <Column field="naam" header="Naam">
          <template #body="{ data }">{{ data.naam || '—' }}</template>
        </Column>
        <template #empty>
          <span data-testid="gap-leden-leeg">Deze gap heeft nog geen leden.</span>
        </template>
      </DataTable>
    </template>
  </section>
</template>
