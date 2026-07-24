/** Tests — AuditTrailView (ADR-029 Fase 3a): naam-weergave + naam-filter + cursor-reset. */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'

vi.mock('@/api', () => ({
  api: {
    auditlog: { lijst: vi.fn() },
    componenten: { lijst: vi.fn(() => Promise.resolve({ items: [] })) },
  },
}))

import { api } from '@/api'
import { HOSTINGMODEL, LEVENSFASE, actorWeergave, diffWeergave, waardeLabel } from '@modules/bwb_ontvlechting/frontend/labels'
import AuditTrailView from '@modules/bwb_ontvlechting/frontend/views/AuditTrailView.vue'

const _pagina = (over = {}) => ({
  items: [
    {
      correlatie_id: 'c1', tijdstip: '2026-06-19T10:00:00Z', actor_naam: 'Jan de Vries',
      actor_email: 'jan@org.nl',
      records: [{ id: 'r1', entiteit_type: 'applicatie', actie: 'create', actor_naam: 'Jan de Vries' }],
    },
    {
      correlatie_id: 'c2', tijdstip: '2026-06-19T09:00:00Z', actor_naam: 'beheerder@org.nl',
      actor_email: 'beheerder@org.nl',
      records: [{ id: 'r2', entiteit_type: 'component', actie: 'update', actor_naam: 'beheerder@org.nl' }],
    },
  ],
  volgende_cursor: null,
  ...over,
})

async function mountView() {
  const w = mount(AuditTrailView, {
    global: { plugins: [createPinia(), [PrimeVue, { unstyled: true }], ToastService] },
  })
  await flushPromises()
  return w
}

beforeEach(() => {
  vi.clearAllMocks()
  api.auditlog.lijst.mockResolvedValue(_pagina())
})
afterEach(() => vi.restoreAllMocks())

