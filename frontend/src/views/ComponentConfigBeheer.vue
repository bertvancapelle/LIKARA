<script setup>
/**
 * ComponentConfigBeheer — platform-beheer van de componentcatalogus (ADR-021 Besluit 8,
 * ADR-012 Addendum C). Schil op `/platform/componentconfig` (CD053). Spiegel van
 * ContractConfigBeheer; de enige afwijking is de systeem-sleutel-bescherming: het
 * componenttype `applicatie` is niet deactiveerbaar (Systeem-Tag i.p.v. toggle; de
 * backend weigert hoe dan ook met 422). GEEN verwijderen (soft-deactivate).
 */
import { computed, reactive, ref } from 'vue'
import Dialog from 'primevue/dialog'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import { useToast } from 'primevue/usetoast'
import { useAuthStore } from '@/store/auth'
import { api } from '@/api'

const DIMENSIES = [
  { key: 'componenttype', label: 'Componenttypen' },
  { key: 'structuurrelatie_type', label: 'Structuurrelatie-typen' },
]
const SLEUTEL_PATROON = /^[a-z][a-z0-9_]*$/

const auth = useAuthStore()
const toast = useToast()
const magBeheren = computed(() => auth.hasRole('platformbeheerder'))

const opties = ref([])
const laden = ref(false)
const fout = ref(null)
const bezig = ref(false)

// ADR-026 — gesloten keuzelijsten (element/laag/aspect) uit de backend-bron; nooit hier hardcoden.
const typeringOpties = reactive({ elementen: [], lagen: [], aspecten: [] })
// De typering is alléén van toepassing op de dimensie componenttype.
const isComponenttype = (key) => key === 'componenttype'

// Systeem-sleutel (Addendum C Besluit 5): componenttype.applicatie — niet deactiveerbaar.
const isSysteem = (o) => o.dimensie === 'componenttype' && o.optie_sleutel === 'applicatie'

function perDimensie(key) {
  return opties.value
    .filter((o) => o.dimensie === key)
    .sort((a, b) => a.volgorde - b.volgorde || a.id - b.id)
}
const dimLabel = (key) => DIMENSIES.find((d) => d.key === key)?.label ?? key

function _vervang(updated) {
  const i = opties.value.findIndex((o) => o.id === updated.id)
  if (i >= 0) opties.value[i] = updated
}

function _toonFout(e) {
  const detail =
    e?.status === 409 || e?.code === 'CONFIGURATIE_CONFLICT'
      ? e?.message || 'Deze sleutel bestaat al binnen deze dimensie.'
      : e?.code === 'SYSTEEM_SLEUTEL_BESCHERMD'
        ? e?.message || 'Deze systeem-sleutel kan niet worden gedeactiveerd.'
        : e?.status === 403
          ? 'Je hebt geen platformbeheer-rechten voor deze actie.'
          : e?.status === 422
            ? (Array.isArray(e?.detail) ? e.detail[0]?.msg : null) || 'Ongeldige invoer.'
            : e?.message || 'Er ging iets mis.'
  toast.add({ severity: e?.status === 409 ? 'warn' : 'error', summary: 'Catalogus', detail, life: 6000 })
  return detail
}

async function laad() {
  laden.value = true
  fout.value = null
  try {
    opties.value = await api.platformComponentconfig.lijst()
  } catch (e) {
    fout.value = e?.message || 'Laden van de catalogus mislukt.'
  } finally {
    laden.value = false
  }
}

async function laadTyperingOpties() {
  try {
    const t = await api.platformComponentconfig.typeringOpties()
    typeringOpties.elementen = t?.elementen ?? []
    typeringOpties.lagen = t?.lagen ?? []
    typeringOpties.aspecten = t?.aspecten ?? []
  } catch {
    // Keuzelijsten niet kritisch voor het tonen van de catalogus; dialogen tonen lege selects.
  }
}

