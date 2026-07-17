// Contextgebonden terug-navigatie: een "← Terug naar X"-knop op detailpagina's, waarbij X de
// route is waar de gebruiker vandaan kwam. De vorige route wordt centraal geregistreerd via een
// router-`afterEach` (zie router/index.js) — dat dekt zowel <router-link>- als programmatische
// navigatie zonder per call `state` mee te geven. Bij directe URL-toegang is er geen vorige route
// → geen knop.
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'

// Module-niveau (SPA-singleton): de route waar de huidige navigatie vandaan kwam.
const vorigeRoute = ref(null) // { name, fullPath } | null

export function registreerVorigeRoute(from) {
  vorigeRoute.value = from?.name ? { name: from.name, fullPath: from.fullPath } : null
}

// Leesbare labels per herkomst-route (naam → mensvriendelijke bestemming).
const HERKOMST_LABELS = {
  landschapskaart: 'Landschapskaart',
  'partij-lijst': 'Partijen',
  'component-lijst': 'Componenten',
  'contract-lijst': 'Contracten',
  dashboard: 'Dashboard',
  blokkades: 'Blokkades',
  auditlog: 'Auditlog',
  gebruikersbeheer: 'Gebruikersbeheer',
}

export function useTerugNavigatie() {
  const router = useRouter()
  const terugLabel = computed(() => {
    const v = vorigeRoute.value
    if (!v) return null // directe URL-toegang → geen terugknop
    const bestemming = HERKOMST_LABELS[v.name]
    return bestemming ? `← Terug naar ${bestemming}` : '← Terug'
  })
  const gaTerug = () => router.back()
  return { terugLabel, gaTerug }
}
