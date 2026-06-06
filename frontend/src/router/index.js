import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../store/auth'
import LoginView from '../views/LoginView.vue'
import AppLayout from '../layouts/AppLayout.vue'
import DashboardView from '../views/DashboardView.vue'
import ApplicatieLijst from '@modules/bwb_ontvlechting/frontend/views/ApplicatieLijst.vue'
import ApplicatieDetail from '@modules/bwb_ontvlechting/frontend/views/ApplicatieDetail.vue'
import ApplicatieFormulier from '@modules/bwb_ontvlechting/frontend/views/ApplicatieFormulier.vue'

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
      { path: 'applicaties', name: 'applicatie-lijst', component: ApplicatieLijst },
      // Statische paden vóór de dynamische /:id (vue-router rankt static > param,
      // maar expliciet vóór geplaatst voor leesbaarheid).
      { path: 'applicaties/nieuw', name: 'applicatie-nieuw', component: ApplicatieFormulier },
      { path: 'applicaties/:id', name: 'applicatie-detail', component: ApplicatieDetail, props: true },
      {
        path: 'applicaties/:id/bewerken',
        name: 'applicatie-bewerken',
        component: ApplicatieFormulier,
        props: true,
      },
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
