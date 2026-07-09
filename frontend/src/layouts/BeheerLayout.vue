<script setup>
/**
 * BeheerLayout — platform-app-shell (ADR-012 / ADR-019 fase 2E-b).
 *
 * Aparte, lichte shell voor de PLATFORM-sectie (`/beheer/*`), los van de
 * tenant-`AppLayout`. Topbar: app-naam + "Beheer", platform-e-mail, uitloggen.
 * Nav: contract- en componentcatalogus (ADR-022 W1: checklist-vragenset is naar
 * de tenant-shell verhuisd). Hergebruikt dezelfde auth-store/logout
 * (httpOnly-cookie, RP-logout). De router-guard borgt dat hier alleen een
 * platform-sessie komt.
 */
import { useAuthStore } from '../store/auth'
import Button from 'primevue/button'
import Toast from 'primevue/toast'

const auth = useAuthStore()

async function uitloggen() {
  await auth.logout()
}
</script>

<template>
  <div class="min-h-screen flex flex-col bg-[var(--lk-color-bg)] text-[var(--lk-color-text)]">
    <header
      class="flex items-center gap-[var(--lk-space-md)] px-[var(--lk-space-lg)] py-[var(--lk-space-sm)] bg-[var(--lk-color-primary)] text-white shadow-[var(--lk-shadow-md)]"
    >
      <span class="font-semibold text-[length:var(--lk-text-lg)]">LIKARA</span>
      <span
        data-testid="beheer-badge"
        class="rounded-[var(--lk-radius-nav)] bg-white/20 px-[var(--lk-space-sm)] py-0.5 text-[length:var(--lk-text-xs)] font-semibold uppercase tracking-wide"
      >
        Beheer
      </span>

      <div class="ml-auto flex items-center gap-[var(--lk-space-md)]">
        <span data-testid="platform-email" class="text-[length:var(--lk-text-sm)]">
          {{ auth.user?.email }}
        </span>
        <Button
          label="Uitloggen"
          severity="secondary"
          data-testid="beheer-uitlog-knop"
          class="!bg-white/15 !text-white !border !border-white/50 hover:!bg-white/25 focus:!outline-white"
          @click="uitloggen"
        />
      </div>
    </header>

    <div class="flex flex-1 min-h-0">
      <aside
        id="beheer-navigatie"
        class="w-60 shrink-0 bg-[var(--lk-color-surface)] border-r border-[var(--lk-color-border)] p-[var(--lk-space-md)]"
      >
        <nav aria-label="Beheernavigatie" class="flex flex-col gap-[var(--lk-space-xs)]">
          <span
            class="px-[var(--lk-space-md)] text-[length:var(--lk-text-xs)] font-semibold uppercase tracking-wide text-[var(--lk-color-text-muted)]"
          >
            Platformbeheer
          </span>
          <router-link
            :to="{ name: 'beheer-contractconfig' }"
            data-testid="nav-contractconfig"
            class="rounded-[var(--lk-radius-nav)] px-[var(--lk-space-md)] py-[var(--lk-space-sm)] text-[var(--lk-color-text)] hover:bg-[var(--lk-color-accent)] aria-[current=page]:bg-[var(--lk-color-accent)] aria-[current=page]:font-semibold"
          >
            Contractcatalogus
          </router-link>
          <router-link
            :to="{ name: 'beheer-componentconfig' }"
            data-testid="nav-componentconfig"
            class="rounded-[var(--lk-radius-nav)] px-[var(--lk-space-md)] py-[var(--lk-space-sm)] text-[var(--lk-color-text)] hover:bg-[var(--lk-color-accent)] aria-[current=page]:bg-[var(--lk-color-accent)] aria-[current=page]:font-semibold"
          >
            Componentcatalogus
          </router-link>
          <router-link
            :to="{ name: 'beheer-relatiekenmerkconfig' }"
            data-testid="nav-relatiekenmerkconfig"
            class="rounded-[var(--lk-radius-nav)] px-[var(--lk-space-md)] py-[var(--lk-space-sm)] text-[var(--lk-color-text)] hover:bg-[var(--lk-color-accent)] aria-[current=page]:bg-[var(--lk-color-accent)] aria-[current=page]:font-semibold"
          >
            Relatie-kenmerk-catalogus
          </router-link>
          <router-link
            :to="{ name: 'beheer-vraagbetekenisconfig' }"
            data-testid="nav-vraagbetekenisconfig"
            class="rounded-[var(--lk-radius-nav)] px-[var(--lk-space-md)] py-[var(--lk-space-sm)] text-[var(--lk-color-text)] hover:bg-[var(--lk-color-accent)] aria-[current=page]:bg-[var(--lk-color-accent)] aria-[current=page]:font-semibold"
          >
            Vraagbetekenis-catalogus
          </router-link>
          <router-link
            :to="{ name: 'beheer-partijsoortconfig' }"
            data-testid="nav-partijsoortconfig"
            class="rounded-[var(--lk-radius-nav)] px-[var(--lk-space-md)] py-[var(--lk-space-sm)] text-[var(--lk-color-text)] hover:bg-[var(--lk-color-accent)] aria-[current=page]:bg-[var(--lk-color-accent)] aria-[current=page]:font-semibold"
          >
            Partijsoort-catalogus
          </router-link>
          <router-link
            :to="{ name: 'beheer-componentrolconfig' }"
            data-testid="nav-componentrolconfig"
            class="rounded-[var(--lk-radius-nav)] px-[var(--lk-space-md)] py-[var(--lk-space-sm)] text-[var(--lk-color-text)] hover:bg-[var(--lk-color-accent)] aria-[current=page]:bg-[var(--lk-color-accent)] aria-[current=page]:font-semibold"
          >
            Componentrollen
          </router-link>
          <router-link
            :to="{ name: 'beheer-bivschaalconfig' }"
            data-testid="nav-bivschaalconfig"
            class="rounded-[var(--lk-radius-nav)] px-[var(--lk-space-md)] py-[var(--lk-space-sm)] text-[var(--lk-color-text)] hover:bg-[var(--lk-color-accent)] aria-[current=page]:bg-[var(--lk-color-accent)] aria-[current=page]:font-semibold"
          >
            BIV-schaal
          </router-link>
          <!-- ADR-042 — applicatiefunctie-catalogus (het wát-veld op de proces-koppeling). -->
          <router-link
            :to="{ name: 'beheer-applicatiefunctieconfig' }"
            data-testid="nav-applicatiefunctieconfig"
            class="rounded-[var(--lk-radius-nav)] px-[var(--lk-space-md)] py-[var(--lk-space-sm)] text-[var(--lk-color-text)] hover:bg-[var(--lk-color-accent)] aria-[current=page]:bg-[var(--lk-color-accent)] aria-[current=page]:font-semibold"
          >
            Applicatiefuncties
          </router-link>
        </nav>
      </aside>

      <main class="flex-1 min-w-0 p-[var(--lk-space-xl)]">
        <router-view />
      </main>
    </div>

    <Toast />
  </div>
</template>
