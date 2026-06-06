import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../store/auth'
import LoginView from '../views/LoginView.vue'
import AppLayout from '../layouts/AppLayout.vue'
import DashboardView from '../views/DashboardView.vue'

// Publieke routes staan standalone (geen app-shell). Geauthenticeerde routes
// hangen als children onder AppLayout: door de meta-merge erven zij
// `requiresAuth`, zodat de guard ongewijzigd blijft werken. Module-views worden
// later als extra children toegevoegd (eventueel met meta.roles).
const Placeholder = { template: '<div />' }

const routes = [
  // Publieke routes
  { path: '/login', name: 'login', component: LoginView, meta: { public: true } },
  { path: '/auth/callback', name: 'auth-callback', component: Placeholder, meta: { public: true } },
  { path: '/403', name: 'verboden', component: Placeholder, meta: { public: true } },

  // Geauthenticeerde app-shell + geneste views
  {
    path: '/',
    component: AppLayout,
    meta: { requiresAuth: true },
    children: [
      { path: '', name: 'dashboard', component: DashboardView },
    ],
  },

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
