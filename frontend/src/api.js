// API-client — fetch met httpOnly cookie (credentials: include).
// Foutformaat conform CLAUDE.md: { fout: { code, http_status, bericht } };
// 422 = FastAPI { detail: [...] }. 401 → single-flight refresh-on-401 (ADR-015 B6).
const BASE = '/api/v1'

// Single-flight refresh: gelijktijdige 401's delen één lopende /auth/refresh-poging
// (geen stampede). Resolved op de HTTP-status van /auth/refresh (geen body/code).
let _refreshPromise = null
function _refreshSessie() {
  if (!_refreshPromise) {
    _refreshPromise = fetch(`${BASE}/auth/refresh`, { method: 'POST', credentials: 'include' })
      .then((r) => r.ok)
      .catch(() => false)
      .finally(() => {
        _refreshPromise = null
      })
  }
  return _refreshPromise
}

async function request(path, options = {}, _isRetry = false) {
  const res = await fetch(`${BASE}${path}`, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  })
  if (res.status === 401 && !_isRetry) {
    // Eén refresh-poging (gedeeld); bij succes de oorspronkelijke request éénmalig
    // herproberen. Keyt op HTTP-status (ADR-014/CD005), niet op body/code.
    const vernieuwd = await _refreshSessie()
    if (vernieuwd) return request(path, options, true)
  }
  if (res.status === 401) {
    // Refresh mislukt of al een retry → sessie-verloop (caller/guard → login).
    const body = await res.json().catch(() => ({}))
    const err = new Error('NIET_GEAUTHENTICEERD')
    err.status = 401
    err.code = body?.fout?.code || 'NIET_GEAUTHENTICEERD'
    throw err
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    const err = new Error(body?.fout?.bericht || `HTTP ${res.status}`)
    // Verrijkt voor fout-mapping in de UI (403/404/409/422).
    err.status = res.status
    err.code = body?.fout?.code || null
    err.detail = body?.detail || null
    throw err
  }
  if (res.status === 204) return null // No Content (bv. DELETE)
  return res.json()
}

function _query(params = {}) {
  const q = new URLSearchParams()
  for (const [sleutel, waarde] of Object.entries(params)) {
    if (Array.isArray(waarde)) {
      // Array → herhaalde param (bv. status=concept&status=geblokkeerd). Lege
      // array → niets (geen filter) — backwards-compatible.
      for (const v of waarde) {
        if (v !== undefined && v !== null && v !== '') q.append(sleutel, v)
      }
    } else if (waarde !== undefined && waarde !== null && waarde !== '') {
      q.set(sleutel, waarde)
    }
  }
  const s = q.toString()
  return s ? `?${s}` : ''
}

