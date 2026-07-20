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
import VeldUitleg from '@modules/bwb_ontvlechting/frontend/views/VeldUitleg.vue'

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
    fout.value = e?.status === 401 ? null : e?.message || 'Laden van de catalogus mislukt.'
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
  checklist_dragend: false,
  ondersteunt_werk: false,
})

// ADR-027 Deel 4 — read-only inzage: kenmerk-definitie per relatietype (code-eigendom).
const kenmerkRelaties = computed(() =>
  opties.value
    .filter((o) => o.dimensie === 'archimate_relatie')
    .sort((a, b) => a.volgorde - b.volgorde || a.id - b.id),
)
function kenmerkRijen(def) {
  return Object.entries(def || {}).map(([sleutel, spec]) => {
    const type = spec?.type ?? 'onbekend'
    let detail = ''
    if (type === 'catalogus') detail = `catalogus · ${spec.catalogus ?? '?'} / ${spec.dimensie ?? '?'}`
    else if (type === 'enum') detail = `enum · ${spec.enum ?? '?'}`
    else if (type === 'registratie') detail = 'vrij registratieveld'
    return { sleutel, type, detail }
  })
}
const addFouten = reactive({})
const addFormFout = ref(null)

function openToevoegen(dim) {
  addDim.value = dim
  Object.assign(addForm, {
    optie_sleutel: '', label: '', volgorde: '',
    archimate_element: '', archimate_laag: '', archimate_aspect: '',
    checklist_dragend: false,
    ondersteunt_werk: false,
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
      data.checklist_dragend = addForm.checklist_dragend
      data.ondersteunt_werk = addForm.ondersteunt_werk
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
const editForm = reactive({ label: '', volgorde: '', archimate_element: '', archimate_laag: '', archimate_aspect: '', checklist_dragend: false, ondersteunt_werk: false })
const editFouten = reactive({})
const editIsComponenttype = computed(() => isComponenttype(editOptie.value?.dimensie))

function openBewerken(optie) {
  editOptie.value = optie
  Object.assign(editForm, {
    label: optie.label, volgorde: String(optie.volgorde),
    archimate_element: optie.archimate_element ?? '',
    archimate_laag: optie.archimate_laag ?? '',
    archimate_aspect: optie.archimate_aspect ?? '',
    checklist_dragend: optie.checklist_dragend === true,
    ondersteunt_werk: optie.ondersteunt_werk === true,
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
      data.checklist_dragend = editForm.checklist_dragend
      data.ondersteunt_werk = editForm.ondersteunt_werk
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
    <h1 id="cat-titel" class="text-[length:var(--lk-text-xl)] font-semibold mb-[var(--lk-space-md)]">
      Componentcatalogus
    </h1>

    <p v-if="fout" role="alert" data-testid="cat-fout" class="text-[var(--lk-color-danger)] mb-[var(--lk-space-sm)]">{{ fout }}</p>
    <p v-if="laden" data-testid="cat-laden" class="text-[var(--lk-color-text-muted)]">Laden…</p>

    <div class="flex flex-col gap-[var(--lk-space-lg)]">
      <section
        v-for="dim in DIMENSIES"
        :key="dim.key"
        class="card"
        :data-testid="`cat-sectie-${dim.key}`"
        :aria-labelledby="`cat-kop-${dim.key}`"
      >
        <div class="flex items-center gap-[var(--lk-space-md)] mb-[var(--lk-space-sm)]">
          <h2 :id="`cat-kop-${dim.key}`" class="text-[length:var(--lk-text-lg)] font-semibold">{{ dim.label }}</h2>
          <!-- LI047 — alléén deze dimensie draagt een systeem-sleutel (`applicatie`, zie isSysteem),
               dus staat de aanduiding hier en niet op elke sectiekop. Verving de tooltip-only uitleg. -->
          <VeldUitleg v-if="dim.key === 'componenttype'" veld="systeem_sleutel" testid="uitleg-systeem-sleutel" />
          <Button
            v-if="magBeheren"
            label="Optie toevoegen"
            :data-testid="`cat-toevoegen-${dim.key}`"
            class="ml-auto"
            @click="openToevoegen(dim.key)"
          />
        </div>

        <table class="w-full text-[length:var(--lk-text-sm)]" :data-testid="`cat-tabel-${dim.key}`">
          <thead>
            <tr class="text-left text-[var(--lk-color-text-muted)]">
              <th class="py-[var(--lk-space-xs)]">Label</th>
              <th>Sleutel</th>
              <th>Volgorde</th>
              <template v-if="isComponenttype(dim.key)">
                <th>Element</th>
                <th>Laag</th>
                <th>Aspect</th>
                <th>Checklist</th>
                <th>Ondersteunt werk</th>
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
              class="border-t border-[var(--lk-color-border)]"
              :class="optie.actief ? '' : 'opacity-50'"
            >
              <td class="py-[var(--lk-space-xs)]">{{ optie.label }}</td>
              <td class="font-mono">{{ optie.optie_sleutel }}</td>
              <td>{{ optie.volgorde }}</td>
              <template v-if="isComponenttype(dim.key)">
                <td class="font-mono" :data-testid="`cat-element-${optie.id}`">{{ optie.archimate_element || '—' }}</td>
                <td class="font-mono" :data-testid="`cat-laag-${optie.id}`">{{ optie.archimate_laag || '—' }}</td>
                <td class="font-mono" :data-testid="`cat-aspect-${optie.id}`">{{ optie.archimate_aspect || '—' }}</td>
                <td>
                  <Tag
                    :data-testid="`cat-dragend-${optie.id}`"
                    :value="optie.checklist_dragend ? 'Ja' : 'Nee'"
                    :severity="optie.checklist_dragend ? 'success' : 'secondary'"
                  />
                </td>
                <td>
                  <Tag
                    :data-testid="`cat-werk-${optie.id}`"
                    :value="optie.ondersteunt_werk ? 'Ja' : 'Nee'"
                    :severity="optie.ondersteunt_werk ? 'success' : 'secondary'"
                  />
                </td>
              </template>
              <td>
                <Tag
                  :data-testid="`cat-status-${optie.id}`"
                  :value="optie.actief ? 'Actief' : 'Gedeactiveerd'"
                  :severity="optie.actief ? 'success' : 'secondary'"
                />
              </td>
              <td class="text-right">
                <div v-if="magBeheren" class="flex items-center justify-end gap-[var(--lk-space-xs)]">
                  <Button label="Bewerken" severity="secondary" :data-testid="`cat-bewerk-${optie.id}`" @click="openBewerken(optie)" />
                  <!-- LI047 — geen uitleg-tooltip meer (zie de "i" bij de sectiekop). De oude tekst
                       noemde bovendien het "subtype-mechanisme"; dat bestaat niet meer sinds de
                       applicatie-subtabel is opgeheven (migratie 0047_li059_drop_applicatie). -->
                  <Tag
                    v-if="isSysteem(optie)"
                    :data-testid="`cat-systeem-${optie.id}`"
                    value="Systeem"
                    severity="info"
                  />
                  <template v-else>
                    <Button
                      v-if="optie.actief"
                      label="Deactiveren"
                      severity="danger"
                      :data-testid="`cat-deactiveer-${optie.id}`"
                      @click="vraagDeactiveren(optie)"
                    />
                    <Button
                      v-else
                      label="Reactiveren"
                      :data-testid="`cat-reactiveer-${optie.id}`"
                      @click="reactiveer(optie)"
                    />
                  </template>
                </div>
              </td>
            </tr>
            <tr v-if="!perDimensie(dim.key).length">
              <td :colspan="isComponenttype(dim.key) ? 10 : 5" :data-testid="`cat-leeg-${dim.key}`" class="py-[var(--lk-space-sm)] text-[var(--lk-color-text-muted)]">
                Nog geen opties in deze dimensie.
              </td>
            </tr>
          </tbody>
        </table>
      </section>

      <!-- ADR-027 Deel 4 — kenmerk-definitie per relatietype: READ-ONLY inzage (code-eigendom). -->
      <section class="card" data-testid="cat-kenmerk-viewer" aria-labelledby="cat-kenmerk-kop">
        <h2 id="cat-kenmerk-kop" class="text-[length:var(--lk-text-lg)] font-semibold mb-[var(--lk-space-xs)]">
          Relatie-kenmerken per relatietype
        </h2>
        <p class="mb-[var(--lk-space-sm)] max-w-prose text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]">
          Deze kenmerk-definities horen bij het relatiemodel (ADR-023) en zijn <strong>code-eigendom</strong> —
          alleen ter inzage, niet bewerkbaar. De <em>inhoud</em> van de catalogus-verwijzingen (disposities,
          relatie-rollen) beheer je wél, via de Relatie-kenmerk-catalogus.
        </p>
        <div class="flex flex-col gap-[var(--lk-space-md)]">
          <div v-for="rel in kenmerkRelaties" :key="rel.id" :data-testid="`cat-kenmerk-${rel.optie_sleutel}`">
            <h3 class="font-semibold">{{ rel.label }} <span class="font-mono text-[length:var(--lk-text-xs)] text-[var(--lk-color-text-muted)]">{{ rel.optie_sleutel }}</span></h3>
            <p
              v-if="!kenmerkRijen(rel.kenmerk_definitie).length"
              :data-testid="`cat-kenmerk-leeg-${rel.optie_sleutel}`"
              class="text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]"
            >
              Geen kenmerken (kale relatie).
            </p>
            <ul v-else class="list-disc pl-[var(--lk-space-lg)] text-[length:var(--lk-text-sm)]">
              <li v-for="k in kenmerkRijen(rel.kenmerk_definitie)" :key="k.sleutel" :data-testid="`cat-kenmerk-${rel.optie_sleutel}-${k.sleutel}`">
                <span class="font-mono">{{ k.sleutel }}</span> — {{ k.type }}<span v-if="k.detail"> ({{ k.detail }})</span>
              </li>
            </ul>
          </div>
        </div>
      </section>
    </div>

    <!-- Toevoegen -->
    <Dialog v-model:visible="addOpen" modal :closable="false" :header="`Optie toevoegen — ${dimLabel(addDim)}`" data-testid="cat-add-dialog">
      <form class="flex flex-col gap-[var(--lk-space-md)] min-w-[22rem]" data-testid="cat-add-form" @submit.prevent="bevestigToevoegen">
        <p v-if="addFormFout" role="alert" data-testid="cat-add-formfout" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ addFormFout }}</p>
        <div class="flex flex-col gap-[var(--lk-space-xs)]">
          <span class="inline-flex items-center gap-[var(--lk-space-xs)]">
            <label for="cat-add-sleutel" class="font-semibold">Sleutel *</label>
            <VeldUitleg veld="sleutel" />
          </span>
          <input id="cat-add-sleutel" v-model="addForm.optie_sleutel" type="text" data-testid="cat-add-sleutel" :aria-invalid="!!addFouten.optie_sleutel" aria-describedby="cat-add-fout-sleutel" placeholder="bv. etl_tool" class="lk-veld font-mono" />
          <span v-if="addFouten.optie_sleutel" id="cat-add-fout-sleutel" role="alert" data-testid="cat-add-fout-optie_sleutel" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ addFouten.optie_sleutel }}</span>
        </div>
        <div class="flex flex-col gap-[var(--lk-space-xs)]">
          <label for="cat-add-label" class="font-semibold">Label *</label>
          <input id="cat-add-label" v-model="addForm.label" type="text" data-testid="cat-add-label" :aria-invalid="!!addFouten.label" aria-describedby="cat-add-fout-label" class="lk-veld" />
          <span v-if="addFouten.label" id="cat-add-fout-label" role="alert" data-testid="cat-add-fout-label" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ addFouten.label }}</span>
        </div>
        <div class="flex flex-col gap-[var(--lk-space-xs)]">
          <label for="cat-add-volgorde" class="font-semibold">Volgorde</label>
          <input id="cat-add-volgorde" v-model="addForm.volgorde" type="number" data-testid="cat-add-volgorde" placeholder="leeg = achteraan" class="lk-veld w-32" />
        </div>
        <!-- ADR-026: ArchiMate-typering — alleen voor dimensie componenttype, verplicht. -->
        <template v-if="isComponenttype(addDim)">
          <div class="flex flex-col gap-[var(--lk-space-xs)]">
            <span class="inline-flex items-center gap-[var(--lk-space-xs)]">
              <label for="cat-add-element" class="font-semibold">ArchiMate-element *</label>
              <VeldUitleg veld="archimate_element" opties="archimate_element" />
            </span>
            <select id="cat-add-element" v-model="addForm.archimate_element" data-testid="cat-add-element" :aria-invalid="!!addFouten.archimate_element" class="lk-veld">
              <option value="">— kies —</option>
              <option v-for="el in typeringOpties.elementen" :key="el" :value="el">{{ el }}</option>
            </select>
            <span v-if="addFouten.archimate_element" role="alert" data-testid="cat-add-fout-archimate_element" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ addFouten.archimate_element }}</span>
          </div>
          <div class="flex flex-col gap-[var(--lk-space-xs)]">
            <span class="inline-flex items-center gap-[var(--lk-space-xs)]">
              <label for="cat-add-laag" class="font-semibold">Laag *</label>
              <VeldUitleg veld="archimate_laag" opties="archimate_laag" />
            </span>
            <select id="cat-add-laag" v-model="addForm.archimate_laag" data-testid="cat-add-laag" :aria-invalid="!!addFouten.archimate_laag" class="lk-veld">
              <option value="">— kies —</option>
              <option v-for="l in typeringOpties.lagen" :key="l" :value="l">{{ l }}</option>
            </select>
            <span v-if="addFouten.archimate_laag" role="alert" data-testid="cat-add-fout-archimate_laag" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ addFouten.archimate_laag }}</span>
          </div>
          <div class="flex flex-col gap-[var(--lk-space-xs)]">
            <span class="inline-flex items-center gap-[var(--lk-space-xs)]">
              <label for="cat-add-aspect" class="font-semibold">Aspect *</label>
              <VeldUitleg veld="archimate_aspect" opties="archimate_aspect" />
            </span>
            <select id="cat-add-aspect" v-model="addForm.archimate_aspect" data-testid="cat-add-aspect" :aria-invalid="!!addFouten.archimate_aspect" class="lk-veld">
              <option value="">— kies —</option>
              <option v-for="a in typeringOpties.aspecten" :key="a" :value="a">{{ a }}</option>
            </select>
            <span v-if="addFouten.archimate_aspect" role="alert" data-testid="cat-add-fout-archimate_aspect" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ addFouten.archimate_aspect }}</span>
          </div>
          <label class="flex items-center gap-[var(--lk-space-sm)]">
            <input type="checkbox" v-model="addForm.checklist_dragend" data-testid="cat-add-checklist_dragend" />
            <span class="font-semibold">Checklist-dragend</span>
          </label>
          <VeldUitleg veld="checklist_dragend" />
          <label class="flex items-center gap-[var(--lk-space-sm)]">
            <input type="checkbox" v-model="addForm.ondersteunt_werk" data-testid="cat-add-ondersteunt_werk" />
            <span class="font-semibold">Ondersteunt werk</span>
          </label>
          <VeldUitleg veld="ondersteunt_werk" />
        </template>
        <div class="flex gap-[var(--lk-space-md)]">
          <Button type="submit" label="Toevoegen" data-testid="cat-add-opslaan" :disabled="bezig" />
          <Button type="button" label="Annuleren" severity="secondary" @click="addOpen = false" />
        </div>
      </form>
    </Dialog>

    <!-- Bewerken (sleutel + dimensie read-only) -->
    <Dialog v-model:visible="editOpen" modal :closable="false" header="Optie bewerken" data-testid="cat-edit-dialog">
      <form class="flex flex-col gap-[var(--lk-space-md)] min-w-[22rem]" data-testid="cat-edit-form" @submit.prevent="bevestigBewerken">
        <dl class="grid grid-cols-[max-content_1fr] gap-x-[var(--lk-space-md)] gap-y-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]">
          <dt class="font-semibold">Dimensie</dt>
          <dd data-testid="cat-edit-dimensie-readonly">{{ dimLabel(editOptie?.dimensie) }}</dd>
          <dt class="font-semibold">Sleutel</dt>
          <dd data-testid="cat-edit-sleutel-readonly" class="font-mono">{{ editOptie?.optie_sleutel }}</dd>
        </dl>
        <p class="text-[length:var(--lk-text-xs)] text-[var(--lk-color-text-muted)]">Dimensie en sleutel liggen vast (stabiele referentie) en zijn niet bewerkbaar.</p>
        <div class="flex flex-col gap-[var(--lk-space-xs)]">
          <label for="cat-edit-label" class="font-semibold">Label *</label>
          <input id="cat-edit-label" v-model="editForm.label" type="text" data-testid="cat-edit-label" :aria-invalid="!!editFouten.label" class="lk-veld" />
          <span v-if="editFouten.label" role="alert" data-testid="cat-edit-fout-label" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ editFouten.label }}</span>
        </div>
        <div class="flex flex-col gap-[var(--lk-space-xs)]">
          <label for="cat-edit-volgorde" class="font-semibold">Volgorde</label>
          <input id="cat-edit-volgorde" v-model="editForm.volgorde" type="number" data-testid="cat-edit-volgorde" class="lk-veld w-32" />
        </div>
        <!-- ADR-026: typering bewerkbaar voor componenttype; leegmaken niet toegestaan. -->
        <template v-if="editIsComponenttype">
          <div class="flex flex-col gap-[var(--lk-space-xs)]">
            <span class="inline-flex items-center gap-[var(--lk-space-xs)]">
              <label for="cat-edit-element" class="font-semibold">ArchiMate-element *</label>
              <VeldUitleg veld="archimate_element" opties="archimate_element" />
            </span>
            <select id="cat-edit-element" v-model="editForm.archimate_element" data-testid="cat-edit-element" :aria-invalid="!!editFouten.archimate_element" class="lk-veld">
              <option value="">— kies —</option>
              <option v-for="el in typeringOpties.elementen" :key="el" :value="el">{{ el }}</option>
            </select>
            <span v-if="editFouten.archimate_element" role="alert" data-testid="cat-edit-fout-archimate_element" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ editFouten.archimate_element }}</span>
          </div>
          <div class="flex flex-col gap-[var(--lk-space-xs)]">
            <span class="inline-flex items-center gap-[var(--lk-space-xs)]">
              <label for="cat-edit-laag" class="font-semibold">Laag *</label>
              <VeldUitleg veld="archimate_laag" opties="archimate_laag" />
            </span>
            <select id="cat-edit-laag" v-model="editForm.archimate_laag" data-testid="cat-edit-laag" :aria-invalid="!!editFouten.archimate_laag" class="lk-veld">
              <option value="">— kies —</option>
              <option v-for="l in typeringOpties.lagen" :key="l" :value="l">{{ l }}</option>
            </select>
            <span v-if="editFouten.archimate_laag" role="alert" data-testid="cat-edit-fout-archimate_laag" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ editFouten.archimate_laag }}</span>
          </div>
          <div class="flex flex-col gap-[var(--lk-space-xs)]">
            <span class="inline-flex items-center gap-[var(--lk-space-xs)]">
              <label for="cat-edit-aspect" class="font-semibold">Aspect *</label>
              <VeldUitleg veld="archimate_aspect" opties="archimate_aspect" />
            </span>
            <select id="cat-edit-aspect" v-model="editForm.archimate_aspect" data-testid="cat-edit-aspect" :aria-invalid="!!editFouten.archimate_aspect" class="lk-veld">
              <option value="">— kies —</option>
              <option v-for="a in typeringOpties.aspecten" :key="a" :value="a">{{ a }}</option>
            </select>
            <span v-if="editFouten.archimate_aspect" role="alert" data-testid="cat-edit-fout-archimate_aspect" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ editFouten.archimate_aspect }}</span>
          </div>
          <label class="flex items-center gap-[var(--lk-space-sm)]">
            <input type="checkbox" v-model="editForm.checklist_dragend" data-testid="cat-edit-checklist_dragend" />
            <span class="font-semibold">Checklist-dragend</span>
            <span class="text-[length:var(--lk-text-xs)] text-[var(--lk-color-text-muted)]">— uitzetten sluit de invoer (bestaande antwoorden blijven leesbaar)</span>
          </label>
          <label class="flex items-center gap-[var(--lk-space-sm)]">
            <input type="checkbox" v-model="editForm.ondersteunt_werk" data-testid="cat-edit-ondersteunt_werk" />
            <span class="font-semibold">Ondersteunt werk</span>
            <span class="text-[length:var(--lk-text-xs)] text-[var(--lk-color-text-muted)]">— uitzetten haalt het type uit de koppel-keuze; bestaande registraties blijven staan</span>
          </label>
        </template>
        <div class="flex gap-[var(--lk-space-md)]">
          <Button type="submit" label="Opslaan" data-testid="cat-edit-opslaan" :disabled="bezig" />
          <Button type="button" label="Annuleren" severity="secondary" @click="editOpen = false" />
        </div>
      </form>
    </Dialog>

    <!-- Deactiveren -->
    <Dialog v-model:visible="deactOpen" modal header="Optie deactiveren" data-testid="cat-deact-dialog">
      <p class="mb-[var(--lk-space-sm)] max-w-prose">
        Wil je <strong>{{ deactOptie?.label }}</strong> (<span class="font-mono">{{ deactOptie?.optie_sleutel }}</span>) deactiveren?
      </p>
      <p data-testid="cat-deact-uitleg" class="mb-[var(--lk-space-md)] max-w-prose text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]">
        Bestaande registraties blijven leesbaar; de optie is alleen niet meer kiesbaar voor nieuwe registraties.
      </p>
      <div class="flex justify-end gap-[var(--lk-space-md)]">
        <Button label="Annuleren" severity="secondary" @click="deactOpen = false" />
        <Button label="Deactiveren" severity="danger" data-testid="cat-deact-bevestig" :disabled="bezig" @click="bevestigDeactiveren" />
      </div>
    </Dialog>
  </section>
</template>
