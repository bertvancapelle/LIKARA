/** Tests — ChecklistscoreSectie (inline scoringslijst, join op checklistvraag_id ↔ vraag.id). */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import ToastService from 'primevue/toastservice'

vi.mock('@/api', () => ({
  api: {
    checklistvragen: { lijst: vi.fn() },
    checklistscores: { lijst: vi.fn(), maak: vi.fn(), werkBij: vi.fn(), opties: vi.fn() },
  },
}))

import { api } from '@/api'
import { useAuthStore } from '@/store/auth'
import ChecklistscoreSectie from '@modules/bwb_ontvlechting/frontend/views/ChecklistscoreSectie.vue'

const APP = 'app-1'
const VRAGEN = [
  { id: 1, code: '1.1', categorie_nr: 1, categorie_naam: 'C', vraag: 'Vraag een', prioriteit: 'hoog' },
  { id: 2, code: '1.2', categorie_nr: 1, categorie_naam: 'C', vraag: 'Vraag twee', prioriteit: 'hoog' },
]

async function mountSectie({ rollen = ['medewerker'], categorieNr = null, componenttype, markeerCode, bewerkbaar } = {}) {
  const pinia = createPinia()
  const auth = useAuthStore(pinia)
  auth.user = { sub: 's', tenant_id: 't', email: 'a@b.nl', roles: rollen }
  const wrapper = mount(ChecklistscoreSectie, {
    props: {
      applicatieId: APP, categorieNr,
      ...(componenttype !== undefined ? { componenttype } : {}),
      ...(markeerCode !== undefined ? { markeerCode } : {}),
      ...(bewerkbaar !== undefined ? { bewerkbaar } : {}),
    },
    global: { plugins: [pinia, [PrimeVue, { unstyled: true }], ToastService] },
  })
  await flushPromises()
  return wrapper
}

beforeEach(() => {
  vi.clearAllMocks()
  api.checklistvragen.lijst.mockResolvedValue(VRAGEN)
  api.checklistscores.lijst.mockResolvedValue({
    items: [{ id: 's1', component_id: APP, checklistvraag_id: 2, score: 'ja' }],
    volgende_cursor: null,
  })
  api.checklistscores.opties.mockResolvedValue({ score: ['ja', 'deels', 'nee', 'nvt'] })
  api.checklistscores.maak.mockResolvedValue({ id: 's2', score: 'nee' })
  api.checklistscores.werkBij.mockResolvedValue({ id: 's1', score: 'nee' })
})
afterEach(() => vi.restoreAllMocks())

