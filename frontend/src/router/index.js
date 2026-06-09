import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../store/auth'
// Eager: het login-scherm en de app-shell horen bij de eerste paint.
import LoginView from '../views/LoginView.vue'
import AppLayout from '../layouts/AppLayout.vue'
// Platform-sectie (2E-b): aparte shell voor `/beheer/*`. Eager (eerste paint van
// de platform-sectie, net als AppLayout voor de tenant-sectie).
import BeheerLayout from '../layouts/BeheerLayout.vue'
// Lazy (OP-19): zware routes als dynamische imports → eigen chunks, kleinere
// initiële bundle. ApplicatieDetail trekt DataTable + de module-secties mee in
// zijn eigen async chunk. Module-loading (Optie A / @modules + cross-root-barrels)
// en de guard blijven ongewijzigd; alleen het laadmoment verschuift.
const DashboardView = () => import('../views/DashboardView.vue')
const BlokkadeOverzichtView = () => import('../views/BlokkadeOverzichtView.vue')
const KoppelingenkaartView = () => import('../views/KoppelingenkaartView.vue')
const ApplicatieLijst = () => import('@modules/bwb_ontvlechting/frontend/views/ApplicatieLijst.vue')
const ApplicatieDetail = () => import('@modules/bwb_ontvlechting/frontend/views/ApplicatieDetail.vue')
const ApplicatieFormulier = () =>
  import('@modules/bwb_ontvlechting/frontend/views/ApplicatieFormulier.vue')
// Platform-beheer-view (2E-c), lazy.
const ChecklistConfigBeheer = () => import('../views/ChecklistConfigBeheer.vue')

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
      { path: 'blokkades', name: 'blokkades', component: BlokkadeOverzichtView },
      { path: 'koppelingenkaart', name: 'koppelingenkaart', component: KoppelingenkaartView },
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

  // Platform-beheersectie (ADR-012 / ADR-019 fase 2E) — eigen shell, geguard op
  // een PLATFORM-sessie (`meta.platform`). De view zelf komt in 2E-c.
  {
    path: '/beheer',
    component: BeheerLayout,
    meta: { requiresAuth: true, platform: true },
    children: [
      { path: '', name: 'beheer-home', redirect: { name: 'beheer-checklistconfig' } },
      { path: 'checklistconfig', name: 'beheer-checklistconfig', component: ChecklistConfigBeheer },
    ],
  },

  // Catch-all
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
})

// Pure routeringsbeslissing (sessietype-bewust, 2E-b) — los van de async
// fetchSession zodat hij unit-testbaar is. `auth` is de auth-store (of een
// equivalente snapshot met isAuthenticated/sessionType/hasRole).
export function routeBeslissing(to, auth) {
  if (to.meta?.public) return true
  if (!auth.isAuthenticated) return { name: 'login', query: { sessie_verlopen: '1' } }

  const platformRoute = !!to.meta?.platform
  // Tenant-sessie op een platform-route → terug naar de tenant-app.
  if (platformRoute && auth.sessionType !== 'platform') return { path: '/' }
  // Platform-sessie op een tenant-route → naar de beheersectie (een platform-
  // account kan de tenant-views niet gebruiken; /auth/me geeft 403).
  if (!platformRoute && auth.sessionType === 'platform') return { path: '/beheer' }

  if (to.meta?.roles?.length && !auth.hasRole(...to.meta.roles)) {
    return { name: 'verboden' }
  }
  return true
}

// Navigation guard — auth + sessietype + rol-check.
router.beforeEach(async (to) => {
  if (to.meta.public) return true

  const auth = useAuthStore()
  try {
    await auth.fetchSession()
  } catch {
    // netwerk-fouten worden hier opgevangen
  }

  return routeBeslissing(to, auth)
})
