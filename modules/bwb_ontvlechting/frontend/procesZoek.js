/**
 * procesZoek — gedeelde proces-picker-bron mét procescontext (ADR-042 slice 4b).
 *
 * Een proces-treffer toont ALTIJD zijn context ("Aanvraag behandelen — Vergunningverlening",
 * het identiteit-patroon; ADR-042 besluit 2: buiten de boomcontext nooit een kale naam).
 * De processen-API levert alleen `ouder_id`; daarom wordt de volledige (begrensde,
 * organisatie-eigen) set één keer opgehaald en client-side gefilterd — zo krijgt elke
 * treffer zijn ouder-naam zonder N+1 en zoekt het veld instant (zoekveld-norm: partieel,
 * hoofdletter-ongevoelig). `ververs()` gooit de cache weg (bv. na proces-beheer).
 */
export function maakProcesZoeker(api) {
  let cache = null

  async function _alle() {
    if (cache) return cache
    const items = []
    let after
    do {
      const pagina = await api.processen.lijst({ limit: 100, after })
      items.push(...pagina.items)
      after = pagina.volgende_cursor
    } while (after)
    const perId = new Map(items.map((p) => [p.id, p]))
    cache = items
      .map((p) => ({ ...p, ouder_naam: (p.ouder_id && perId.get(p.ouder_id)?.naam) || null }))
      .sort((a, b) => a.naam.localeCompare(b.naam, 'nl'))
    return cache
  }

  /** ZoekSelect-compatibel: `({ zoek }) => { items }` — client-side, mét context. */
  async function zoekFunctie(params = {}) {
    const term = (params.zoek || '').trim().toLowerCase()
    const alle = await _alle()
    return { items: alle.filter((p) => !term || p.naam.toLowerCase().includes(term)), volgende_cursor: null }
  }

  /** Weergave mét procescontext (identiteit-patroon); top-level = kale naam. */
  const weergave = (p) => (p?.ouder_naam ? `${p.naam} — ${p.ouder_naam}` : (p?.naam ?? ''))

  return { zoekFunctie, weergave, ververs: () => { cache = null } }
}