// ── Toevoegen ────────────────────────────────────────────────────────────────
const addOpen = ref(false)
const addDim = ref(null)
const addForm = reactive({
  optie_sleutel: '', label: '', volgorde: '',
  archimate_element: '', archimate_laag: '', archimate_aspect: '',
})
const addFouten = reactive({})
const addFormFout = ref(null)

function openToevoegen(dim) {
  addDim.value = dim
  Object.assign(addForm, {
    optie_sleutel: '', label: '', volgorde: '',
    archimate_element: '', archimate_laag: '', archimate_aspect: '',
  })
  Object.keys(addFouten).forEach((k) => delete addFouten[k])
  addFormFout.value = null
  addOpen.value = true
}
function _valideerAdd() {
  Object.keys(addFouten).forEach((k) => delete addFouten[k])
  const sl = addForm.optie_sleutel.trim()
  if (!sl) addFouten.optie_sleutel = 'Sleutel is verplicht.'
  else if (!SLEUTEL_PATROON.test(sl))
    addFouten.optie_sleutel = 'Lowercase snake_case (a-z, 0-9, _), begin met een letter.'
  if (!addForm.label.trim()) addFouten.label = 'Label is verplicht.'
  // ADR-026 Besluit 4: typering verplicht bij aanmaken van een componenttype.
  if (isComponenttype(addDim.value)) {
    if (!addForm.archimate_element) addFouten.archimate_element = 'Element is verplicht.'
    if (!addForm.archimate_laag) addFouten.archimate_laag = 'Laag is verplicht.'
    if (!addForm.archimate_aspect) addFouten.archimate_aspect = 'Aspect is verplicht.'
  }
  return Object.keys(addFouten).length === 0
}
async function bevestigToevoegen() {
  if (!_valideerAdd()) return
  bezig.value = true
  addFormFout.value = null
  try {
    const data = { dimensie: addDim.value, optie_sleutel: addForm.optie_sleutel.trim(), label: addForm.label.trim() }
    const v = addForm.volgorde !== '' ? Number.parseInt(addForm.volgorde, 10) : null
    if (v !== null && !Number.isNaN(v)) data.volgorde = v
    if (isComponenttype(addDim.value)) {
      data.archimate_element = addForm.archimate_element
      data.archimate_laag = addForm.archimate_laag
      data.archimate_aspect = addForm.archimate_aspect
    }
    const optie = await api.platformComponentconfig.maak(data)
    opties.value.push(optie)
    toast.add({ severity: 'success', summary: 'Toegevoegd', detail: optie.optie_sleutel, life: 3000 })
    addOpen.value = false
  } catch (e) {
    if (e?.status === 422 && Array.isArray(e.detail)) {
      for (const d of e.detail) {
        const f = Array.isArray(d.loc) ? d.loc[d.loc.length - 1] : null
        if (f && f in addForm) addFouten[f] = d.msg
      }
    }
    addFormFout.value = _toonFout(e)
  } finally {
    bezig.value = false
  }
}

// ── Bewerken (label + volgorde; sleutel/dimensie immutabel — ook voor systeem) ─
const editOpen = ref(false)
const editOptie = ref(null)
const editForm = reactive({ label: '', volgorde: '', archimate_element: '', archimate_laag: '', archimate_aspect: '' })
const editFouten = reactive({})
const editIsComponenttype = computed(() => isComponenttype(editOptie.value?.dimensie))

