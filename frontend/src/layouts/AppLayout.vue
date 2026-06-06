<script setup>
/**
 * AppLayout — geauthenticeerde app-shell (topbar + inklapbare sidebar).
 *
 * Topbar: app-naam, ingelogde gebruiker (e-mail), uitlog-knop.
 * Sidebar: sectie-navigatie (Dashboard nu; module-secties later).
 * Midden: <router-view> voor de geauthenticeerde child-routes.
 */
import { ref } from 'vue'
import { useAuthStore } from '../store/auth'
import Button from 'primevue/button'
import Toast from 'primevue/toast'

const auth = useAuthStore()
const ingeklapt = ref(_laadVoorkeur())

function _laadVoorkeur() {
  try {
    return localStorage.getItem('cd-sidebar-ingeklapt') === '1'
  } catch {
    return false
  }
}

function toggleSidebar() {
  ingeklapt.value = !ingeklapt.value
  try {
    localStorage.setItem('cd-sidebar-ingeklapt', ingeklapt.value ? '1' : '0')
  } catch {
    /* localStorage niet beschikbaar — voorkeur niet bewaren is acceptabel */
  }
}

async function uitloggen() {
  // OP-4-beperking (bewust): dit wist ALLEEN de lokale `cd_session`-cookie via
  // de auth-store; de Keycloak-SSO-sessie blijft staan. Een volgende /login kan
  // de gebruiker daardoor stilzwijgend opnieuw binnenlaten. RP-initiated logout
  // (Keycloak end-session) is OP-4 en valt buiten scope — hier geen eigen
  // end-session-aanroep. De store regelt de redirect naar /login.
  await auth.logout()
}
</script>

<template>
  <div class="min-h-screen flex flex-col bg-[var(--cd-color-bg)] text-[var(--cd-color-text)]">
    <!-- Topbar -->
    <header
      class="flex items-center gap-[var(--cd-space-md)] px-[var(--cd-space-lg)] py-[var(--cd-space-sm)] bg-[var(--cd-color-primary)] text-white shadow-[var(--cd-shadow-md)]"
    >
      <button
        type="button"
        data-testid="sidebar-toggle"
        :aria-expanded="(!ingeklapt).toString()"
        aria-controls="hoofd-navigatie"
        aria-label="Navigatie in- of uitklappen"
        class="rounded-[var(--cd-radius-btn)] px-[var(--cd-space-sm)] py-1 text-[length:var(--cd-text-lg)] leading-none hover:bg-white/15 focus:outline-2 focus:outline-offset-2 focus:outline-white"
        @click="toggleSidebar"
      >
        ☰
      </button>
      <span class="font-semibold text-[length:var(--cd-text-lg)]">CompliData</span>

      <div class="ml-auto flex items-center gap-[var(--cd-space-md)]">
        <span data-testid="gebruiker-email" class="text-[length:var(--cd-text-sm)]">
          {{ auth.user?.email }}
        </span>
        <Button
          label="Uitloggen"
          severity="secondary"
          size="small"
          data-testid="uitlog-knop"
          class="!bg-white/15 !text-white !border !border-white/50 hover:!bg-white/25 focus:!outline-white"
          @click="uitloggen"
        />
      </div>
    </header>

    <div class="flex flex-1 min-h-0">
      <!-- Sidebar -->
      <aside
        v-show="!ingeklapt"
        id="hoofd-navigatie"
        class="w-60 shrink-0 bg-[var(--cd-color-surface)] border-r border-[var(--cd-color-border)] p-[var(--cd-space-md)]"
      >
        <nav aria-label="Hoofdnavigatie" class="flex flex-col gap-[var(--cd-space-xs)]">
          <router-link
            :to="{ name: 'dashboard' }"
            data-testid="nav-dashboard"
            class="rounded-[var(--cd-radius-nav)] px-[var(--cd-space-md)] py-[var(--cd-space-sm)] text-[var(--cd-color-text)] hover:bg-[var(--cd-color-accent)] aria-[current=page]:bg-[var(--cd-color-accent)] aria-[current=page]:font-semibold"
          >
            Dashboard
          </router-link>

          <span
            class="mt-[var(--cd-space-md)] px-[var(--cd-space-md)] text-[length:var(--cd-text-xs)] font-semibold uppercase tracking-wide text-[var(--cd-color-text-muted)]"
          >
            BWB-ontvlechting
          </span>
          <router-link
            :to="{ name: 'applicatie-lijst' }"
            data-testid="nav-applicaties"
            class="rounded-[var(--cd-radius-nav)] px-[var(--cd-space-md)] py-[var(--cd-space-sm)] text-[var(--cd-color-text)] hover:bg-[var(--cd-color-accent)] aria-[current=page]:bg-[var(--cd-color-accent)] aria-[current=page]:font-semibold"
          >
            Applicaties
          </router-link>
        </nav>
      </aside>

      <!-- Hoofdinhoud -->
      <main class="flex-1 min-w-0 p-[var(--cd-space-xl)]">
        <router-view />
      </main>
    </div>

    <!-- Toast-container voor feedback uit de geauthenticeerde views -->
    <Toast />
  </div>
</template>
