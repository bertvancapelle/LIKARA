<script setup>
/**
 * DeliverableLijstView — migratielaag (ADR-023 Fase E/F): lijst + aanmaken van deliverables.
 * Leunt op `GET /deliverables` (keyset) + `POST /deliverables`. "+ Nieuwe deliverable"
 * (rol-gegate op DELIVERABLE·AANMAKEN) opent een dialog (naam + toelichting) en navigeert na
 * opslaan naar het nieuwe detail.
 */
import { computed, onMounted, reactive, ref } from 'vue'
import { Button, Column, DataTable, Dialog, InputText, Textarea, useToast } from '@/primevue'
import { useRouter } from '@/composables/router'
import { useAuthStore } from '@/store/auth'
import { api } from '@/api'
import VeldUitleg from '@modules/bwb_ontvlechting/frontend/views/VeldUitleg.vue'

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
    const pagina = await api.deliverables.lijst({ limit: 25, after: reset ? undefined : cursor.value })
    items.value = reset ? pagina.items : items.value.concat(pagina.items)
    cursor.value = pagina.volgende_cursor
  } catch (e) {
    fout.value = e?.status === 401 ? null : e?.message || 'Er ging iets mis bij het laden van de deliverables.'
  } finally {
    laden.value = false
    eersteGeladen.value = true
  }
}

// ── Nieuwe deliverable ─────────────────────────────────────────────────────────
const nieuwOpen = ref(false)
const bezig = ref(false)
const form = reactive({ naam: '', toelichting: '' })
const fouten = reactive({})

function openNieuw() {
  Object.assign(form, { naam: '', toelichting: '' })
  Object.keys(fouten).forEach((k) => delete fouten[k])
  nieuwOpen.value = true
}
function valideer() {
  Object.keys(fouten).forEach((k) => delete fouten[k])
  if (!form.naam.trim()) fouten.naam = 'Naam is verplicht.'
  return Object.keys(fouten).length === 0
}
async function bevestigNieuw() {
  if (!valideer()) return
  bezig.value = true
  try {
    const d = await api.deliverables.maak({ naam: form.naam.trim(), toelichting: form.toelichting.trim() || null })
    toast.add({ severity: 'success', summary: 'Deliverable aangemaakt', life: 3000 })
    nieuwOpen.value = false
    router.push({ name: 'deliverable-detail', params: { id: d.id } })
  } catch (e) {
    if (e?.status === 422 && Array.isArray(e.detail)) {
      for (const dd of e.detail) {
        const veld = Array.isArray(dd.loc) ? dd.loc[dd.loc.length - 1] : null
        if (veld && veld in form) fouten[veld] = dd.msg
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
  <section aria-labelledby="del-titel">
    <div class="mb-[var(--lk-space-md)] flex items-center gap-[var(--lk-space-md)]">
      <h1 id="del-titel" class="text-[var(--lk-color-primary)]">
        Deliverables
      </h1>
      <Button v-if="magAanmaken" label="+ Nieuwe deliverable" data-testid="del-nieuw" class="ml-auto" @click="openNieuw" />
    </div>

    <p
      v-if="fout"
      role="alert"
      data-testid="del-lijst-fout"
      class="mb-[var(--lk-space-md)] rounded-[var(--lk-radius-badge)] border border-[var(--lk-color-danger)] bg-[var(--lk-color-danger)]/10 px-[var(--lk-space-md)] py-[var(--lk-space-sm)] text-[var(--lk-color-danger)]"
    >
      {{ fout }}
    </p>

    <DataTable
      :value="items"
      data-testid="del-tabel"
      class="bg-[var(--lk-color-surface)] rounded-[var(--lk-radius-card)] shadow-[var(--lk-shadow-sm)]"
    >
      <Column field="naam" header="Naam">
        <template #body="{ data }">
          <router-link
            :to="{ name: 'deliverable-detail', params: { id: data.id } }"
            data-testid="del-link"
            class="text-[var(--lk-color-primary)] font-medium hover:underline focus:outline-2 focus:outline-offset-2 focus:outline-[var(--lk-color-primary)]"
          >
            {{ data.naam }}
          </router-link>
        </template>
      </Column>
      <Column header="Toelichting">
        <template #body="{ data }">
          <span class="block max-w-[40ch] truncate" :title="data.toelichting || ''">
            {{ data.toelichting || '—' }}
          </span>
        </template>
      </Column>
      <template #empty>
        <span v-if="eersteGeladen && !laden" data-testid="del-lijst-leeg">
          Nog geen deliverables.
          <template v-if="magAanmaken">Maak de eerste deliverable aan met “+ Nieuwe deliverable”.</template>
        </span>
        <span v-else>Laden…</span>
      </template>
    </DataTable>

    <div class="mt-[var(--lk-space-md)]">
      <Button v-if="cursor" label="Meer laden" severity="secondary" data-testid="meer-laden" :disabled="laden" @click="laad()" />
    </div>

    <Dialog v-model:visible="nieuwOpen" modal :closable="false" header="Nieuwe deliverable" data-testid="del-nieuw-dialog">
      <form class="flex flex-col gap-[var(--lk-space-md)] min-w-[24rem]" data-testid="del-nieuw-form" @submit.prevent="bevestigNieuw">
        <div class="flex flex-col gap-[var(--lk-space-xs)]">
          <label for="dl-naam" class="font-semibold">Naam *</label>
          <div class="flex items-center gap-[var(--lk-space-xs)]">
            <InputText id="dl-naam" v-model="form.naam" data-testid="dl-naam" :aria-invalid="!!fouten.naam" class="flex-1" />
            <VeldUitleg veld="deliverable" />
          </div>
          <span v-if="fouten.naam" role="alert" data-testid="dl-fout-naam" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ fouten.naam }}</span>
        </div>
        <div class="flex flex-col gap-[var(--lk-space-xs)]">
          <label for="dl-toelichting" class="font-semibold">Toelichting</label>
          <Textarea id="dl-toelichting" v-model="form.toelichting" rows="3" data-testid="dl-toelichting" />
        </div>
        <div class="flex gap-[var(--lk-space-md)]">
          <Button type="submit" label="Aanmaken" data-testid="dl-opslaan" :disabled="bezig" />
          <Button type="button" label="Annuleren" severity="secondary" @click="nieuwOpen = false" />
        </div>
      </form>
    </Dialog>
  </section>
</template>