function openBewerken(optie) {
  editOptie.value = optie
  Object.assign(editForm, {
    label: optie.label, volgorde: String(optie.volgorde),
    archimate_element: optie.archimate_element ?? '',
    archimate_laag: optie.archimate_laag ?? '',
    archimate_aspect: optie.archimate_aspect ?? '',
  })
  Object.keys(editFouten).forEach((k) => delete editFouten[k])
  editOpen.value = true
}
async function bevestigBewerken() {
  Object.keys(editFouten).forEach((k) => delete editFouten[k])
  if (!editForm.label.trim()) {
    editFouten.label = 'Label is verplicht.'
    return
  }
  // ADR-026 Besluit 5: een componenttype-typering mag niet leeggemaakt worden.
  if (editIsComponenttype.value) {
    if (!editForm.archimate_element) editFouten.archimate_element = 'Element is verplicht.'
    if (!editForm.archimate_laag) editFouten.archimate_laag = 'Laag is verplicht.'
    if (!editForm.archimate_aspect) editFouten.archimate_aspect = 'Aspect is verplicht.'
    if (Object.keys(editFouten).length) return
  }
  bezig.value = true
  try {
    const data = { label: editForm.label.trim() }
    const v = Number.parseInt(editForm.volgorde, 10)
    if (!Number.isNaN(v)) data.volgorde = v
    if (editIsComponenttype.value) {
      data.archimate_element = editForm.archimate_element
      data.archimate_laag = editForm.archimate_laag
      data.archimate_aspect = editForm.archimate_aspect
    }
    const updated = await api.platformComponentconfig.werkBij(editOptie.value.id, data)
    _vervang(updated)
    toast.add({ severity: 'success', summary: 'Opgeslagen', detail: updated.optie_sleutel, life: 3000 })
    editOpen.value = false
  } catch (e) {
    _toonFout(e)
  } finally {
    bezig.value = false
  }
}

// ── Deactiveren / reactiveren (soft) ─────────────────────────────────────────
const deactOpen = ref(false)
const deactOptie = ref(null)
function vraagDeactiveren(optie) {
  deactOptie.value = optie
  deactOpen.value = true
}
async function bevestigDeactiveren() {
  bezig.value = true
  try {
    const updated = await api.platformComponentconfig.werkBij(deactOptie.value.id, { actief: false })
    _vervang(updated)
    deactOpen.value = false
    toast.add({ severity: 'success', summary: 'Gedeactiveerd', detail: updated.optie_sleutel, life: 3000 })
  } catch (e) {
    _toonFout(e)
  } finally {
    bezig.value = false
  }
}
async function reactiveer(optie) {
  try {
    const updated = await api.platformComponentconfig.werkBij(optie.id, { actief: true })
    _vervang(updated)
    toast.add({ severity: 'success', summary: 'Gereactiveerd', detail: updated.optie_sleutel, life: 3000 })
  } catch (e) {
    _toonFout(e)
  }
}

laad()
laadTyperingOpties()
</script>

