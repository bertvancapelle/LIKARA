<script setup>
/**
 * LoginView — launch-/landingspagina (platform-view).
 *
 * De app toont zelf GEEN wachtwoordveld: de "Inloggen"-knop start de
 * Keycloak-redirect-flow (ADR-002) via een volledige browser-redirect naar het
 * backend-endpoint `/api/v1/auth/login`. Na succesvolle login zet de backend de
 * httpOnly `cd_session`-cookie en redirect terug naar `next` (default `/`); de
 * router-guard zet de geauthenticeerde gebruiker daarna door.
 */
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import Button from 'primevue/button'

const route = useRoute()
const bezig = ref(false)

const sessieVerlopen = computed(() => route.query.sessie_verlopen === '1')

function _veiligeNext(waarde) {
  // Open-redirect-bescherming: alleen een same-origin relatief pad doorgeven.
  // De backend hervalideert dit sowieso (_valideer_next).
  if (typeof waarde !== 'string') return null
  if (
    waarde.startsWith('/') &&
    !waarde.startsWith('//') &&
    !waarde.includes('\\') &&
    !waarde.includes('://')
  ) {
    return waarde
  }
  return null
}

function inloggen() {
  bezig.value = true
  const next = _veiligeNext(route.query.next)
  const url = next
    ? `/api/v1/auth/login?next=${encodeURIComponent(next)}`
    : '/api/v1/auth/login'
  window.location.assign(url)
}
</script>

<template>
  <main
    class="min-h-screen flex items-center justify-center bg-[var(--cd-color-bg)] p-[var(--cd-space-lg)]"
  >
    <section
      class="w-full max-w-md bg-[var(--cd-color-surface)] shadow-[var(--cd-shadow-lg)] rounded-[var(--cd-radius-card)] p-[var(--cd-space-2xl)]"
      aria-labelledby="login-titel"
    >
      <h1
        id="login-titel"
        class="text-[length:var(--cd-text-2xl)] font-semibold text-[var(--cd-color-primary)] mb-[var(--cd-space-sm)]"
      >
        LIKARA
      </h1>
      <p class="text-[var(--cd-color-text-muted)] mb-[var(--cd-space-lg)]">
        Gecontroleerd databeheer en migratie-analyse voor de Nederlandse overheid.
      </p>

      <p
        v-if="sessieVerlopen"
        role="alert"
        data-testid="sessie-verlopen"
        class="mb-[var(--cd-space-md)] rounded-[var(--cd-radius-badge)] border border-[var(--cd-color-warning)] bg-[var(--cd-color-accent)] px-[var(--cd-space-md)] py-[var(--cd-space-sm)] text-[length:var(--cd-text-sm)] text-[var(--cd-color-text)]"
      >
        Je sessie is verlopen. Log opnieuw in om verder te gaan.
      </p>

      <Button
        label="Inloggen"
        class="w-full justify-center"
        data-testid="inloggen-knop"
        :disabled="bezig"
        :aria-busy="bezig"
        @click="inloggen"
      />

      <p
        v-if="bezig"
        data-testid="bezig"
        class="mt-[var(--cd-space-sm)] text-[length:var(--cd-text-sm)] text-[var(--cd-color-text-muted)]"
      >
        Bezig met doorsturen naar de beveiligde inlogpagina…
      </p>

      <p
        class="mt-[var(--cd-space-lg)] text-[length:var(--cd-text-xs)] text-[var(--cd-color-text-muted)]"
      >
        Je wordt doorgestuurd naar de beveiligde inlogomgeving van de organisatie.
      </p>
    </section>
  </main>
</template>
