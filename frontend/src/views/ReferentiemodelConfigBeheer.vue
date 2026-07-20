<script setup>
/**
 * ReferentiemodelConfigBeheer — platform-beheer van het referentiemodel-aanbod (gate 1b §2.1).
 * Schil op `/platform/referentiemodelconfig`. Spiegel van ApplicatiefunctieConfigBeheer,
 * met één bewust verschil: GEEN toevoegen — het aanbod is gesloten (het modelbestand reist
 * mee in de release; nieuw aanbod = release-curatie, geen beheerscherm-handeling). Dít is wat
 * "gecureerd" betekent: elk model met navolgbare herkomst (bron, versie, licentie), en de
 * beheerder bepaalt alleen label, volgorde en beschikbaarheid (soft-deactivate).
 */
import { computed, reactive, ref } from 'vue'
import Dialog from 'primevue/dialog'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import { useToast } from 'primevue/usetoast'
import { useAuthStore } from '@/store/auth'
import { api } from '@/api'

const auth = useAuthStore()
const toast = useToast()
const magBeheren = computed(() => auth.hasRole('platformbeheerder'))

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
    e?.status === 403
      ? 'Je hebt geen platformbeheer-rechten voor deze actie.'
      : e?.status === 422
        ? (Array.isArray(e?.detail) ? e.detail[0]?.msg : null) || 'Ongeldige invoer.'
        : e?.message || 'Er ging iets mis.'
  toast.add({ severity: 'error', summary: 'Referentiemodellen', detail, life: 6000 })
}

async function laad() {
  laden.value = true
  fout.value = null
  try {
    opties.value = await api.platformReferentiemodelconfig.lijst()
  } catch (e) {
    fout.value = e?.status === 401 ? null : e?.message || 'Laden van het aanbod mislukt.'
  } finally {
    laden.value = false
  }
}

// ── Bewerken (label + volgorde; sleutel/herkomst/versie = gecureerde identiteit) ──
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
    const updated = await api.platformReferentiemodelconfig.werkBij(editOptie.value.id, data)
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
    const updated = await api.platformReferentiemodelconfig.werkBij(deactOptie.value.id, { actief: false })
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
    const updated = await api.platformReferentiemodelconfig.werkBij(optie.id, { actief: true })
    _vervang(updated)
    toast.add({ severity: 'success', summary: 'Gereactiveerd', detail: updated.optie_sleutel, life: 3000 })
  } catch (e) {
    _toonFout(e)
  }
}

laad()
</script>

