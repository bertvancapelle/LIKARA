<script setup>
/**
 * BeheerLayout — platform-app-shell (ADR-012 / ADR-019 fase 2E-b).
 *
 * Aparte, lichte shell voor de PLATFORM-sectie (`/beheer/*`), los van de
 * tenant-`AppLayout`. Topbar: app-naam + "Beheer", platform-e-mail, uitloggen.
 * Minimale nav (checklistconfiguratie). Hergebruikt dezelfde auth-store/logout
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
  <div class="min-h-screen flex flex-col bg-[var(--cd-color-bg)] text-[var(--cd-color-text)]">
    <header
      class="flex items-center gap-[var(--cd-space-md)] px-[var(--cd-space-lg)] py-[var(--cd-space-sm)] bg-[var(--cd-color-primary)] text-white shadow-[var(--cd-shadow-md)]"
    >
      <span class="font-semibold text-[length:var(--cd-text-lg)]">CompliData</span>
      <span
        data-testid="beheer-badge"
        class="rounded-[var(--cd-radius-nav)] bg-white/20 px-[var(--cd-space-sm)] py-0.5 text-[length:var(--cd-text-xs)] font-semibold uppercase tracking-wide"
      >
        Beheer
      </span>

      <div class="ml-auto flex items-center gap-[var(--cd-space-md)]">
        <span data-testid="platform-email" class="text-[length:var(--cd-text-sm)]">
          {{ auth.user?.email }}
        </span>
        <Button
          label="Uitloggen"
          severity="secondary"
          size="small"
          data-testid="beheer-uitlog-knop"
          class="!bg-white/15 !text-white !border !border-white/50 hover:!bg-white/25 focus:!outline-white"
          @click="uitloggen"
        />
      </div>
    </header>

    <div class="flex flex-1 min-h-0">
      <aside
        id="beheer-navigatie"
        class="w-60 shrink-0 bg-[var(--cd-color-surface)] border-r border-[var(--cd-color-border)] p-[var(--cd-space-md)]"
      >
        <nav aria-label="Beheernavigatie" class="flex flex-col gap-[var(--cd-space-xs)]">
          <span
            class="px-[var(--cd-space-md)] text-[length:var(--cd-text-xs)] font-semibold uppercase tracking-wide text-[var(--cd-color-text-muted)]"
          >
            Platformbeheer
          </span>
          <router-link
            :to="{ name: 'beheer-checklistconfig' }"
            data-testid="nav-checklistconfig"
            class="rounded-[var(--cd-radius-nav)] px-[var(--cd-space-md)] py-[var(--cd-space-sm)] text-[var(--cd-color-text)] hover:bg-[var(--cd-color-accent)] aria-[current=page]:bg-[var(--cd-color-accent)] aria-[current=page]:font-semibold"
          >
            Checklistconfiguratie
          </router-link>
        </nav>
      </aside>

      <main class="flex-1 min-w-0 p-[var(--cd-space-xl)]">
        <router-view />
      </main>
    </div>

    <Toast />
  </div>
</template>
