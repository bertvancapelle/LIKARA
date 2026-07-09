import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../store/auth'
import { registreerVorigeRoute } from '../composables/useTerugNavigatie'
// Eager: het login-scherm en de app-shell horen bij de eerste paint.
import LoginView from '../views/LoginView.vue'
import AppLayout from '../layouts/AppLayout.vue'
// Platform-sectie (2E-b): aparte shell voor `/beheer/*`. Eager (eerste paint van
// de platform-sectie, net als AppLayout voor de tenant-sectie).
import BeheerLayout from '../layouts/BeheerLayout.vue'
// Lazy (OP-19): zware routes als dynamische imports → eigen chunks, kleinere
// initiële bundle. ComponentDetail trekt DataTable + de module-secties mee in
// zijn eigen async chunk. Module-loading (Optie A / @modules + cross-root-barrels)
// en de guard blijven ongewijzigd; alleen het laadmoment verschuift.
const DashboardView = () => import('../views/DashboardView.vue')
const BlokkadeOverzichtView = () => import('../views/BlokkadeOverzichtView.vue')
// ADR-023 Fase F / F-2 — cross-element laagprojectie, lazy.
const ArchitectuurView = () => import('../views/ArchitectuurView.vue')
const LandschapskaartView = () => import('@modules/bwb_ontvlechting/frontend/views/LandschapskaartView.vue')
// ADR-023 Fase F / F-3 stap 2 — consistentie-signalering technische plaatsing, lazy.
const PlaatsingSignalenView = () => import('../views/PlaatsingSignalenView.vue')
// ADR-035 — coherent Signalering-scherm (registratiegaten + plaatsing als tabs), lazy.
const SignaleringView = () => import('../views/SignaleringView.vue')
// ADR-021 Fase D — componenten (technische laag), lazy (OP-19).
const ComponentLijst = () => import('@modules/bwb_ontvlechting/frontend/views/ComponentLijst.vue')
const ComponentDetail = () => import('@modules/bwb_ontvlechting/frontend/views/ComponentDetail.vue')
// ADR-042 4b — het componentformulier is een OVERLAY (in lijst/detail), geen route-pagina meer.
// ADR-020 contractregister (Fase D1), lazy (OP-19).
const PartijLijst = () => import('@modules/bwb_ontvlechting/frontend/views/PartijLijst.vue')
const PartijFormulier = () =>
  import('@modules/bwb_ontvlechting/frontend/views/PartijFormulier.vue')
const PartijDetail = () => import('@modules/bwb_ontvlechting/frontend/views/PartijDetail.vue')
const ContractLijst = () => import('@modules/bwb_ontvlechting/frontend/views/ContractLijst.vue')
// ADR-042 slice 4a — procesregister (boom + detail), lazy.
const ProcesLijst = () => import('@modules/bwb_ontvlechting/frontend/views/ProcesLijst.vue')
const ProcesDetail = () => import('@modules/bwb_ontvlechting/frontend/views/ProcesDetail.vue')
const ContractFormulier = () => import('@modules/bwb_ontvlechting/frontend/views/ContractFormulier.vue')
const ContractDetail = () => import('@modules/bwb_ontvlechting/frontend/views/ContractDetail.vue')
// ADR-029 Fase 4 — gebruikersbeheer (beheerder-only; backend handhaaft via GEBRUIKERSBEHEER).
const GebruikersbeheerView = () => import('@modules/bwb_ontvlechting/frontend/views/GebruikersbeheerView.vue')
// ADR-029 Fase 3a — auditlog (beheerder/auditor; backend handhaaft via AUDITLOG.LEZEN).
const AuditTrailView = () => import('@modules/bwb_ontvlechting/frontend/views/AuditTrailView.vue')
// ADR-022 W1 — tenant-beheer van de checklist-vragenset, lazy.
const ChecklistConfigBeheer = () => import('../views/ChecklistConfigBeheer.vue')
// ADR-020 fase E — platform-beheer contractcatalogus, lazy.
const ContractConfigBeheer = () => import('../views/ContractConfigBeheer.vue')
// ADR-021 fase C — platform-beheer componentcatalogus, lazy.
const ComponentConfigBeheer = () => import('../views/ComponentConfigBeheer.vue')
// ADR-023 Fase F / F-4 — platform-beheer relatie-kenmerk-catalogus, lazy.
const RelatieKenmerkConfigBeheer = () => import('../views/RelatieKenmerkConfigBeheer.vue')
// Catalogi-beheer-schuld dichten — platform-beheer vraagbetekenis + partijsoort, lazy.
const VraagBetekenisConfigBeheer = () => import('../views/VraagBetekenisConfigBeheer.vue')
const PartijsoortConfigBeheer = () => import('../views/PartijsoortConfigBeheer.vue')
// ADR-028 — platform-beheer componentrol- + BIV-schaal-catalogus, lazy.
const RolConfigBeheer = () => import('../views/RolConfigBeheer.vue')
const BivConfigBeheer = () => import('../views/BivConfigBeheer.vue')
// ADR-042 — platform-beheer applicatiefunctie-catalogus, lazy.
const ApplicatiefunctieConfigBeheer = () => import('../views/ApplicatiefunctieConfigBeheer.vue')
// ADR-023 Fase F (F-1) — migratielaag-overzicht (read-only), lazy.
const PlateauLijstView = () => import('../views/migratie/PlateauLijstView.vue')
const PlateauDetailView = () => import('../views/migratie/PlateauDetailView.vue')
const GapLijstView = () => import('../views/migratie/GapLijstView.vue')
const GapDetailView = () => import('../views/migratie/GapDetailView.vue')
const WorkPackageLijstView = () => import('../views/migratie/WorkPackageLijstView.vue')
const WorkPackageDetailView = () => import('../views/migratie/WorkPackageDetailView.vue')
const DeliverableLijstView = () => import('../views/migratie/DeliverableLijstView.vue')
const DeliverableDetailView = () => import('../views/migratie/DeliverableDetailView.vue')

