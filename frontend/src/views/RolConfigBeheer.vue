<script setup>
/**
 * RolConfigBeheer — platform-beheer van de componentrol-catalogus (ADR-028).
 * Schil op `/platform/componentrolconfig`. Enkel-doel (één platte lijst); spiegel van
 * PartijsoortConfigBeheer. GEEN verwijderen (soft-deactivate via `actief`). De rol
 * `interne_applicatie` (Intern) is een beschermde systeem-sleutel: niet deactiveerbaar
 * (Systeem-Tag i.p.v. toggle; een 422 SYSTEEM_SLEUTEL_BESCHERMD wordt netjes afgevangen).
 */
import { computed, reactive, ref } from 'vue'
import Dialog from 'primevue/dialog'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import { useToast } from 'primevue/usetoast'
import { useAuthStore } from '@/store/auth'
import { api } from '@/api'

const SLEUTEL_PATROON = /^[a-z][a-z0-9_]*$/
const SYSTEEM_SLEUTEL = 'interne_applicatie'
const auth = useAuthStore()
const toast = useToast()
const magBeheren = computed(() => auth.hasRole('platformbeheerder'))
const isSysteem = (o) => o.optie_sleutel === SYSTEEM_SLEUTEL

const opties = ref([])
const laden = ref(false)
const fout = ref(null)
const bezig = ref(false)

const gesorteerd = computed(() =>
  [...opties.value].sort((a, b) => a.volgorde - b.volgorde || a.id - b.id),
)

function _vervang(updated) {
  const i = opties.value.findIndex((o) => o.id === updated.id)
  if (i >= 0) opties.value[i] = updated
}

function _toonFout(e) {
  const detail =
    e?.status === 409 || e?.code === 'CONFIGURATIE_CONFLICT'
      ? e?.message || 'Deze sleutel bestaat al.'
      : e?.code === 'SYSTEEM_SLEUTEL_BESCHERMD'
        ? e?.message || 'Deze systeem-sleutel kan niet worden gedeactiveerd.'
        : e?.status === 403
          ? 'Je hebt geen platformbeheer-rechten voor deze actie.'
          : e?.status === 422
            ? (Array.isArray(e?.detail) ? e.detail[0]?.msg : null) || 'Ongeldige invoer.'
            : e?.message || 'Er ging iets mis.'
  toast.add({ severity: e?.status === 409 ? 'warn' : 'error', summary: 'Componentrollen', detail, life: 6000 })
  return detail
}

async function laad() {
  laden.value = true
  fout.value = null
  try {
    opties.value = await api.platformComponentrolconfig.lijst()
  } catch (e) {
    fout.value = e?.message || 'Laden van de catalogus mislukt.'
  } finally {
    laden.value = false
  }
}

// ── Toevoegen ────────────────────────────────────────────────────────────────
const addOpen = ref(false)
const addForm = reactive({ optie_sleutel: '', label: '', volgorde: '' })
const addFouten = reactive({})
const addFormFout = ref(null)

