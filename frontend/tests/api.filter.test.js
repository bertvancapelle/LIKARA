/**
 * Borging — api-client filterconventie (snake_case + allowlist).
 *
 * WAAROM DEZE TEST BESTAAT (niet schrappen):
 * Het Koppelingen-tabblad toonde alle 17 flows van het hele landschap i.p.v. de 5 van
 * Zaaksysteem, doordat `KoppelingSectie` `bron_id/doel_id` (snake_case) doorgaf terwijl de
 * client `bronId/doelId` (camelCase) verwachtte → het filter viel stil als `undefined` weg →
 * ongefilterde "haal alles op"-call. Dit is exact de V012-les die tóch opnieuw optrad.
 *
 * Borging: (1) een meegegeven filter MOET in de uitgaande query-string staan; (2) een
 * ONBEKENDE filter-key MOET een LUIDE fout geven (nooit stil weglaten). Zo wordt een
 * toekomstige naam-mismatch onmiddellijk rood i.p.v. een ongefilterde call.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

let laatsteUrl = null
let laatsteOpties = null
beforeEach(() => {
  laatsteUrl = null
  laatsteOpties = null
  vi.stubGlobal('fetch', vi.fn(async (url, opties) => {
    laatsteUrl = String(url)
    laatsteOpties = opties
    return { ok: true, status: 200, json: async () => ({ items: [], volgende_cursor: null }) }
  }))
})
afterEach(() => vi.unstubAllGlobals())

// Import ná de fetch-stub (de module gebruikt de global fetch via request()).
const { api } = await import('@/api')

describe('api-client — filter belandt in de query-string', () => {
  it('relaties.lijst zet bron_id/relatietype in de URL (de Koppelingen-bug)', async () => {
    await api.relaties.lijst({ bron_id: 'abc', relatietype: 'flow' })
    expect(laatsteUrl).toContain('bron_id=abc')
    expect(laatsteUrl).toContain('relatietype=flow')
  })

  it('blokkades.lijst zet component_id in de URL', async () => {
    await api.blokkades.lijst({ component_id: 'xyz', limit: 25 })
    expect(laatsteUrl).toContain('component_id=xyz')
  })

  it('contracten.lijst zet leverancier_id in de URL', async () => {
    await api.contracten.lijst({ leverancier_id: 'lev1' })
    expect(laatsteUrl).toContain('leverancier_id=lev1')
  })

  it('landschapskaart.subgraaf (Fase B) doet een POST met component_ids + diepte in de body', async () => {
    await api.landschapskaart.subgraaf(['a1', 'a2'], 2)
    expect(laatsteUrl).toContain('/landschapskaart/subgraaf')
    expect(laatsteOpties?.method).toBe('POST')
    expect(JSON.parse(laatsteOpties.body)).toEqual({ component_ids: ['a1', 'a2'], diepte: 2 })
  })

  it('landschapskaart.subgraaf — diepte default 1 als niet meegegeven', async () => {
    await api.landschapskaart.subgraaf(['a1'])
    expect(JSON.parse(laatsteOpties.body)).toEqual({ component_ids: ['a1'], diepte: 1 })
  })

  it('bewust-leeg filter wordt weggelaten (geen lege param in de URL)', async () => {
    await api.relaties.lijst({ bron_id: undefined, relatietype: 'flow' })
    expect(laatsteUrl).not.toContain('bron_id')
    expect(laatsteUrl).toContain('relatietype=flow')
  })

  it('ADR-028: componenten.lijst zet componentrol (herhaald) + BIV-drempels in de URL', async () => {
    await api.componenten.lijst({
      componentrol: ['externe_dataprovider', 'koppelvlak'],
      biv_beschikbaarheid_min: 'midden',
      biv_vertrouwelijkheid_min: 'hoog',
    })
    expect(laatsteUrl).toContain('componentrol=externe_dataprovider')
    expect(laatsteUrl).toContain('componentrol=koppelvlak')
    expect(laatsteUrl).toContain('biv_beschikbaarheid_min=midden')
    expect(laatsteUrl).toContain('biv_vertrouwelijkheid_min=hoog')
  })

  it('LI033: organisatiegebruik.lijstVoorOrganisatie zet organisatie_id in de URL', async () => {
    await api.organisatiegebruik.lijstVoorOrganisatie({ organisatie_id: 'org-1' })
    expect(laatsteUrl).toContain('/organisatiegebruik')
    expect(laatsteUrl).toContain('organisatie_id=org-1')
  })

  it('ADR-042: processen.lijst zet zoek/sort/order/ouder_id in de URL', async () => {
    await api.processen.lijst({ zoek: 'vergunning', sort: 'naam', order: 'desc', ouder_id: 'p-1' })
    expect(laatsteUrl).toContain('/processen')
    expect(laatsteUrl).toContain('zoek=vergunning')
    expect(laatsteUrl).toContain('sort=naam')
    expect(laatsteUrl).toContain('order=desc')
    expect(laatsteUrl).toContain('ouder_id=p-1')
  })
})

describe('api-client — onbekende filter-key faalt LUID (geen stille drop)', () => {
  it('relaties.lijst met camelCase bronId gooit een duidelijke fout', () => {
    expect(() => api.relaties.lijst({ bronId: 'abc' })).toThrow(/onbekende filter-parameter 'bronId' voor relaties\.lijst/)
  })

  it('blokkades.lijst met applicatieId (oude camelCase) gooit', () => {
    expect(() => api.blokkades.lijst({ applicatieId: 'x' })).toThrow(/onbekende filter-parameter/)
  })

  it('een willekeurige typo-key gooit i.p.v. stil te negeren', () => {
    expect(() => api.componenten.lijst({ statuss: 'concept' })).toThrow(/onbekende filter-parameter 'statuss'/)
  })

  it('ADR-028: een BIV-typo (biv_vertrouwelijkheid zonder _min) gooit LUID', () => {
    expect(() => api.componenten.lijst({ biv_vertrouwelijkheid: 'hoog' })).toThrow(/onbekende filter-parameter 'biv_vertrouwelijkheid'/)
  })

  it('LI033: organisatiegebruik.lijstVoorOrganisatie met camelCase organisatieId gooit LUID', () => {
    expect(() => api.organisatiegebruik.lijstVoorOrganisatie({ organisatieId: 'x' })).toThrow(
      /onbekende filter-parameter 'organisatieId' voor organisatiegebruik\.lijstVoorOrganisatie/,
    )
  })

  it('ADR-042: processen.lijst met camelCase ouderId gooit LUID', () => {
    expect(() => api.processen.lijst({ ouderId: 'p-1' })).toThrow(
      /onbekende filter-parameter 'ouderId' voor processen\.lijst/,
    )
  })
})