describe('AuditTrailView', () => {
  it('toont de gebeurtenissen met naam (en e-mail-fallback)', async () => {
    const w = await mountView()
    const t = w.text()
    expect(t).toContain('Jan de Vries')       // geresolveerde naam
    expect(t).toContain('beheerder@org.nl')    // ongekoppeld → e-mail-fallback
    expect(t).toContain('Aangemaakt')          // actie-label
  })

  it('filter op naam roept de api met actor_naam', async () => {
    const w = await mountView()
    await w.find('[data-testid="filter-naam"]').setValue('Jan')
    await w.find('[data-testid="audit-toepassen"]').trigger('click')
    await flushPromises()
    expect(api.auditlog.lijst).toHaveBeenLastCalledWith(expect.objectContaining({ actor_naam: 'Jan' }))
  })

  // LI051 — soort "zoekveld zonder aantal": geplakte rommel in de "wie"-zoekterm toont de melding
  // met de opgeschoonde term, direct onder het zoekveld; de achterkant krijgt de opgeschoonde term.
  it('LI051 — geplakte rommel in "zoek op wie": melding met de opgeschoonde term', async () => {
    const w = await mountView()
    await w.find('[data-testid="filter-naam"]').setValue('Ja\x00n')
    await w.find('[data-testid="audit-toepassen"]').trigger('click')
    await flushPromises()
    const melding = w.find('[data-testid="zoek-opschoon-melding"]')
    expect(melding.exists()).toBe(true)
    expect(melding.text()).toContain('Jan')
    expect(w.find('[data-testid="filter-naam"]').element.value).toBe('Jan')
    expect(api.auditlog.lijst).toHaveBeenLastCalledWith(expect.objectContaining({ actor_naam: 'Jan' }))
  })

  it('LI051 — een gewone "wie"-zoekopdracht toont geen melding', async () => {
    const w = await mountView()
    await w.find('[data-testid="filter-naam"]').setValue('Jan')
    await w.find('[data-testid="audit-toepassen"]').trigger('click')
    await flushPromises()
    expect(w.find('[data-testid="zoek-opschoon-melding"]').exists()).toBe(false)
  })

  it('filterwijziging reset de cursor (geen after meer)', async () => {
    api.auditlog.lijst.mockResolvedValueOnce(_pagina({ volgende_cursor: 'CUR1' }))
    const w = await mountView()
    await w.find('[data-testid="audit-meer"]').trigger('click')      // Meer laden → after=CUR1
    await flushPromises()
    expect(api.auditlog.lijst).toHaveBeenLastCalledWith(expect.objectContaining({ after: 'CUR1' }))
    await w.find('[data-testid="filter-actie"]').setValue('update')  // filterwijziging → reset
    await flushPromises()
    const laatste = api.auditlog.lijst.mock.calls.at(-1)[0]
    expect(laatste.after).toBeUndefined()
    expect(laatste.actie).toBe('update')
  })

  it('LI019 — "Wie": systeem-actor leesbaar + actor_sub-fallback', async () => {
    api.auditlog.lijst.mockResolvedValue({
      items: [
        { correlatie_id: 's1', tijdstip: '2026-06-19T10:00:00Z', actor_naam: null, actor_email: null, actor_sub: 'system:dev_seed',
          records: [{ id: 'r', entiteit_type: 'component', entiteit_id: 'x', actie: 'create' }] },
        { correlatie_id: 's2', tijdstip: '2026-06-19T09:00:00Z', actor_naam: null, actor_email: null, actor_sub: 'kc|abc',
          records: [{ id: 'r2', entiteit_type: 'component', entiteit_id: 'y', actie: 'update' }] },
      ],
      volgende_cursor: null,
    })
    const w = await mountView()
    const wies = w.findAll('[data-testid="audit-wie"]').map((n) => n.text())
    expect(wies).toContain('Systeem (seed)') // system: → leesbaar label
    expect(wies).toContain('kc|abc') // geen naam/email → sub-fallback
  })

  it('LI019 — Onderdeel toont objectnaam, met entiteit_id-fallback', async () => {
    api.auditlog.lijst.mockResolvedValue({
      items: [
        { correlatie_id: 'o1', tijdstip: '2026-06-19T10:00:00Z', actor_naam: 'Jan',
          records: [{ id: 'r', entiteit_type: 'component', entiteit_id: 'comp-1', entiteit_naam: 'Zaaksysteem', actie: 'update' }] },
        { correlatie_id: 'o2', tijdstip: '2026-06-19T09:00:00Z', actor_naam: 'Jan',
          records: [{ id: 'r2', entiteit_type: 'component', entiteit_id: 'comp-2', entiteit_naam: null, actie: 'delete' }] },
      ],
      volgende_cursor: null,
    })
    const w = await mountView()
    const ond = w.findAll('[data-testid="audit-onderdeel"]').map((n) => n.text())
    expect(ond).toContain('Component — Zaaksysteem')
    expect(ond.some((t) => t.includes('comp-2'))).toBe(true) // naam null → fallback naar id
  })

  it('LI019 — diff standaard ingeklapt; uitklappen toont "veld: oud → nieuw"', async () => {
    api.auditlog.lijst.mockResolvedValue({
      items: [
        { correlatie_id: 'd1', tijdstip: '2026-06-19T10:00:00Z', actor_naam: 'Jan',
          records: [{ id: 'r', entiteit_type: 'component', entiteit_id: 'c', entiteit_naam: 'Zaaksysteem', actie: 'update',
            wijziging: { naam: { oud: 'Oud', nieuw: 'Nieuw' } } }] },
      ],
      volgende_cursor: null,
    })
    const w = await mountView()
    expect(w.find('[data-testid="audit-diff"]').exists()).toBe(false) // standaard ingeklapt
    await w.find('[data-testid="audit-toggle-d1"]').trigger('click')
    await flushPromises()
    expect(w.find('[data-testid="audit-diff"]').exists()).toBe(true)
    const regel = w.find('[data-testid="audit-diff-regel"]').text()
    expect(regel).toBe('Naam: Oud → Nieuw')
  })

  it('LI019 — diffWeergave/actorWeergave hulpfuncties (create/delete-varianten)', () => {
    expect(actorWeergave({ actor_naam: 'Jan', actor_email: 'j@x', actor_sub: 's' })).toBe('Jan')
    expect(actorWeergave({ actor_email: 'j@x' })).toBe('j@x')
    expect(actorWeergave({ actor_sub: 'system:worker' })).toBe('Systeem (worker)')
    expect(actorWeergave({ actor_sub: 'system:onbekend' })).toBe('Systeem')
    expect(actorWeergave({})).toBe('—')
    // LI048 snede 3: een regel is nu een object (veld + tekst, en bij lange waarden was/nu),
    // zodat de weergave kan kiezen tussen één regel en gestapeld. De TEKST blijft gelijk.
    expect(diffWeergave({ actie: 'create', wijziging: { naam: { nieuw: 'B' } } }).regels.map((r) => r.tekst)).toEqual(['Naam = B'])
    expect(diffWeergave({ actie: 'delete', wijziging: { naam: { oud: 'A' } } }).regels.map((r) => r.tekst)).toEqual(['Naam was A'])
    expect(diffWeergave({ actie: 'create', wijziging: { naam: { nieuw: 'B' } } }).intro).toBe('Aangemaakt met:')
  })
})