<template>
  <section aria-labelledby="rm-titel">
    <h1 id="rm-titel" class="mb-[var(--lk-space-md)]">
      Referentiemodellen
    </h1>
    <p class="mb-[var(--lk-space-md)] max-w-prose text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]">
      Het gecureerde aanbod van referentiemodellen dat tenants kunnen inlezen, met navolgbare
      herkomst (bron, versie, licentie). Nieuwe modellen komen mee met een release — hier
      beheer je alleen het label, de volgorde en de beschikbaarheid. Deactiveren haalt een
      model uit het aanbod; wat een tenant al heeft ingelezen blijft staan.
    </p>

    <p v-if="fout" role="alert" data-testid="rm-fout" class="text-[var(--lk-color-danger)] mb-[var(--lk-space-sm)]">{{ fout }}</p>
    <p v-if="laden" data-testid="rm-laden" class="text-[var(--lk-color-text-muted)]">Laden…</p>

    <section class="card" data-testid="rm-sectie">
      <h2 class="mb-[var(--lk-space-sm)]">Aangeboden modellen</h2>

      <table class="w-full text-[length:var(--lk-text-sm)]" data-testid="rm-tabel">
        <thead>
          <tr class="text-left text-[var(--lk-color-text-muted)]">
            <th class="py-[var(--lk-space-xs)]">Label</th>
            <th>Versie</th>
            <th>Herkomst</th>
            <th>Status</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="optie in gesorteerd"
            :key="optie.id"
            :data-testid="`rm-rij-${optie.id}`"
            class="border-t border-[var(--lk-color-border)]"
            :class="optie.actief ? '' : 'opacity-50'"
          >
            <td class="py-[var(--lk-space-xs)] font-medium">{{ optie.label }}</td>
            <td>{{ optie.versie }}</td>
            <td class="max-w-md text-[length:var(--lk-text-xs)] text-[var(--lk-color-text-muted)]">{{ optie.herkomst }}</td>
            <td>
              <Tag :data-testid="`rm-status-${optie.id}`" :value="optie.actief ? 'Actief' : 'Gedeactiveerd'" :severity="optie.actief ? 'success' : 'secondary'" />
            </td>
            <td class="text-right">
              <div v-if="magBeheren" class="flex items-center justify-end gap-[var(--lk-space-xs)]">
                <Button label="Bewerken" severity="secondary" :data-testid="`rm-bewerk-${optie.id}`" @click="openBewerken(optie)" />
                <Button v-if="optie.actief" label="Deactiveren" severity="danger" :data-testid="`rm-deactiveer-${optie.id}`" @click="vraagDeactiveren(optie)" />
                <Button v-else label="Reactiveren" :data-testid="`rm-reactiveer-${optie.id}`" @click="reactiveer(optie)" />
              </div>
            </td>
          </tr>
          <tr v-if="!gesorteerd.length && !laden">
            <td colspan="5" data-testid="rm-leeg" class="py-[var(--lk-space-sm)] text-[var(--lk-color-text-muted)]">
              Geen modellen in het aanbod. Modellen komen mee met een release van LIKARA.
            </td>
          </tr>
        </tbody>
      </table>
    </section>

    <!-- Bewerken -->
    <Dialog v-model:visible="editOpen" modal :closable="false" header="Referentiemodel bewerken" data-testid="rm-edit-dialog">
      <form class="flex flex-col gap-[var(--lk-space-md)] min-w-[24rem]" data-testid="rm-edit-form" @submit.prevent="bevestigBewerken">
        <dl class="grid grid-cols-[max-content_1fr] gap-x-[var(--lk-space-md)] gap-y-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]">
          <dt class="font-semibold">Sleutel</dt>
          <dd data-testid="rm-edit-sleutel-readonly" class="font-mono">{{ editOptie?.optie_sleutel }}</dd>
          <dt class="font-semibold">Versie</dt>
          <dd>{{ editOptie?.versie }}</dd>
          <dt class="font-semibold">Herkomst</dt>
          <dd class="max-w-prose">{{ editOptie?.herkomst }}</dd>
        </dl>
        <p class="text-[length:var(--lk-text-xs)] text-[var(--lk-color-text-muted)]">
          Sleutel, versie en herkomst zijn de gecureerde identiteit van het model en liggen vast
          (een nieuwe modelversie komt mee met een release).
        </p>
        <div class="flex flex-col gap-[var(--lk-space-xs)]">
          <label for="rm-edit-label" class="font-semibold">Label *</label>
          <input id="rm-edit-label" v-model="editForm.label" type="text" data-testid="rm-edit-label" :aria-invalid="!!editFouten.label" class="lk-veld" />
          <span v-if="editFouten.label" role="alert" data-testid="rm-edit-fout-label" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ editFouten.label }}</span>
        </div>
        <div class="flex flex-col gap-[var(--lk-space-xs)]">
          <label for="rm-edit-volgorde" class="font-semibold">Volgorde</label>
          <input id="rm-edit-volgorde" v-model="editForm.volgorde" type="number" data-testid="rm-edit-volgorde" class="lk-veld w-32" />
        </div>
        <div class="flex gap-[var(--lk-space-md)]">
          <Button type="submit" label="Opslaan" data-testid="rm-edit-opslaan" :disabled="bezig" />
          <Button type="button" label="Annuleren" severity="secondary" @click="editOpen = false" />
        </div>
      </form>
    </Dialog>

    <!-- Deactiveren -->
    <Dialog v-model:visible="deactOpen" modal header="Referentiemodel deactiveren" data-testid="rm-deact-dialog">
      <p class="mb-[var(--lk-space-sm)] max-w-prose">
        "{{ deactOptie?.label }}" uit het aanbod halen? Tenants kunnen het dan niet meer (opnieuw)
        inlezen; wat al is ingelezen blijft gewoon staan.
      </p>
      <div class="flex gap-[var(--lk-space-md)]">
        <Button label="Deactiveren" severity="danger" data-testid="rm-deact-bevestig" :disabled="bezig" @click="bevestigDeactiveren" />
        <Button label="Annuleren" severity="secondary" @click="deactOpen = false" />
      </div>
    </Dialog>
  </section>
</template>
