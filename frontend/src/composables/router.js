// Platform-barrel voor vue-router-composables.
//
// Module-views staan buiten de vite-root en kunnen 'vue-router' niet altijd
// resolven (node_modules in frontend/). Ze importeren `useRouter`/`useRoute`
// daarom via `@/composables/router`. (Route-params komen bij voorkeur via
// `props: true` binnen, maar programmatische navigatie heeft `useRouter` nodig.)
export { useRoute, useRouter } from 'vue-router'