describe('ChecklistscoreSectie', () => {
  it('rendert de vragen en de huidige score (ongescoord = leeg)', async () => {
    const w = await mountSectie()
    expect(w.text()).toContain('Vraag een')
    expect(w.find('[data-testid="cs-score-1.1"]').element.value).toBe('') // ongescoord
    expect(w.find('[data-testid="cs-score-1.2"]').element.value).toBe('ja') // gescoord
  })

  it('toont de voortgang X/N', async () => {
    const w = await mountSectie()
    expect(w.find('[data-testid="cs-voortgang"]').text()).toContain('1/2')
  })

  it('markeert de aangewezen vraag-rij bij een herkomst-doorklik (markeerCode)', async () => {
    const w = await mountSectie({ markeerCode: '1.1' })
    await flushPromises()
    const rij = w.find('[data-testid="cs-rij-1.1"]')
    expect(rij.classes()).toContain('bg-[var(--lk-color-accent)]')
    // Niet-aangewezen rij krijgt de markering niet.
    expect(w.find('[data-testid="cs-rij-1.2"]').classes()).not.toContain('bg-[var(--lk-color-accent)]')
  })

  // ── Onderdeel 2: client-side kolomsortering ────────────────────────────────
  const _codes = (w) => w.findAll('[data-testid^="cs-rij-"]').map((r) => r.attributes('data-testid'))

  it('sorteert client-side op kolomklik (code asc → desc togglet de volgorde)', async () => {
    const w = await mountSectie()
    expect(_codes(w)).toEqual(['cs-rij-1.1', 'cs-rij-1.2']) // default = code oplopend
    await w.find('[data-testid="cs-sort-code"]').trigger('click') // → aflopend
    expect(_codes(w)).toEqual(['cs-rij-1.2', 'cs-rij-1.1'])
    await w.find('[data-testid="cs-sort-code"]').trigger('click') // → weer oplopend
    expect(_codes(w)).toEqual(['cs-rij-1.1', 'cs-rij-1.2'])
  })

  it('markeer-naar-vraag vindt de juiste rij ook ná sortering (id-based, niet positie)', async () => {
    const w = await mountSectie({ markeerCode: '1.1' })
    await flushPromises()
    await w.find('[data-testid="cs-sort-code"]').trigger('click') // volgorde omkeren
    await flushPromises()
    expect(w.find('[data-testid="cs-rij-1.1"]').classes()).toContain('bg-[var(--lk-color-accent)]')
  })

  // ── Onderdeel 3: gedeelde score-kleur op het keuzeveld ─────────────────────
  it('kleurt het score-keuzeveld volgens de gedeelde score-kleur (ja = groen)', async () => {
    const w = await mountSectie() // 1.2 is gescoord 'ja', 1.1 ongescoord
    expect(w.find('[data-testid="cs-score-1.2"]').classes()).toContain('text-[var(--lk-color-success)]')
    expect(w.find('[data-testid="cs-score-1.1"]').classes()).not.toContain('text-[var(--lk-color-success)]')
  })

  // ── ADR-022 Fase E: componenttype-scoping van de vragenset ─────────────────
  it('zonder componenttype: haalt de vragen ongescoped op', async () => {
    await mountSectie()
    expect(api.checklistvragen.lijst).toHaveBeenCalledWith(null)
  })

  it('met componenttype: geeft die door aan checklistvragen.lijst', async () => {
    await mountSectie({ componenttype: 'applicatie' })
    expect(api.checklistvragen.lijst).toHaveBeenCalledWith('applicatie')
  })

  it('maakt een score aan voor een ongescoorde vraag (checklistvraag_id)', async () => {
    const w = await mountSectie()
    await w.find('[data-testid="cs-score-1.1"]').setValue('nee')
    await flushPromises()
    expect(api.checklistscores.maak).toHaveBeenCalledWith({
      component_id: APP,
      checklistvraag_id: 1,
      score: 'nee',
    })
    expect(w.emitted('gewijzigd')).toBeTruthy()
  })

  it('werkt een bestaande score bij via het score-id', async () => {
    const w = await mountSectie()
    await w.find('[data-testid="cs-score-1.2"]').setValue('nee')
    await flushPromises()
    expect(api.checklistscores.werkBij).toHaveBeenCalledWith('s1', { score: 'nee' })
    expect(api.checklistscores.maak).not.toHaveBeenCalled()
  })

  it('valt bij 409 (race) terug op werkBij na refetch', async () => {
    const conflict = new Error('bestaat al')
    conflict.status = 409
    api.checklistscores.maak.mockRejectedValueOnce(conflict)
    // na refetch bestaat de score wél
    api.checklistscores.lijst
      .mockResolvedValueOnce({ items: [{ id: 's1', component_id: APP, checklistvraag_id: 2, score: 'ja' }], volgende_cursor: null })
      .mockResolvedValueOnce({ items: [{ id: 's9', component_id: APP, checklistvraag_id: 1, score: 'nee' }], volgende_cursor: null })
    const w = await mountSectie()
    await w.find('[data-testid="cs-score-1.1"]').setValue('nee')
    await flushPromises()
    expect(api.checklistscores.werkBij).toHaveBeenCalledWith('s9', { score: 'nee' })
  })

  it('rol-gating: viewer kan niet scoren (controls disabled)', async () => {
    const w = await mountSectie({ rollen: ['viewer'] })
    expect(w.find('[data-testid="cs-score-1.1"]').attributes('disabled')).toBeDefined()
  })

  // ── CD026: uitklaprij bevinding/actie (ADR-037: eigenaar verviel) ────────────
  it('klapt een gescoorde rij uit en toont de velden', async () => {
    const w = await mountSectie()
    expect(w.find('[data-testid="cs-detail-1.2"]').exists()).toBe(false)
    await w.find('[data-testid="cs-toggle-1.2"]').trigger('click')
    expect(w.find('[data-testid="cs-detail-1.2"]').exists()).toBe(true)
    expect(w.find('[data-testid="cs-bevinding-1.2"]').exists()).toBe(true)
    expect(w.find('[data-testid="cs-eigenaar-1.2"]').exists()).toBe(false)
    expect(w.find('[data-testid="cs-actie-1.2"]').exists()).toBe(true)
    expect(w.find('[data-testid="cs-toggle-1.2"]').attributes('aria-expanded')).toBe('true')
  })

  it('toont bij een ongescoorde vraag de hint en géén opslaan-knop', async () => {
    const w = await mountSectie()
    await w.find('[data-testid="cs-toggle-1.1"]').trigger('click') // 1.1 = ongescoord
    expect(w.find('[data-testid="cs-detail-hint-1.1"]').exists()).toBe(true)
    expect(w.find('[data-testid="cs-bevinding-1.1"]').exists()).toBe(false)
    expect(w.find('[data-testid="cs-velden-opslaan-1.1"]').exists()).toBe(false)
  })

  it('slaat bevinding/actie op zonder score mee te sturen', async () => {
    api.checklistscores.werkBij.mockResolvedValue({
      id: 's1', score: 'ja', bevinding: 'Onderbouwing.', actie: 'Actie.',
    })
    const w = await mountSectie()
    await w.find('[data-testid="cs-toggle-1.2"]').trigger('click')
    await w.find('[data-testid="cs-bevinding-1.2"]').setValue('Onderbouwing.')
    await w.find('[data-testid="cs-actie-1.2"]').setValue('Actie.')
    await w.find('[data-testid="cs-velden-opslaan-1.2"]').trigger('click')
    await flushPromises()
    expect(api.checklistscores.werkBij).toHaveBeenCalledWith('s1', {
      bevinding: 'Onderbouwing.',
      actie: 'Actie.',
    })
    // geen score in de payload van de velden-opslag
    const payload = api.checklistscores.werkBij.mock.calls.at(-1)[1]
    expect(payload).not.toHaveProperty('score')
    expect(w.find('[data-testid="cs-velden-status-1.2"]').text()).toContain('opgeslagen')
  })

  it('rol-gating: viewer ziet de velden alleen-lezen en geen opslaan-knop', async () => {
    const w = await mountSectie({ rollen: ['viewer'] })
    await w.find('[data-testid="cs-toggle-1.2"]').trigger('click')
    expect(w.find('[data-testid="cs-bevinding-1.2"]').attributes('disabled')).toBeDefined()
    expect(w.find('[data-testid="cs-actie-1.2"]').attributes('disabled')).toBeDefined()
    expect(w.find('[data-testid="cs-velden-opslaan-1.2"]').exists()).toBe(false)
  })

  // ── CD029 (ADR-019): gestructureerd antwoordveld per type ──────────────────
  function _gescoord(vraagId, antwoord_waarde = null) {
    return { items: [{ id: 's1', component_id: APP, checklistvraag_id: vraagId, score: 'ja', antwoord_waarde }], volgende_cursor: null }
  }

  it('kolomkop is "Afgehandeld" i.p.v. "Score"', async () => {
    const w = await mountSectie()
    expect(w.find('thead').text()).toContain('Afgehandeld')
    expect(w.find('thead').text()).not.toContain('Score')
  })

  it('enkelvoudige keuze: opslaan stuurt {optie}, zonder score', async () => {
    api.checklistvragen.lijst.mockResolvedValue([{
      id: 1, code: '2.1', categorie_nr: 2, categorie_naam: 'T', vraag: 'Hosting', prioriteit: 'hoog',
      antwoordtype: 'enkelvoudige_keuze',
      opties: [
        { optie_sleutel: 'saas', label: 'SaaS', volgorde: 0, actief: true, afgeleid_bron: 'HostingModel' },
        { optie_sleutel: 'on_premise', label: 'On premise', volgorde: 1, actief: true, afgeleid_bron: 'HostingModel' },
      ],
    }])
    api.checklistscores.lijst.mockResolvedValue(_gescoord(1))
    api.checklistscores.werkBij.mockResolvedValue({ id: 's1', score: 'ja', antwoord_waarde: { optie: 'saas' } })
    const w = await mountSectie()
    await w.find('[data-testid="cs-toggle-2.1"]').trigger('click')
    await w.find('[data-testid="cs-antwoord-2.1"]').setValue('saas')
    await w.find('[data-testid="cs-velden-opslaan-2.1"]').trigger('click')
    await flushPromises()
    const payload = api.checklistscores.werkBij.mock.calls.at(-1)[1]
    expect(payload.antwoord_waarde).toEqual({ optie: 'saas' })
    expect(payload).not.toHaveProperty('score')
  })

  it('meerkeuze: twee opties aanvinken → opslaan stuurt {opties:[...]}', async () => {
    api.checklistvragen.lijst.mockResolvedValue([{
      id: 1, code: '4.1', categorie_nr: 4, categorie_naam: 'D', vraag: 'Type', prioriteit: 'hoog',
      antwoordtype: 'meerkeuze',
      opties: [
        { optie_sleutel: 'a', label: 'A', volgorde: 0, actief: true, afgeleid_bron: null },
        { optie_sleutel: 'b', label: 'B', volgorde: 1, actief: true, afgeleid_bron: null },
      ],
    }])
    api.checklistscores.lijst.mockResolvedValue(_gescoord(1))
    api.checklistscores.werkBij.mockResolvedValue({ id: 's1', score: 'ja', antwoord_waarde: { opties: ['a', 'b'] } })
    const w = await mountSectie()
    await w.find('[data-testid="cs-toggle-4.1"]').trigger('click')
    await w.find('[data-testid="cs-antwoord-4.1-a"]').setValue(true)
    await w.find('[data-testid="cs-antwoord-4.1-b"]').setValue(true)
    await w.find('[data-testid="cs-velden-opslaan-4.1"]').trigger('click')
    await flushPromises()
    const payload = api.checklistscores.werkBij.mock.calls.at(-1)[1]
    expect(payload.antwoord_waarde).toEqual({ opties: ['a', 'b'] })
    expect(payload).not.toHaveProperty('score')
  })

  it('getal: waarde invullen → opslaan stuurt {getal:n}', async () => {
    api.checklistvragen.lijst.mockResolvedValue([{
      id: 1, code: '12.4', categorie_nr: 12, categorie_naam: 'R', vraag: 'Prioriteit', prioriteit: 'hoog',
      antwoordtype: 'getal', opties: [],
    }])
    api.checklistscores.lijst.mockResolvedValue(_gescoord(1))
    api.checklistscores.werkBij.mockResolvedValue({ id: 's1', score: 'ja', antwoord_waarde: { getal: 3 } })
    const w = await mountSectie()
    await w.find('[data-testid="cs-toggle-12.4"]').trigger('click')
    await w.find('[data-testid="cs-antwoord-12.4"]').setValue('3')
    await w.find('[data-testid="cs-velden-opslaan-12.4"]').trigger('click')
    await flushPromises()
    const payload = api.checklistscores.werkBij.mock.calls.at(-1)[1]
    expect(payload.antwoord_waarde).toEqual({ getal: 3 })
  })

  it('rol-gating: viewer ziet het antwoordveld disabled', async () => {
    api.checklistvragen.lijst.mockResolvedValue([{
      id: 1, code: '2.1', categorie_nr: 2, categorie_naam: 'T', vraag: 'Hosting', prioriteit: 'hoog',
      antwoordtype: 'enkelvoudige_keuze',
      opties: [{ optie_sleutel: 'saas', label: 'SaaS', volgorde: 0, actief: true, afgeleid_bron: 'HostingModel' }],
    }])
    api.checklistscores.lijst.mockResolvedValue(_gescoord(1))
    const w = await mountSectie({ rollen: ['viewer'] })
    await w.find('[data-testid="cs-toggle-2.1"]').trigger('click')
    expect(w.find('[data-testid="cs-antwoord-2.1"]').attributes('disabled')).toBeDefined()
    expect(w.find('[data-testid="cs-velden-opslaan-2.1"]').exists()).toBe(false)
  })

  // ── CD022: filtering op categorie + globale voortgang ──────────────────────
  it('toont met categorieNr alleen de vragen van die categorie (voortgang blijft globaal)', async () => {
    api.checklistvragen.lijst.mockResolvedValue([
      { id: 1, code: '1.1', categorie_nr: 1, categorie_naam: 'Een', vraag: 'V een', prioriteit: 'hoog' },
      { id: 2, code: '2.1', categorie_nr: 2, categorie_naam: 'Twee', vraag: 'V twee', prioriteit: 'hoog' },
    ])
    api.checklistscores.lijst.mockResolvedValue({ items: [], volgende_cursor: null })
    const w = await mountSectie({ categorieNr: 1 })
    expect(w.find('[data-testid="cs-rij-1.1"]').exists()).toBe(true)
    expect(w.find('[data-testid="cs-rij-2.1"]').exists()).toBe(false) // andere categorie verborgen
    // voortgang telt ALLE vragen (globaal), niet alleen de getoonde categorie
    expect(w.find('[data-testid="cs-voortgang"]').text()).toContain('0/2')
  })
})

