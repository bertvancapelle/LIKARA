/** Tests — GebruikersbeheerView (ADR-029 Fase 4): lijst + aanmaak-dialog + eenmalig wachtwoord. */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'

vi.mock('@/api', () => ({
  api: {
    gebruikers: {
      lijst: vi.fn(), maak: vi.fn(),
      wachtwoordReset: vi.fn(), wijzigRol: vi.fn(), wijzigStatus: vi.fn(), corrigeer: vi.fn(),
    },
    partijen: { lijst: vi.fn(() => Promise.resolve({ items: [] })), maak: vi.fn() },
  },
}))

import { api } from '@/api'
import { useAuthStore } from '@/store/auth'
import GebruikersbeheerView from '@modules/bwb_ontvlechting/frontend/views/GebruikersbeheerView.vue'
import ZoekSelect from '@modules/bwb_ontvlechting/frontend/views/ZoekSelect.vue'
import AfdelingSelect from '@modules/bwb_ontvlechting/frontend/views/AfdelingSelect.vue'
import { partijLijstFake } from './helpers/partijMock.js'

const _gebruikers = () => [
  { id: 'g1', keycloak_sub: 's1', persoon_id: 'p1', naam: 'Jan de Vries', email: 'jan@org.nl', aangemaakt_op: '2026-06-20T10:00:00Z' },
  { id: 'g2', keycloak_sub: 's2', persoon_id: 'p2', naam: 'Piet Paulusma', email: 'piet@org.nl', aangemaakt_op: '2026-06-20T11:00:00Z' },
]

async function mountView({ rollen = ['beheerder'] } = {}) {
  const pinia = createPinia()
  const auth = useAuthStore(pinia)
  auth.user = { sub: 's', tenant_id: 't', email: 'a@b.nl', roles: rollen }
  const w = mount(GebruikersbeheerView, {
    attachTo: document.body,
    global: { plugins: [pinia, [PrimeVue, { unstyled: true }], ToastService], stubs: { teleport: true } },
  })
  await flushPromises()
  return w
}

async function _vulFormulier(
  w,
  { naam = 'Wendy Test', email = 'wendy@org.nl', organisatie = 'org-1', afdeling = 'afd-1' } = {},
) {
  await w.find('[data-testid="gebr-toevoegen"]').trigger('click')
  await flushPromises()
  if (naam !== null) await w.find('[data-testid="gebr-naam"]').setValue(naam)
  if (email !== null) await w.find('[data-testid="gebr-email"]').setValue(email)
  // Organisatie eerst (eerste ZoekSelect) → scoopt + reset de afdeling; dan de afdeling (AfdelingSelect).
  if (organisatie !== null) {
    w.findComponent(ZoekSelect).vm.$emit('update:modelValue', organisatie)
    await flushPromises()
  }
  if (afdeling !== null) {
    w.findComponent(AfdelingSelect).vm.$emit('update:modelValue', afdeling)
    await flushPromises()
  }
}

beforeEach(() => {
  vi.clearAllMocks()
  api.gebruikers.lijst.mockResolvedValue(_gebruikers())
})
afterEach(() => vi.restoreAllMocks())

describe('GebruikersbeheerView — lijst + gating', () => {
  it('toont de lijst van gebruikers', async () => {
    const w = await mountView()
    expect(w.text()).toContain('Jan de Vries')
    expect(w.text()).toContain('piet@org.nl')
  })

  it('toevoegen-knop alleen voor beheerder', async () => {
    let w = await mountView({ rollen: ['beheerder'] })
    expect(w.find('[data-testid="gebr-toevoegen"]').exists()).toBe(true)
    w = await mountView({ rollen: ['medewerker'] })
    expect(w.find('[data-testid="gebr-toevoegen"]').exists()).toBe(false)
  })
})

