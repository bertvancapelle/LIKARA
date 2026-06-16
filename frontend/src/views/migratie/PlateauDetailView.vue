<script setup>
/**
 * PlateauDetailView — migratielaag (ADR-023 Fase F / F-1): plateau-detail + leden.
 * Read-only; leunt op `GET /plateaus/{id}` + `GET /plateaus/{id}/leden`. Per lid de
 * dispositie (backend-label) en — voor contracten — de contractuele bevestiging.
 */
import { onMounted, ref } from 'vue'
import { Column, DataTable, Tag } from '@/primevue'
import { api } from '@/api'

const props = defineProps({ id: { type: String, required: true } })

const plateau = ref(null)
const leden = ref([])
const laden = ref(true)
const fout = ref(null)

const TYPE_LABEL = { component: 'Component', contract: 'Contract' }

function formatDatum(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '—'
  return new Intl.DateTimeFormat('nl-NL', { dateStyle: 'medium', timeStyle: 'short' }).format(d)
}

onMounted(async () => {
  try {
    plateau.value = await api.plateaus.haal(props.id)
    leden.value = await api.plateaus.leden(props.id)
  } catch (e) {
    fout.value = e?.message || 'Het plateau kon niet worden geladen.'
  } finally {
    laden.value = false
  }
})
</script>

<template>
  <section aria-labelledby="plateau-detail-titel">
    <router-link
      :to="{ name: 'plateau-lijst' }"
      class="text-[length:var(--cd-text-sm)] text-[var(--cd-color-primary)] hover:underline"
    >
      ← Plateaus
    </router-link>

    <p v-if="fout" role="alert" data-testid="plateau-detail-fout" class="my-[var(--cd-space-md)] text-[var(--cd-color-danger)]">
      {{ fout }}
    </p>
    <p v-else-if="laden" data-testid="plateau-detail-laden" class="my-[var(--cd-space-md)] text-[var(--cd-color-text-muted)]">Laden…</p>

    <template v-else-if="plateau">
      <h1
        id="plateau-detail-titel"
        data-testid="plateau-naam"
        class="mt-[var(--cd-space-sm)] mb-[var(--cd-space-sm)] text-[length:var(--cd-text-2xl)] font-semibold text-[var(--cd-color-primary)]"
      >
        {{ plateau.naam }}
      </h1>
      <p v-if="plateau.toelichting" class="mb-[var(--cd-space-lg)] text-[var(--cd-color-text)]">{{ plateau.toelichting }}</p>

      <h2 class="mb-[var(--cd-space-sm)] text-[length:var(--cd-text-lg)] font-semibold">Leden</h2>
      <DataTable
        :value="leden"
        data-testid="plateau-leden-tabel"
        class="bg-[var(--cd-color-surface)] rounded-[var(--cd-radius-card)] shadow-[var(--cd-shadow-sm)]"
      >
        <Column header="Type">
          <template #body="{ data }">{{ TYPE_LABEL[data.lid_element_type] || data.lid_element_type }}</template>
        </Column>
        <Column header="Dispositie">
          <template #body="{ data }">
            <Tag :value="data.dispositie_label || data.dispositie" severity="info" />
          </template>
        </Column>
        <Column header="Contractueel bevestigd">
          <template #body="{ data }">
            <span v-if="data.lid_element_type !== 'contract'" class="text-[var(--cd-color-text-muted)]">n.v.t.</span>
            <Tag
              v-else
              :value="data.contractueel_bevestigd ? 'Bevestigd' : 'Niet bevestigd'"
              :severity="data.contractueel_bevestigd ? 'success' : 'warning'"
              data-testid="lid-bevestiging"
            />
          </template>
        </Column>
        <Column header="Aantal gebruikers">
          <template #body="{ data }">{{ data.bevestigd_aantal_gebruikers ?? '—' }}</template>
        </Column>
        <Column header="Bevestigd door">
          <template #body="{ data }">{{ data.bevestigd_door || '—' }}</template>
        </Column>
        <Column header="Bevestigd op">
          <template #body="{ data }">{{ formatDatum(data.bevestigd_op) }}</template>
        </Column>
        <template #empty>
          <span data-testid="plateau-leden-leeg">Dit plateau heeft nog geen leden.</span>
        </template>
      </DataTable>
    </template>
  </section>
</template>
