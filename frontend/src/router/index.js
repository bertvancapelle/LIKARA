import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../store/auth'
import LoginView from '../views/LoginView.vue'

// Basisstructuur — module-routes worden toegevoegd onder
// modules/<module>/frontend en hier geregistreerd. Platform-views staan in
// src/views/. Placeholder-componenten houden de overige routes zelfstandig.
const Placeholder = { template: '<div />' }

const routes = [
  // Publieke routes
  { path: '/login', name: 'login', component: LoginView, meta: { public: true } },
  { path: '/auth/callback', name: 'auth-callback', component: Placeholder, meta: { public: true } },
  { path: '/403', name: 'verboden', component: Placeholder, meta: { public: true } },

  // Beveiligde basisroute
  { path: '/', name: 'dashboard', component: Placeholder, meta: { requiresAuth: true } },

  // Catch-all
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
})

// Navigation guard — auth + rol-check (rollen volgen uit ADR-010).
router.beforeEach(async (to) => {
  if (to.meta.public) return true

  const auth = useAuthStore()
  try {
    await auth.fetchSession()
  } catch {
    // netwerk-fouten worden hier opgevangen
  }

  if (!auth.isAuthenticated) {
    return { name: 'login', query: { sessie_verlopen: '1' } }
  }

  if (to.meta.roles && to.meta.roles.length > 0) {
    if (!auth.hasRole(...to.meta.roles)) {
      return { name: 'verboden' }
    }
  }

  return true
})
