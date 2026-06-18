<script setup>
/**
 * AppLayout — geauthenticeerde app-shell (topbar + inklapbare sidebar).
 *
 * Topbar: app-naam, ingelogde gebruiker (e-mail), uitlog-knop.
 * Sidebar: sectie-navigatie (Dashboard nu; module-secties later).
 * Midden: <router-view> voor de geauthenticeerde child-routes.
 */
import { computed, ref } from 'vue'
import { useAuthStore } from '../store/auth'
import Button from 'primevue/button'
import Toast from 'primevue/toast'

const auth = useAuthStore()
const ingeklapt = ref(_laadVoorkeur())

// F-1/F-5: de migratielaag-views zijn voor elke tenant-rol leesbaar (RBAC `_INHOUD`).
// De nav-groep is de affordance; de backend handhaaft (vereist_permissie). Geen rol ⇒
// niet zichtbaar.
const magMigratieZien = computed(() =>
  auth.hasRole('viewer', 'medewerker', 'beheerder', 'auditor'),
)
// F-2: het architectuuroverzicht (ARCHITECTUUR.LEZEN) — élke tenant-rol leest.
const magArchitectuurZien = computed(() =>
  auth.hasRole('viewer', 'medewerker', 'beheerder', 'auditor'),
)

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
  // RP-initiated logout (OP-4, CD008/CD010): de store roept `/auth/logout` aan
  // (wist `cd_session`/`cd_refresh` + trekt het Redis-refresh-handle in) en
  // navigeert naar de Keycloak end-session-URL, zodat óók de SSO-sessie eindigt
  // (geen stil herinloggen). Zonder URL valt de store terug op `/login`.
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
          <!-- ADR-021 W1 (CD054b): "Applicaties" als apart menu-item vervallen —
               Componenten is de enige ingang; "alle applicaties" = typefilter Applicatie. -->
          <router-link
            :to="{ name: 'component-lijst' }"
            data-testid="nav-componenten"
            class="rounded-[var(--cd-radius-nav)] px-[var(--cd-space-md)] py-[var(--cd-space-sm)] text-[var(--cd-color-text)] hover:bg-[var(--cd-color-accent)] aria-[current=page]:bg-[var(--cd-color-accent)] aria-[current=page]:font-semibold"
          >
            Componenten
          </router-link>
          <router-link
            :to="{ name: 'partij-lijst' }"
            data-testid="nav-partijen"
            class="rounded-[var(--cd-radius-nav)] px-[var(--cd-space-md)] py-[var(--cd-space-sm)] text-[var(--cd-color-text)] hover:bg-[var(--cd-color-accent)] aria-[current=page]:bg-[var(--cd-color-accent)] aria-[current=page]:font-semibold"
          >
            Partijen
          </router-link>
          <router-link
            :to="{ name: 'contract-lijst' }"
            data-testid="nav-contracten"
            class="rounded-[var(--cd-radius-nav)] px-[var(--cd-space-md)] py-[var(--cd-space-sm)] text-[var(--cd-color-text)] hover:bg-[var(--cd-color-accent)] aria-[current=page]:bg-[var(--cd-color-accent)] aria-[current=page]:font-semibold"
          >
            Contracten
          </router-link>
          <router-link
            :to="{ name: 'blokkades' }"
            data-testid="nav-blokkades"
            class="rounded-[var(--cd-radius-nav)] px-[var(--cd-space-md)] py-[var(--cd-space-sm)] text-[var(--cd-color-text)] hover:bg-[var(--cd-color-accent)] aria-[current=page]:bg-[var(--cd-color-accent)] aria-[current=page]:font-semibold"
          >
            Blokkades
          </router-link>
          <router-link
            :to="{ name: 'koppelingenkaart' }"
            data-testid="nav-koppelingenkaart"
            class="rounded-[var(--cd-radius-nav)] px-[var(--cd-space-md)] py-[var(--cd-space-sm)] text-[var(--cd-color-text)] hover:bg-[var(--cd-color-accent)] aria-[current=page]:bg-[var(--cd-color-accent)] aria-[current=page]:font-semibold"
          >
            Koppelingenkaart
          </router-link>
          <router-link
            v-if="magArchitectuurZien"
            :to="{ name: 'architectuur' }"
            data-testid="nav-architectuur"
            class="rounded-[var(--cd-radius-nav)] px-[var(--cd-space-md)] py-[var(--cd-space-sm)] text-[var(--cd-color-text)] hover:bg-[var(--cd-color-accent)] aria-[current=page]:bg-[var(--cd-color-accent)] aria-[current=page]:font-semibold"
          >
            Architectuur
          </router-link>
          <router-link
            v-if="magArchitectuurZien"
            :to="{ name: 'plaatsingssignalen' }"
            data-testid="nav-plaatsingssignalen"
            class="rounded-[var(--cd-radius-nav)] px-[var(--cd-space-md)] py-[var(--cd-space-sm)] text-[var(--cd-color-text)] hover:bg-[var(--cd-color-accent)] aria-[current=page]:bg-[var(--cd-color-accent)] aria-[current=page]:font-semibold"
          >
            Plaatsingssignalen
          </router-link>
          <router-link
            :to="{ name: 'checklistvragen' }"
            data-testid="nav-checklistvragen"
            class="rounded-[var(--cd-radius-nav)] px-[var(--cd-space-md)] py-[var(--cd-space-sm)] text-[var(--cd-color-text)] hover:bg-[var(--cd-color-accent)] aria-[current=page]:bg-[var(--cd-color-accent)] aria-[current=page]:font-semibold"
          >
            Checklistvragen
          </router-link>

          <!-- ADR-023 Fase F (F-1): migratielaag-overzicht, één "Migratie"-groep met vier
               sub-items. Gegate op leesrecht (elke tenant-rol heeft dat). -->
          <template v-if="magMigratieZien">
            <span
              data-testid="nav-migratie-groep"
              class="mt-[var(--cd-space-md)] px-[var(--cd-space-md)] text-[length:var(--cd-text-xs)] font-semibold uppercase tracking-wide text-[var(--cd-color-text-muted)]"
            >
              Migratie
            </span>
            <router-link
              :to="{ name: 'plateau-lijst' }"
              data-testid="nav-plateaus"
              class="rounded-[var(--cd-radius-nav)] px-[var(--cd-space-md)] py-[var(--cd-space-sm)] text-[var(--cd-color-text)] hover:bg-[var(--cd-color-accent)] aria-[current=page]:bg-[var(--cd-color-accent)] aria-[current=page]:font-semibold"
            >
              Plateaus
            </router-link>
            <router-link
              :to="{ name: 'gap-lijst' }"
              data-testid="nav-gaps"
              class="rounded-[var(--cd-radius-nav)] px-[var(--cd-space-md)] py-[var(--cd-space-sm)] text-[var(--cd-color-text)] hover:bg-[var(--cd-color-accent)] aria-[current=page]:bg-[var(--cd-color-accent)] aria-[current=page]:font-semibold"
            >
              Gaps
            </router-link>
            <router-link
              :to="{ name: 'work-package-lijst' }"
              data-testid="nav-werkpakketten"
              class="rounded-[var(--cd-radius-nav)] px-[var(--cd-space-md)] py-[var(--cd-space-sm)] text-[var(--cd-color-text)] hover:bg-[var(--cd-color-accent)] aria-[current=page]:bg-[var(--cd-color-accent)] aria-[current=page]:font-semibold"
            >
              Werkpakketten
            </router-link>
            <router-link
              :to="{ name: 'deliverable-lijst' }"
              data-testid="nav-deliverables"
              class="rounded-[var(--cd-radius-nav)] px-[var(--cd-space-md)] py-[var(--cd-space-sm)] text-[var(--cd-color-text)] hover:bg-[var(--cd-color-accent)] aria-[current=page]:bg-[var(--cd-color-accent)] aria-[current=page]:font-semibold"
            >
              Deliverables
            </router-link>
          </template>
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
