/** Tests — meldingen.toastSucces (LI035-standaard: korte succes-toast, uniforme vorm). */
import { describe, expect, it, vi } from 'vitest'
import { toastSucces } from '@/meldingen'

describe('toastSucces — dé succes-vorm', () => {
  it('toont een korte succes-toast: severity success, life 3000', () => {
    const toast = { add: vi.fn() }
    toastSucces(toast, 'Toegevoegd')
    expect(toast.add).toHaveBeenCalledWith({ severity: 'success', summary: 'Toegevoegd', life: 3000 })
  })

  it('geeft een optioneel detail door zonder de vorm te veranderen', () => {
    const toast = { add: vi.fn() }
    toastSucces(toast, 'Opgeslagen', 'biv_hoog')
    expect(toast.add).toHaveBeenCalledWith({
      severity: 'success', summary: 'Opgeslagen', detail: 'biv_hoog', life: 3000,
    })
  })
})
