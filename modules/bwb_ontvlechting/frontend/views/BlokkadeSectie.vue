<script setup>
/**
 * BlokkadeSectie — blokkades van één applicatie (systeem-afgeleid, ADR-013).
 *
 * GEEN "Toevoegen"/"Verwijderen": blokkades ontstaan/lossen automatisch op bij
 * een Checklistscore. De gebruiker beheert alleen de opvolging via PATCH
 * (status/toelichting/eigenaar). Na een PATCH emit de sectie 'gewijzigd' zodat de
 * ouder de lifecycle-indicator herlaadt (geblokkeerd ↔ migratieklaar kan schuiven).
 */
import { computed, reactive, ref } from 'vue'
import { Button, Column, DataTable, Dialog, InputText, Tag, Textarea, useToast } from '@/primevue'
import { useAuthStore } from '@/store/auth'
import { api } from '@/api'
import { BLOKKADE_STATUS, BLOKKADE_STATUS_SEVERITY, SCORE, label } from '../labels'
import ScoreBadge from './ScoreBadge.vue'

const props = defineProps({ applicatieId: { type: String, required: true } })
const emit = defineEmits(['gewijzigd', 'naar-vraag'])

// Herkomst-doorklik: een vraag-code als "2.7" → checklist-categorie 2. De ouder
// (ApplicatieDetail) schakelt naar het Checklist-tabblad + die categorie en
// markeert de vraag. Read-only navigatie; geen schrijf-affordance.
function categorieVan(code) {
  const nr = Number.parseInt(String(code ?? '').split('.')[0], 10)
  return Number.isInteger(nr) ? nr : null
}
function naarVraag(rij) {
  if (!rij?.vraag_code) return
  emit('naar-vraag', {
    code: rij.vraag_code,
    categorieNr: categorieVan(rij.vraag_code),
    checklistvraagId: rij.checklistvraag_id,
  })
}
const auth = useAuthStore()
const toast = useToast()

const mag = computed(() => auth.hasRole('medewerker', 'beheerder'))

const items = ref([])
const cursor = ref(null)
const laden = ref(false)
const fout = ref(null)
const opties = ref({ status: [] })

// Sortering (CD020) — null = server-default (created_at asc), niet meegestuurd.
const sortVeld = ref(null)
const sortRichting = ref(null) // 'asc' | 'desc'
const primeSortOrder = computed(() =>
  sortRichting.value === 'asc' ? 1 : sortRichting.value === 'desc' ? -1 : 0,
)

const aantalOpen = computed(
  () => items.value.filter((b) => b.status === 'open' || b.status === 'in_behandeling').length,
)

const dialogOpen = ref(false)
const bewerkenId = ref(null)
const bewerkenOpgelost = ref(false) // ADR-016: opgelost = read-only, niet handmatig
const bezig = ref(false)
const form = reactive({ status: '', toelichting: '', eigenaar: '' })
const fouten = reactive({})
let laatsteTrigger = null

// ADR-016: handmatig alleen open ↔ in_behandeling; `opgelost` ontstaat enkel via
// de auto-logica (Checklistscore ja/nvt) → geen keuze-optie in de dropdown.
const handmatigeStatusOpties = computed(() => opties.value.status.filter((s) => s !== 'opgelost'))

function _toastFout(e) {
  const per = { 403: 'Geen rechten voor deze actie.', 404: 'Niet gevonden.', 409: e?.message || 'Conflict.' }
  toast.add({ severity: 'error', summary: 'Fout', detail: per[e?.status] || e?.message || 'Er ging iets mis.', life: 5000 })
}

async function laad({ reset = false } = {}) {
  laden.value = true
  fout.value = null
  try {
    const params = { component_id: props.applicatieId, limit: 25, after: reset ? undefined : cursor.value }
    if (sortVeld.value) {
      params.sort = sortVeld.value
      params.order = sortRichting.value
    }
    const p = await api.blokkades.lijst(params)
    items.value = reset ? p.items : items.value.concat(p.items)
    cursor.value = p.volgende_cursor
  } catch (e) {
    fout.value = e?.message || 'Laden van blokkades mislukt.'
  } finally {
    laden.value = false
  }
}

