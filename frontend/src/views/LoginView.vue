<script setup>
/**
 * LoginView — launch-/landingspagina (platform-view).
 *
 * De app toont zelf GEEN wachtwoordveld: de "Inloggen"-knop start de
 * Keycloak-redirect-flow (ADR-002) via een volledige browser-redirect naar het
 * backend-endpoint `/api/v1/auth/login`. Na succesvolle login zet de backend de
 * httpOnly `lk_session`-cookie en redirect terug naar `next` (default `/`); de
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
    class="min-h-screen flex items-center justify-center bg-[var(--lk-color-bg)] p-[var(--lk-space-lg)]"
  >
    <section
      class="w-full max-w-md bg-[var(--lk-color-surface)] shadow-[var(--lk-shadow-lg)] rounded-[var(--lk-radius-card)] p-[var(--lk-space-2xl)]"
      aria-labelledby="login-titel"
    >
      <h1
        id="login-titel"
        class="text-[var(--lk-color-primary)] mb-[var(--lk-space-sm)]"
      >
        LIKARA
      </h1>
      <p class="text-[var(--lk-color-text-muted)] mb-[var(--lk-space-lg)]">
        Logische ICT Kaart Afhankelijkheden Relaties Analyse — logisch inzicht in uw ICT-landschap.
      </p>

      <p
        v-if="sessieVerlopen"
        role="alert"
        data-testid="sessie-verlopen"
        class="mb-[var(--lk-space-md)] rounded-[var(--lk-radius-badge)] border border-[var(--lk-color-warning)] bg-[var(--lk-color-accent)] px-[var(--lk-space-md)] py-[var(--lk-space-sm)] text-[length:var(--lk-text-sm)] text-[var(--lk-color-text)]"
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
        class="mt-[var(--lk-space-sm)] text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]"
      >
        Bezig met doorsturen naar de beveiligde inlogpagina…
      </p>

      <p
        class="mt-[var(--lk-space-lg)] text-[length:var(--lk-text-xs)] text-[var(--lk-color-text-muted)]"
      >
        Je wordt doorgestuurd naar de beveiligde inlogomgeving van de organisatie.
      </p>
    </section>
  </main>
</template>
