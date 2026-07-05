// Centrale verlopen-sessie-vangrail — de handler-fabriek (pure, testbaar). `api.js` roept de
// geregistreerde handler aan op het bewezen-gefaalde-refresh-punt (nooit terwijl een sessie nog
// te redden is). De handler wist de sessie en leidt netjes naar de inlogpagina met de bestaande
// "sessie verlopen"-melding, mét behoud van waar de gebruiker was (next; same-origin, server-
// hervalideerd). Losgekoppeld van main.js zodat de redirect-logica los te unit-testen is.
export function sessieVerlopenHandler(router, auth) {
  return () => {
    auth.user = null
    auth.sessionType = null
    const huidig = router.currentRoute.value
    if (huidig?.meta?.public) return // al op login/callback → niet opnieuw redirecten
    const pad = huidig?.fullPath
    const next = pad && pad !== '/' ? pad : undefined
    router.push({ name: 'login', query: { sessie_verlopen: '1', ...(next ? { next } : {}) } })
  }
}