function onSort(event) {
  sortVeld.value = event.sortField
  sortRichting.value = event.sortOrder === 1 ? 'asc' : 'desc'
  cursor.value = null
  laad({ reset: true })
}

async function _laadOptiesEenmalig() {
  if (!opties.value.status.length) {
    try {
      opties.value = await api.blokkades.opties()
    } catch (e) {
      _toastFout(e)
    }
  }
}

async function openBewerken(e, rij) {
  laatsteTrigger = e?.currentTarget ?? null
  bewerkenId.value = rij.id
  bewerkenOpgelost.value = rij.status === 'opgelost'
  Object.keys(fouten).forEach((k) => delete fouten[k])
  Object.assign(form, { status: rij.status, toelichting: rij.toelichting || '', eigenaar: rij.eigenaar || '' })
  await _laadOptiesEenmalig()
  dialogOpen.value = true
}

function focusEerste() {
  // Bij een opgeloste blokkade is er geen status-select → focus het eerste editbare veld.
  setTimeout(
    () => (document.getElementById('bk-status') || document.getElementById('bk-eigenaar'))?.focus?.(),
    0,
  )
}
function onHide() {
  laatsteTrigger?.focus?.()
}

function _serverveldfouten(e) {
  if (e?.status === 422 && Array.isArray(e.detail)) {
    let t = false
    for (const d of e.detail) {
      const v = Array.isArray(d.loc) ? d.loc[d.loc.length - 1] : null
      if (v && v in form) {
        fouten[v] = d.msg || 'Ongeldige waarde.'
        t = true
      }
    }
    return t
  }
  return false
}

async function opslaan() {
  Object.keys(fouten).forEach((k) => delete fouten[k])
  const payload = {
    toelichting: form.toelichting.trim() || null,
    eigenaar: form.eigenaar.trim() || null,
  }
  // Opgeloste blokkade: status NIET meesturen (read-only; backend-guard ADR-016).
  if (!bewerkenOpgelost.value) {
    if (!form.status) {
      fouten.status = 'Maak een keuze.'
      return
    }
    payload.status = form.status
  }
  bezig.value = true
  try {
    await api.blokkades.werkBij(bewerkenId.value, payload)
    toast.add({ severity: 'success', summary: 'Blokkade bijgewerkt', life: 3000 })
    dialogOpen.value = false
    await laad({ reset: true })
    emit('gewijzigd')
  } catch (e) {
    if (!_serverveldfouten(e)) _toastFout(e)
  } finally {
    bezig.value = false
  }
}

defineExpose({ aantalOpen, herlaad: () => laad({ reset: true }) })

laad({ reset: true })
</script>