describe('AuditTrailView — LI048: de gedeelde kop, met expliciet zoeken', () => {
  it('draagt de gedeelde LijstKop met het zoekveld erin', async () => {
    const w = await mountView()
    expect(w.get('[data-testid="lijst-kop"]').find('[data-testid="filter-naam"]').exists()).toBe(true)
  })

  it('zoekt NIET tijdens typen — alleen op Enter of op de knop', async () => {
    // Op een auditlog kunnen heel veel regels staan; elke toetsaanslag een zoekopdracht laten
    // afvuren is daar geen dienst. Dit is het ene functionele verschil dat blijft, dus valt deze
    // toets om zodra iemand het "verbetert" naar zoeken-tijdens-typen.
    const w = await mountView()
    api.auditlog.lijst.mockClear()
    const veld = w.get('[data-testid="filter-naam"]')
    await veld.setValue('jansen')
    await veld.trigger('input')
    await flushPromises()
    expect(api.auditlog.lijst).not.toHaveBeenCalled()   // typen doet niets

    await veld.trigger('keyup.enter')
    await flushPromises()
    expect(api.auditlog.lijst).toHaveBeenCalled()       // Enter wél
  })

  it('de Zoeken-knop voert de zoekopdracht uit', async () => {
    const w = await mountView()
    api.auditlog.lijst.mockClear()
    await w.get('[data-testid="audit-toepassen"]').trigger('click')
    await flushPromises()
    expect(api.auditlog.lijst).toHaveBeenCalled()
  })
})

