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
})