<template>
  <section aria-labelledby="cat-titel">
    <h1 id="cat-titel" class="text-[length:var(--cd-text-xl)] font-semibold mb-[var(--cd-space-md)]">
      Componentcatalogus
    </h1>

    <p v-if="fout" role="alert" data-testid="cat-fout" class="text-[var(--cd-color-danger)] mb-[var(--cd-space-sm)]">{{ fout }}</p>
    <p v-if="laden" data-testid="cat-laden" class="text-[var(--cd-color-text-muted)]">Laden…</p>

    <div class="flex flex-col gap-[var(--cd-space-lg)]">
      <section
        v-for="dim in DIMENSIES"
        :key="dim.key"
        class="card"
        :data-testid="`cat-sectie-${dim.key}`"
        :aria-labelledby="`cat-kop-${dim.key}`"
      >
        <div class="flex items-center gap-[var(--cd-space-md)] mb-[var(--cd-space-sm)]">
          <h2 :id="`cat-kop-${dim.key}`" class="text-[length:var(--cd-text-lg)] font-semibold">{{ dim.label }}</h2>
          <Button
            v-if="magBeheren"
            label="Optie toevoegen"
            size="small"
            :data-testid="`cat-toevoegen-${dim.key}`"
            class="ml-auto"
            @click="openToevoegen(dim.key)"
          />
        </div>

        <table class="w-full text-[length:var(--cd-text-sm)]" :data-testid="`cat-tabel-${dim.key}`">
          <thead>
            <tr class="text-left text-[var(--cd-color-text-muted)]">
              <th class="py-[var(--cd-space-xs)]">Label</th>
              <th>Sleutel</th>
              <th>Volgorde</th>
              <template v-if="isComponenttype(dim.key)">
                <th>Element</th>
                <th>Laag</th>
                <th>Aspect</th>
              </template>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="optie in perDimensie(dim.key)"
              :key="optie.id"
              :data-testid="`cat-rij-${optie.id}`"
              class="border-t border-[var(--cd-color-border)]"
              :class="optie.actief ? '' : 'opacity-50'"
            >
              <td class="py-[var(--cd-space-xs)]">{{ optie.label }}</td>
              <td class="font-mono">{{ optie.optie_sleutel }}</td>
              <td>{{ optie.volgorde }}</td>
              <template v-if="isComponenttype(dim.key)">
                <td class="font-mono" :data-testid="`cat-element-${optie.id}`">{{ optie.archimate_element || '—' }}</td>
                <td class="font-mono" :data-testid="`cat-laag-${optie.id}`">{{ optie.archimate_laag || '—' }}</td>
                <td class="font-mono" :data-testid="`cat-aspect-${optie.id}`">{{ optie.archimate_aspect || '—' }}</td>
              </template>
              <td>
                <Tag
                  :data-testid="`cat-status-${optie.id}`"
                  :value="optie.actief ? 'Actief' : 'Gedeactiveerd'"
                  :severity="optie.actief ? 'success' : 'secondary'"
                />
              </td>
              <td class="text-right">
                <div v-if="magBeheren" class="flex items-center justify-end gap-[var(--cd-space-xs)]">
                  <Button label="Bewerken" size="small" severity="secondary" :data-testid="`cat-bewerk-${optie.id}`" @click="openBewerken(optie)" />
                  <Tag
                    v-if="isSysteem(optie)"
                    :data-testid="`cat-systeem-${optie.id}`"
                    value="Systeem"
                    severity="info"
                    title="Systeem-sleutel — gekoppeld aan het subtype-mechanisme; niet deactiveerbaar."
                  />
                  <template v-else>
                    <Button
                      v-if="optie.actief"
                      label="Deactiveren"
                      size="small"
                      severity="danger"
                      :data-testid="`cat-deactiveer-${optie.id}`"
                      @click="vraagDeactiveren(optie)"
                    />
                    <Button
                      v-else
                      label="Reactiveren"
                      size="small"
                      :data-testid="`cat-reactiveer-${optie.id}`"
                      @click="reactiveer(optie)"
                    />
                  </template>
                </div>
              </td>
            </tr>
            <tr v-if="!perDimensie(dim.key).length">
              <td :colspan="isComponenttype(dim.key) ? 8 : 5" :data-testid="`cat-leeg-${dim.key}`" class="py-[var(--cd-space-sm)] text-[var(--cd-color-text-muted)]">
                Nog geen opties in deze dimensie.
              </td>
            </tr>
          </tbody>
        </table>
      </section>
    </div>

    <!-- Toevoegen -->
    <Dialog v-model:visible="addOpen" modal :closable="false" :header="`Optie toevoegen — ${dimLabel(addDim)}`" data-testid="cat-add-dialog">
      <form class="flex flex-col gap-[var(--cd-space-md)] min-w-[22rem]" data-testid="cat-add-form" @submit.prevent="bevestigToevoegen">
        <p v-if="addFormFout" role="alert" data-testid="cat-add-formfout" class="text-[var(--cd-color-danger)] text-[length:var(--cd-text-sm)]">{{ addFormFout }}</p>
        <div class="flex flex-col gap-[var(--cd-space-xs)]">
          <label for="cat-add-sleutel" class="font-semibold">Sleutel *</label>
          <input id="cat-add-sleutel" v-model="addForm.optie_sleutel" type="text" data-testid="cat-add-sleutel" :aria-invalid="!!addFouten.optie_sleutel" aria-describedby="cat-add-fout-sleutel" placeholder="bv. etl_tool" class="rounded-[var(--cd-radius-input)] border border-[var(--cd-color-border)] px-[var(--cd-space-sm)] py-[var(--cd-space-xs)] bg-white font-mono" />
          <span v-if="addFouten.optie_sleutel" id="cat-add-fout-sleutel" role="alert" data-testid="cat-add-fout-optie_sleutel" class="text-[var(--cd-color-danger)] text-[length:var(--cd-text-sm)]">{{ addFouten.optie_sleutel }}</span>
        </div>
        <div class="flex flex-col gap-[var(--cd-space-xs)]">
          <label for="cat-add-label" class="font-semibold">Label *</label>
          <input id="cat-add-label" v-model="addForm.label" type="text" data-testid="cat-add-label" :aria-invalid="!!addFouten.label" aria-describedby="cat-add-fout-label" class="rounded-[var(--cd-radius-input)] border border-[var(--cd-color-border)] px-[var(--cd-space-sm)] py-[var(--cd-space-xs)] bg-white" />
          <span v-if="addFouten.label" id="cat-add-fout-label" role="alert" data-testid="cat-add-fout-label" class="text-[var(--cd-color-danger)] text-[length:var(--cd-text-sm)]">{{ addFouten.label }}</span>
        </div>
        <div class="flex flex-col gap-[var(--cd-space-xs)]">
          <label for="cat-add-volgorde" class="font-semibold">Volgorde</label>
          <input id="cat-add-volgorde" v-model="addForm.volgorde" type="number" data-testid="cat-add-volgorde" placeholder="leeg = achteraan" class="w-32 rounded-[var(--cd-radius-input)] border border-[var(--cd-color-border)] px-[var(--cd-space-sm)] py-[var(--cd-space-xs)] bg-white" />
        </div>
        <!-- ADR-026: ArchiMate-typering — alleen voor dimensie componenttype, verplicht. -->
        <template v-if="isComponenttype(addDim)">
          <div class="flex flex-col gap-[var(--cd-space-xs)]">
            <label for="cat-add-element" class="font-semibold">ArchiMate-element *</label>
            <select id="cat-add-element" v-model="addForm.archimate_element" data-testid="cat-add-element" :aria-invalid="!!addFouten.archimate_element" class="rounded-[var(--cd-radius-input)] border border-[var(--cd-color-border)] px-[var(--cd-space-sm)] py-[var(--cd-space-xs)] bg-white">
              <option value="">— kies —</option>
              <option v-for="el in typeringOpties.elementen" :key="el" :value="el">{{ el }}</option>
            </select>
            <span v-if="addFouten.archimate_element" role="alert" data-testid="cat-add-fout-archimate_element" class="text-[var(--cd-color-danger)] text-[length:var(--cd-text-sm)]">{{ addFouten.archimate_element }}</span>
          </div>
          <div class="flex flex-col gap-[var(--cd-space-xs)]">
            <label for="cat-add-laag" class="font-semibold">Laag *</label>
            <select id="cat-add-laag" v-model="addForm.archimate_laag" data-testid="cat-add-laag" :aria-invalid="!!addFouten.archimate_laag" class="rounded-[var(--cd-radius-input)] border border-[var(--cd-color-border)] px-[var(--cd-space-sm)] py-[var(--cd-space-xs)] bg-white">
              <option value="">— kies —</option>
              <option v-for="l in typeringOpties.lagen" :key="l" :value="l">{{ l }}</option>
            </select>
            <span v-if="addFouten.archimate_laag" role="alert" data-testid="cat-add-fout-archimate_laag" class="text-[var(--cd-color-danger)] text-[length:var(--cd-text-sm)]">{{ addFouten.archimate_laag }}</span>
          </div>
          <div class="flex flex-col gap-[var(--cd-space-xs)]">
            <label for="cat-add-aspect" class="font-semibold">Aspect *</label>
            <select id="cat-add-aspect" v-model="addForm.archimate_aspect" data-testid="cat-add-aspect" :aria-invalid="!!addFouten.archimate_aspect" class="rounded-[var(--cd-radius-input)] border border-[var(--cd-color-border)] px-[var(--cd-space-sm)] py-[var(--cd-space-xs)] bg-white">
              <option value="">— kies —</option>
              <option v-for="a in typeringOpties.aspecten" :key="a" :value="a">{{ a }}</option>
            </select>
            <span v-if="addFouten.archimate_aspect" role="alert" data-testid="cat-add-fout-archimate_aspect" class="text-[var(--cd-color-danger)] text-[length:var(--cd-text-sm)]">{{ addFouten.archimate_aspect }}</span>
          </div>
        </template>
        <div class="flex gap-[var(--cd-space-md)]">
          <Button type="submit" label="Toevoegen" data-testid="cat-add-opslaan" :disabled="bezig" />
          <Button type="button" label="Annuleren" severity="secondary" @click="addOpen = false" />
        </div>
      </form>
    </Dialog>

    <!-- Bewerken (sleutel + dimensie read-only) -->
    <Dialog v-model:visible="editOpen" modal :closable="false" header="Optie bewerken" data-testid="cat-edit-dialog">
      <form class="flex flex-col gap-[var(--cd-space-md)] min-w-[22rem]" data-testid="cat-edit-form" @submit.prevent="bevestigBewerken">
        <dl class="grid grid-cols-[max-content_1fr] gap-x-[var(--cd-space-md)] gap-y-[var(--cd-space-xs)] text-[length:var(--cd-text-sm)]">
          <dt class="font-semibold">Dimensie</dt>
          <dd data-testid="cat-edit-dimensie-readonly">{{ dimLabel(editOptie?.dimensie) }}</dd>
          <dt class="font-semibold">Sleutel</dt>
          <dd data-testid="cat-edit-sleutel-readonly" class="font-mono">{{ editOptie?.optie_sleutel }}</dd>
        </dl>
        <p class="text-[length:var(--cd-text-xs)] text-[var(--cd-color-text-muted)]">Dimensie en sleutel liggen vast (stabiele referentie) en zijn niet bewerkbaar.</p>
        <div class="flex flex-col gap-[var(--cd-space-xs)]">
          <label for="cat-edit-label" class="font-semibold">Label *</label>
          <input id="cat-edit-label" v-model="editForm.label" type="text" data-testid="cat-edit-label" :aria-invalid="!!editFouten.label" class="rounded-[var(--cd-radius-input)] border border-[var(--cd-color-border)] px-[var(--cd-space-sm)] py-[var(--cd-space-xs)] bg-white" />
          <span v-if="editFouten.label" role="alert" data-testid="cat-edit-fout-label" class="text-[var(--cd-color-danger)] text-[length:var(--cd-text-sm)]">{{ editFouten.label }}</span>
        </div>
        <div class="flex flex-col gap-[var(--cd-space-xs)]">
          <label for="cat-edit-volgorde" class="font-semibold">Volgorde</label>
          <input id="cat-edit-volgorde" v-model="editForm.volgorde" type="number" data-testid="cat-edit-volgorde" class="w-32 rounded-[var(--cd-radius-input)] border border-[var(--cd-color-border)] px-[var(--cd-space-sm)] py-[var(--cd-space-xs)] bg-white" />
        </div>
        <!-- ADR-026: typering bewerkbaar voor componenttype; leegmaken niet toegestaan. -->
        <template v-if="editIsComponenttype">
          <div class="flex flex-col gap-[var(--cd-space-xs)]">
            <label for="cat-edit-element" class="font-semibold">ArchiMate-element *</label>
            <select id="cat-edit-element" v-model="editForm.archimate_element" data-testid="cat-edit-element" :aria-invalid="!!editFouten.archimate_element" class="rounded-[var(--cd-radius-input)] border border-[var(--cd-color-border)] px-[var(--cd-space-sm)] py-[var(--cd-space-xs)] bg-white">
              <option value="">— kies —</option>
              <option v-for="el in typeringOpties.elementen" :key="el" :value="el">{{ el }}</option>
            </select>
            <span v-if="editFouten.archimate_element" role="alert" data-testid="cat-edit-fout-archimate_element" class="text-[var(--cd-color-danger)] text-[length:var(--cd-text-sm)]">{{ editFouten.archimate_element }}</span>
          </div>
          <div class="flex flex-col gap-[var(--cd-space-xs)]">
            <label for="cat-edit-laag" class="font-semibold">Laag *</label>
            <select id="cat-edit-laag" v-model="editForm.archimate_laag" data-testid="cat-edit-laag" :aria-invalid="!!editFouten.archimate_laag" class="rounded-[var(--cd-radius-input)] border border-[var(--cd-color-border)] px-[var(--cd-space-sm)] py-[var(--cd-space-xs)] bg-white">
              <option value="">— kies —</option>
              <option v-for="l in typeringOpties.lagen" :key="l" :value="l">{{ l }}</option>
            </select>
            <span v-if="editFouten.archimate_laag" role="alert" data-testid="cat-edit-fout-archimate_laag" class="text-[var(--cd-color-danger)] text-[length:var(--cd-text-sm)]">{{ editFouten.archimate_laag }}</span>
          </div>
          <div class="flex flex-col gap-[var(--cd-space-xs)]">
            <label for="cat-edit-aspect" class="font-semibold">Aspect *</label>
            <select id="cat-edit-aspect" v-model="editForm.archimate_aspect" data-testid="cat-edit-aspect" :aria-invalid="!!editFouten.archimate_aspect" class="rounded-[var(--cd-radius-input)] border border-[var(--cd-color-border)] px-[var(--cd-space-sm)] py-[var(--cd-space-xs)] bg-white">
              <option value="">— kies —</option>
              <option v-for="a in typeringOpties.aspecten" :key="a" :value="a">{{ a }}</option>
            </select>
            <span v-if="editFouten.archimate_aspect" role="alert" data-testid="cat-edit-fout-archimate_aspect" class="text-[var(--cd-color-danger)] text-[length:var(--cd-text-sm)]">{{ editFouten.archimate_aspect }}</span>
          </div>
        </template>
        <div class="flex gap-[var(--cd-space-md)]">
          <Button type="submit" label="Opslaan" data-testid="cat-edit-opslaan" :disabled="bezig" />
          <Button type="button" label="Annuleren" severity="secondary" @click="editOpen = false" />
        </div>
      </form>
    </Dialog>

    <!-- Deactiveren -->
    <Dialog v-model:visible="deactOpen" modal header="Optie deactiveren" data-testid="cat-deact-dialog">
      <p class="mb-[var(--cd-space-sm)] max-w-prose">
        Wil je <strong>{{ deactOptie?.label }}</strong> (<span class="font-mono">{{ deactOptie?.optie_sleutel }}</span>) deactiveren?
      </p>
      <p data-testid="cat-deact-uitleg" class="mb-[var(--cd-space-md)] max-w-prose text-[length:var(--cd-text-sm)] text-[var(--cd-color-text-muted)]">
        Bestaande registraties blijven leesbaar; de optie is alleen niet meer kiesbaar voor nieuwe registraties.
      </p>
      <div class="flex justify-end gap-[var(--cd-space-md)]">
        <Button label="Annuleren" severity="secondary" @click="deactOpen = false" />
        <Button label="Deactiveren" severity="danger" data-testid="cat-deact-bevestig" :disabled="bezig" @click="bevestigDeactiveren" />
      </div>
    </Dialog>
  </section>
</template>