describe('ChecklistscoreSectie — ADR-027 read-only (bewerkbaar=false)', () => {
  it('toont de gesloten-melding en disablet de score-invoer; bestaande scores blijven leesbaar', async () => {
    const w = await mountSectie({ rollen: ['medewerker'], bewerkbaar: false })
    expect(w.find('[data-testid="cs-gesloten"]').exists()).toBe(true)
    // score-select is disabled (geen invoer); de waarde blijft wél zichtbaar
    expect(w.find('[data-testid="cs-score-1.2"]').attributes('disabled')).toBeDefined()
    expect(w.text()).toContain('1.2')
  })

  it('bij bewerkbaar=true is de invoer open en is er geen gesloten-melding', async () => {
    const w = await mountSectie({ rollen: ['medewerker'], bewerkbaar: true })
    expect(w.find('[data-testid="cs-gesloten"]').exists()).toBe(false)
    expect(w.find('[data-testid="cs-score-1.2"]').attributes('disabled')).toBeUndefined()
  })

  it('viewer (zonder bewerk-rol) ziet géén gesloten-melding (geen ruis)', async () => {
    const w = await mountSectie({ rollen: ['viewer'], bewerkbaar: false })
    expect(w.find('[data-testid="cs-gesloten"]').exists()).toBe(false)
  })
})
