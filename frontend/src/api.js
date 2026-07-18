// API-client — fetch met httpOnly cookie (credentials: include).
// Foutformaat conform CLAUDE.md: { fout: { code, http_status, bericht } };
// 422 = FastAPI { detail: [...] }. 401 → single-flight refresh-on-401 (ADR-015 B6).
const BASE = '/api/v1'

// Single-flight refresh: gelijktijdige 401's delen één lopende /auth/refresh-poging
// (geen stampede). Resolved op de HTTP-status van /auth/refresh (geen body/code).
// Raw fetch (NIET via request()) → de refresh-respons voedt de refresh-on-401-logica nooit
// terug (geen lus). Geëxporteerd zodat de sessiecheck (store/auth.js) dezelfde single-flight
// refresh kan proberen vóór hij een sessie opgeeft (consistent met de data-fetches).
let _refreshPromise = null
export function refreshSessie() {
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

// Centrale verlopen-sessie-vangrail. `api.js` blijft framework-loos (geen router/store-import):
// de app registreert bij init één handler (registreerSessieVerlopenHandler) die de sessie als
// verlopen afhandelt (user=null + redirect naar login?sessie_verlopen=1&next=<pad>). De hook wordt
// UITSLUITEND aangeroepen op het bewezen-gefaalde-refresh-punt (zie request()), dus nooit terwijl
// een sessie nog te redden is. Single-flight: bij een storm van gelijktijdige 401's grijpt hij
// éénmaal; een geslaagde (2xx) respons reset de vlag (sessie weer levend).
let _sessieVerlopenHandler = null
let _sessieVerloopBezig = false
export function registreerSessieVerlopenHandler(fn) {
  _sessieVerlopenHandler = fn
  _sessieVerloopBezig = false // (her)registratie = schone staat
}
function _meldSessieVerlopen() {
  if (_sessieVerloopBezig) return
  _sessieVerloopBezig = true
  try {
    _sessieVerlopenHandler?.()
  } catch {
    /* een fout in de handler mag de app niet breken */
  }
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
    const vernieuwd = await refreshSessie()
    if (vernieuwd) return request(path, options, true)
  }
  if (res.status === 401) {
    // Bewezen-gefaalde refresh (of al een retry) → sessie onherstelbaar verlopen. Centrale
    // vangrail: één keer netjes naar login leiden (geen rauwe code in beeld). De fout blijft
    // `.status===401` dragen zodat lokale catches desgewenst nog kunnen onderscheiden.
    _meldSessieVerlopen()
    const body = await res.json().catch(() => ({}))
    const err = new Error('NIET_GEAUTHENTICEERD')
    err.status = 401
    err.code = body?.fout?.code || 'NIET_GEAUTHENTICEERD'
    throw err
  }
  // Geslaagde respons ⇒ sessie leeft (weer); reset de vangrail-vlag voor een volgende cyclus.
  if (res.ok) _sessieVerloopBezig = false
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

// Filter-query mét allowlist (borging — zie likara-frontend "API-client-filterconventie").
// Eén conventie: filternamen zijn SNAKE_CASE, exact gelijk aan de backend-query-params, zodat
// er geen camel/snake-vertaalgrens is waar een filter stil kan verdwijnen. Een doorgegeven
// key die NIET in de allowlist staat → LUIDE fout (geen stille drop → nooit ongefilterd "alles").
// `_query` blijft bewust-lege waarden (undefined/null/'') weglaten: "bewust niet gezet" ≠
// "gezet onder een onbekende naam". Achtergrond: de Koppelingen-bug (KoppelingSectie gaf
// bron_id/doel_id terwijl de client bronId/doelId verwachtte → filter weg → alle 17 flows) en
// de V012-les.
function _filterQuery(naam, params, toegestaan) {
  const ok = new Set(toegestaan)
  for (const sleutel of Object.keys(params || {})) {
    if (!ok.has(sleutel)) {
      throw new Error(
        `onbekende filter-parameter '${sleutel}' voor ${naam} — toegestaan: ${toegestaan.join(', ')}`,
      )
    }
  }
  return _query(params || {})
}

export const api = {
  me: () => request('/auth/me'),
  logout: () => request('/auth/logout', { method: 'POST' }),

  // Tenant-breed dashboard-overzicht (read-only aggregatie, één respons).
  dashboard: () => request('/dashboard'),

  // ADR-029 — gebruikersbeheer (GEBRUIKERSBEHEER, beheerder-only; backend handhaaft).
  // `maak` retourneert { gebruiker, tijdelijk_wachtwoord } (eenmalig).
  gebruikers: {
    lijst: (params = {}) => request(`/gebruikers${_filterQuery('gebruikers.lijst', params, ['limit', 'after'])}`),
    maak: (data) => request('/gebruikers', { method: 'POST', body: JSON.stringify(data) }),
    // ADR-029 Fase 2b — beheeracties op een bestaande gebruiker (alleen Beheerder; backend handhaaft).
    // `wachtwoordReset` retourneert { tijdelijk_wachtwoord } (eenmalig).
    wachtwoordReset: (id) => request(`/gebruikers/${id}/wachtwoord-reset`, { method: 'POST' }),
    wijzigRol: (id, rol) => request(`/gebruikers/${id}/rol`, { method: 'PATCH', body: JSON.stringify({ rol }) }),
    wijzigStatus: (id, actief) => request(`/gebruikers/${id}/status`, { method: 'PATCH', body: JSON.stringify({ actief }) }),
    corrigeer: (id, data) => request(`/gebruikers/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  },

  // ADR-029 Fase 3a — audit-spoor lezen (AUDITLOG, beheerder/auditor; backend handhaaft).
  // Lege filterparams worden door _query weggelaten. Levert {items, volgende_cursor}.
  auditlog: {
    lijst: (params = {}) =>
      request(`/auditlog${_filterQuery('auditlog.lijst', params, ['limit', 'after', 'actor_naam', 'component_id', 'actie', 'van', 'tot'])}`),
  },

  // ADR-029 — objecthistorie ('i'-knop). Toegang volgt het object; backend handhaaft de
  // object-leespermissie + tenant-resolutie. Levert {items, volgende_cursor}.
  objecthistorie: {
    lijst: ({ entiteitType, entiteitId, ...rest } = {}) =>
      request(`/objecthistorie/${entiteitType}/${entiteitId}${_filterQuery('objecthistorie.lijst', rest, ['limit', 'after'])}`),
  },

  // LI059 facade-purge — de aparte `/applicaties`-API is opgeheven; applicaties zijn
  // componenten (type 'applicatie') en lopen via `api.componenten`.

  datatypes: {
    // sort/order optioneel (CD020) — weglaten = server-default (created_at asc).
    lijst: (params = {}) =>
      request(`/datatypes${_filterQuery('datatypes.lijst', params, ['applicatie_id', 'limit', 'after', 'sort', 'order'])}`),
    haal: (id) => request(`/datatypes/${id}`),
    maak: (data) => request('/datatypes', { method: 'POST', body: JSON.stringify(data) }),
    werkBij: (id, data) =>
      request(`/datatypes/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
    verwijder: (id) => request(`/datatypes/${id}`, { method: 'DELETE' }),
    opties: () => request('/datatypes/opties'),
  },

  gebruikersgroepen: {
    // sort/order optioneel (CD020) — weglaten = server-default (created_at asc).
    lijst: (params = {}) =>
      request(
        `/gebruikersgroepen${_filterQuery('gebruikersgroepen.lijst', params, ['applicatie_id', 'limit', 'after', 'sort', 'order'])}`,
      ),
    haal: (id) => request(`/gebruikersgroepen/${id}`),
    maak: (data) =>
      request('/gebruikersgroepen', { method: 'POST', body: JSON.stringify(data) }),
    werkBij: (id, data) =>
      request(`/gebruikersgroepen/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
    verwijder: (id) => request(`/gebruikersgroepen/${id}`, { method: 'DELETE' }),
    // Gebruikersgroep heeft geen enum-velden → geen opties-endpoint.
    // Fase B slice 2a/2b (LI022/LI023) — gebruiker-context-picker voor het kaart-beginscherm.
    // `contexten`: distinct (organisatie, afdeling)-contexten met component-telling (alleen `zoek`).
    // `contextComponenten`: de componenten van één context (nullable composiet-sleutel → null-match).
    contexten: (params = {}) =>
      request(`/gebruikersgroepen/contexten${_filterQuery('gebruikersgroepen.contexten', params, ['zoek'])}`),
    contextComponenten: (params = {}) =>
      request(
        `/gebruikersgroepen/contexten/componenten${_filterQuery('gebruikersgroepen.contextComponenten', params, ['organisatie_id', 'afdeling_id'])}`,
      ),
  },

  // ADR-036 grof gebruiksfeit — "organisatie gebruikt applicatie". LI033: `lijstVoorOrganisatie`
  // levert de applicaties die één organisatie gebruikt (grove feit + component-naam + `verfijnd`-vlag,
  // grof-only incluis) in de gedeelde rij-vorm — één bron voor het "Gebruikte applicaties"-blok én de
  // Landschapskaart-subgraaf.
  organisatiegebruik: {
    lijstVoorOrganisatie: (params = {}) =>
      request(`/organisatiegebruik${_filterQuery('organisatiegebruik.lijstVoorOrganisatie', params, ['organisatie_id'])}`),
    // ADR-046 stuk 2 — de invoerroute voor het grove feit (de endpoints bestonden al,
    // de client miste ze): per component de organisaties (mét afdelingsnamen), losse
    // aanmaak (409 GEBRUIK_BESTAAT bij duplicaat) en verwijderen (409
    // GEBRUIK_HEEFT_VERFIJNING zolang er gebruikersgroepen onder hangen).
    lijstVoorApplicatie: (params = {}) =>
      request(`/organisatiegebruik${_filterQuery('organisatiegebruik.lijstVoorApplicatie', params, ['applicatie_id'])}`),
    maak: (data) => request('/organisatiegebruik', { method: 'POST', body: JSON.stringify(data) }),
    verwijder: (id) => request(`/organisatiegebruik/${id}`, { method: 'DELETE' }),
  },

  // ADR-024 slice 2a — partij-beheer (element-backed; alle aarden). `aard`-filter op de lijst.
  // Het contract-domein hergebruikt deze client voor de leverancier-picker (aard externe_partij).
  partijen: {
    lijst: (params = {}) =>
      request(`/partijen${_filterQuery('partijen.lijst', params, ['aard', 'aard_in', 'scope', 'organisatie_id', 'afdeling_id', 'limit', 'after', 'sort', 'order', 'zoek'])}`),
    haal: (id) => request(`/partijen/${id}`),
    maak: (data) => request('/partijen', { method: 'POST', body: JSON.stringify(data) }),
    werkBij: (id, data) =>
      request(`/partijen/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
    verwijder: (id) => request(`/partijen/${id}`, { method: 'DELETE' }),
    soorten: () => request('/partijen/soorten'),
    // ADR-042 slice 5 — afgeleid beeld: processen via de componenten van deze organisatie.
    processen: (id) => request(`/partijen/${id}/processen`),
    // LI019 — componenten van een leverancier (partij) via de contract-keten.
    componentenViaContract: (id) => request(`/partijen/${id}/componenten`),
  },

  // ADR-024 slice 2b — rol-toewijzing (partij vervult rol op component/contract). Eigen tabel
  // (geen relatie-model). Lezen filtert op precies één van object_id/partij_id; rollen = de
  // beheerbare beheerrol-catalogus voor het rol-dropdown.
  roltoewijzingen: {
    lijst: (params = {}) =>
      request(`/roltoewijzingen${_filterQuery('roltoewijzingen.lijst', params, ['object_id', 'partij_id'])}`),
    rollen: () => request('/roltoewijzingen/rollen'),
    maak: (data) => request('/roltoewijzingen', { method: 'POST', body: JSON.stringify(data) }),
    verwijder: (id) => request(`/roltoewijzingen/${id}`, { method: 'DELETE' }),
  },

  // ADR-027 — component-klaarverklaring (niet-scorend; per component één levende verklaring).
  klaarverklaringen: {
    // component_id MOET zowel in de destructuring als in de query (V012-les: anders dropt
    // de client de filter stil).
    lijst: (params = {}) => request(`/klaarverklaringen${_filterQuery('klaarverklaringen.lijst', params, ['component_id'])}`),
    maak: (data) => request('/klaarverklaringen', { method: 'POST', body: JSON.stringify(data) }),
    wijzigStatus: (id, data) =>
      request(`/klaarverklaringen/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  },

  // ADR-020 contractregister — contract (tenant-CRUD) + sub-overzichten.
  contracten: {
    lijst: (params = {}) =>
      request(
        `/contracten${_filterQuery('contracten.lijst', params, ['limit', 'after', 'sort', 'order', 'leverancier_id', 'contracttype', 'dekking', 'kostenmodel', 'zoek'])}`,
      ),
    haal: (id) => request(`/contracten/${id}`),
    maak: (data) => request('/contracten', { method: 'POST', body: JSON.stringify(data) }),
    werkBij: (id, data) =>
      request(`/contracten/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
    verwijder: (id) => request(`/contracten/${id}`, { method: 'DELETE' }),
    deelcontracten: (id) => request(`/contracten/${id}/deelcontracten`),
    // ADR-030 — per-band (component↔contract) dekking.
    bandDekking: {
      ophalen: (contractId, componentId) => request(`/contracten/${contractId}/band-dekking/${componentId}`),
      instellen: (contractId, componentId, sleutels) =>
        request(`/contracten/${contractId}/band-dekking/${componentId}`, { method: 'PUT', body: JSON.stringify({ dekking_sleutels: sleutels }) }),
      verwijderen: (contractId, componentId) =>
        request(`/contracten/${contractId}/band-dekking/${componentId}`, { method: 'DELETE' }),
    },
    applicaties: (id) => request(`/contracten/${id}/applicaties`),
    // Fase B slice 2a (LI022) — ALLE aan het contract gekoppelde componenten (context-route naar de
    // kaart-subgraaf), incl. kale/profielloze componenten die `/applicaties` weglaat.
    componenten: (id) => request(`/contracten/${id}/componenten`),
  },

  // ADR-020 — applicatie↔contract-koppeling (precies één rol per koppeling).
  // ADR-021 — componenten (technische laag) + structuurgraaf. Met de shared-PK is een
  // applicatie-id identiek aan zijn component-id (zelfde waarden).
  componenten: {
    // Verenigde lijst (CD054b W1): besturingsfilters status/hostingmodel/eigenaar
    // naast componenttype + zoek. `status` is een array (herhaalde param).
    // ADR-023 Fase C: `laag` (application/technology) filtert op ArchiMate-laag
    // (read-only catalogus-typing) bovenop het type-filter.
    lijst: (params = {}) =>
      request(
        // LI040 — BIV filtert op de hoogste as (`biv_min`) of het gat (`biv_ontbreekt`);
        // de drie per-as-params zijn vervallen. `migratiepad` = het Bedoeling-filter.
        // LI040 — `*_ontbreekt` maakt "nog niet vastgelegd" vindbaar (filter op NULL).
        `/componenten${_filterQuery('componenten.lijst', params, ['limit', 'after', 'sort', 'order', 'componenttype', 'laag', 'status', 'hostingmodel', 'levensfase', 'levensfase_ontbreekt', 'migratiepad', 'migratiepad_ontbreekt', 'complexiteit', 'complexiteit_ontbreekt', 'prioriteit', 'prioriteit_ontbreekt', 'eigenaar_organisatie_id', 'leverancier_id', 'zoek', 'componentrol', 'biv_min', 'biv_ontbreekt', 'klaarverklaring', 'afwijking', 'ondersteunt_werk'])}`,
      ),
    haal: (id) => request(`/componenten/${id}`),
    maak: (data) => request('/componenten', { method: 'POST', body: JSON.stringify(data) }),
    werkBij: (id, data) => request(`/componenten/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
    verwijder: (id) => request(`/componenten/${id}`, { method: 'DELETE' }),
    opties: () => request('/componenten/opties'),
    // ADR-022 Fase E — type-generieke beoordeling starten (concept → in_inventarisatie).
    startBeoordeling: (id) => request(`/componenten/${id}/start-beoordeling`, { method: 'POST' }),
    structuur: (id) => request(`/componenten/${id}/structuur`),
    // ADR-022 Fase C — read-only "wat verdwijnt"-samenvatting bij verwijderen.
    verwijderImpact: (id) => request(`/componenten/${id}/verwijder-impact`),
    // 'component → contracten' (vervangt het oude app→contracten-overzicht, CD054).
    contracten: (id) => request(`/componenten/${id}/contracten`),
    // ADR-021 Fase E — read-only impactanalyse (afhankelijke componenten + readiness).
    impact: (id) => request(`/componenten/${id}/impact`),
  },

  // ADR-023 — unified getypeerd relatiemodel. Vervangt de in de cutover vervallen
  // `component-structuren`-CRUD: structuurrelaties (assignment = draait-op, host→gehoste)
  // worden hier gelegd. Endpoints/relatietype zijn immutabel → werkBij wijzigt alleen
  // `omschrijving`/`kenmerken`.
  relaties: {
    lijst: (params = {}) =>
      request(`/relaties${_filterQuery('relaties.lijst', params, ['limit', 'after', 'bron_id', 'doel_id', 'relatietype', 'paar_bron_id', 'paar_doel_id', 'sort', 'order'])}`),
    haal: (id) => request(`/relaties/${id}`),
    maak: (data) => request('/relaties', { method: 'POST', body: JSON.stringify(data) }),
    werkBij: (id, data) => request(`/relaties/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
    verwijder: (id) => request(`/relaties/${id}`, { method: 'DELETE' }),
  },

  // ADR-023 Fase F (F-2) — cross-element laagprojectie (read-only architectuuroverzicht).
  architectuur: {
    // sort/order optioneel (ADR-017) — weglaten = server-default (created_at asc).
    elementen: (params = {}) =>
      request(`/architectuur/elementen${_filterQuery('architectuur.elementen', params, ['limit', 'after', 'laag', 'aspect', 'type', 'sort', 'order'])}`),
  },

  // ADR-025 — Landschapskaart: volledige graaf (nodes + edges) in één read-only call.
  // Fase B (LI022) — `subgraaf`: set-scoped graaf (de gegeven component-ids + hun directe 1-hop-buren)
  // via POST (de id-lijst wordt lang → geen GET-querystring). Zelfde respons-vorm als `haalGrafdata`.
  landschapskaart: {
    haalGrafdata: (params = {}) => request(`/landschapskaart${_filterQuery('landschapskaart.haalGrafdata', params, ['diepte'])}`),
    subgraaf: (component_ids, diepte = 1) =>
      request('/landschapskaart/subgraaf', { method: 'POST', body: JSON.stringify({ component_ids, diepte }) }),
  },

  // ADR-033 slice 2 — opgeslagen & deelbare Impact-verkenner-views. Lijst = eigen + gedeeld
  // (server filtert op maker/gedeeld); ophalen/wijzigen/verwijderen no-leak-404 voor niet-eigen.
  impactViews: {
    lijst: () => request('/impact-views'),
    haal: (id) => request(`/impact-views/${id}`),
    maak: (data) => request('/impact-views', { method: 'POST', body: JSON.stringify(data) }),
    werkBij: (id, data) => request(`/impact-views/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
    verwijder: (id) => request(`/impact-views/${id}`, { method: 'DELETE' }),
  },

  // ADR-041 — persoonlijke voorkeuren ("onthoud als mijn standaard"). Strikt per gebruiker (server
  // stempelt de `sub`); `zet` = upsert van de héle waarde, `herroep` = terug naar baseline.
  voorkeuren: {
    haalAlle: () => request('/voorkeuren'),
    zet: (sleutel, waarde) => request(`/voorkeuren/${sleutel}`, { method: 'PUT', body: JSON.stringify({ waarde }) }),
    herroep: (sleutel) => request(`/voorkeuren/${sleutel}`, { method: 'DELETE' }),
  },

  // ADR-023 Fase F (F-3 stap 2) — consistentie-signalering technische plaatsing (read-only).
  signalen: {
    plaatsing: () => request('/signalen/plaatsing'),
  },

  // ADR-035 Slice 1 — Signalering registratiegaten (read-only). Centraal overzicht
  // (ARCHITECTUUR.LEZEN) + per-component badge (COMPONENT.LEZEN).
  signalering: {
    registratiegaten: () => request('/signalering/registratiegaten'),
    badgeComponent: (id) => request(`/signalering/badges/component/${id}`),
  },

  // ADR-023 Fase E/F (F-1) — migratielaag (read-only overzicht). Leunt volledig op de
  // bestaande lees-endpoints; geen nieuwe backend-semantiek.
  plateaus: {
    // `zoek` (ILIKE op naam) bedient het plateau-koppelveld in de deliverable-keten (UX-A4-3).
    lijst: (params = {}) => request(`/plateaus${_filterQuery('plateaus.lijst', params, ['limit', 'after', 'zoek'])}`),
    haal: (id) => request(`/plateaus/${id}`),
    maak: (data) => request('/plateaus', { method: 'POST', body: JSON.stringify(data) }),
    werkBij: (id, data) => request(`/plateaus/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
    verwijder: (id) => request(`/plateaus/${id}`, { method: 'DELETE' }),
    // UX-A4-1 — beheer van leden. ADR-046: `disposities()` is met het dispositie-
    // invoerveld vervallen (het plateau draagt geen eigen bedoeling meer).
    leden: (id) => request(`/plateaus/${id}/leden`),
    voegLid: (id, data) => request(`/plateaus/${id}/leden`, { method: 'POST', body: JSON.stringify(data) }),
    werkLid: (id, lidId, data) =>
      request(`/plateaus/${id}/leden/${lidId}`, { method: 'PATCH', body: JSON.stringify(data) }),
    verwijderLid: (id, lidId) => request(`/plateaus/${id}/leden/${lidId}`, { method: 'DELETE' }),
  },
  gaps: {
    lijst: (params = {}) => request(`/gaps${_filterQuery('gaps.lijst', params, ['limit', 'after'])}`),
    haal: (id) => request(`/gaps/${id}`), // GapDetail incl. de twee readiness-cijfers
    maak: (data) => request('/gaps', { method: 'POST', body: JSON.stringify(data) }),
    werkBij: (id, data) => request(`/gaps/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
    verwijder: (id) => request(`/gaps/${id}`, { method: 'DELETE' }),
    leden: (id) => request(`/gaps/${id}/leden`),
    voegLid: (id, lid_id) => request(`/gaps/${id}/leden`, { method: 'POST', body: JSON.stringify({ lid_id }) }),
    verwijderLid: (id, lidId) => request(`/gaps/${id}/leden/${lidId}`, { method: 'DELETE' }),
  },
  workPackages: {
    // `zoek` (CD017 ILIKE op naam) bedient het "bovenliggend werkpakket"-keuzeveld (UX-A4-2).
    lijst: (params = {}) => request(`/work-packages${_filterQuery('workPackages.lijst', params, ['limit', 'after', 'zoek'])}`),
    haal: (id) => request(`/work-packages/${id}`),
    maak: (data) => request('/work-packages', { method: 'POST', body: JSON.stringify(data) }),
    werkBij: (id, data) => request(`/work-packages/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
    verwijder: (id) => request(`/work-packages/${id}`, { method: 'DELETE' }),
    subboom: (id) => request(`/work-packages/${id}/subboom`),
  },
  // ADR-042 slice 1 — procesregister (nestbare procesboom). Schermen volgen in slice 4;
  // de allowlist volgt de route: sort/order (ADR-017), zoek (ILIKE), ouder_id (boom-niveau).
  processen: {
    lijst: (params = {}) => request(`/processen${_filterQuery('processen.lijst', params, ['limit', 'after', 'sort', 'order', 'zoek', 'ouder_id'])}`),
    haal: (id) => request(`/processen/${id}`),
    maak: (data) => request('/processen', { method: 'POST', body: JSON.stringify(data) }),
    werkBij: (id, data) => request(`/processen/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
    verwijder: (id) => request(`/processen/${id}`, { method: 'DELETE' }),
    subboom: (id) => request(`/processen/${id}/subboom`),
    // ADR-042 slice 5 — doorgerolde koppelregels uit de volledige subboom (read-only).
    rollup: (id) => request(`/processen/${id}/rollup`),
  },
  // ADR-042 slice 3 — koppelregels component→proces ("vervult applicatiefunctie in").
  // Lezen kan per proces (?proces_id=) óf per component (?component_id=), precies één.
  procesvervullingen: {
    lijst: (params = {}) => request(`/procesvervullingen${_filterQuery('procesvervullingen.lijst', params, ['proces_id', 'component_id'])}`),
    functies: () => request('/procesvervullingen/functies'),
    maak: (data) => request('/procesvervullingen', { method: 'POST', body: JSON.stringify(data) }),
    // LI035 — alleen de kenmerk-velden (applicatiefunctie/toelichting); ankers onwijzigbaar.
    werkBij: (id, data) => request(`/procesvervullingen/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
    verwijder: (id) => request(`/procesvervullingen/${id}`, { method: 'DELETE' }),
  },
  // ADR-049 gate 2a — koppelregel component→bedrijfsfunctie (kaal). `dekking` levert de
  // GEDEELDE leesregel per plek (fijn verdringt grof — één afleiding, server-side); de boom
  // leest die, ze rekent niet zelf. Leeg `ouder_functie_id` bij maak = grof (geldt overal),
  // gevuld = fijn (déze plek). Verwijderen = beheerder (backend handhaaft).
  functievervullingen: {
    dekking: () => request('/functievervullingen/dekking'),
    // ADR-043 gate 4 (G2) — "waarvoor dient dit systeem": de koppelingen van één component,
    // uit dezelfde leesregel (fijn verdringt grof), her-geïndexeerd op het component.
    componentKoppelingen: (componentId) => request(`/functievervullingen/component/${componentId}`),
    // ADR-051 gate 3 — de VIER standen per plek + gedeelde tellers (één afleiding, twee vensters).
    standen: () => request('/functievervullingen/standen'),
    maak: (data) => request('/functievervullingen', { method: 'POST', body: JSON.stringify(data) }),
    // ADR-051 — "hier draait geen systeem — vastgesteld" (bevinding) + het oordeel op een koppeling.
    geenSysteem: (data) => request('/functievervullingen/geen-systeem', { method: 'POST', body: JSON.stringify(data) }),
    zetOordeel: (id, oordeel) => request(`/functievervullingen/${id}/oordeel`, { method: 'PATCH', body: JSON.stringify({ oordeel }) }),
    verwijder: (id) => request(`/functievervullingen/${id}`, { method: 'DELETE' }),
  },
  // ADR-043 gate 1a — bedrijfsfunctie-as (de logische ruggengraat). Het gebruikers-pad
  // maakt uitsluitend EIGEN functies; modelinhoud is server-side read-only (422
  // MODELINHOUD_BESCHERMD — de UI toont die affordance dan ook niet).
  bedrijfsfuncties: {
    // ADR-044: het `ouder_id`-lijstfilter is vervallen (de boom leeft in plaatsingen;
    // "directe deelfuncties van X" beantwoordt GET /{id}/subboom).
    lijst: (params = {}) => request(`/bedrijfsfuncties${_filterQuery('bedrijfsfuncties.lijst', params, ['limit', 'after', 'sort', 'order', 'zoek'])}`),
    haal: (id) => request(`/bedrijfsfuncties/${id}`),
    maak: (data) => request('/bedrijfsfuncties', { method: 'POST', body: JSON.stringify(data) }),
    werkBij: (id, data) => request(`/bedrijfsfuncties/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
    verwijder: (id) => request(`/bedrijfsfuncties/${id}`, { method: 'DELETE' }),
    subboom: (id) => request(`/bedrijfsfuncties/${id}/subboom`),
    // ADR-044 — plaatsingen: hang een functie (óók) onder een ouder / haal één plek weg.
    plaats: (id, data) => request(`/bedrijfsfuncties/${id}/plaatsingen`, { method: 'POST', body: JSON.stringify(data) }),
    verwijderPlaatsing: (id, ouderId) => request(`/bedrijfsfuncties/${id}/plaatsingen/${ouderId}`, { method: 'DELETE' }),
  },
  // Gate 1b — referentiemodel inlezen: eerst het VOORBEELD (dry-run, schrijft niets),
  // dan pas bevestigen (inlezen). POST zonder body: het model komt uit het gecureerde
  // aanbod. Inlezen = beheerder (backend handhaaft via REFERENTIEMODEL.AANMAKEN).
  referentiemodellen: {
    overzicht: () => request('/referentiemodellen'),
    voorbeeld: (modelSleutel) =>
      request(`/referentiemodellen/${encodeURIComponent(modelSleutel)}/voorbeeld`, { method: 'POST' }),
    inlezen: (modelSleutel) =>
      request(`/referentiemodellen/${encodeURIComponent(modelSleutel)}/inlezen`, { method: 'POST' }),
  },
  deliverables: {
    lijst: (params = {}) => request(`/deliverables${_filterQuery('deliverables.lijst', params, ['limit', 'after'])}`),
    haal: (id) => request(`/deliverables/${id}`),
    maak: (data) => request('/deliverables', { method: 'POST', body: JSON.stringify(data) }),
    werkBij: (id, data) => request(`/deliverables/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
    verwijder: (id) => request(`/deliverables/${id}`, { method: 'DELETE' }),
    keten: (id) => request(`/deliverables/${id}/keten`),
    // Realisatieketen: werkpakket → deliverable → plateau (UX-A4-3, expliciet + optioneel).
    koppelWerkpakket: (id, work_package_id) =>
      request(`/deliverables/${id}/werkpakketten`, { method: 'POST', body: JSON.stringify({ work_package_id }) }),
    ontkoppelWerkpakket: (id, relatieId) =>
      request(`/deliverables/${id}/werkpakketten/${relatieId}`, { method: 'DELETE' }),
    koppelPlateau: (id, plateau_id) =>
      request(`/deliverables/${id}/plateaus`, { method: 'POST', body: JSON.stringify({ plateau_id }) }),
    ontkoppelPlateau: (id, relatieId) =>
      request(`/deliverables/${id}/plateaus/${relatieId}`, { method: 'DELETE' }),
  },

  componentContracten: {
    maak: (data) => request('/component-contracten', { method: 'POST', body: JSON.stringify(data) }),
    werkBij: (id, data) =>
      request(`/component-contracten/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
    verwijder: (id) => request(`/component-contracten/${id}`, { method: 'DELETE' }),
  },

  // ADR-052 slice 2 — "bewust geen"-bevinding per component (soort = 'koppelingen' | 'contract').
  componentBevindingen: {
    lijst: (componentId) => request(`/component-bevindingen/component/${componentId}`),
    maak: (componentId, data) =>
      request(`/component-bevindingen/component/${componentId}`, { method: 'POST', body: JSON.stringify(data) }),
    verwijder: (componentId, soort) =>
      request(`/component-bevindingen/component/${componentId}/${soort}`, { method: 'DELETE' }),
  },

  // ADR-052 slice 3 — live norm-status per component ({ feiten: { feit: status } }).
  // Slice 4a — de verschoven lat onderscheiden van de bewuste afwijking (besluiten 8-11):
  //   afwijking(id)   → { bewust:[...], verschoven:[...] } per component (componentvenster)
  //   verschovenLat() → [{ feit, aantal, componenten:[{id,naam}] }] (werkvoorraadvenster)
  componentNormen: {
    status: (componentId) => request(`/component-normen/status/${componentId}`),
    afwijking: (componentId) => request(`/component-normen/afwijking/${componentId}`),
    verschovenLat: () => request('/component-normen/verschoven-lat'),
    // Slice 4b — het norm-beheerscherm: lees de definitie, voorspel impact, zet de verplicht-vlag.
    definitie: () => request('/component-normen'),
    impact: (feit, verplicht) => request(`/component-normen/${feit}/impact?verplicht=${verplicht}`),
    zetVerplicht: (feit, verplicht) =>
      request(`/component-normen/${feit}`, { method: 'PUT', body: JSON.stringify({ verplicht }) }),
  },

  // ADR-020 §0 (CD043) — tenant-leeszijde van de classificatie-catalogus: alleen
  // ACTIEVE opties per dimensie (voor formulier-checkboxen + rol-select).
  contractconfig: {
    opties: () => request('/contracten/opties'),
  },

  checklistscores: {
    // ADR-022 Fase A: scores ankeren op component_id (== applicatie-id, shared-PK).
    lijst: (params = {}) =>
      request(`/checklistscores${_filterQuery('checklistscores.lijst', params, ['component_id', 'limit', 'after'])}`),
    maak: (data) => request('/checklistscores', { method: 'POST', body: JSON.stringify(data) }),
    werkBij: (id, data) =>
      request(`/checklistscores/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
    verwijder: (id) => request(`/checklistscores/${id}`, { method: 'DELETE' }),
    opties: () => request('/checklistscores/opties'),
  },

  // Blokkade is systeem-afgeleid: geen maak/verwijder (backend kent ze niet).
  blokkades: {
    // sort/order optioneel (CD020, per-app lijst) — weglaten = server-default.
    lijst: (params = {}) =>
      request(
        `/blokkades${_filterQuery('blokkades.lijst', params, ['component_id', 'status', 'limit', 'after', 'sort', 'order'])}`,
      ),
    // Tenant-breed sorteerbaar overzicht (CD016, consument ADR-017).
    overzicht: (params = {}) =>
      request(`/blokkades/overzicht${_filterQuery('blokkades.overzicht', params, ['limit', 'after', 'status', 'sort', 'order'])}`),
    haal: (id) => request(`/blokkades/${id}`),
    werkBij: (id, data) =>
      request(`/blokkades/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
    opties: () => request('/blokkades/opties'),
  },

  // Read-only referentiedata (89 vragen), één respons (geen cursor).
  // ADR-022 Fase E: optionele `componenttype`-scoping (symmetrisch met de engine);
  // weggelaten = alle actieve vragen.
  checklistvragen: {
    lijst: (componenttype) =>
      request(`/checklistvragen${componenttype ? `?componenttype=${encodeURIComponent(componenttype)}` : ''}`),
  },

  // ADR-022 W1 — TENANT-beheer van de checklist-vragenset + antwoordconfiguratie
  // (lk_app, tenant-shell). Vragen worden geadresseerd op hun `id`. Server
  // handhaaft alle regels (CHECKLISTVRAAG_BESTAAT-409, orphan-409, afgeleid, type).
  checklistconfig: {
    lijst: () => request('/checklistconfig'),
    betekenissen: () => request('/checklistconfig/betekenissen'),
    impact: (componenttype) =>
      request(`/checklistconfig/impact?componenttype=${encodeURIComponent(componenttype)}`),
    maakVraag: (data) =>
      request('/checklistconfig/vragen', { method: 'POST', body: JSON.stringify(data) }),
    werkVraagBij: (id, data) =>
      request(`/checklistconfig/vragen/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
    zetAntwoordtype: (id, antwoordtype) =>
      request(`/checklistconfig/vragen/${id}/antwoordtype`, {
        method: 'PATCH',
        body: JSON.stringify({ antwoordtype }),
      }),
    zetBetekenis: (id, betekenis) =>
      request(`/checklistconfig/vragen/${id}/betekenis`, {
        method: 'PATCH',
        body: JSON.stringify({ betekenis }),
      }),
    zetActief: (id, actief) =>
      request(`/checklistconfig/vragen/${id}/actief`, {
        method: 'POST',
        body: JSON.stringify({ actief }),
      }),
    voegOptieToe: (id, data) =>
      request(`/checklistconfig/vragen/${id}/opties`, {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    wijzigOptie: (id, data) =>
      request(`/checklistconfig/opties/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
    deactiveerOptie: (id) =>
      request(`/checklistconfig/opties/${id}/deactiveren`, { method: 'POST' }),
  },

  // ADR-020 Besluit 6/7 — platform-beheer van de contract-classificatie-catalogus
  // (ADR-012 Addendum B). GÉÉN verwijder: er is geen DELETE-endpoint (soft-deactivate
  // via werkBij `actief`). Zelfde platform-auth-pad als het checklistconfig-beheer.
  platformContractconfig: {
    lijst: (params = {}) => request(`/platform/contractconfig${_filterQuery('platformContractconfig.lijst', params, ['dimensie'])}`),
    maak: (data) => request('/platform/contractconfig', { method: 'POST', body: JSON.stringify(data) }),
    werkBij: (id, data) =>
      request(`/platform/contractconfig/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  },

  // ADR-021 Besluit 8 / ADR-012 Addendum C — platform-beheer van de componentcatalogus.
  // GÉÉN verwijder (geen DELETE-endpoint; soft-deactivate via werkBij `actief`).
  platformComponentconfig: {
    lijst: (params = {}) => request(`/platform/componentconfig${_filterQuery('platformComponentconfig.lijst', params, ['dimensie'])}`),
    // ADR-026 — gesloten keuzelijsten (element/laag/aspect) uit de backend-bron.
    typeringOpties: () => request('/platform/componentconfig/typering-opties'),
    maak: (data) => request('/platform/componentconfig', { method: 'POST', body: JSON.stringify(data) }),
    werkBij: (id, data) =>
      request(`/platform/componentconfig/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  },

  // ADR-023 Fase F / F-4 — platform-beheer van de relatie-kenmerk-catalogus.
  // GÉÉN verwijder (geen DELETE-endpoint; soft-deactivate via werkBij `actief`).
  platformRelatiekenmerkconfig: {
    lijst: (params = {}) => request(`/platform/relatiekenmerkconfig${_filterQuery('platformRelatiekenmerkconfig.lijst', params, ['dimensie'])}`),
    maak: (data) => request('/platform/relatiekenmerkconfig', { method: 'POST', body: JSON.stringify(data) }),
    werkBij: (id, data) =>
      request(`/platform/relatiekenmerkconfig/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  },
  // Catalogi-beheer-schuld dichten — enkel-doel platform-catalogi (geen dimensie). Soft-deactivate.
  platformVraagbetekenisconfig: {
    lijst: () => request('/platform/vraagbetekenisconfig'),
    maak: (data) => request('/platform/vraagbetekenisconfig', { method: 'POST', body: JSON.stringify(data) }),
    werkBij: (id, data) =>
      request(`/platform/vraagbetekenisconfig/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  },
  platformPartijsoortconfig: {
    lijst: () => request('/platform/partijsoortconfig'),
    maak: (data) => request('/platform/partijsoortconfig', { method: 'POST', body: JSON.stringify(data) }),
    werkBij: (id, data) =>
      request(`/platform/partijsoortconfig/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  },
  // ADR-028 — platform-beheer componentrol-catalogus.
  platformComponentrolconfig: {
    lijst: () => request('/platform/componentrolconfig'),
    maak: (data) => request('/platform/componentrolconfig', { method: 'POST', body: JSON.stringify(data) }),
    werkBij: (id, data) =>
      request(`/platform/componentrolconfig/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  },
  // ADR-028 — platform-beheer BIV-schaal-catalogus.
  platformBivschaalconfig: {
    lijst: () => request('/platform/bivschaalconfig'),
    maak: (data) => request('/platform/bivschaalconfig', { method: 'POST', body: JSON.stringify(data) }),
    werkBij: (id, data) =>
      request(`/platform/bivschaalconfig/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  },
  // ADR-042 — platform-beheer applicatiefunctie-catalogus (geen DELETE: soft-deactivate).
  platformApplicatiefunctieconfig: {
    lijst: () => request('/platform/applicatiefunctieconfig'),
    maak: (data) => request('/platform/applicatiefunctieconfig', { method: 'POST', body: JSON.stringify(data) }),
    werkBij: (id, data) =>
      request(`/platform/applicatiefunctieconfig/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  },
  // Gate 1b — platform-beheer referentiemodel-aanbod. GESLOTEN aanbod: geen `maak`
  // (nieuw model = release-curatie: bestand + HERKOMST.md + seed); wel label/volgorde/
  // actief (soft-deactivate).
  platformReferentiemodelconfig: {
    lijst: () => request('/platform/referentiemodelconfig'),
    werkBij: (id, data) =>
      request(`/platform/referentiemodelconfig/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  },
}
