import { defineStore } from 'pinia'

// Auth store patroon — framework-basis, zonder applicatie-specifieke logica.
// Sessie loopt via httpOnly cookie (ADR-004); nooit localStorage.
// RBAC (rollen) wordt ingevuld zodra ADR-010 de rolstructuur vaststelt.
export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null,
  }),
  getters: {
    isAuthenticated: (state) => !!state.user,
    // /auth/me levert `tenant_id` (UUID); geen slug. (Was `tenant_slug` → altijd null.)
    tenantId: (state) => state.user?.tenant_id ?? null,
    roles: (state) => state.user?.roles ?? [],
  },
  actions: {
    async fetchSession() {
      try {
        const res = await fetch('/api/v1/auth/me', { credentials: 'include' })
        if (!res.ok) {
          this.user = null
          return
        }
        this.user = await res.json()
      } catch {
        this.user = null
      }
    },
    async logout() {
      this.user = null
      try {
        const res = await fetch('/api/v1/auth/logout', {
          method: 'POST',
          credentials: 'include',
        })
        const result = await res.json().catch(() => ({}))
        if (result?.keycloak_logout_url) {
          window.location.href = result.keycloak_logout_url
          return
        }
      } catch {}
      window.location.href = '/login'
    },
    // Rolcheck — unie van rechten. Geeft nu altijd false tot ADR-010 rollen levert.
    hasRole(...requiredRoles) {
      const userRoles = this.user?.roles ?? []
      return requiredRoles.some((role) => userRoles.includes(role))
    },
  },
})
