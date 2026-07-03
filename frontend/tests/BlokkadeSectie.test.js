/** Tests — BlokkadeSectie (read + PATCH; geen toevoegen/verwijderen). */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'

vi.mock('@/api', () => ({
  api: { blokkades: { lijst: vi.fn(), werkBij: vi.fn(), opties: vi.fn() } },
}))

import { api } from '@/api'
import { useAuthStore } from '@/store/auth'
import BlokkadeSectie from '@modules/bwb_ontvlechting/frontend/views/BlokkadeSectie.vue'

const APP = 'app-1'

function _blok(id, status = 'open') {
  return {
    id, status, toelichting: 'iets',
    // ADR-037: afgeleide verantwoordelijke van het antwoord (read-only).
    verantwoordelijke_naam: 'J. de Vries', verantwoordelijke_afdeling: 'Informatievoorziening',
    // Herkomst-verrijking (per-component lijst → BlokkadeLijstItem).
    checklistvraag_id: `v-${id}`, vraag_code: '2.7', vraag: 'Gedeelde infra?', score: 'deels',
  }
}

async function mountSectie({ rollen = ['beheerder'], items = [_blok('b1')] } = {}) {
  const pinia = createPinia()
  const auth = useAuthStore(pinia)
  auth.user = { sub: 's', tenant_id: 't', email: 'a@b.nl', roles: rollen }
  api.blokkades.lijst.mockResolvedValue({ items, volgende_cursor: null })
  const wrapper = mount(BlokkadeSectie, {
    props: { applicatieId: APP },
    attachTo: document.body,
    global: { plugins: [pinia, [PrimeVue, { unstyled: true }], ToastService], stubs: { teleport: true } },
  })
  await flushPromises()
  return wrapper
}

beforeEach(() => {
  vi.clearAllMocks()
  api.blokkades.opties.mockResolvedValue({ status: ['open', 'in_behandeling', 'opgelost'] })
  api.blokkades.werkBij.mockResolvedValue({ id: 'b1', status: 'opgelost' })
})
afterEach(() => vi.restoreAllMocks())

describe('BlokkadeSectie', () => {
  it('rendert de blokkades en de open-teller', async () => {
    const w = await mountSectie({ items: [_blok('b1', 'open'), _blok('b2', 'opgelost')] })
    expect(api.blokkades.lijst).toHaveBeenCalledWith({ component_id: APP, limit: 25, after: undefined })
    expect(w.find('[data-testid="bk-open-teller"]').text()).toContain('1 open')
  })

  it('toont de herkomst-kolom met de veroorzakende vraag-code + gekleurde score', async () => {
    const w = await mountSectie()
    const knop = w.find('[data-testid="bk-herkomst-b1"]')
    expect(knop.exists()).toBe(true)
    expect(knop.text()).toContain('2.7')
    // Onderdeel 3: de score via de gedeelde ScoreBadge (deels = oranje), tekst zichtbaar.
    const badge = w.find('[data-testid="score-badge-deels"]')
    expect(badge.exists()).toBe(true)
    expect(badge.classes()).toContain('text-[var(--lk-color-warning)]')
  })

  it('emit naar-vraag met code + afgeleide categorie bij klik op de herkomst', async () => {
    const w = await mountSectie()
    await w.find('[data-testid="bk-herkomst-b1"]').trigger('click')
    const ev = w.emitted('naar-vraag')
    expect(ev).toBeTruthy()
    expect(ev[0][0]).toMatchObject({ code: '2.7', categorieNr: 2 })
  })

  it('biedt GEEN toevoegen/verwijderen-affordance', async () => {
    const w = await mountSectie()
    expect(w.find('[data-testid="bk-toevoegen"]').exists()).toBe(false)
    expect(w.find('[data-testid="bk-verwijder-bevestig"]').exists()).toBe(false)
    expect(w.text()).not.toContain('Verwijderen')
  })

  it('bewerkt een blokkade via PATCH; dropdown alleen open/in_behandeling (ADR-016)', async () => {
    const w = await mountSectie()
    await w.find('[data-testid="bk-bewerk-b1"]').trigger('click')
    await flushPromises()
    // ADR-016: handmatige keuze is open/in_behandeling — `opgelost` is GEEN optie.
    const opties = w.find('[data-testid="bk-veld-status"]').findAll('option')
    expect(opties.length).toBe(2)
    expect(opties.map((o) => o.element.value)).toEqual(['open', 'in_behandeling'])
    await w.find('[data-testid="bk-veld-status"]').setValue('in_behandeling')
    await w.find('[data-testid="bk-veld-toelichting"]').setValue('Nieuwe toelichting')
    await w.find('[data-testid="bk-form"]').trigger('submit')
    await flushPromises()
    // ADR-037: geen eigenaar-veld meer in de PATCH — alleen status/toelichting.
    expect(api.blokkades.werkBij).toHaveBeenCalledWith('b1', {
      status: 'in_behandeling',
      toelichting: 'Nieuwe toelichting',
    })
    expect(w.emitted('gewijzigd')).toBeTruthy()
  })

  it('toont de afgeleide verantwoordelijke (persoon — afdeling), read-only', async () => {
    const w = await mountSectie()
    const cel = w.find('[data-testid="bk-verantw-b1"]')
    expect(cel.exists()).toBe(true)
    expect(cel.text()).toContain('J. de Vries — Informatievoorziening')
    // Geen bewerk-affordance voor de verantwoordelijke (afgeleid, geen overschrijven in v1).
    expect(w.find('[data-testid="bk-veld-eigenaar"]').exists()).toBe(false)
  })

  it('opgeloste blokkade: status read-only badge, geen select, status niet meegestuurd', async () => {
    const w = await mountSectie({ items: [_blok('b2', 'opgelost')] })
    await w.find('[data-testid="bk-bewerk-b2"]').trigger('click')
    await flushPromises()
    // read-only weergave i.p.v. een keuze
    expect(w.find('[data-testid="bk-status-readonly"]').exists()).toBe(true)
    expect(w.find('[data-testid="bk-veld-status"]').exists()).toBe(false)
    await w.find('[data-testid="bk-veld-toelichting"]').setValue('Aangepast')
    await w.find('[data-testid="bk-form"]').trigger('submit')
    await flushPromises()
    // PATCH zonder status (anders 409 backend-guard); ADR-037: geen eigenaar-veld meer.
    expect(api.blokkades.werkBij).toHaveBeenCalledWith('b2', {
      toelichting: 'Aangepast',
    })
  })

  it('toont 422-veldfout in de Dialog op het juiste veld', async () => {
    const err = new Error('val')
    err.status = 422
    err.detail = [{ loc: ['body', 'status'], msg: 'te lang' }]
    api.blokkades.werkBij.mockRejectedValueOnce(err)
    const w = await mountSectie()
    await w.find('[data-testid="bk-bewerk-b1"]').trigger('click')
    await flushPromises()
    await w.find('[data-testid="bk-form"]').trigger('submit')
    await flushPromises()
    expect(w.find('[data-testid="bk-fout-status"]').text()).toContain('te lang')
  })
})