function openToevoegen() {
  Object.assign(addForm, { optie_sleutel: '', label: '', volgorde: '' })
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
  return Object.keys(addFouten).length === 0
}
async function bevestigToevoegen() {
  if (!_valideerAdd()) return
  bezig.value = true
  addFormFout.value = null
  try {
    const data = { optie_sleutel: addForm.optie_sleutel.trim(), label: addForm.label.trim() }
    const v = addForm.volgorde !== '' ? Number.parseInt(addForm.volgorde, 10) : null
    if (v !== null && !Number.isNaN(v)) data.volgorde = v
    const optie = await api.platformComponentrolconfig.maak(data)
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

// ── Bewerken (label + volgorde; sleutel immutabel) ────────────────────────────
const editOpen = ref(false)
const editOptie = ref(null)
const editForm = reactive({ label: '', volgorde: '' })
const editFouten = reactive({})

function openBewerken(optie) {
  editOptie.value = optie
  Object.assign(editForm, { label: optie.label, volgorde: String(optie.volgorde) })
  Object.keys(editFouten).forEach((k) => delete editFouten[k])
  editOpen.value = true
}
async function bevestigBewerken() {
  Object.keys(editFouten).forEach((k) => delete editFouten[k])
  if (!editForm.label.trim()) {
    editFouten.label = 'Label is verplicht.'
    return
  }
  bezig.value = true
  try {
    const data = { label: editForm.label.trim() }
    const v = Number.parseInt(editForm.volgorde, 10)
    if (!Number.isNaN(v)) data.volgorde = v
    const updated = await api.platformComponentrolconfig.werkBij(editOptie.value.id, data)
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
    const updated = await api.platformComponentrolconfig.werkBij(deactOptie.value.id, { actief: false })
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
    const updated = await api.platformComponentrolconfig.werkBij(optie.id, { actief: true })
    _vervang(updated)
    toast.add({ severity: 'success', summary: 'Gereactiveerd', detail: updated.optie_sleutel, life: 3000 })
  } catch (e) {
    _toonFout(e)
  }
}

laad()
</script>

<template>
  <section aria-labelledby="rol-titel">
    <h1 id="rol-titel" class="text-[length:var(--lk-text-xl)] font-semibold mb-[var(--lk-space-md)]">
      Componentrollen
    </h1>
    <p class="mb-[var(--lk-space-md)] max-w-prose text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]">
      De rol van een component: intern, interne/externe dataprovider of koppelvlak. "Intern" is de
      beschermde standaard en kan niet worden gedeactiveerd.
    </p>

    <p v-if="fout" role="alert" data-testid="rol-fout" class="text-[var(--lk-color-danger)] mb-[var(--lk-space-sm)]">{{ fout }}</p>
    <p v-if="laden" data-testid="rol-laden" class="text-[var(--lk-color-text-muted)]">Laden…</p>

    <section class="card" data-testid="rol-sectie">
      <div class="flex items-center gap-[var(--lk-space-md)] mb-[var(--lk-space-sm)]">
        <h2 class="text-[length:var(--lk-text-lg)] font-semibold">Rol-opties</h2>
        <Button v-if="magBeheren" label="Optie toevoegen" data-testid="rol-toevoegen" class="ml-auto" @click="openToevoegen" />
      </div>

      <table class="w-full text-[length:var(--lk-text-sm)]" data-testid="rol-tabel">
        <thead>
          <tr class="text-left text-[var(--lk-color-text-muted)]">
            <th class="py-[var(--lk-space-xs)]">Label</th>
            <th>Sleutel</th>
            <th>Volgorde</th>
            <th>Status</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="optie in gesorteerd"
            :key="optie.id"
            :data-testid="`rol-rij-${optie.id}`"
            class="border-t border-[var(--lk-color-border)]"
            :class="optie.actief ? '' : 'opacity-50'"
          >
            <td class="py-[var(--lk-space-xs)]">{{ optie.label }}</td>
            <td class="font-mono">{{ optie.optie_sleutel }}</td>
            <td>{{ optie.volgorde }}</td>
            <td>
              <Tag :data-testid="`rol-status-${optie.id}`" :value="optie.actief ? 'Actief' : 'Gedeactiveerd'" :severity="optie.actief ? 'success' : 'secondary'" />
            </td>
            <td class="text-right">
              <div v-if="magBeheren" class="flex items-center justify-end gap-[var(--lk-space-xs)]">
                <Button label="Bewerken" severity="secondary" :data-testid="`rol-bewerk-${optie.id}`" @click="openBewerken(optie)" />
                <Tag
                  v-if="isSysteem(optie)"
                  :data-testid="`rol-systeem-${optie.id}`"
                  value="Systeem"
                  severity="info"
                  title="Beschermde standaard-rol — niet deactiveerbaar."
                />
                <template v-else>
                  <Button v-if="optie.actief" label="Deactiveren" severity="danger" :data-testid="`rol-deactiveer-${optie.id}`" @click="vraagDeactiveren(optie)" />
                  <Button v-else label="Reactiveren" :data-testid="`rol-reactiveer-${optie.id}`" @click="reactiveer(optie)" />
                </template>
              </div>
            </td>
          </tr>
          <tr v-if="!gesorteerd.length">
            <td colspan="5" data-testid="rol-leeg" class="py-[var(--lk-space-sm)] text-[var(--lk-color-text-muted)]">Nog geen rol-opties.</td>
          </tr>
        </tbody>
      </table>
    </section>

    <!-- Toevoegen -->
    <Dialog v-model:visible="addOpen" modal :closable="false" header="Rol-optie toevoegen" data-testid="rol-add-dialog">
      <form class="flex flex-col gap-[var(--lk-space-md)] min-w-[22rem]" data-testid="rol-add-form" @submit.prevent="bevestigToevoegen">
        <p v-if="addFormFout" role="alert" data-testid="rol-add-formfout" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ addFormFout }}</p>
        <div class="flex flex-col gap-[var(--lk-space-xs)]">
          <label for="rol-add-sleutel" class="font-semibold">Sleutel *</label>
          <input id="rol-add-sleutel" v-model="addForm.optie_sleutel" type="text" data-testid="rol-add-sleutel" :aria-invalid="!!addFouten.optie_sleutel" placeholder="bv. koppelvlak" class="rounded-[var(--lk-radius-input)] border border-[var(--lk-color-border)] px-[var(--lk-space-sm)] py-[var(--lk-space-xs)] bg-white font-mono" />
          <span v-if="addFouten.optie_sleutel" role="alert" data-testid="rol-add-fout-optie_sleutel" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ addFouten.optie_sleutel }}</span>
        </div>
        <div class="flex flex-col gap-[var(--lk-space-xs)]">
          <label for="rol-add-label" class="font-semibold">Label *</label>
          <input id="rol-add-label" v-model="addForm.label" type="text" data-testid="rol-add-label" :aria-invalid="!!addFouten.label" class="rounded-[var(--lk-radius-input)] border border-[var(--lk-color-border)] px-[var(--lk-space-sm)] py-[var(--lk-space-xs)] bg-white" />
          <span v-if="addFouten.label" role="alert" data-testid="rol-add-fout-label" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ addFouten.label }}</span>
        </div>
        <div class="flex flex-col gap-[var(--lk-space-xs)]">
          <label for="rol-add-volgorde" class="font-semibold">Volgorde</label>
          <input id="rol-add-volgorde" v-model="addForm.volgorde" type="number" data-testid="rol-add-volgorde" placeholder="leeg = achteraan" class="w-32 rounded-[var(--lk-radius-input)] border border-[var(--lk-color-border)] px-[var(--lk-space-sm)] py-[var(--lk-space-xs)] bg-white" />
        </div>
        <div class="flex gap-[var(--lk-space-md)]">
          <Button type="submit" label="Toevoegen" data-testid="rol-add-opslaan" :disabled="bezig" />
          <Button type="button" label="Annuleren" severity="secondary" @click="addOpen = false" />
        </div>
      </form>
    </Dialog>

    <!-- Bewerken -->
    <Dialog v-model:visible="editOpen" modal :closable="false" header="Rol-optie bewerken" data-testid="rol-edit-dialog">
      <form class="flex flex-col gap-[var(--lk-space-md)] min-w-[22rem]" data-testid="rol-edit-form" @submit.prevent="bevestigBewerken">
        <dl class="grid grid-cols-[max-content_1fr] gap-x-[var(--lk-space-md)] gap-y-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]">
          <dt class="font-semibold">Sleutel</dt>
          <dd data-testid="rol-edit-sleutel-readonly" class="font-mono">{{ editOptie?.optie_sleutel }}</dd>
        </dl>
        <p class="text-[length:var(--lk-text-xs)] text-[var(--lk-color-text-muted)]">De sleutel ligt vast (stabiele referentie) en is niet bewerkbaar.</p>
        <div class="flex flex-col gap-[var(--lk-space-xs)]">
          <label for="rol-edit-label" class="font-semibold">Label *</label>
          <input id="rol-edit-label" v-model="editForm.label" type="text" data-testid="rol-edit-label" :aria-invalid="!!editFouten.label" class="rounded-[var(--lk-radius-input)] border border-[var(--lk-color-border)] px-[var(--lk-space-sm)] py-[var(--lk-space-xs)] bg-white" />
          <span v-if="editFouten.label" role="alert" data-testid="rol-edit-fout-label" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ editFouten.label }}</span>
        </div>
        <div class="flex flex-col gap-[var(--lk-space-xs)]">
          <label for="rol-edit-volgorde" class="font-semibold">Volgorde</label>
          <input id="rol-edit-volgorde" v-model="editForm.volgorde" type="number" data-testid="rol-edit-volgorde" class="w-32 rounded-[var(--lk-radius-input)] border border-[var(--lk-color-border)] px-[var(--lk-space-sm)] py-[var(--lk-space-xs)] bg-white" />
        </div>
        <div class="flex gap-[var(--lk-space-md)]">
          <Button type="submit" label="Opslaan" data-testid="rol-edit-opslaan" :disabled="bezig" />
          <Button type="button" label="Annuleren" severity="secondary" @click="editOpen = false" />
        </div>
      </form>
    </Dialog>

    <!-- Deactiveren -->
    <Dialog v-model:visible="deactOpen" modal header="Rol deactiveren" data-testid="rol-deact-dialog">
      <p class="mb-[var(--lk-space-sm)] max-w-prose">
        Wil je <strong>{{ deactOptie?.label }}</strong> (<span class="font-mono">{{ deactOptie?.optie_sleutel }}</span>) deactiveren?
      </p>
      <p data-testid="rol-deact-uitleg" class="mb-[var(--lk-space-md)] max-w-prose text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]">
        Bestaande componenten behouden hun rol; de optie is alleen niet meer kiesbaar voor nieuwe registraties.
      </p>
      <div class="flex justify-end gap-[var(--lk-space-md)]">
        <Button label="Annuleren" severity="secondary" @click="deactOpen = false" />
        <Button label="Deactiveren" severity="danger" data-testid="rol-deact-bevestig" :disabled="bezig" @click="bevestigDeactiveren" />
      </div>
    </Dialog>
  </section>
</template>
