<script setup>
/**
 * GapLijstView — migratielaag (ADR-023 Fase E/F): lijst + aanmaken van gaps.
 * Leunt op `GET /gaps` (keyset) + `POST /gaps`. "+ Nieuwe gap" (rol-gegate op GAP·AANMAKEN)
 * opent een dialog: naam + toelichting + een verplicht baseline-plateau (vertreksituatie) en
 * doel-plateau (eindsituatie), beide via een zoekveld. Na opslaan naar het nieuwe gap-detail.
 */
import { computed, onMounted, reactive, ref } from 'vue'
import { Button, Column, DataTable, Dialog, InputText, Textarea, useToast } from '@/primevue'
import { useRouter } from '@/composables/router'
import { useAuthStore } from '@/store/auth'
import { api } from '@/api'
import VeldUitleg from '@modules/bwb_ontvlechting/frontend/views/VeldUitleg.vue'
import ZoekSelect from '@modules/bwb_ontvlechting/frontend/views/ZoekSelect.vue'

const router = useRouter()
const toast = useToast()
const auth = useAuthStore()
const magAanmaken = computed(() => auth.hasRole('medewerker', 'beheerder'))

const items = ref([])
const cursor = ref(null)
const laden = ref(false)
const fout = ref(null)
const eersteGeladen = ref(false)

async function laad({ reset = false } = {}) {
  laden.value = true
  fout.value = null
  try {
    const pagina = await api.gaps.lijst({ limit: 25, after: reset ? undefined : cursor.value })
    items.value = reset ? pagina.items : items.value.concat(pagina.items)
    cursor.value = pagina.volgende_cursor
  } catch (e) {
    fout.value = e?.status === 401 ? null : e?.message || 'Er ging iets mis bij het laden van de gaps.'
  } finally {
    laden.value = false
    eersteGeladen.value = true
  }
}

// ── Nieuwe gap ─────────────────────────────────────────────────────────────────
const nieuwOpen = ref(false)
const bezig = ref(false)
const form = reactive({ naam: '', toelichting: '', baseline_plateau_id: '', doel_plateau_id: '' })
const fouten = reactive({})
const zoekPlateaus = (params) => api.plateaus.lijst(params)

function openNieuw() {
  Object.assign(form, { naam: '', toelichting: '', baseline_plateau_id: '', doel_plateau_id: '' })
  Object.keys(fouten).forEach((k) => delete fouten[k])
  nieuwOpen.value = true
}
function valideer() {
  Object.keys(fouten).forEach((k) => delete fouten[k])
  if (!form.naam.trim()) fouten.naam = 'Naam is verplicht.'
  if (!form.baseline_plateau_id) fouten.baseline_plateau_id = 'Kies een baseline-plateau (vertreksituatie).'
  if (!form.doel_plateau_id) fouten.doel_plateau_id = 'Kies een doel-plateau (eindsituatie).'
  if (form.baseline_plateau_id && form.baseline_plateau_id === form.doel_plateau_id)
    fouten.doel_plateau_id = 'Baseline en doel mogen niet hetzelfde plateau zijn.'
  return Object.keys(fouten).length === 0
}
async function bevestigNieuw() {
  if (!valideer()) return
  bezig.value = true
  try {
    const g = await api.gaps.maak({
      naam: form.naam.trim(),
      toelichting: form.toelichting.trim() || null,
      baseline_plateau_id: form.baseline_plateau_id,
      doel_plateau_id: form.doel_plateau_id,
    })
    toast.add({ severity: 'success', summary: 'Gap aangemaakt', life: 3000 })
    nieuwOpen.value = false
    router.push({ name: 'gap-detail', params: { id: g.id } })
  } catch (e) {
    if (e?.code === 'BASELINE_GELIJK_AAN_DOEL') {
      fouten.doel_plateau_id = 'Baseline en doel mogen niet hetzelfde plateau zijn.'
    } else if (e?.code === 'ONGELDIG_PLATEAU') {
      fouten.baseline_plateau_id = 'Baseline en doel moeten een plateau zijn.'
    } else if (e?.status === 422 && Array.isArray(e.detail)) {
      for (const d of e.detail) {
        const veld = Array.isArray(d.loc) ? d.loc[d.loc.length - 1] : null
        if (veld && veld in form) fouten[veld] = d.msg
      }
    } else {
      toast.add({ severity: 'error', summary: 'Fout', detail: e?.message || 'Er ging iets mis.', life: 5000 })
    }
  } finally {
    bezig.value = false
  }
}

onMounted(() => laad({ reset: true }))
</script>