// Migratielaag-reads zijn voor elke tenant-rol leesbaar (RBAC `_INHOUD`); de guard
// gate't de routes op die rolset (platform-sessies worden al eerder weggeleid).
const MIGRATIE_ROLLEN = ['viewer', 'medewerker', 'beheerder', 'auditor']

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
      // ADR-023 Fase F / F-2 — cross-element laagprojectie (read-only); élke tenant-rol leest.
      { path: 'architectuur', name: 'architectuur', component: ArchitectuurView, meta: { roles: MIGRATIE_ROLLEN } },
      // ADR-025 — Landschapskaart (read-only grafische landschapsweergave); zelfde leesrecht als architectuur.
      { path: 'landschapskaart', name: 'landschapskaart', component: LandschapskaartView, meta: { roles: MIGRATIE_ROLLEN } },
      { path: 'signalen/plaatsing', name: 'plaatsingssignalen', component: PlaatsingSignalenView, meta: { roles: MIGRATIE_ROLLEN } },
      // ADR-035 — Signalering-scherm (registratiegaten + plaatsing-tab); zelfde leesrecht.
      { path: 'signalering', name: 'signalering', component: SignaleringView, meta: { roles: MIGRATIE_ROLLEN } },
      // ADR-021 W1 (CD054b): de Applicaties-lijst is opgegaan in de verenigde
      // Componenten-lijst. `/applicaties` redirect (naam behouden zodat bestaande
      // navigaties/bookmarks niet breken) naar Componenten met typefilter=applicatie.
      // Het detail `/applicaties/:id` blijft de rijke subtype-view.
      // LI059 Slice 4 — de aparte Applicatie-schermen zijn opgegaan in de generieke
      // component-beleving. De oude routes blijven als REDIRECT bestaan zodat bookmarks/
      // deep-links niet breken (naam behouden). `applicatie-lijst` → Componenten (typefilter).
      { path: 'applicaties', name: 'applicatie-lijst', redirect: { name: 'component-lijst', query: { type: 'applicatie' } } },
      { path: 'applicaties/nieuw', name: 'applicatie-nieuw', redirect: { name: 'component-nieuw' } },
      { path: 'applicaties/:id', name: 'applicatie-detail', redirect: (to) => ({ name: 'component-detail', params: { id: to.params.id } }) },
      { path: 'applicaties/:id/bewerken', name: 'applicatie-bewerken', redirect: (to) => ({ name: 'component-bewerken', params: { id: to.params.id } }) },
      // ADR-029 — gebruikersbeheer (beheerder-only via de backend; nav-affordance gegate).
      { path: 'gebruikers', name: 'gebruikersbeheer', component: GebruikersbeheerView },
      // ADR-029 Fase 3a — auditlog (beheerder/auditor; backend handhaaft AUDITLOG.LEZEN).
      { path: 'auditlog', name: 'auditlog', component: AuditTrailView },
      // ADR-021 componenten — statische subpaden vóór de dynamische /:id.
      { path: 'componenten', name: 'component-lijst', component: ComponentLijst },
      // ADR-042 4b — aanmaken/bewerken als overlay; de routes blijven als redirect
      // (deep-links/bookmarks) en openen de overlay via een query-vlag.
      { path: 'componenten/nieuw', name: 'component-nieuw', redirect: { name: 'component-lijst', query: { nieuw: '1' } } },
      { path: 'componenten/:id', name: 'component-detail', component: ComponentDetail, props: true },
      {
        path: 'componenten/:id/bewerken',
        name: 'component-bewerken',
        redirect: (to) => ({ name: 'component-detail', params: { id: to.params.id }, query: { bewerk: '1' } }),
      },
      // ADR-024 partijenregister — statische subpaden vóór de dynamische /:id.
      { path: 'partijen', name: 'partij-lijst', component: PartijLijst },
      { path: 'partijen/nieuw', name: 'partij-nieuw', component: PartijFormulier },
      { path: 'partijen/:id', name: 'partij-detail', component: PartijDetail, props: true },
      {
        path: 'partijen/:id/bewerken',
        name: 'partij-bewerken',
        component: PartijFormulier,
        props: true,
      },
      // ADR-042 — procesregister. Statische subpaden vóór de dynamische /:id.
      { path: 'processen', name: 'proces-lijst', component: ProcesLijst },
      { path: 'processen/:id', name: 'proces-detail', component: ProcesDetail, props: true },
      { path: 'contracten', name: 'contract-lijst', component: ContractLijst },
      { path: 'contracten/nieuw', name: 'contract-nieuw', component: ContractFormulier },
      { path: 'contracten/:id', name: 'contract-detail', component: ContractDetail, props: true },
      {
        path: 'contracten/:id/bewerken',
        name: 'contract-bewerken',
        component: ContractFormulier,
        props: true,
      },
      // ADR-022 W1 — checklist-vragenset is tenant-eigendom: tenant-facing route
      // (lk_app, tenant-shell), verhuisd uit /beheer.
      { path: 'checklistvragen', name: 'checklistvragen', component: ChecklistConfigBeheer },
      // ADR-023 Fase F (F-1) — migratielaag-overzicht (read-only). Statische subpaden
      // vóór de dynamische /:id; gegate op de tenant-rolset via meta.roles.
      { path: 'migratie/plateaus', name: 'plateau-lijst', component: PlateauLijstView, meta: { roles: MIGRATIE_ROLLEN } },
      { path: 'migratie/plateaus/:id', name: 'plateau-detail', component: PlateauDetailView, props: true, meta: { roles: MIGRATIE_ROLLEN } },
      { path: 'migratie/gaps', name: 'gap-lijst', component: GapLijstView, meta: { roles: MIGRATIE_ROLLEN } },
      { path: 'migratie/gaps/:id', name: 'gap-detail', component: GapDetailView, props: true, meta: { roles: MIGRATIE_ROLLEN } },
      { path: 'migratie/werkpakketten', name: 'work-package-lijst', component: WorkPackageLijstView, meta: { roles: MIGRATIE_ROLLEN } },
      { path: 'migratie/werkpakketten/:id', name: 'work-package-detail', component: WorkPackageDetailView, props: true, meta: { roles: MIGRATIE_ROLLEN } },
      { path: 'migratie/deliverables', name: 'deliverable-lijst', component: DeliverableLijstView, meta: { roles: MIGRATIE_ROLLEN } },
      { path: 'migratie/deliverables/:id', name: 'deliverable-detail', component: DeliverableDetailView, props: true, meta: { roles: MIGRATIE_ROLLEN } },
    ],
  },

  // Platform-beheersectie (ADR-012 / ADR-019 fase 2E) — eigen shell, geguard op
  // een PLATFORM-sessie (`meta.platform`). De view zelf komt in 2E-c.
  {
    path: '/beheer',
    component: BeheerLayout,
    meta: { requiresAuth: true, platform: true },
    children: [
      // ADR-022 W1: checklistconfig is naar de tenant-shell verhuisd; beheer-home
      // redirect daarom naar de eerste resterende platform-route (contractconfig).
      { path: '', name: 'beheer-home', redirect: { name: 'beheer-contractconfig' } },
      { path: 'contractconfig', name: 'beheer-contractconfig', component: ContractConfigBeheer },
      { path: 'componentconfig', name: 'beheer-componentconfig', component: ComponentConfigBeheer },
      { path: 'relatiekenmerkconfig', name: 'beheer-relatiekenmerkconfig', component: RelatieKenmerkConfigBeheer },
      { path: 'vraagbetekenisconfig', name: 'beheer-vraagbetekenisconfig', component: VraagBetekenisConfigBeheer },
      { path: 'partijsoortconfig', name: 'beheer-partijsoortconfig', component: PartijsoortConfigBeheer },
      { path: 'componentrolconfig', name: 'beheer-componentrolconfig', component: RolConfigBeheer },
      { path: 'bivschaalconfig', name: 'beheer-bivschaalconfig', component: BivConfigBeheer },
      { path: 'applicatiefunctieconfig', name: 'beheer-applicatiefunctieconfig', component: ApplicatiefunctieConfigBeheer },
    ],
  },

  // Catch-all
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
})

// Registreer na elke navigatie de herkomst-route, zodat detailpagina's een contextuele
// "← Terug naar X"-knop kunnen tonen (useTerugNavigatie). Dekt <router-link> én push.
router.afterEach((to, from) => registreerVorigeRoute(from))

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
