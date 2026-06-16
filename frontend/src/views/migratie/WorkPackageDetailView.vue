<script setup>
/**
 * WorkPackageDetailView — migratielaag (ADR-023 Fase F / F-1): werkpakket-detail.
 * Read-only; leunt op `GET /work-packages/{id}` + `/subboom` (afstammelingen met niveau +
 * pad) + `GET /work-packages/{ouder}` voor de naam van het bovenliggende pakket.
 */
import { computed, onMounted, ref } from 'vue'
import { Column, DataTable } from '@/primevue'
import { api } from '@/api'

const props = defineProps({ id: { type: String, required: true } })

const wp = ref(null)
const ouder = ref(null)
const subboom = ref([])
const laden = ref(true)
const fout = ref(null)

const directeSubpakketten = computed(() => subboom.value.filter((i) => i.niveau === 1))

onMounted(async () => {
  try {
    wp.value = await api.workPackages.haal(props.id)
    subboom.value = await api.workPackages.subboom(props.id)
    if (wp.value.bovenliggend_id) {
      ouder.value = await api.workPackages.haal(wp.value.bovenliggend_id).catch(() => null)
    }
  } catch (e) {
    fout.value = e?.message || 'Het werkpakket kon niet worden geladen.'
  } finally {
    laden.value = false
  }
})
</script>

<template>
  <section aria-labelledby="wp-detail-titel">
    <router-link
      :to="{ name: 'work-package-lijst' }"
      class="text-[length:var(--cd-text-sm)] text-[var(--cd-color-primary)] hover:underline"
    >
      ← Werkpakketten
    </router-link>

    <p v-if="fout" role="alert" data-testid="wp-detail-fout" class="my-[var(--cd-space-md)] text-[var(--cd-color-danger)]">
      {{ fout }}
    </p>
    <p v-else-if="laden" data-testid="wp-detail-laden" class="my-[var(--cd-space-md)] text-[var(--cd-color-text-muted)]">Laden…</p>

    <template v-else-if="wp">
      <h1
        id="wp-detail-titel"
        data-testid="wp-naam"
        class="mt-[var(--cd-space-sm)] mb-[var(--cd-space-sm)] text-[length:var(--cd-text-2xl)] font-semibold text-[var(--cd-color-primary)]"
      >
        {{ wp.naam }}
      </h1>
      <p v-if="wp.toelichting" class="mb-[var(--cd-space-md)] text-[var(--cd-color-text)]">{{ wp.toelichting }}</p>

      <p data-testid="wp-ouder" class="mb-[var(--cd-space-lg)] text-[var(--cd-color-text)]">
        <span class="font-medium">Onderdeel van:</span>
        <router-link
          v-if="wp.bovenliggend_id"
          :to="{ name: 'work-package-detail', params: { id: wp.bovenliggend_id } }"
          data-testid="wp-ouder-link"
          class="text-[var(--cd-color-primary)] hover:underline"
        >
          {{ ouder?.naam || 'bovenliggend pakket' }}
        </router-link>
        <span v-else> top-niveau (geen bovenliggend pakket)</span>
      </p>

      <h2 class="mb-[var(--cd-space-sm)] text-[length:var(--cd-text-lg)] font-semibold">
        Subpakketten ({{ directeSubpakketten.length }} direct)
      </h2>
      <DataTable
        :value="subboom"
        data-testid="wp-subboom-tabel"
        class="bg-[var(--cd-color-surface)] rounded-[var(--cd-radius-card)] shadow-[var(--cd-shadow-sm)]"
      >
        <Column field="naam" header="Naam">
          <template #body="{ data }">
            <router-link
              :to="{ name: 'work-package-detail', params: { id: data.id } }"
              class="text-[var(--cd-color-primary)] hover:underline"
            >
              {{ data.naam }}
            </router-link>
          </template>
        </Column>
        <Column field="niveau" header="Niveau" />
        <Column header="Pad">
          <template #body="{ data }">{{ data.pad.join(' › ') }}</template>
        </Column>
        <template #empty>
          <span data-testid="wp-subboom-leeg">Dit werkpakket heeft geen subpakketten.</span>
        </template>
      </DataTable>
    </template>
  </section>
</template>
