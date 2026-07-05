<script setup>
/**
 * DashboardView — tenant-breed overzicht (CD014, #9; ADR-022 Fase F, Besluit 3).
 *
 * Drie blokken op basis van één read-only aggregatie (`GET /api/v1/dashboard`):
 * (a) readiness per componenttype (één blok per checklist-dragend type, geen
 * gefuseerd totaal), (b) open-blokkades-teller, (c) recentst gewijzigde
 * componenten. Begroeting met gebruiker/rol blijft.
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
    fout.value = e?.status === 401 ? null : e?.message || 'Er ging iets mis bij het laden van het dashboard.'
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
      class="text-[length:var(--lk-text-2xl)] font-semibold text-[var(--lk-color-primary)] mb-[var(--lk-space-sm)]"
    >
      Welkom<span v-if="auth.user?.email">, {{ auth.user.email }}</span>
    </h1>

    <p
      v-if="auth.roles.length"
      data-testid="dashboard-rollen"
      class="mb-[var(--lk-space-md)] text-[var(--lk-color-text-muted)]"
    >
      Rol(len): {{ auth.roles.join(', ') }}
    </p>

    <p
      v-if="fout"
      role="alert"
      data-testid="dashboard-fout"
      class="mb-[var(--lk-space-md)] rounded-[var(--lk-radius-badge)] border border-[var(--lk-color-danger)] bg-[var(--lk-color-danger)]/10 px-[var(--lk-space-md)] py-[var(--lk-space-sm)] text-[var(--lk-color-danger)]"
    >
      {{ fout }}
    </p>

    <p
      v-else-if="laden && !geladen"
      data-testid="dashboard-laden"
      class="text-[var(--lk-color-text-muted)]"
    >
      Dashboard laden…
    </p>

    <div v-else-if="data" class="flex flex-col gap-[var(--lk-space-lg)]">
      <!-- (a) Readiness per componenttype (ADR-022 Fase F, Besluit 3) -->
      <div aria-labelledby="dashboard-readiness-titel">
        <h2
          id="dashboard-readiness-titel"
          class="text-[length:var(--lk-text-lg)] font-semibold mb-[var(--lk-space-sm)]"
        >
          Gereedheid per componenttype
        </h2>

        <div
          v-if="data.readiness_per_type.length"
          class="flex flex-col gap-[var(--lk-space-md)]"
        >
          <div
            v-for="t in data.readiness_per_type"
            :key="t.componenttype"
            :data-testid="`readiness-type-${t.componenttype}`"
            aria-labelledby="dashboard-readiness-titel"
          >
            <h3 class="text-[length:var(--lk-text-md)] font-semibold mb-[var(--lk-space-xs)]">
              {{ t.componenttype_label }}
            </h3>
            <div class="grid grid-cols-2 md:grid-cols-4 gap-[var(--lk-space-md)]">
              <!-- Klikbare statustegel → componentenlijst, voorgefilterd op exact deze
                   status én dit componenttype (de lijst reproduceert de telling). Zelfde
                   klikbare-tegel-patroon als de open-blokkades-tegel. -->
              <router-link
                v-for="status in STATUS_VOLGORDE"
                :key="status"
                :to="{ name: 'component-lijst', query: { status, type: t.componenttype } }"
                :data-testid="`telling-${t.componenttype}-${status}`"
                :aria-label="`${t.telling[status] ?? 0} ${lifecycleLabel(status)} — ${t.componenttype_label}, bekijk de componenten`"
                class="card flex flex-col gap-[var(--lk-space-xs)] bg-[var(--lk-color-surface)] rounded-[var(--lk-radius-card)] shadow-[var(--lk-shadow-sm)] p-[var(--lk-space-md)] hover:shadow-[var(--lk-shadow-md)] focus:outline-2 focus:outline-offset-2 focus:outline-[var(--lk-color-primary)]"
              >
                <span class="text-[length:var(--lk-text-2xl)] font-semibold text-[var(--lk-color-primary)]">
                  {{ t.telling[status] ?? 0 }}
                </span>
                <Tag :value="lifecycleLabel(status)" :severity="lifecycleSeverity(status)" />
              </router-link>
            </div>
            <p
              :data-testid="`readiness-rollup-${t.componenttype}`"
              class="mt-[var(--lk-space-xs)] text-[var(--lk-color-text-muted)]"
            >
              {{ t.migratieklaar }} van {{ t.totaal }} migratieklaar
            </p>
          </div>
        </div>

        <p v-else data-testid="readiness-leeg" class="text-[var(--lk-color-text-muted)]">
          Nog geen beoordeelde componenten in deze tenant.
        </p>
      </div>

      <!-- (b) Actieve blokkades (open + in behandeling — ADR-013-definitie) -->
      <div aria-labelledby="dashboard-blokkades-titel">
        <h2
          id="dashboard-blokkades-titel"
          class="text-[length:var(--lk-text-lg)] font-semibold mb-[var(--lk-space-sm)]"
        >
          Actieve blokkades
        </h2>
        <router-link
          :to="{ name: 'blokkades', query: { status: 'actief' } }"
          data-testid="open-blokkades"
          class="card inline-flex items-baseline gap-[var(--lk-space-sm)] bg-[var(--lk-color-surface)] rounded-[var(--lk-radius-card)] shadow-[var(--lk-shadow-sm)] px-[var(--lk-space-lg)] py-[var(--lk-space-md)] hover:shadow-[var(--lk-shadow-md)] focus:outline-2 focus:outline-offset-2 focus:outline-[var(--lk-color-primary)]"
        >
          <span
            class="text-[length:var(--lk-text-2xl)] font-semibold"
            :class="data.open_blokkades > 0 ? 'text-[var(--lk-color-danger)]' : 'text-[var(--lk-color-text-muted)]'"
          >
            {{ data.open_blokkades }}
          </span>
          <span class="text-[var(--lk-color-text-muted)]">
            {{ data.open_blokkades === 1 ? 'actieve blokkade' : 'actieve blokkades' }}
          </span>
        </router-link>
      </div>

      <!-- (b2) ADR-027 slice 3 — klaarverklaring-voortgang (read-only afgeleid; engine ongemoeid) -->
      <div aria-labelledby="dashboard-klaarverklaring-titel">
        <h2
          id="dashboard-klaarverklaring-titel"
          class="text-[length:var(--lk-text-lg)] font-semibold mb-[var(--lk-space-sm)]"
        >
          Migratiegereedheid
        </h2>
        <div class="flex flex-wrap gap-[var(--lk-space-md)]">
          <router-link
            :to="{ name: 'component-lijst', query: { klaarverklaring: 'klaar' } }"
            data-testid="telling-klaar-verklaard"
            class="card inline-flex items-baseline gap-[var(--lk-space-sm)] bg-[var(--lk-color-surface)] rounded-[var(--lk-radius-card)] shadow-[var(--lk-shadow-sm)] px-[var(--lk-space-lg)] py-[var(--lk-space-md)] hover:shadow-[var(--lk-shadow-md)] focus:outline-2 focus:outline-offset-2 focus:outline-[var(--lk-color-primary)]"
          >
            <span class="text-[length:var(--lk-text-2xl)] font-semibold text-[var(--lk-color-success)]">{{ data.klaar_verklaard }}</span>
            <span class="text-[var(--lk-color-text-muted)]">klaar verklaard</span>
          </router-link>

          <router-link
            :to="{ name: 'component-lijst', query: { afwijking: 1 } }"
            data-testid="telling-klaar-afwijking"
            class="card inline-flex items-baseline gap-[var(--lk-space-sm)] rounded-[var(--lk-radius-card)] shadow-[var(--lk-shadow-sm)] px-[var(--lk-space-lg)] py-[var(--lk-space-md)] hover:shadow-[var(--lk-shadow-md)] focus:outline-2 focus:outline-offset-2 focus:outline-[var(--lk-color-primary)]"
            :class="data.klaar_met_afwijking > 0 ? 'bg-[color-mix(in_srgb,var(--lk-color-warn)_12%,transparent)]' : 'bg-[var(--lk-color-surface)]'"
          >
            <span aria-hidden="true" class="text-[length:var(--lk-text-xl)]">⚠</span>
            <span
              class="text-[length:var(--lk-text-2xl)] font-semibold"
              :class="data.klaar_met_afwijking > 0 ? 'text-[var(--lk-color-warn)]' : 'text-[var(--lk-color-text-muted)]'"
            >{{ data.klaar_met_afwijking }}</span>
            <span class="text-[var(--lk-color-text-muted)]">klaar verklaard, checklist nog niet compleet</span>
          </router-link>
        </div>
      </div>

      <!-- (c) Recent gewijzigd -->
      <div aria-labelledby="dashboard-recent-titel">
        <h2
          id="dashboard-recent-titel"
          class="text-[length:var(--lk-text-lg)] font-semibold mb-[var(--lk-space-sm)]"
        >
          Recent gewijzigd
        </h2>
        <ul
          v-if="data.recent_gewijzigd.length"
          data-testid="recent-lijst"
          class="flex flex-col gap-[var(--lk-space-xs)]"
        >
          <li
            v-for="app in data.recent_gewijzigd"
            :key="app.id"
            class="flex items-center gap-[var(--lk-space-md)] bg-[var(--lk-color-surface)] rounded-[var(--lk-radius-card)] shadow-[var(--lk-shadow-sm)] px-[var(--lk-space-md)] py-[var(--lk-space-sm)]"
          >
            <router-link
              :to="{ name: 'component-detail', params: { id: app.id } }"
              data-testid="recent-link"
              class="text-[var(--lk-color-primary)] font-medium hover:underline focus:outline-2 focus:outline-offset-2 focus:outline-[var(--lk-color-primary)]"
            >
              {{ app.naam }}
            </router-link>
            <Tag :value="lifecycleLabel(app.lifecycle_status)" :severity="lifecycleSeverity(app.lifecycle_status)" />
            <span class="ml-auto text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]">
              {{ formatDatum(app.gewijzigd_op) }}
            </span>
          </li>
        </ul>
        <p v-else data-testid="recent-leeg" class="text-[var(--lk-color-text-muted)]">
          Er zijn nog geen componenten in deze tenant.
        </p>
      </div>
    </div>
  </section>
</template>