describe('AuditTrailView — LI048: zoeken vindt wat er in beeld staat', () => {
  it('toont de gevonden regels, niet alleen dat er gezocht is', async () => {
    // De toets die hier ontbrak. De bestaande "roept de api met actor_naam" bewijst alleen dát
    // er een verzoek uitgaat, met een nagebootste server — nooit dat er iets terugkomt. Precies
    // daardoor kon het scherm stil kapot zijn: het zocht in persoonsnamen terwijl de kolom Wie
    // `naam or e-mail` toont, dus iedereen zonder gekoppelde persoon was onvindbaar.
    const w = await mountView()
    api.auditlog.lijst.mockResolvedValueOnce(_pagina({
      items: [{
        correlatie_id: 'e1', tijdstip: '2026-06-19T10:00:00Z',
        actor_naam: 'test:bert@test', actor_email: 'test:bert@test', actor_sub: 'kc|bert',
        records: [{ id: 're1', entiteit_type: 'component', actie: 'update', actor_naam: 'test:bert@test' }],
      }],
    }))
    await w.find('[data-testid="filter-naam"]').setValue('bert')
    await w.find('[data-testid="audit-toepassen"]').trigger('click')
    await flushPromises()

    expect(api.auditlog.lijst).toHaveBeenLastCalledWith(expect.objectContaining({ actor_naam: 'bert' }))
    // DE KERN: er staat een regel op het scherm, en de kolom Wie toont waarop is gezocht.
    expect(w.find('[data-testid="audit-leeg"]').exists()).toBe(false)
    expect(w.text()).toContain('test:bert@test')
  })

  it('een term die niets oplevert toont de lege melding, geen fout', async () => {
    // "Niets gevonden" moet blijven bestaan naast "niet gezocht" — het onderscheid mag niet
    // vervagen doordat de reparatie altijd iets terugstuurt.
    const w = await mountView()
    api.auditlog.lijst.mockResolvedValueOnce(_pagina({ items: [] }))
    await w.find('[data-testid="filter-naam"]').setValue('zzz-bestaat-niet')
    await w.find('[data-testid="audit-toepassen"]').trigger('click')
    await flushPromises()
    expect(w.get('[data-testid="audit-leeg"]').text()).toContain('Geen gebeurtenissen gevonden')
    expect(w.find('[data-testid="audit-fout"]').exists()).toBe(false)
  })

  it('het label wijst naar de kolom die de gebruiker ziet', async () => {
    // "Zoek op naam…" verwees naar iets wat op dit scherm meestal niet eens getoond wordt.
    const w = await mountView()
    expect(w.get('[data-testid="filter-naam"]').attributes('placeholder')).toBe('Zoek op wie…')
  })
})

describe('AuditTrailView — LI048: de regel vertelt wat er gebeurde', () => {
  // De gebeurtenis draagt zijn eigen samenvatting (backend besluit 2). Zo ziet een echte
  // aanmaak van een werkpakket eruit: de supertype-rij zit in `records`, maar is niet de zin.
  const _aanmaakWerkpakket = () => ({
    items: [{
      correlatie_id: 'w1', tijdstip: '2026-06-19T10:00:00Z',
      actor_naam: 'test:bert@test', actor_email: 'test:bert@test',
      entiteit_type: 'work_package', entiteit_id: '9f1282d4-48ec-41d8-aadc-c794ac5fabd7',
      entiteit_naam: 'WP-Audit', actie: 'create', aantal_afgeleid: 0,
      records: [
        { id: 'e1', entiteit_type: 'element', actie: 'create', wijziging: { element_type: { oud: null, nieuw: 'work_package' } } },
        { id: 'w1r', entiteit_type: 'work_package', actie: 'create', entiteit_naam: 'WP-Audit', wijziging: { naam: { oud: null, nieuw: 'WP-Audit' } } },
      ],
    }],
    volgende_cursor: null,
  })

  it('DE INGEKLAPTE REGEL: toont het werkpakket met zijn naam, niet de element-code', async () => {
    // Dit was de klacht: "Element — 9f1282d4-48ec-41d8-aadc-c794ac5fabd7 · Aangemaakt
    // (+1 afgeleid)". Er stond geen enkele toets op de ingeklapte regel — precies de tekst die
    // de consultant als eerste leest.
    api.auditlog.lijst.mockResolvedValue(_aanmaakWerkpakket())
    const w = await mountView()
    const onderdeel = w.get('[data-testid="audit-onderdeel"]').text()
    expect(onderdeel).toContain('WP-Audit')
    expect(onderdeel).not.toContain('9f1282d4')          // geen kale code meer
    expect(onderdeel.toLowerCase()).not.toContain('element')
  })

  it('telt de betekenisloze supertype-rij niet als afgeleid gevolg', async () => {
    // "(+1 afgeleid)" verwees naar een regel die alleen zei dát er iets bestond.
    api.auditlog.lijst.mockResolvedValue(_aanmaakWerkpakket())
    const w = await mountView()
    expect(w.text()).not.toContain('afgeleid')
  })

  it('GEEN RAUWE OPSLAGTAAL op het scherm', async () => {
    // Werkt een geval niet, dan is dat een bevinding — geen terugval op de code die we juist
    // wilden verbergen. Deze toets bewaakt dat de zin nooit in opslagtaal vervalt.
    api.auditlog.lijst.mockResolvedValue(_aanmaakWerkpakket())
    const w = await mountView()
    const zichtbaar = w.text()
    for (const opslagterm of ['work_package', 'element_type', 'phase_out', 'keycloak_sub']) {
      expect(zichtbaar).not.toContain(opslagterm)
    }
  })

  it('een verwijdering toont de naam zoals die WAS', async () => {
    // Het object bestaat niet meer; deze regel is het enige spoor dat overblijft.
    api.auditlog.lijst.mockResolvedValue({
      items: [{
        correlatie_id: 'd1', tijdstip: '2026-06-19T10:00:00Z',
        actor_naam: 'test:bert@test', actor_email: 'test:bert@test',
        entiteit_type: 'component', entiteit_id: 'aaaa1111-0000-0000-0000-000000000000',
        entiteit_naam: 'Cascade', actie: 'delete', aantal_afgeleid: 0,
        records: [{ id: 'd1r', entiteit_type: 'component', actie: 'delete', entiteit_naam: 'Cascade', wijziging: { naam: { oud: 'Cascade', nieuw: null } } }],
      }],
      volgende_cursor: null,
    })
    const w = await mountView()
    expect(w.get('[data-testid="audit-onderdeel"]').text()).toContain('Cascade')
  })

  it('valt terug op de oude vorm als het antwoord de samenvatting niet draagt', async () => {
    // Achterwaarts: een ouder antwoord zonder de nieuwe velden mag niet leeg renderen.
    const w = await mountView()   // standaard _pagina() heeft geen entiteit_type op de gebeurtenis
    expect(w.get('[data-testid="audit-onderdeel"]').text().length).toBeGreaterThan(0)
  })
})

