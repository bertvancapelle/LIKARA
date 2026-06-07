<script setup>
/**
 * DashboardView — tenant-breed overzicht (CD014, #9).
 *
 * Drie blokken op basis van één read-only aggregatie (`GET /api/v1/dashboard`):
 * (a) applicaties per lifecycle-status, (b) open-blokkades-teller,
 * (c) recentst gewijzigde applicaties. Begroeting met gebruiker/rol blijft.
 *
 * Module-presentatie (labels/severity) via de cross-root-barrel
 * `@modules/bwb_ontvlechting/frontend/labels` — geen platform↔module-koppeling
 * in code, alleen presentatie. Geen nep-data: leeg blijft leeg.
 */
import { onMounted, ref } from 'vue'
import { Tag } from '@/primevue'
import { useAuthStore } from '@/store/auth'
import { api } from '@/api'
import { LIFECYCLE, LIFECYCLE_SEVERITY, label } from '@modules/bwb_ontvlechting/frontend/labels'

const auth = useAuthStore()

// Vaste toon-volgorde van de reële lifecycle-statussen (checklist_compleet is
// transient en zit niet in de telling).
const STATUS_VOLGORDE = ['concept', 'in_inventarisatie', 'geblokkeerd', 'migratieklaar']

const data = ref(null)
const laden = ref(false)
const fout = ref(null)
const geladen = ref(false)

async function laad() {
  laden.value = true
  fout.value = null
  try {
    data.value = await api.dashboard()
  } catch (e) {
    fout.value = e?.message || 'Er ging iets mis bij het laden van het dashboard.'
  } finally {
    laden.value = false
    geladen.value = true
  }
}

const lifecycleLabel = (c) => label(LIFECYCLE, c)
const lifecycleSeverity = (c) => LIFECYCLE_SEVERITY[c] || 'info'

function formatDatum(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  return new Intl.DateTimeFormat('nl-NL', { dateStyle: 'medium', timeStyle: 'short' }).format(d)
}

onMounted(laad)
</script>

<template>
  <section aria-labelledby="dashboard-titel">
    <h1
      id="dashboard-titel"
      class="text-[length:var(--cd-text-2xl)] font-semibold text-[var(--cd-color-primary)] mb-[var(--cd-space-sm)]"
    >
      Welkom<span v-if="auth.user?.email">, {{ auth.user.email }}</span>
    </h1>

    <p
      v-if="auth.roles.length"
      data-testid="dashboard-rollen"
      class="mb-[var(--cd-space-md)] text-[var(--cd-color-text-muted)]"
    >
      Rol(len): {{ auth.roles.join(', ') }}
    </p>

    <p
      v-if="fout"
      role="alert"
      data-testid="dashboard-fout"
      class="mb-[var(--cd-space-md)] rounded-[var(--cd-radius-badge)] border border-[var(--cd-color-danger)] bg-[var(--cd-color-danger)]/10 px-[var(--cd-space-md)] py-[var(--cd-space-sm)] text-[var(--cd-color-danger)]"
    >
      {{ fout }}
    </p>

    <p
      v-else-if="laden && !geladen"
      data-testid="dashboard-laden"
      class="text-[var(--cd-color-text-muted)]"
    >
      Dashboard laden…
    </p>

    <div v-else-if="data" class="flex flex-col gap-[var(--cd-space-lg)]">
      <!-- (a) Applicaties per lifecycle-status -->
      <div aria-labelledby="dashboard-lifecycle-titel">
        <h2
          id="dashboard-lifecycle-titel"
          class="text-[length:var(--cd-text-lg)] font-semibold mb-[var(--cd-space-sm)]"
        >
          Applicaties per status
        </h2>
        <div data-testid="lifecycle-telling" class="grid grid-cols-2 md:grid-cols-4 gap-[var(--cd-space-md)]">
          <div
            v-for="status in STATUS_VOLGORDE"
            :key="status"
            :data-testid="`telling-${status}`"
            class="card flex flex-col gap-[var(--cd-space-xs)] bg-[var(--cd-color-surface)] rounded-[var(--cd-radius-card)] shadow-[var(--cd-shadow-sm)] p-[var(--cd-space-md)]"
          >
            <span class="text-[length:var(--cd-text-2xl)] font-semibold text-[var(--cd-color-primary)]">
              {{ data.lifecycle_telling[status] ?? 0 }}
            </span>
            <Tag :value="lifecycleLabel(status)" :severity="lifecycleSeverity(status)" />
          </div>
        </div>
      </div>

      <!-- (b) Open blokkades -->
      <div aria-labelledby="dashboard-blokkades-titel">
        <h2
          id="dashboard-blokkades-titel"
          class="text-[length:var(--cd-text-lg)] font-semibold mb-[var(--cd-space-sm)]"
        >
          Open blokkades
        </h2>
        <div
          data-testid="open-blokkades"
          class="card inline-flex items-baseline gap-[var(--cd-space-sm)] bg-[var(--cd-color-surface)] rounded-[var(--cd-radius-card)] shadow-[var(--cd-shadow-sm)] px-[var(--cd-space-lg)] py-[var(--cd-space-md)]"
        >
          <span
            class="text-[length:var(--cd-text-2xl)] font-semibold"
            :class="data.open_blokkades > 0 ? 'text-[var(--cd-color-danger)]' : 'text-[var(--cd-color-text-muted)]'"
          >
            {{ data.open_blokkades }}
          </span>
          <span class="text-[var(--cd-color-text-muted)]">
            {{ data.open_blokkades === 1 ? 'open blokkade' : 'open blokkades' }}
          </span>
        </div>
      </div>

      <!-- (c) Recent gewijzigd -->
      <div aria-labelledby="dashboard-recent-titel">
        <h2
          id="dashboard-recent-titel"
          class="text-[length:var(--cd-text-lg)] font-semibold mb-[var(--cd-space-sm)]"
        >
          Recent gewijzigd
        </h2>
        <ul
          v-if="data.recent_gewijzigd.length"
          data-testid="recent-lijst"
          class="flex flex-col gap-[var(--cd-space-xs)]"
        >
          <li
            v-for="app in data.recent_gewijzigd"
            :key="app.id"
            class="flex items-center gap-[var(--cd-space-md)] bg-[var(--cd-color-surface)] rounded-[var(--cd-radius-card)] shadow-[var(--cd-shadow-sm)] px-[var(--cd-space-md)] py-[var(--cd-space-sm)]"
          >
            <router-link
              :to="{ name: 'applicatie-detail', params: { id: app.id } }"
              data-testid="recent-link"
              class="text-[var(--cd-color-primary)] font-medium hover:underline focus:outline-2 focus:outline-offset-2 focus:outline-[var(--cd-color-primary)]"
            >
              {{ app.naam }}
            </router-link>
            <Tag :value="lifecycleLabel(app.lifecycle_status)" :severity="lifecycleSeverity(app.lifecycle_status)" />
            <span class="ml-auto text-[length:var(--cd-text-sm)] text-[var(--cd-color-text-muted)]">
              {{ formatDatum(app.gewijzigd_op) }}
            </span>
          </li>
        </ul>
        <p v-else data-testid="recent-leeg" class="text-[var(--cd-color-text-muted)]">
          Er zijn nog geen applicaties in deze tenant.
        </p>
      </div>
    </div>
  </section>
</template>
