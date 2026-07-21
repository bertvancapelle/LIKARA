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
import { actorWeergave, diffWeergave } from '@modules/bwb_ontvlechting/frontend/labels'
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
    expect(diffWeergave({ actie: 'create', wijziging: { naam: { nieuw: 'B' } } })).toEqual({ intro: 'Aangemaakt met:', regels: ['Naam = B'] })
    expect(diffWeergave({ actie: 'delete', wijziging: { naam: { oud: 'A' } } })).toEqual({ intro: 'Verwijderd:', regels: ['Naam was A'] })
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
