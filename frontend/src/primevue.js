// Platform-barrel voor PrimeVue-componenten.
//
// Module-views staan buiten de vite-root (modules/<module>/frontend) en kunnen
// bare `primevue/*`-imports daar niet resolven (node_modules staat in frontend/).
// Ze importeren PrimeVue daarom via `@/primevue` (deze barrel resolvet wél binnen
// frontend/). Breid uit zodra een view een extra component nodig heeft.
export { default as DataTable } from 'primevue/datatable'
export { default as Column } from 'primevue/column'
export { default as Tag } from 'primevue/tag'
export { default as Button } from 'primevue/button'
export { default as Dialog } from 'primevue/dialog'
export { default as InputText } from 'primevue/inputtext'
export { default as Textarea } from 'primevue/textarea'
export { default as Toast } from 'primevue/toast'
// Toast-composable (cross-root: ook via deze barrel voor module-views).
export { useToast } from 'primevue/usetoast'
