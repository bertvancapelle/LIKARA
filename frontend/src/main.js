import { createApp } from 'vue'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'
import { router } from './router'
import { registreerSessieVerlopenHandler } from './api'
import { sessieVerlopenHandler } from './sessieVangrail'
import { useAuthStore } from './store/auth'
import App from './App.vue'
import presets from './presets'
import './assets/main.css'

const app = createApp(App)
app.use(createPinia())
app.use(router)
// PrimeVue Unstyled + centrale PassThrough presets (ADR-047)
app.use(PrimeVue, { unstyled: true, pt: presets })
app.use(ToastService)

// Centrale verlopen-sessie-vangrail (zie api.js + sessieVangrail.js). api.js roept deze handler aan
// op het bewezen-gefaalde-refresh-punt (nooit terwijl een sessie nog te redden is).
registreerSessieVerlopenHandler(sessieVerlopenHandler(router, useAuthStore()))

app.mount('#app')
