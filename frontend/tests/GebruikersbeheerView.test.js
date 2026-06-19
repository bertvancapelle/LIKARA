/** Tests — GebruikersbeheerView (ADR-029 Fase 4): lijst + aanmaak-dialog + eenmalig wachtwoord. */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'

vi.mock('@/api', () => ({
  api: {
    gebruikers: { lijst: vi.fn(), maak: vi.fn() },
    partijen: { lijst: vi.fn(() => Promise.resolve({ items: [] })) },
  },
}))

import { api } from '@/api'
import { useAuthStore } from '@/store/auth'
import GebruikersbeheerView from '@modules/bwb_ontvlechting/frontend/views/GebruikersbeheerView.vue'
import ZoekSelect from '@modules/bwb_ontvlechting/frontend/views/ZoekSelect.vue'

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

async function _vulFormulier(w, { naam = 'Wendy Test', email = 'wendy@org.nl', afdeling = 'afd-1' } = {}) {
  await w.find('[data-testid="gebr-toevoegen"]').trigger('click')
  await flushPromises()
  if (naam !== null) await w.find('[data-testid="gebr-naam"]').setValue(naam)
  if (email !== null) await w.find('[data-testid="gebr-email"]').setValue(email)
  if (afdeling !== null) w.findComponent(ZoekSelect).vm.$emit('update:modelValue', afdeling)
  await flushPromises()
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
  it('valideert verplichte velden (geen API-call)', async () => {
    const w = await mountView()
    await _vulFormulier(w, { naam: '', email: '', afdeling: null })
    await w.find('[data-testid="gebr-form"]').trigger('submit')
    expect(w.find('[data-testid="gebr-fout-naam"]').exists()).toBe(true)
    expect(w.find('[data-testid="gebr-fout-email"]').exists()).toBe(true)
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