describe('AuditTrailView — LI048 snede 3: namen en waarden in schermtaal', () => {
  it('BESLUIT 4: een keuzewaarde komt in schermtaal, niet in opslagtaal', async () => {
    // Was: "Levensfase: production → phase_out". De waardenmaps bestonden al maar waren
    // nergens aan een veld gekoppeld — die koppeling is deze snede.
    const r = diffWeergave({ actie: 'update', wijziging: { levensfase: { oud: 'productie', nieuw: 'uitfaseren' } } })
    const tekst = r.regels.map((x) => x.tekst).join(' ')
    expect(tekst).not.toContain('uitfaseren')       // niet de ruwe sleutel
    expect(tekst).toContain('Levensfase')
  })

  it('leest DEZELFDE bron als de rest van het product, geen tweede tabel', async () => {
    // De kern van "één bron": wat het detailscherm zegt, zegt het auditlog ook. Zou er een
    // eigen lijstje ontstaan, dan lopen ze uiteen zodra iemand één label wijzigt.
    for (const [sleutel, verwacht] of Object.entries(LEVENSFASE)) {
      expect(waardeLabel('levensfase', sleutel)).toBe(verwacht)
    }
    for (const [sleutel, verwacht] of Object.entries(HOSTINGMODEL)) {
      expect(waardeLabel('hostingmodel', sleutel)).toBe(verwacht)
    }
  })

  it('een onbekende waarde valt terug op zichzelf, nooit op leeg', async () => {
    expect(waardeLabel('levensfase', 'iets_nieuws')).toBe('iets_nieuws')
    expect(waardeLabel('onbekend_veld', 'waarde')).toBe('waarde')
    expect(waardeLabel('levensfase', null)).toBe('—')
    expect(waardeLabel('verplicht', true)).toBe('Ja')
  })

  it('een KORTE waarde blijft op één regel', async () => {
    const r = diffWeergave({ actie: 'update', wijziging: { naam: { oud: 'Oud', nieuw: 'Nieuw' } } })
    expect(r.regels[0].gestapeld).toBeFalsy()
    expect(r.regels[0].tekst).toBe('Naam: Oud → Nieuw')
  })

  it('een LANGE waarde komt onder elkaar te staan', async () => {
    // Het geval waarmee het verschil onvindbaar was: twintig woorden, vier verschil aan het eind.
    const oud = 'Centraal systeem voor zaakgericht werken — gedeeld alle gemeenten'
    const nieuw = 'Centraal systeem voor zaakgericht werken — gedeeld alle gemeenten en kan worden aangepast'
    const r = diffWeergave({ actie: 'update', wijziging: { beschrijving: { oud, nieuw } } })
    expect(r.regels[0].gestapeld).toBe(true)
    expect(r.regels[0].was).toBe(oud)
    expect(r.regels[0].nu).toBe(nieuw)
  })

  it('rendert de gestapelde vorm met Was/Nu onder elkaar', async () => {
    api.auditlog.lijst.mockResolvedValue({
      items: [{
        correlatie_id: 'l1', tijdstip: '2026-06-19T10:00:00Z',
        actor_naam: 'test:bert@test', actor_email: 'test:bert@test',
        entiteit_type: 'component', entiteit_id: 'aaaa1111-0000-0000-0000-000000000000',
        entiteit_naam: 'Zaaksysteem', actie: 'update', aantal_afgeleid: 0,
        records: [{
          id: 'l1r', entiteit_type: 'component', actie: 'update', entiteit_naam: 'Zaaksysteem',
          wijziging: { beschrijving: {
            oud: 'Centraal systeem voor zaakgericht werken — gedeeld alle gemeenten',
            nieuw: 'Centraal systeem voor zaakgericht werken — gedeeld alle gemeenten en aangepast',
          } },
        }],
      }],
      volgende_cursor: null,
    })
    const w = await mountView()
    await w.get('[data-testid="audit-toggle-l1"]').trigger('click')
    await flushPromises()
    const gestapeld = w.get('[data-testid="audit-diff-gestapeld"]')
    expect(gestapeld.text()).toContain('Was:')
    expect(gestapeld.text()).toContain('Nu:')
  })
})

