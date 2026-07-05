import { defineStore } from 'pinia'
import { refreshSessie } from '../api'

// Auth store patroon — framework-basis, zonder applicatie-specifieke logica.
// Sessie loopt via httpOnly cookie (ADR-004); nooit localStorage.
// RBAC (rollen) wordt ingevuld zodra ADR-010 de rolstructuur vaststelt.
export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null,
    // 'tenant' | 'platform' | null — bepaalt welke app-sectie de gebruiker ziet (2E-b).
    sessionType: null,
  }),
  getters: {
    isAuthenticated: (state) => !!state.user,
    isPlatform: (state) => state.sessionType === 'platform',
    isTenant: (state) => state.sessionType === 'tenant',
    // /auth/me levert `tenant_id` (UUID); geen slug. (Was `tenant_slug` → altijd null.)
    tenantId: (state) => state.user?.tenant_id ?? null,
    roles: (state) => state.user?.roles ?? [],
  },
  actions: {
    async fetchSession() {
      // Sessietype-detectie (ADR-012 / 2E-b): tenant-account → /auth/me (heeft
      // tenant_id); platform-account → /auth/me geeft 403 (TENANT_MISMATCH), dan
      // /auth/platform/me. Beide via dezelfde httpOnly-cookie.
      //
      // Scheefje gladgestreken: waar een data-fetch bij een 401 eerst stil ververst
      // (api.js), doet de sessiecheck dat nu óók — vóór hij de sessie opgeeft. Zo wordt een
      // nog-te-redden sessie (access-token verlopen, refresh nog geldig) bij navigatie niet
      // onnodig afgebroken. Pas ná een bewezen-gefaalde refresh geldt de sessie als verlopen.
      const detecteer = async () => {
        const me = await fetch('/api/v1/auth/me', { credentials: 'include' })
        if (me.ok) {
          this.user = await me.json()
          this.sessionType = 'tenant'
          return { ok: true }
        }
        const pme = await fetch('/api/v1/auth/platform/me', { credentials: 'include' })
        if (pme.ok) {
          this.user = await pme.json()
          this.sessionType = 'platform'
          return { ok: true }
        }
        // 401 op beide = geen levende sessie (mogelijk nog te verversen); 403 = verkeerd
        // sessietype (geen refresh die dat oplost).
        return { ok: false, verlopen: me.status === 401 || pme.status === 401 }
      }
      try {
        let r = await detecteer()
        if (!r.ok && r.verlopen && (await refreshSessie())) {
          r = await detecteer() // stille refresh geslaagd → sessie opnieuw ophalen
        }
        if (r.ok) return
      } catch {
        /* netwerkfout → geen sessie */
      }
      this.user = null
      this.sessionType = null
    },
    async logout() {
      this.user = null
      this.sessionType = null
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
