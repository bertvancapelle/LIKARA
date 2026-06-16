<script setup>
/**
 * DeliverableDetailView — migratielaag (ADR-023 Fase F / F-1): deliverable-detail.
 * Read-only; leunt op `GET /deliverables/{id}` + `/keten` (de realisatieketen
 * work_package → deliverable → plateau, uit het bestaande relatiemodel).
 */
import { onMounted, ref } from 'vue'
import { Column, DataTable } from '@/primevue'
import { api } from '@/api'

const props = defineProps({ id: { type: String, required: true } })

const deliverable = ref(null)
const keten = ref({ werkpakketten: [], plateaus: [] })
const laden = ref(true)
const fout = ref(null)

onMounted(async () => {
  try {
    deliverable.value = await api.deliverables.haal(props.id)
    keten.value = await api.deliverables.keten(props.id)
  } catch (e) {
    fout.value = e?.message || 'De deliverable kon niet worden geladen.'
  } finally {
    laden.value = false
  }
})
</script>

<template>
  <section aria-labelledby="del-detail-titel">
    <router-link
      :to="{ name: 'deliverable-lijst' }"
      class="text-[length:var(--cd-text-sm)] text-[var(--cd-color-primary)] hover:underline"
    >
      ← Deliverables
    </router-link>

    <p v-if="fout" role="alert" data-testid="del-detail-fout" class="my-[var(--cd-space-md)] text-[var(--cd-color-danger)]">
      {{ fout }}
    </p>
    <p v-else-if="laden" data-testid="del-detail-laden" class="my-[var(--cd-space-md)] text-[var(--cd-color-text-muted)]">Laden…</p>

    <template v-else-if="deliverable">
      <h1
        id="del-detail-titel"
        data-testid="del-naam"
        class="mt-[var(--cd-space-sm)] mb-[var(--cd-space-sm)] text-[length:var(--cd-text-2xl)] font-semibold text-[var(--cd-color-primary)]"
      >
        {{ deliverable.naam }}
      </h1>
      <p v-if="deliverable.toelichting" class="mb-[var(--cd-space-lg)] text-[var(--cd-color-text)]">{{ deliverable.toelichting }}</p>

      <h2 class="mb-[var(--cd-space-sm)] text-[length:var(--cd-text-lg)] font-semibold">Opgeleverd door (werkpakketten)</h2>
      <DataTable
        :value="keten.werkpakketten"
        data-testid="del-werkpakketten-tabel"
        class="mb-[var(--cd-space-lg)] bg-[var(--cd-color-surface)] rounded-[var(--cd-radius-card)] shadow-[var(--cd-shadow-sm)]"
      >
        <Column field="naam" header="Werkpakket">
          <template #body="{ data }">
            <router-link
              :to="{ name: 'work-package-detail', params: { id: data.element_id } }"
              class="text-[var(--cd-color-primary)] hover:underline"
            >
              {{ data.naam }}
            </router-link>
          </template>
        </Column>
        <template #empty>
          <span data-testid="del-werkpakketten-leeg">Nog geen werkpakket gekoppeld.</span>
        </template>
      </DataTable>

      <h2 class="mb-[var(--cd-space-sm)] text-[length:var(--cd-text-lg)] font-semibold">Helpt realiseren (plateaus)</h2>
      <DataTable
        :value="keten.plateaus"
        data-testid="del-plateaus-tabel"
        class="bg-[var(--cd-color-surface)] rounded-[var(--cd-radius-card)] shadow-[var(--cd-shadow-sm)]"
      >
        <Column field="naam" header="Plateau">
          <template #body="{ data }">
            <router-link
              :to="{ name: 'plateau-detail', params: { id: data.element_id } }"
              class="text-[var(--cd-color-primary)] hover:underline"
            >
              {{ data.naam }}
            </router-link>
          </template>
        </Column>
        <template #empty>
          <span data-testid="del-plateaus-leeg">Nog geen plateau gekoppeld.</span>
        </template>
      </DataTable>
    </template>
  </section>
</template>