describe('AuditTrailView — LI048: het filter heet naar wat het doet', () => {
  it('het filter heet Component, niet Onderdeel', async () => {
    // "Onderdeel" beloofde meer dan het veld waarmaakt: hier zijn alléén componenten kiesbaar,
    // terwijl de KOLOM Onderdeel ook checklistvragen, werkpakketten en partijen toont. Wie op
    // een checklistvraag zocht kwam er nooit, zonder dat iets dat aangaf.
    const w = await mountView()
    const label = w.get('label[for="filter-component"]')
    expect(label.text()).toBe('Component')
    expect(label.text()).not.toContain('Onderdeel')
  })

  it('de veldtekst belooft niets anders dan het label', async () => {
    // Label en veldtekst stonden op losse plekken; juist daardoor kon de tekst iets anders
    // zeggen dan het label. Ze moeten over hetzelfde ding gaan.
    const w = await mountView()
    // ZoekSelect zet zijn testid als PREFIX op de interne elementen, niet op de root.
    const veld = w.get('[data-testid="filter-component-input"]')
    expect(veld.attributes('placeholder').toLowerCase()).toContain('component')
  })

  it('de KOLOM blijft Onderdeel — die toont wél alle soorten', async () => {
    // Het verschil tussen filter en kolom is nu eerlijk in plaats van misleidend; het mag niet
    // "opgelost" worden door de kolom óók Component te noemen.
    const w = await mountView()
    expect(w.text()).toContain('Onderdeel')
  })
})
