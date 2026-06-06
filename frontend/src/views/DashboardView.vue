<script setup>
/**
 * DashboardView — minimale geauthenticeerde landingspagina.
 * Begroeting met gebruiker/rol; de module-inhoud volgt in een latere opdracht.
 * Geen nep-data/-widgets.
 */
import { computed } from 'vue'
import { useAuthStore } from '../store/auth'

const auth = useAuthStore()
const rollen = computed(() => auth.roles)
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
      v-if="rollen.length"
      data-testid="dashboard-rollen"
      class="mb-[var(--cd-space-md)] text-[var(--cd-color-text-muted)]"
    >
      Rol(len): {{ rollen.join(', ') }}
    </p>

    <div class="card">
      <p>
        Je bent ingelogd in CompliData. De BWB-ontvlechtingsmodule verschijnt hier
        binnenkort.
      </p>
    </div>
  </section>
</template>