<template>
  <section class="card" aria-labelledby="sectie-blokkades">
    <div class="flex items-center gap-[var(--cd-space-md)] mb-[var(--cd-space-sm)]">
      <h2 id="sectie-blokkades" class="text-[length:var(--cd-text-lg)] font-semibold">Blokkades</h2>
      <span data-testid="bk-open-teller" class="ml-auto text-[var(--cd-color-text-muted)] text-[length:var(--cd-text-sm)]">{{ aantalOpen }} open</span>
    </div>

    <p v-if="fout" role="alert" data-testid="bk-fout" class="text-[var(--cd-color-danger)] mb-[var(--cd-space-sm)]">{{ fout }}</p>

    <DataTable
      :value="items"
      lazy
      :sort-field="sortVeld"
      :sort-order="primeSortOrder"
      data-testid="bk-tabel"
      @sort="onSort"
    >
      <Column header="Status" sort-field="status" sortable><template #body="{ data }"><Tag :value="label(BLOKKADE_STATUS, data.status)" :severity="BLOKKADE_STATUS_SEVERITY[data.status] || 'info'" /></template></Column>
      <Column header="Veroorzaakt door">
        <template #body="{ data }">
          <button
            v-if="data.vraag_code"
            type="button"
            :data-testid="`bk-herkomst-${data.id}`"
            :title="`${data.vraag || ''}${data.score ? ` — antwoord: ${label(SCORE, data.score)}` : ''}`"
            class="text-[var(--cd-color-primary)] font-medium hover:underline focus:outline-2 focus:outline-offset-2 focus:outline-[var(--cd-color-primary)]"
            @click="naarVraag(data)"
          >
            Vraag {{ data.vraag_code }}
          </button>
          <span v-if="data.vraag_code && data.score"> (<ScoreBadge :score="data.score" />)</span>
          <span v-else class="text-[var(--cd-color-text-muted)]">—</span>
        </template>
      </Column>
      <Column field="toelichting" header="Toelichting" sortable />
      <Column field="eigenaar" header="Eigenaar" sortable />
      <Column header="">
        <template #body="{ data }">
          <Button v-if="mag" label="Bewerken" severity="secondary" :data-testid="`bk-bewerk-${data.id}`" @click="(e) => openBewerken(e, data)" />
        </template>
      </Column>
      <template #empty><span data-testid="bk-leeg">Geen blokkades.</span></template>
    </DataTable>

    <Button v-if="cursor" label="Meer laden" severity="secondary" data-testid="bk-meer" :disabled="laden" class="mt-[var(--cd-space-sm)]" @click="laad()" />

    <Dialog v-model:visible="dialogOpen" modal :closable="false" header="Blokkade bewerken" data-testid="bk-dialog" @show="focusEerste" @hide="onHide">
      <form class="flex flex-col gap-[var(--cd-space-md)] min-w-[20rem]" data-testid="bk-form" @submit.prevent="opslaan">
        <div class="flex flex-col gap-[var(--cd-space-xs)]">
          <label for="bk-status" class="font-semibold">Status<span v-if="!bewerkenOpgelost"> *</span></label>
          <!-- ADR-016: opgelost is read-only (auto-afgeleid), niet handmatig kiesbaar. -->
          <template v-if="bewerkenOpgelost">
            <Tag data-testid="bk-status-readonly" :value="label(BLOKKADE_STATUS, 'opgelost')" :severity="BLOKKADE_STATUS_SEVERITY.opgelost" />
            <span data-testid="bk-status-readonly-hint" class="text-[var(--cd-color-text-muted)] text-[length:var(--cd-text-sm)]">Auto-opgelost — niet handmatig wijzigbaar.</span>
          </template>
          <select v-else id="bk-status" autofocus v-model="form.status" data-testid="bk-veld-status" :aria-invalid="!!fouten.status" aria-describedby="bk-fout-status" class="rounded-[var(--cd-radius-input)] border border-[var(--cd-color-border)] px-[var(--cd-space-sm)] py-[var(--cd-space-xs)] bg-white">
            <option v-for="s in handmatigeStatusOpties" :key="s" :value="s">{{ label(BLOKKADE_STATUS, s) }}</option>
          </select>
          <span v-if="fouten.status" id="bk-fout-status" role="alert" data-testid="bk-fout-status" class="text-[var(--cd-color-danger)] text-[length:var(--cd-text-sm)]">{{ fouten.status }}</span>
        </div>
        <div class="flex flex-col gap-[var(--cd-space-xs)]">
          <label for="bk-eigenaar" class="font-semibold">Eigenaar</label>
          <InputText id="bk-eigenaar" v-model="form.eigenaar" data-testid="bk-veld-eigenaar" :aria-invalid="!!fouten.eigenaar" aria-describedby="bk-fout-eigenaar" />
          <span v-if="fouten.eigenaar" id="bk-fout-eigenaar" role="alert" data-testid="bk-fout-eigenaar" class="text-[var(--cd-color-danger)] text-[length:var(--cd-text-sm)]">{{ fouten.eigenaar }}</span>
        </div>
        <div class="flex flex-col gap-[var(--cd-space-xs)]">
          <label for="bk-toelichting" class="font-semibold">Toelichting</label>
          <Textarea id="bk-toelichting" v-model="form.toelichting" rows="3" data-testid="bk-veld-toelichting" />
        </div>
        <div class="flex gap-[var(--cd-space-md)]">
          <Button type="submit" label="Opslaan" data-testid="bk-opslaan" :disabled="bezig" />
          <Button type="button" label="Annuleren" severity="secondary" @click="dialogOpen = false" />
        </div>
      </form>
    </Dialog>
  </section>
</template>
