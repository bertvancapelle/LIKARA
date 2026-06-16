<script setup>
/**
 * PlateauLijstView — migratielaag (ADR-023 Fase F / F-1): lijst van plateaus.
 * Read-only; leunt op `GET /plateaus`. Keyset-paginering ("Meer laden").
 */
import { onMounted, ref } from 'vue'
import { Button, Column, DataTable } from '@/primevue'
import { api } from '@/api'

const items = ref([])
const cursor = ref(null)
const laden = ref(false)
const fout = ref(null)
const eersteGeladen = ref(false)

async function laad({ reset = false } = {}) {
  laden.value = true
  fout.value = null
  try {
    const pagina = await api.plateaus.lijst({ limit: 25, after: reset ? undefined : cursor.value })
    items.value = reset ? pagina.items : items.value.concat(pagina.items)
    cursor.value = pagina.volgende_cursor
  } catch (e) {
    fout.value = e?.message || 'Er ging iets mis bij het laden van de plateaus.'
  } finally {
    laden.value = false
    eersteGeladen.value = true
  }
}

onMounted(() => laad({ reset: true }))
</script>

<template>
  <section aria-labelledby="plateaus-titel">
    <h1
      id="plateaus-titel"
      class="mb-[var(--cd-space-md)] text-[length:var(--cd-text-2xl)] font-semibold text-[var(--cd-color-primary)]"
    >
      Plateaus
    </h1>

    <p
      v-if="fout"
      role="alert"
      data-testid="plateau-lijst-fout"
      class="mb-[var(--cd-space-md)] rounded-[var(--cd-radius-badge)] border border-[var(--cd-color-danger)] bg-[var(--cd-color-danger)]/10 px-[var(--cd-space-md)] py-[var(--cd-space-sm)] text-[var(--cd-color-danger)]"
    >
      {{ fout }}
    </p>

    <DataTable
      :value="items"
      data-testid="plateaus-tabel"
      class="bg-[var(--cd-color-surface)] rounded-[var(--cd-radius-card)] shadow-[var(--cd-shadow-sm)]"
    >
      <Column field="naam" header="Naam">
        <template #body="{ data }">
          <router-link
            :to="{ name: 'plateau-detail', params: { id: data.id } }"
            data-testid="plateau-link"
            class="text-[var(--cd-color-primary)] font-medium hover:underline focus:outline-2 focus:outline-offset-2 focus:outline-[var(--cd-color-primary)]"
          >
            {{ data.naam }}
          </router-link>
        </template>
      </Column>
      <Column header="Toelichting">
        <template #body="{ data }">
          <span class="block max-w-[40ch] truncate" :title="data.toelichting || ''">
            {{ data.toelichting || '—' }}
          </span>
        </template>
      </Column>
      <template #empty>
        <span v-if="eersteGeladen && !laden" data-testid="plateau-lijst-leeg">
          Nog geen plateaus geregistreerd.
        </span>
        <span v-else>Laden…</span>
      </template>
    </DataTable>

    <div class="mt-[var(--cd-space-md)]">
      <Button
        v-if="cursor"
        label="Meer laden"
        severity="secondary"
        data-testid="meer-laden"
        :disabled="laden"
        @click="laad()"
      />
    </div>
  </section>
</template>