<template>
  <section aria-labelledby="gaps-titel">
    <div class="mb-[var(--lk-space-md)] flex items-center gap-[var(--lk-space-md)]">
      <h1 id="gaps-titel" class="text-[var(--lk-color-primary)]">Gaps</h1>
      <Button v-if="magAanmaken" label="+ Nieuwe gap" data-testid="gap-nieuw" class="ml-auto" @click="openNieuw" />
    </div>

    <p
      v-if="fout"
      role="alert"
      data-testid="gap-lijst-fout"
      class="mb-[var(--lk-space-md)] rounded-[var(--lk-radius-badge)] border border-[var(--lk-color-danger)] bg-[var(--lk-color-danger)]/10 px-[var(--lk-space-md)] py-[var(--lk-space-sm)] text-[var(--lk-color-danger)]"
    >
      {{ fout }}
    </p>

    <DataTable :value="items" data-testid="gaps-tabel" class="bg-[var(--lk-color-surface)] rounded-[var(--lk-radius-card)] shadow-[var(--lk-shadow-sm)]">
      <Column field="naam" header="Naam">
        <template #body="{ data }">
          <router-link
            :to="{ name: 'gap-detail', params: { id: data.id } }"
            data-testid="gap-link"
            class="text-[var(--lk-color-primary)] font-medium hover:underline focus:outline-2 focus:outline-offset-2 focus:outline-[var(--lk-color-primary)]"
          >
            {{ data.naam }}
          </router-link>
        </template>
      </Column>
      <Column header="Toelichting">
        <template #body="{ data }">
          <span class="block max-w-[40ch] truncate" :title="data.toelichting || ''">{{ data.toelichting || '—' }}</span>
        </template>
      </Column>
      <template #empty>
        <span v-if="eersteGeladen && !laden" data-testid="gap-lijst-leeg">
          Nog geen gaps.
          <template v-if="magAanmaken">Maak de eerste gap aan met “+ Nieuwe gap”.</template>
        </span>
        <span v-else>Laden…</span>
      </template>
    </DataTable>

    <div class="mt-[var(--lk-space-md)]">
      <Button v-if="cursor" label="Meer laden" severity="secondary" data-testid="meer-laden" :disabled="laden" @click="laad()" />
    </div>

    <Dialog v-model:visible="nieuwOpen" modal :closable="false" header="Nieuwe gap" data-testid="gap-nieuw-dialog">
      <form class="flex flex-col gap-[var(--lk-space-md)] min-w-[26rem]" data-testid="gap-nieuw-form" @submit.prevent="bevestigNieuw">
        <div class="flex flex-col gap-[var(--lk-space-xs)]">
          <label for="gn-naam" class="font-semibold">Naam *</label>
          <div class="flex items-center gap-[var(--lk-space-xs)]">
            <InputText id="gn-naam" v-model="form.naam" data-testid="gn-naam" :aria-invalid="!!fouten.naam" class="flex-1" />
            <VeldUitleg veld="gap" />
          </div>
          <span v-if="fouten.naam" role="alert" data-testid="gn-fout-naam" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ fouten.naam }}</span>
        </div>
        <div class="flex flex-col gap-[var(--lk-space-xs)]">
          <label for="gn-toelichting" class="font-semibold">Toelichting</label>
          <Textarea id="gn-toelichting" v-model="form.toelichting" rows="2" data-testid="gn-toelichting" />
        </div>
        <div class="flex flex-col gap-[var(--lk-space-xs)]">
          <label for="gn-baseline" class="font-semibold">Baseline-plateau (vertreksituatie) *</label>
          <ZoekSelect id="gn-baseline" testid="gn-baseline-zoek" v-model="form.baseline_plateau_id" :zoek-functie="zoekPlateaus" :invalid="!!fouten.baseline_plateau_id" placeholder="Zoek een plateau…" />
          <span v-if="fouten.baseline_plateau_id" role="alert" data-testid="gn-fout-baseline" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ fouten.baseline_plateau_id }}</span>
        </div>
        <div class="flex flex-col gap-[var(--lk-space-xs)]">
          <label for="gn-doel" class="font-semibold">Doel-plateau (eindsituatie) *</label>
          <ZoekSelect id="gn-doel" testid="gn-doel-zoek" v-model="form.doel_plateau_id" :zoek-functie="zoekPlateaus" :invalid="!!fouten.doel_plateau_id" placeholder="Zoek een plateau…" />
          <span v-if="fouten.doel_plateau_id" role="alert" data-testid="gn-fout-doel" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ fouten.doel_plateau_id }}</span>
        </div>
        <div class="flex gap-[var(--lk-space-md)]">
          <Button type="submit" label="Aanmaken" data-testid="gn-opslaan" :disabled="bezig" />
          <Button type="button" label="Annuleren" severity="secondary" @click="nieuwOpen = false" />
        </div>
      </form>
    </Dialog>
  </section>
</template>