export const api = {
  me: () => request('/auth/me'),
  logout: () => request('/auth/logout', { method: 'POST' }),

  // Tenant-breed dashboard-overzicht (read-only aggregatie, één respons).
  dashboard: () => request('/dashboard'),

  applicaties: {
    // sort/order/filters optioneel — alles weggelaten → server-default
    // (created_at asc, geen filters), exact backwards-compatible (ADR-017/CD017).
    // `status` is een array (herhaalde param); lege array → geen statusfilter.
    lijst: ({ limit, after, sort, order, status, hostingmodel, eigenaar, zoek } = {}) =>
      request(
        `/applicaties${_query({ limit, after, sort, order, status, hostingmodel, eigenaar, zoek })}`,
      ),
    haal: (id) => request(`/applicaties/${id}`),
    maak: (data) => request('/applicaties', { method: 'POST', body: JSON.stringify(data) }),
    werkBij: (id, data) =>
      request(`/applicaties/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
    startInventarisatie: (id) =>
      request(`/applicaties/${id}/start-inventarisatie`, { method: 'POST' }),
    verwijder: (id) => request(`/applicaties/${id}`, { method: 'DELETE' }),
    opties: () => request('/applicaties/opties'),
    // ADR-020: 'app → waar valt hij onder' (gekoppelde contracten met rol + leverancier).
    contracten: (id) => request(`/applicaties/${id}/contracten`),
  },

  datatypes: {
    // sort/order optioneel (CD020) — weglaten = server-default (created_at asc).
    lijst: ({ applicatieId, limit, after, sort, order } = {}) =>
      request(`/datatypes${_query({ applicatie_id: applicatieId, limit, after, sort, order })}`),
    haal: (id) => request(`/datatypes/${id}`),
    maak: (data) => request('/datatypes', { method: 'POST', body: JSON.stringify(data) }),
    werkBij: (id, data) =>
      request(`/datatypes/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
    verwijder: (id) => request(`/datatypes/${id}`, { method: 'DELETE' }),
    opties: () => request('/datatypes/opties'),
  },

  gebruikersgroepen: {
    // sort/order optioneel (CD020) — weglaten = server-default (created_at asc).
    lijst: ({ applicatieId, limit, after, sort, order } = {}) =>
      request(
        `/gebruikersgroepen${_query({ applicatie_id: applicatieId, limit, after, sort, order })}`,
      ),
    haal: (id) => request(`/gebruikersgroepen/${id}`),
    maak: (data) =>
      request('/gebruikersgroepen', { method: 'POST', body: JSON.stringify(data) }),
    werkBij: (id, data) =>
      request(`/gebruikersgroepen/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
    verwijder: (id) => request(`/gebruikersgroepen/${id}`, { method: 'DELETE' }),
    // Gebruikersgroep heeft geen enum-velden → geen opties-endpoint.
  },

  koppelingen: {
    // Eén ouder-filter per call (bron OF doel); de detail-view doet twee calls
    // en concateneert de disjuncte sets (DB-CHECK bron != doel → geen overlap).
    lijst: ({ bronApplicatieId, doelApplicatieId, limit, after, sort, order } = {}) =>
      request(
        `/koppelingen${_query({
          bron_applicatie_id: bronApplicatieId,
          doel_applicatie_id: doelApplicatieId,
          limit,
          after,
          sort,
          order,
        })}`,
      ),
    haal: (id) => request(`/koppelingen/${id}`),
    maak: (data) => request('/koppelingen', { method: 'POST', body: JSON.stringify(data) }),
    werkBij: (id, data) =>
      request(`/koppelingen/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
    verwijder: (id) => request(`/koppelingen/${id}`, { method: 'DELETE' }),
    opties: () => request('/koppelingen/opties'),
  },

  // ADR-020 contractregister — leverancier (tenant-CRUD).
  leveranciers: {
    lijst: ({ limit, after, sort, order, zoek } = {}) =>
      request(`/leveranciers${_query({ limit, after, sort, order, zoek })}`),
    haal: (id) => request(`/leveranciers/${id}`),
    maak: (data) => request('/leveranciers', { method: 'POST', body: JSON.stringify(data) }),
    werkBij: (id, data) =>
      request(`/leveranciers/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
    verwijder: (id) => request(`/leveranciers/${id}`, { method: 'DELETE' }),
  },

  // ADR-020 contractregister — contract (tenant-CRUD) + sub-overzichten.
  contracten: {
    lijst: ({ limit, after, sort, order, leverancierId, contracttype, dekking, kostenmodel, zoek } = {}) =>
      request(
        `/contracten${_query({
          limit,
          after,
          sort,
          order,
          leverancier_id: leverancierId,
          contracttype,
          dekking,
          kostenmodel,
          zoek,
        })}`,
      ),
    haal: (id) => request(`/contracten/${id}`),
    maak: (data) => request('/contracten', { method: 'POST', body: JSON.stringify(data) }),
    werkBij: (id, data) =>
      request(`/contracten/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
    verwijder: (id) => request(`/contracten/${id}`, { method: 'DELETE' }),
    deelcontracten: (id) => request(`/contracten/${id}/deelcontracten`),
    applicaties: (id) => request(`/contracten/${id}/applicaties`),
  },

  // ADR-020 — applicatie↔contract-koppeling (precies één rol per koppeling).
  applicatieContracten: {
    maak: (data) => request('/applicatie-contracten', { method: 'POST', body: JSON.stringify(data) }),
    werkBij: (id, data) =>
      request(`/applicatie-contracten/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
    verwijder: (id) => request(`/applicatie-contracten/${id}`, { method: 'DELETE' }),
  },

  // ADR-020 §0 (CD043) — tenant-leeszijde van de classificatie-catalogus: alleen
  // ACTIEVE opties per dimensie (voor formulier-checkboxen + rol-select).
  contractconfig: {
    opties: () => request('/contracten/opties'),
  },

  checklistscores: {
    lijst: ({ applicatieId, limit, after } = {}) =>
      request(`/checklistscores${_query({ applicatie_id: applicatieId, limit, after })}`),
    maak: (data) => request('/checklistscores', { method: 'POST', body: JSON.stringify(data) }),
    werkBij: (id, data) =>
      request(`/checklistscores/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
    verwijder: (id) => request(`/checklistscores/${id}`, { method: 'DELETE' }),
    opties: () => request('/checklistscores/opties'),
  },

  // Blokkade is systeem-afgeleid: geen maak/verwijder (backend kent ze niet).
  blokkades: {
    // sort/order optioneel (CD020, per-app lijst) — weglaten = server-default.
    lijst: ({ applicatieId, status, limit, after, sort, order } = {}) =>
      request(
        `/blokkades${_query({ applicatie_id: applicatieId, status, limit, after, sort, order })}`,
      ),
    // Tenant-breed sorteerbaar overzicht (CD016, consument ADR-017).
    overzicht: ({ limit, after, status, sort, order } = {}) =>
      request(`/blokkades/overzicht${_query({ limit, after, status, sort, order })}`),
    haal: (id) => request(`/blokkades/${id}`),
    werkBij: (id, data) =>
      request(`/blokkades/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
    opties: () => request('/blokkades/opties'),
  },

  // Read-only referentiedata (89 vragen), één respons (geen cursor).
  checklistvragen: {
    lijst: () => request('/checklistvragen'),
  },

  // Platform-beheer van de checklist-antwoordconfiguratie (ADR-019 fase 2D/2E,
  // platform-sessie). Server handhaaft alle regels (orphan-409, afgeleid, type).
  platformChecklistconfig: {
    lijst: () => request('/platform/checklistconfig'),
    zetAntwoordtype: (code, antwoordtype) =>
      request(`/platform/checklistconfig/vragen/${encodeURIComponent(code)}`, {
        method: 'PATCH',
        body: JSON.stringify({ antwoordtype }),
      }),
    voegOptieToe: (code, data) =>
      request(`/platform/checklistconfig/vragen/${encodeURIComponent(code)}/opties`, {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    wijzigOptie: (id, data) =>
      request(`/platform/checklistconfig/opties/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(data),
      }),
    deactiveerOptie: (id) =>
      request(`/platform/checklistconfig/opties/${id}/deactiveren`, { method: 'POST' }),
  },

  // ADR-020 Besluit 6/7 — platform-beheer van de contract-classificatie-catalogus
  // (ADR-012 Addendum B). GÉÉN verwijder: er is geen DELETE-endpoint (soft-deactivate
  // via werkBij `actief`). Zelfde platform-auth-pad als het checklistconfig-beheer.
  platformContractconfig: {
    lijst: ({ dimensie } = {}) => request(`/platform/contractconfig${_query({ dimensie })}`),
    maak: (data) => request('/platform/contractconfig', { method: 'POST', body: JSON.stringify(data) }),
    werkBij: (id, data) =>
      request(`/platform/contractconfig/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  },
}