describe('GebruikersbeheerView — aanmaak-dialog', () => {
  it('valideert verplichte velden — naam, email, organisatie én afdeling (geen API-call)', async () => {
    const w = await mountView()
    await _vulFormulier(w, { naam: '', email: '', organisatie: null, afdeling: null })
    await w.find('[data-testid="gebr-form"]').trigger('submit')
    expect(w.find('[data-testid="gebr-fout-naam"]').exists()).toBe(true)
    expect(w.find('[data-testid="gebr-fout-email"]').exists()).toBe(true)
    expect(w.find('[data-testid="gebr-fout-organisatie"]').exists()).toBe(true)
    expect(w.find('[data-testid="gebr-fout-afdeling"]').exists()).toBe(true)
    expect(api.gebruikers.maak).not.toHaveBeenCalled()
  })

  // LI032 — organisatie-keuze scoopt de afdeling; picker = alleen interne organisaties.
  it('organisatie-picker zoekt alleen interne organisaties (scope=intern)', async () => {
    const w = await mountView()
    await w.find('[data-testid="gebr-toevoegen"]').trigger('click')
    await flushPromises()
    await w.find('[data-testid="gebr-organisatie-input"]').trigger('focus')
    await flushPromises()
    expect(api.partijen.lijst).toHaveBeenCalledWith(
      expect.objectContaining({ aard: 'organisatie', scope: 'intern' }),
    )
  })

  it('afdelingsveld is uitgeschakeld met hint zolang er geen organisatie is', async () => {
    const w = await mountView()
    await w.find('[data-testid="gebr-toevoegen"]').trigger('click')
    await flushPromises()
    expect(w.find('[data-testid="gebr-afdeling-hint"]').exists()).toBe(true)
    expect(w.find('[data-testid="gebr-afdeling-input"]').attributes('disabled')).toBeDefined()
  })

  it('na organisatie-keuze: afdeling actief + gescoped op die organisatie; ter-plekke-aanmaken', async () => {
    api.partijen.maak.mockResolvedValueOnce({ id: 'afdN', naam: 'Directie' })
    const w = await mountView()
    await w.find('[data-testid="gebr-toevoegen"]').trigger('click')
    await flushPromises()
    w.findComponent(ZoekSelect).vm.$emit('update:modelValue', 'org-9') // organisatie kiezen
    await flushPromises()
    expect(w.find('[data-testid="gebr-afdeling-hint"]').exists()).toBe(false) // hint weg
    // afdeling-picker zoekt nu gescoped op de gekozen organisatie
    await w.find('[data-testid="gebr-afdeling-input"]').trigger('focus')
    await flushPromises()
    expect(api.partijen.lijst).toHaveBeenCalledWith(
      expect.objectContaining({ aard: 'organisatie_eenheid', organisatie_id: 'org-9' }),
    )
    // ter-plekke aanmaken landt binnen die organisatie
    await w.find('[data-testid="gebr-afdeling-aanmaak-open"]').trigger('mousedown')
    await w.find('[data-testid="gebr-afdeling-aanmaak-open"]').trigger('click')
    await flushPromises()
    await w.find('[data-testid="gebr-afdeling-naam"]').setValue('Directie')
    await w.find('[data-testid="gebr-afdeling-aanmaak-bevestig"]').trigger('click')
    await flushPromises()
    expect(api.partijen.maak).toHaveBeenCalledWith({
      aard: 'organisatie_eenheid', naam: 'Directie', organisatie_id: 'org-9',
    })
  })

  it('een andere organisatie kiezen reset de al gekozen afdeling', async () => {
    api.gebruikers.maak.mockResolvedValue({ gebruiker: {}, tijdelijk_wachtwoord: 'x' })
    const w = await mountView()
    await _vulFormulier(w, { organisatie: 'org-A', afdeling: 'afd-A' })
    // andere organisatie kiezen → afdeling gewist
    w.findComponent(ZoekSelect).vm.$emit('update:modelValue', 'org-B')
    await flushPromises()
    await w.find('[data-testid="gebr-form"]').trigger('submit')
    await flushPromises()
    // afdeling is gereset → validatiefout, geen aanmaak (bewijst dat afd-A niet meelekt onder org-B)
    expect(w.find('[data-testid="gebr-fout-afdeling"]').exists()).toBe(true)
    expect(api.gebruikers.maak).not.toHaveBeenCalled()
  })

  it('succesvolle aanmaak toont eenmalig wachtwoord + kopieerknop (formulier weg)', async () => {
    api.gebruikers.maak.mockResolvedValue({
      gebruiker: { id: 'g9', keycloak_sub: 's9', persoon_id: 'p9', naam: 'Wendy Test', email: 'wendy@org.nl', aangemaakt_op: '2026-06-20T12:00:00Z' },
      tijdelijk_wachtwoord: 'Tijdelijk!9xZ',
    })
    const w = await mountView()
    await _vulFormulier(w)
    await w.find('[data-testid="gebr-form"]').trigger('submit')
    await flushPromises()
    expect(api.gebruikers.maak).toHaveBeenCalledWith(
      expect.objectContaining({ naam: 'Wendy Test', email: 'wendy@org.nl', afdeling_id: 'afd-1', rol: 'medewerker' }),
    )
    expect(w.find('[data-testid="gebr-wachtwoord"]').text()).toContain('Tijdelijk!9xZ')
    expect(w.find('[data-testid="gebr-kopieer"]').exists()).toBe(true)
    expect(w.find('[data-testid="gebr-form"]').exists()).toBe(false) // formulier-staat weg
  })

  it('422-veldfout landt op het juiste veld', async () => {
    const err = new Error('Ongeldig')
    err.status = 422
    err.detail = [{ loc: ['body', 'email'], msg: 'Geef een geldig e-mailadres op.' }]
    api.gebruikers.maak.mockRejectedValue(err)
    const w = await mountView()
    await _vulFormulier(w)
    await w.find('[data-testid="gebr-form"]').trigger('submit')
    await flushPromises()
    expect(w.find('[data-testid="gebr-fout-email"]').text()).toContain('geldig e-mailadres')
    expect(w.find('[data-testid="gebr-wachtwoord"]').exists()).toBe(false)
  })

  it('email-al-in-gebruik (422-envelope) landt op het e-mailveld', async () => {
    const err = new Error('Er bestaat al een gebruiker met dit e-mailadres.')
    err.status = 422
    err.code = 'EMAIL_AL_IN_GEBRUIK'
    api.gebruikers.maak.mockRejectedValue(err)
    const w = await mountView()
    await _vulFormulier(w)
    await w.find('[data-testid="gebr-form"]').trigger('submit')
    await flushPromises()
    expect(w.find('[data-testid="gebr-fout-email"]').text()).toContain('al een gebruiker')
  })

  it('503 toont nette fout (geen crash, formulier blijft, geen wachtwoord)', async () => {
    const err = new Error('De gebruikersdienst is tijdelijk niet beschikbaar.')
    err.status = 503
    err.code = 'KEYCLOAK_NIET_BESCHIKBAAR'
    api.gebruikers.maak.mockRejectedValue(err)
    const w = await mountView()
    await _vulFormulier(w)
    await w.find('[data-testid="gebr-form"]').trigger('submit')
    await flushPromises()
    expect(w.find('[data-testid="gebr-wachtwoord"]').exists()).toBe(false)
    expect(w.find('[data-testid="gebr-form"]').exists()).toBe(true) // formulier blijft staan
  })

  it('Klaar sluit de dialog én herlaadt de lijst', async () => {
    api.gebruikers.maak.mockResolvedValue({
      gebruiker: { id: 'g9', keycloak_sub: 's9', persoon_id: 'p9', naam: 'Wendy Test', email: 'wendy@org.nl', aangemaakt_op: '2026-06-20T12:00:00Z' },
      tijdelijk_wachtwoord: 'Tijdelijk!9xZ',
    })
    const w = await mountView()
    expect(api.gebruikers.lijst).toHaveBeenCalledTimes(1) // mount
    await _vulFormulier(w)
    await w.find('[data-testid="gebr-form"]').trigger('submit')
    await flushPromises()
    await w.find('[data-testid="gebr-klaar"]').trigger('click')
    await flushPromises()
    expect(api.gebruikers.lijst).toHaveBeenCalledTimes(2) // herladen na Klaar
  })
})

