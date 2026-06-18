<script setup>
/**
 * PartijRollenSectie — rollen die één partij vervult op objecten (ADR-024 slice 2b).
 *
 * Gemount op partij-detail (alleen-lezen). Toont op welke componenten/contracten de partij een
 * rol heeft (Object · Type · Rol). Géén toevoeg-knop: een toewijzing ontstaat vanuit het object
 * (component-/contract-detail), niet vanuit de partij. Registratief; raakt de engine niet.
 */
import { computed, onMounted, ref } from 'vue'
import { Column, DataTable, Tag } from '@/primevue'
import { api } from '@/api'
import { humaniseer } from '../labels'

const props = defineProps({ partijId: { type: String, required: true } })

const items = ref([])
const laden = ref(false)

// Object-type → detail-route (subtype-componenten linken net als elders naar component-detail).
const objectRoute = (rij) =>
  rij.object_type === 'contract'
    ? { name: 'contract-detail', params: { id: rij.object_id } }
    : { name: 'component-detail', params: { id: rij.object_id } }
const typeLabel = (t) => humaniseer(t)

async function laad() {
  laden.value = true
  try {
    items.value = await api.roltoewijzingen.lijst({ partij_id: props.partijId })
  } catch {
    items.value = []
  } finally {
    laden.value = false
  }
}

onMounted(laad)
const heeftRijen = computed(() => items.value.length > 0)
defineExpose({ items, laad })
</script>

<template>
  <section class="card" aria-labelledby="sectie-partij-rollen" data-testid="pr-sectie">
    <h2 id="sectie-partij-rollen" class="text-[length:var(--cd-text-lg)] font-semibold mb-[var(--cd-space-sm)]">
      Rollen op objecten
    </h2>
    <DataTable :value="items" data-testid="pr-tabel">
      <Column header="Object">
        <template #body="{ data }">
          <router-link :to="objectRoute(data)" data-testid="pr-object-link" class="text-[var(--cd-color-primary)] hover:underline">{{ data.object_naam }}</router-link>
        </template>
      </Column>
      <Column header="Type"><template #body="{ data }"><Tag :value="typeLabel(data.object_type)" severity="secondary" /></template></Column>
      <Column header="Rol"><template #body="{ data }">{{ data.rol_label }}</template></Column>
      <template #empty><span data-testid="pr-leeg">Deze partij heeft nog geen rollen op objecten.</span></template>
    </DataTable>
  </section>
</template>
