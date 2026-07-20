<script setup>
/**
 * PlaatsingSignalenView — consistentie-signalering technische plaatsing
 * (ADR-023 Fase F / F-3 stap 2).
 *
 * Read-only attentielijst: per component een zacht signaal waar het checklist-antwoord
 * over technische plaatsing níét overeenkomt met het bestaan van een draait_op-relatie.
 * Geen fout, blokkeert niets. Leunt volledig op `GET /signalen/plaatsing` (server-side
 * afgeleid uit de betekenis-markering × draait_op). Generiek over componenttypen.
 */
import { onMounted, ref } from 'vue'
import { api } from '@/api'
import { detailRoute } from '@/detailIngang'
import { humaniseer } from '@modules/bwb_ontvlechting/frontend/labels'

// Leesbare signaalteksten (geen jargon).
const SIGNAAL_LABEL = {
  beoordeeld_niet_vastgelegd: 'Plaatsing beoordeeld maar niet vastgelegd',
  vastgelegd_niet_beoordeeld: 'Plaatsing vastgelegd maar niet beoordeeld',
}

const items = ref([])
const laden = ref(false)
const fout = ref(null)
const eersteGeladen = ref(false)

const signaalLabel = (s) => SIGNAAL_LABEL[s] || s
const typeLabel = (t) => humaniseer(t)

async function laad() {
  laden.value = true
  fout.value = null
  try {
    items.value = await api.signalen.plaatsing()
  } catch (e) {
    fout.value = e?.status === 401 ? null : e?.message || 'Er ging iets mis bij het laden van de plaatsingssignalen.'
  } finally {
    laden.value = false
    eersteGeladen.value = true
  }
}

onMounted(laad)
</script>

<template>
  <section aria-labelledby="signalen-titel">
    <h1
      id="signalen-titel"
      class="mb-[var(--lk-space-sm)] text-[var(--lk-color-primary)]"
    >
      Plaatsingssignalen
    </h1>
    <p class="mb-[var(--lk-space-md)] text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]">
      Attentiepunten waar het antwoord over technische plaatsing niet overeenkomt met of het
      component daadwerkelijk ergens op draait. Een zacht signaal — geen fout, blokkeert niets.
    </p>

    <p v-if="fout" role="alert" data-testid="signalen-fout" class="mb-[var(--lk-space-md)] rounded-[var(--lk-radius-badge)] border border-[var(--lk-color-danger)] bg-[var(--lk-color-danger)]/10 px-[var(--lk-space-md)] py-[var(--lk-space-sm)] text-[var(--lk-color-danger)]">
      {{ fout }}
    </p>
    <p v-if="laden && !eersteGeladen" data-testid="signalen-laden" class="text-[var(--lk-color-text-muted)]">Laden…</p>

    <p
      v-if="eersteGeladen && !laden && items.length === 0"
      data-testid="signalen-leeg"
      class="rounded-[var(--lk-radius-card)] bg-[var(--lk-color-surface)] px-[var(--lk-space-md)] py-[var(--lk-space-md)] text-[var(--lk-color-text-muted)] shadow-[var(--lk-shadow-sm)]"
    >
      Geen plaatsingssignalen — alle beoordeelde plaatsingen komen overeen met de vastgelegde relaties.
    </p>

    <table
      v-else-if="items.length"
      data-testid="signalen-tabel"
      class="w-full bg-[var(--lk-color-surface)] rounded-[var(--lk-radius-card)] shadow-[var(--lk-shadow-sm)] text-[length:var(--lk-text-sm)]"
    >
      <thead>
        <tr class="text-left text-[length:var(--lk-text-xs)] uppercase tracking-wide text-[var(--lk-color-text-muted)]">
          <th class="px-[var(--lk-space-md)] py-[var(--lk-space-sm)]">Component</th>
          <th class="px-[var(--lk-space-md)] py-[var(--lk-space-sm)]">Type</th>
          <th class="px-[var(--lk-space-md)] py-[var(--lk-space-sm)]">Signaal</th>
          <th class="px-[var(--lk-space-md)] py-[var(--lk-space-sm)]">Reden</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="s in items"
          :key="s.component_id"
          :data-testid="`signaal-${s.component_id}`"
          class="border-t border-[var(--lk-color-border)]"
        >
          <td class="px-[var(--lk-space-md)] py-[var(--lk-space-sm)] font-medium">
            <router-link
              :to="detailRoute('component', s.component_id)"
              :data-testid="`signaal-link-${s.component_id}`"
              class="text-[var(--lk-color-primary)] hover:underline focus:outline-2 focus:outline-offset-2 focus:outline-[var(--lk-color-primary)]"
            >
              {{ s.naam }}
            </router-link>
          </td>
          <td class="px-[var(--lk-space-md)] py-[var(--lk-space-sm)]">{{ typeLabel(s.componenttype) }}</td>
          <td class="px-[var(--lk-space-md)] py-[var(--lk-space-sm)]">
            <span
              :data-testid="`signaal-type-${s.component_id}`"
              class="inline-block rounded-[var(--lk-radius-badge)] bg-[var(--lk-color-warning)]/15 px-[var(--lk-space-sm)] py-[2px] text-[var(--lk-color-warning-text,var(--lk-color-text))]"
            >{{ signaalLabel(s.signaal) }}</span>
          </td>
          <td class="px-[var(--lk-space-md)] py-[var(--lk-space-sm)] text-[var(--lk-color-text-muted)]">{{ s.reden }}</td>
        </tr>
      </tbody>
    </table>
  </section>
</template>