// ── ADR-029 Fase 2b — beheer-paneel (rol/status + vier acties) ─────────────────────
describe('GebruikersbeheerView — beheer-paneel', () => {
  // s1 = een andere gebruiker (beheerder, actief); s = het eigen account (medewerker, actief).
  const _met_rol_status = () => [
    { id: 'g1', keycloak_sub: 's1', persoon_id: 'p1', naam: 'Jan de Vries', email: 'jan@org.nl', aangemaakt_op: '2026-06-20T10:00:00Z', rol: 'beheerder', enabled: true, organisatie_id: 'org-1', organisatie_naam: 'Gemeente Tiel', afdeling_id: 'afd-1', afdeling: 'Burgerzaken' },
    { id: 'g2', keycloak_sub: 's2', persoon_id: 'p2', naam: 'Piet Paulusma', email: 'piet@org.nl', aangemaakt_op: '2026-06-20T11:00:00Z', rol: 'medewerker', enabled: false, organisatie_id: 'org-1', organisatie_naam: 'Gemeente Tiel', afdeling_id: 'afd-1', afdeling: 'Burgerzaken' },
    { id: 'g3', keycloak_sub: 's3', persoon_id: 'p3', naam: 'Onbekend Account', email: 'x@org.nl', aangemaakt_op: '2026-06-20T11:00:00Z', rol: null, enabled: null },
  ]

  async function _openBeheer(w, id) {
    await w.find(`[data-testid="gebr-beheren-${id}"]`).trigger('click')
    await flushPromises()
  }

  it('lijst toont rol + status; uitgeschakeld herkenbaar; ontbrekend → Onbekend (geen fout)', async () => {
    api.gebruikers.lijst.mockResolvedValue(_met_rol_status())
    const w = await mountView()
    expect(w.find('[data-testid="gebr-rol-g1"]').text()).toBe('Beheerder')
    expect(w.find('[data-testid="gebr-status-g1"]').text()).toContain('Actief')
    expect(w.find('[data-testid="gebr-status-g2"]').text()).toContain('Uitgeschakeld')
    expect(w.find('[data-testid="gebr-rol-g3"]').text()).toBe('Onbekend')
    expect(w.find('[data-testid="gebr-status-g3"]').text()).toContain('Onbekend')
    expect(w.find('[data-testid="gebr-fout"]').exists()).toBe(false) // ontbrekend ≠ fout
  })

  it('acties verborgen voor een niet-beheerder', async () => {
    api.gebruikers.lijst.mockResolvedValue(_met_rol_status())
    const w = await mountView({ rollen: ['medewerker'] })
    expect(w.find('[data-testid="gebr-beheren-g1"]').exists()).toBe(false)
    expect(w.find('[data-testid="gebr-toevoegen"]').exists()).toBe(false)
  })

  it('wachtwoord opnieuw instellen toont het eenmalige wachtwoord één keer', async () => {
    api.gebruikers.lijst.mockResolvedValue(_met_rol_status())
    api.gebruikers.wachtwoordReset.mockResolvedValue({ tijdelijk_wachtwoord: 'NieuwTijdelijk!7Q' })
    const w = await mountView()
    await _openBeheer(w, 'g1')
    await w.find('[data-testid="gebr-wachtwoord-reset"]').trigger('click')
    await flushPromises()
    expect(api.gebruikers.wachtwoordReset).toHaveBeenCalledWith('g1')
    expect(w.find('[data-testid="gebr-reset-wachtwoord"]').text()).toBe('NieuwTijdelijk!7Q')
    // De reset-knop is weg (eenmalige weergave); er is geen tweede ophaalpad.
    expect(w.find('[data-testid="gebr-wachtwoord-reset"]').exists()).toBe(false)
  })

  it('rol wijzigen → PATCH rol met de gekozen rol', async () => {
    api.gebruikers.lijst.mockResolvedValue(_met_rol_status())
    api.gebruikers.wijzigRol.mockResolvedValue(null)
    const w = await mountView()
    await _openBeheer(w, 'g2') // medewerker (niet eigen account)
    await w.find('[data-testid="gebr-beheer-rol-select"]').setValue('auditor')
    await w.find('[data-testid="gebr-rol-opslaan"]').trigger('click')
    await flushPromises()
    expect(api.gebruikers.wijzigRol).toHaveBeenCalledWith('g2', 'auditor')
  })

  it('uitschakelen vraagt eerst bevestiging, daarna PATCH status=false', async () => {
    api.gebruikers.lijst.mockResolvedValue(_met_rol_status())
    api.gebruikers.wijzigStatus.mockResolvedValue(null)
    const w = await mountView()
    await _openBeheer(w, 'g1') // actief beheerder, niet eigen account
    await w.find('[data-testid="gebr-uitschakelen"]').trigger('click') // 1e klik = bevestiging
    await flushPromises()
    expect(api.gebruikers.wijzigStatus).not.toHaveBeenCalled()
    expect(w.find('[data-testid="gebr-uit-bevestig"]').exists()).toBe(true)
    await w.find('[data-testid="gebr-uitschakelen"]').trigger('click') // 2e klik = doorzetten
    await flushPromises()
    expect(api.gebruikers.wijzigStatus).toHaveBeenCalledWith('g1', false)
  })

  it('inschakelen bij een uitgeschakeld account → PATCH status=true', async () => {
    api.gebruikers.lijst.mockResolvedValue(_met_rol_status())
    api.gebruikers.wijzigStatus.mockResolvedValue(null)
    const w = await mountView()
    await _openBeheer(w, 'g2') // enabled=false
    await w.find('[data-testid="gebr-inschakelen"]').trigger('click')
    await flushPromises()
    expect(api.gebruikers.wijzigStatus).toHaveBeenCalledWith('g2', true)
  })

  it('gegevens corrigeren → PATCH naam/e-mail (+ afdeling, voorgevuld)', async () => {
    api.gebruikers.lijst.mockResolvedValue(_met_rol_status())
    api.gebruikers.corrigeer.mockResolvedValue({ id: 'g1', naam: 'Jan Nieuw', email: 'jan.nieuw@org.nl' })
    const w = await mountView()
    await _openBeheer(w, 'g1')
    // Organisatie/afdeling zijn voorgevuld (uit de verrijkte read) → geen extra keuze nodig.
    expect(w.find('[data-testid="gebr-beheer-organisatie-input"]').element.value).toBe('Gemeente Tiel')
    expect(w.find('[data-testid="gebr-beheer-afdeling-input"]').element.value).toBe('Burgerzaken')
    await w.find('[data-testid="gebr-beheer-naam"]').setValue('Jan Nieuw')
    await w.find('[data-testid="gebr-beheer-email"]').setValue('jan.nieuw@org.nl')
    await w.find('[data-testid="gebr-gegevens-opslaan"]').trigger('click')
    await flushPromises()
    expect(api.gebruikers.corrigeer).toHaveBeenCalledWith('g1', { naam: 'Jan Nieuw', email: 'jan.nieuw@org.nl', afdeling_id: 'afd-1' })
  })

  it('bewerk: de afdeling-picker toont ALLE afdelingen van de organisatie, niet alleen de huidige (LI032)', async () => {
    const afdelingen = [
      { id: 'afd-1', naam: 'Burgerzaken', aard: 'organisatie_eenheid' },
      { id: 'afd-2', naam: 'Directie', aard: 'organisatie_eenheid' },
      { id: 'afd-3', naam: 'Informatievoorziening', aard: 'organisatie_eenheid' },
    ]
    api.gebruikers.lijst.mockResolvedValue(_met_rol_status())
    // Realistische mock: de afdeling-lijst filtert op de zoekterm (zoals de backend-ILIKE).
    api.partijen.lijst.mockImplementation((params) => {
      if (params?.aard === 'organisatie_eenheid') {
        return Promise.resolve({
          items: params.zoek
            ? afdelingen.filter((a) => a.naam.toLowerCase().includes(params.zoek.toLowerCase()))
            : afdelingen,
          volgende_cursor: null,
        })
      }
      return Promise.resolve({ items: [], volgende_cursor: null })
    })
    const w = await mountView()
    await _openBeheer(w, 'g1') // afdeling voorgevuld op 'Burgerzaken'
    await w.find('[data-testid="gebr-beheer-afdeling-input"]').trigger('focus')
    await flushPromises()
    // Bij openen zichtbaar: ALLE afdelingen van de organisatie — niet alleen de huidige.
    expect(w.find('[data-testid="gebr-beheer-afdeling-optie-afd-2"]').exists()).toBe(true) // Directie
    expect(w.find('[data-testid="gebr-beheer-afdeling-optie-afd-3"]').exists()).toBe(true) // Informatievoorziening
    expect(w.findAll('[data-testid^="gebr-beheer-afdeling-optie-"]').length).toBe(3)
  })

  // ── Picker-integratie (LI032): param-filterende mock + open-picker-assert ─────────────
  // Toont dat elke picker de JUISTE entiteitsoort/scope aanroept — een verkeerde bron valt hier om.
  const _bvowbGebruiker = () => [
    { id: 'g1', keycloak_sub: 's1', persoon_id: 'p1', naam: 'Jan de Vries', email: 'jan@org.nl', aangemaakt_op: '2026-06-20T10:00:00Z', rol: 'beheerder', enabled: true, organisatie_id: 'org-bvowb', organisatie_naam: 'BvoWB', afdeling_id: 'afd-iv', afdeling: 'Informatievoorziening' },
  ]

  it('bewerk: de organisatie-picker toont ALLEEN interne organisaties — geen afdelingen/externe (LI032)', async () => {
    api.gebruikers.lijst.mockResolvedValue(_bvowbGebruiker())
    api.partijen.lijst.mockImplementation(partijLijstFake())
    const w = await mountView()
    await _openBeheer(w, 'g1')
    await w.find('[data-testid="gebr-beheer-organisatie-input"]').trigger('focus')
    await flushPromises()
    // Alleen de twee interne organisaties; GEEN afdeling (organisatie_eenheid), GEEN externe organisatie.
    expect(w.find('[data-testid="gebr-beheer-organisatie-optie-org-bvowb"]').exists()).toBe(true)
    expect(w.find('[data-testid="gebr-beheer-organisatie-optie-org-rid"]').exists()).toBe(true)
    expect(w.findAll('[data-testid^="gebr-beheer-organisatie-optie-"]').length).toBe(2)
    expect(api.partijen.lijst).toHaveBeenCalledWith(
      expect.objectContaining({ aard: 'organisatie', scope: 'intern' }),
    )
  })

  it('bewerk: na org-wissel toont de afdeling-picker de afdelingen van de NIEUWE organisatie (LI032)', async () => {
    api.gebruikers.lijst.mockResolvedValue(_bvowbGebruiker())
    api.partijen.lijst.mockImplementation(partijLijstFake())
    const w = await mountView()
    await _openBeheer(w, 'g1')
    // Wissel van organisatie via de org-picker (open → kies RID Rivierenland).
    await w.find('[data-testid="gebr-beheer-organisatie-input"]').trigger('focus')
    await flushPromises()
    await w.find('[data-testid="gebr-beheer-organisatie-optie-org-rid"]').trigger('mousedown')
    await flushPromises()
    // De afdeling-picker (geremount) toont nu ALLEEN RID's afdelingen, niet die van BvoWB.
    await w.find('[data-testid="gebr-beheer-afdeling-input"]').trigger('focus')
    await flushPromises()
    expect(w.find('[data-testid="gebr-beheer-afdeling-optie-afd-sd"]').exists()).toBe(true) // Servicedesk
    expect(w.find('[data-testid="gebr-beheer-afdeling-optie-afd-pa"]').exists()).toBe(true) // Projecten & Advies
    expect(w.findAll('[data-testid^="gebr-beheer-afdeling-optie-"]').length).toBe(2)
    expect(api.partijen.lijst).toHaveBeenCalledWith(
      expect.objectContaining({ aard: 'organisatie_eenheid', organisatie_id: 'org-rid' }),
    )
  })

  it('bewerk: elke geopende gebruiker toont zijn EIGEN organisatie — geen stale label (LI032)', async () => {
    // Twee gebruikers bij verschillende interne organisaties; open beide na elkaar.
    api.gebruikers.lijst.mockResolvedValue([
      { id: 'g1', keycloak_sub: 's1', persoon_id: 'p1', naam: 'Jan de Vries', email: 'jan@org.nl', aangemaakt_op: '2026-06-20T10:00:00Z', rol: 'beheerder', enabled: true, organisatie_id: 'org-bvowb', organisatie_naam: 'BvoWB', afdeling_id: 'afd-iv', afdeling: 'Informatievoorziening' },
      { id: 'g2', keycloak_sub: 's2', persoon_id: 'p2', naam: 'Kees Rijk', email: 'kees@org.nl', aangemaakt_op: '2026-06-20T11:00:00Z', rol: 'medewerker', enabled: true, organisatie_id: 'org-rid', organisatie_naam: 'RID Rivierenland', afdeling_id: 'afd-sd', afdeling: 'Servicedesk' },
    ])
    api.partijen.lijst.mockImplementation(partijLijstFake())
    const w = await mountView()
    await _openBeheer(w, 'g1')
    expect(w.find('[data-testid="gebr-beheer-organisatie-input"]').element.value).toBe('BvoWB')
    await w.find('[data-testid="gebr-beheer-sluit"]').trigger('click')
    await flushPromises()
    await _openBeheer(w, 'g2') // andere gebruiker → mag GEEN 'BvoWB' meer tonen (stale label)
    expect(w.find('[data-testid="gebr-beheer-organisatie-input"]').element.value).toBe('RID Rivierenland')
  })

  it('org-wissel reset de afdeling + blokkade-uitleg (aanspreekpunt) wordt getoond, geen rauwe code', async () => {
    api.gebruikers.lijst.mockResolvedValue(_met_rol_status())
    api.gebruikers.corrigeer.mockRejectedValue(Object.assign(
      new Error('Deze persoon is nog aanspreekpunt van GemSoft B.V.; maak dat eerst los.'),
      { status: 409, code: 'AANSPREEKPUNT_BLOKKEERT_VERPLAATSING' },
    ))
    const w = await mountView()
    await _openBeheer(w, 'g1')
    // andere organisatie kiezen → de al gekozen afdeling wordt gereset (veld leeg)
    w.findAllComponents(ZoekSelect).find((c) => c.props('testid') === 'gebr-beheer-organisatie')
      .vm.$emit('update:modelValue', 'org-9')
    await flushPromises()
    expect(w.find('[data-testid="gebr-beheer-afdeling-input"]').element.value).toBe('') // afdeling gereset
    // een afdeling onder de nieuwe organisatie kiezen, opslaan → blokkade → nette melding, dialog blijft
    w.findComponent(AfdelingSelect).vm.$emit('update:modelValue', 'afd-9')
    await flushPromises()
    await w.find('[data-testid="gebr-gegevens-opslaan"]').trigger('click')
    await flushPromises()
    expect(api.gebruikers.corrigeer).toHaveBeenCalledWith('g1', expect.objectContaining({ afdeling_id: 'afd-9' }))
    expect(w.find('[data-testid="gebr-beheer-dialog"]').exists()).toBe(true) // dialog blijft open bij blokkade
    expect(w.text()).not.toContain('AANSPREEKPUNT_BLOKKEERT_VERPLAATSING') // geen rauwe code
  })

  it('geen zinloze affordances op het eigen account (uitschakelen + de-beheerrol verborgen)', async () => {
    // Eigen account (sub 's') als beheerder.
    api.gebruikers.lijst.mockResolvedValue([
      { id: 'me', keycloak_sub: 's', persoon_id: 'pm', naam: 'Ik Zelf', email: 'ik@org.nl', aangemaakt_op: '2026-06-20T10:00:00Z', rol: 'beheerder', enabled: true },
    ])
    const w = await mountView() // rollen ['beheerder'], sub 's'
    await _openBeheer(w, 'me')
    expect(w.find('[data-testid="gebr-uitschakelen"]').exists()).toBe(false) // niet je eigen account uitschakelen
    expect(w.find('[data-testid="gebr-status-eigen-note"]').exists()).toBe(true)
    expect(w.find('[data-testid="gebr-beheer-rol-select"]').exists()).toBe(false) // niet jezelf de-beheerrollen
    expect(w.find('[data-testid="gebr-rol-eigen-note"]').exists()).toBe(true)
  })

  it('foutmapping: 409 laatste-beheerder → begrijpelijke melding, dialog blijft open', async () => {
    api.gebruikers.lijst.mockResolvedValue(_met_rol_status())
    api.gebruikers.wijzigStatus.mockRejectedValue(Object.assign(new Error('x'), { status: 409, code: 'LAATSTE_BEHEERDER' }))
    const w = await mountView()
    await _openBeheer(w, 'g1')
    await w.find('[data-testid="gebr-uitschakelen"]').trigger('click')
    await w.find('[data-testid="gebr-uitschakelen"]').trigger('click')
    await flushPromises()
    expect(w.find('[data-testid="gebr-beheer-dialog"]').exists()).toBe(true) // dialog blijft open
  })

  it('foutmapping: 422 op correctie → inline veldfout op e-mail; dialog blijft open', async () => {
    api.gebruikers.lijst.mockResolvedValue(_met_rol_status())
    api.gebruikers.corrigeer.mockRejectedValue(Object.assign(new Error('x'), { status: 422, detail: [{ loc: ['body', 'email'], msg: 'Geef een geldig e-mailadres op.' }] }))
    const w = await mountView()
    await _openBeheer(w, 'g1')
    // Geldige client-side waarden zodat de server-422 (niet de client-check) de fout levert.
    await w.find('[data-testid="gebr-beheer-naam"]').setValue('Jan')
    await w.find('[data-testid="gebr-beheer-email"]').setValue('jan@org.nl')
    await w.find('[data-testid="gebr-gegevens-opslaan"]').trigger('click')
    await flushPromises()
    expect(w.find('[data-testid="gebr-beheer-fout-email"]').exists()).toBe(true)
    expect(w.find('[data-testid="gebr-beheer-dialog"]').exists()).toBe(true)
  })

  it('foutmapping: 503 → begrijpelijke melding zonder technische termen (dialog open)', async () => {
    api.gebruikers.lijst.mockResolvedValue(_met_rol_status())
    api.gebruikers.wachtwoordReset.mockRejectedValue(Object.assign(new Error('x'), { status: 503 }))
    const w = await mountView()
    await _openBeheer(w, 'g1')
    await w.find('[data-testid="gebr-wachtwoord-reset"]').trigger('click')
    await flushPromises()
    expect(w.find('[data-testid="gebr-beheer-dialog"]').exists()).toBe(true)
    expect(w.find('[data-testid="gebr-reset-wachtwoord"]').exists()).toBe(false) // geen wachtwoord getoond bij fout
  })
})
