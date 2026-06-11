<script setup>
/**
 * ContractSectie — gekoppelde contracten van één applicatie (in ApplicatieDetail).
 *
 * Secties-in-detail-patroon (CD003/CD004). Toont de app→contracten-lijst (CD041) met
 * per rij rol-wijzigen (uit de actieve `relatie_rol`-opties) en ontkoppelen. "Contract
 * koppelen"-Dialog met verplichte rol; 409 `KOPPELING_BESTAAT` als nette fout. Het
 * register voedt de engine niet (ADR-020 Besluit 9/10) → alleen de sectie ververst.
 */
import { computed, onMounted, reactive, ref } from 'vue'
import { Button, Dialog, useToast } from '@/primevue'
import { useAuthStore } from '@/store/auth'
import { api } from '@/api'
import { CONTRACTTYPE, REGISTER_FOUT, label } from '../labels'

const props = defineProps({ applicatieId: { type: String, required: true } })
const auth = useAuthStore()
const toast = useToast()
const mag = computed(() => auth.hasRole('medewerker', 'beheerder'))

const items = ref([])
// §3 — 'valt onder'-conventie (model garandeert geen uniciteit: 0, 1 of meer).
const valtOnder = computed(() => items.value.filter((r) => r.relatie_rol === 'valt_onder'))
const laden = ref(false)
const fout = ref(null)

const contracten = ref([])
const rolOpties = ref([])
const dialogOpen = ref(false)
const bezig = ref(false)
const eersteVeld = ref(null)
let laatsteTrigger = null

const form = reactive({ contract_id: '', relatie_rol: '' })
const fouten = reactive({})

function _toastFout(e) {
  const detail =
    e?.code && REGISTER_FOUT[e.code]
      ? e?.message || REGISTER_FOUT[e.code]
      : { 403: 'Geen rechten voor deze actie.', 404: 'Niet gevonden.', 409: e?.message || 'Conflict.' }[e?.status] ||
        e?.message ||
        'Er ging iets mis.'
  toast.add({ severity: 'error', summary: 'Fout', detail, life: 5000 })
}

async function laad() {
  laden.value = true
  fout.value = null
  try {
    items.value = await api.applicaties.contracten(props.applicatieId)
  } catch (e) {
    fout.value = e?.message || 'Laden van gekoppelde contracten mislukt.'
  } finally {
    laden.value = false
  }
}

// Rol-opties zijn bij eerste render al nodig voor de inline rol-select per rij.
async function _zorgRolOpties() {
  if (rolOpties.value.length) return
  try {
    rolOpties.value = (await api.contractconfig.opties()).relatie_rol || []
  } catch (e) {
    _toastFout(e)
  }
}

async function _laadBronnenEenmalig() {
  await _zorgRolOpties()
  if (!contracten.value.length) {
    try {
      const p = await api.contracten.lijst({ limit: 100 })
      contracten.value = p.items
    } catch (e) {
      _toastFout(e)
    }
  }
}

function _reset() {
  Object.assign(form, { contract_id: '', relatie_rol: '' })
  Object.keys(fouten).forEach((k) => delete fouten[k])
}

async function openKoppelen(e) {
  laatsteTrigger = e?.currentTarget ?? null
  await _laadBronnenEenmalig()
  _reset()
  dialogOpen.value = true
}
function focusEerste() {
  setTimeout(() => {
    const el = eersteVeld.value?.$el ?? eersteVeld.value
    el?.focus?.()
  }, 0)
}
function onHide() {
  laatsteTrigger?.focus?.()
}

function valideer() {
  Object.keys(fouten).forEach((k) => delete fouten[k])
  if (!form.contract_id) fouten.contract_id = 'Kies een contract.'
  if (!form.relatie_rol) fouten.relatie_rol = 'Kies een rol.'
  return Object.keys(fouten).length === 0
}

async function koppel() {
  if (!valideer()) return
  bezig.value = true
  try {
    await api.applicatieContracten.maak({
      applicatie_id: props.applicatieId,
      contract_id: form.contract_id,
      relatie_rol: form.relatie_rol,
    })
    toast.add({ severity: 'success', summary: 'Gekoppeld', life: 3000 })
    dialogOpen.value = false
    await laad()
  } catch (e) {
    _toastFout(e)
  } finally {
    bezig.value = false
  }
}

async function wijzigRol(rij, event) {
  const nieuw = event.target.value
  try {
    await api.applicatieContracten.werkBij(rij.koppeling_id, { relatie_rol: nieuw })
    toast.add({ severity: 'success', summary: 'Rol gewijzigd', life: 2500 })
    await laad()
  } catch (e) {
    _toastFout(e)
    await laad() // herstel de getoonde waarde bij fout
  }
}

const verwijderOpen = ref(false)
const teOntkoppelen = ref(null)
function vraagOntkoppel(e, rij) {
  laatsteTrigger = e?.currentTarget ?? null
  teOntkoppelen.value = rij
  verwijderOpen.value = true
}
async function bevestigOntkoppel() {
  bezig.value = true
  try {
    await api.applicatieContracten.verwijder(teOntkoppelen.value.koppeling_id)
    toast.add({ severity: 'success', summary: 'Ontkoppeld', life: 3000 })
    verwijderOpen.value = false
    await laad()
  } catch (e) {
    _toastFout(e)
  } finally {
    bezig.value = false
  }
}

const typeLabel = (c) => label(CONTRACTTYPE, c)

onMounted(() => Promise.all([laad(), _zorgRolOpties()]))

// §5 — het context-paneel bij categorie 8 hergebruikt deze al geladen koppeling-state.
defineExpose({ items, laad })
</script>

<template>
  <section class="card" aria-labelledby="sectie-contracten">
    <div class="flex items-center gap-[var(--cd-space-md)] mb-[var(--cd-space-sm)]">
      <h2 id="sectie-contracten" class="text-[length:var(--cd-text-lg)] font-semibold">Contracten</h2>
      <Button v-if="mag" label="Contract koppelen" size="small" data-testid="ct-koppelen" class="ml-auto" @click="openKoppelen" />
    </div>

    <p v-if="fout" role="alert" data-testid="ct-fout" class="text-[var(--cd-color-danger)] mb-[var(--cd-space-sm)]">{{ fout }}</p>

    <!-- §3 — 'valt onder'-samenvatting boven de tabel -->
    <p data-testid="ct-valt-onder" class="mb-[var(--cd-space-sm)] text-[length:var(--cd-text-sm)]">
      <template v-if="valtOnder.length">
        <span class="font-semibold">Valt onder:</span>
        <span v-for="(r, i) in valtOnder" :key="r.koppeling_id">
          <router-link :to="{ name: 'contract-detail', params: { id: r.contract_id } }" class="text-[var(--cd-color-primary)] hover:underline">{{ r.contractnaam }}</router-link>
          ({{ r.leverancier_naam }}){{ i < valtOnder.length - 1 ? ', ' : '' }}
        </span>
      </template>
      <span v-else class="text-[var(--cd-color-text-muted)]">Geen valt-onder-contract geregistreerd.</span>
    </p>

    <table v-if="items.length" class="w-full text-[length:var(--cd-text-sm)]" data-testid="ct-tabel">
      <thead>
        <tr class="text-left text-[var(--cd-color-text-muted)]">
          <th class="py-[var(--cd-space-xs)]">Contract</th>
          <th>Leverancier</th>
          <th>Type</th>
          <th>Rol</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="rij in items" :key="rij.koppeling_id" class="border-t border-[var(--cd-color-border)]">
          <td class="py-[var(--cd-space-xs)]">
            <router-link :to="{ name: 'contract-detail', params: { id: rij.contract_id } }" class="text-[var(--cd-color-primary)] hover:underline">{{ rij.contractnaam }}</router-link>
          </td>
          <td>{{ rij.leverancier_naam }}</td>
          <td>{{ typeLabel(rij.contracttype) }}</td>
          <td>
            <select
              v-if="mag"
              :value="rij.relatie_rol"
              :data-testid="`ct-rol-${rij.koppeling_id}`"
              :aria-label="`Rol van ${rij.contractnaam}`"
              class="rounded-[var(--cd-radius-input)] border border-[var(--cd-color-border)] px-[var(--cd-space-sm)] py-[var(--cd-space-xs)] bg-white"
              @change="(e) => wijzigRol(rij, e)"
            >
              <option v-for="o in rolOpties" :key="o.optie_sleutel" :value="o.optie_sleutel">{{ o.label }}</option>
              <option v-if="!rolOpties.some((o) => o.optie_sleutel === rij.relatie_rol)" :value="rij.relatie_rol">{{ rij.relatie_rol_label }}</option>
            </select>
            <span v-else>{{ rij.relatie_rol_label }}</span>
          </td>
          <td class="text-right">
            <Button v-if="mag" label="Ontkoppelen" size="small" severity="danger" :data-testid="`ct-ontkoppel-${rij.koppeling_id}`" @click="(e) => vraagOntkoppel(e, rij)" />
          </td>
        </tr>
      </tbody>
    </table>
    <p v-else-if="!laden" data-testid="ct-leeg" class="text-[var(--cd-color-text-muted)]">Nog geen gekoppelde contracten.</p>

    <Dialog v-model:visible="dialogOpen" modal :closable="false" header="Contract koppelen" data-testid="ct-dialog" @show="focusEerste" @hide="onHide">
      <form class="flex flex-col gap-[var(--cd-space-md)] min-w-[22rem]" data-testid="ct-form" @submit.prevent="koppel">
        <div class="flex flex-col gap-[var(--cd-space-xs)]">
          <label for="ct-contract" class="font-semibold">Contract *</label>
          <select id="ct-contract" ref="eersteVeld" v-model="form.contract_id" data-testid="ct-veld-contract" :aria-invalid="!!fouten.contract_id" class="rounded-[var(--cd-radius-input)] border border-[var(--cd-color-border)] px-[var(--cd-space-sm)] py-[var(--cd-space-xs)] bg-white">
            <option value="" disabled>— kies een contract —</option>
            <option v-for="c in contracten" :key="c.id" :value="c.id">{{ c.contractnaam }} — {{ c.leverancier_naam }}</option>
          </select>
          <span v-if="fouten.contract_id" role="alert" data-testid="ct-fout-contract" class="text-[var(--cd-color-danger)] text-[length:var(--cd-text-sm)]">{{ fouten.contract_id }}</span>
        </div>
        <div class="flex flex-col gap-[var(--cd-space-xs)]">
          <label for="ct-rol" class="font-semibold">Rol *</label>
          <select id="ct-rol" v-model="form.relatie_rol" data-testid="ct-veld-rol" :aria-invalid="!!fouten.relatie_rol" class="rounded-[var(--cd-radius-input)] border border-[var(--cd-color-border)] px-[var(--cd-space-sm)] py-[var(--cd-space-xs)] bg-white">
            <option value="" disabled>— kies een rol —</option>
            <option v-for="o in rolOpties" :key="o.optie_sleutel" :value="o.optie_sleutel">{{ o.label }}</option>
          </select>
          <span v-if="fouten.relatie_rol" role="alert" data-testid="ct-fout-rol" class="text-[var(--cd-color-danger)] text-[length:var(--cd-text-sm)]">{{ fouten.relatie_rol }}</span>
        </div>
        <div class="flex gap-[var(--cd-space-md)]">
          <Button type="submit" label="Koppelen" data-testid="ct-opslaan" :disabled="bezig" />
          <Button type="button" label="Annuleren" severity="secondary" @click="dialogOpen = false" />
        </div>
      </form>
    </Dialog>

    <Dialog v-model:visible="verwijderOpen" modal header="Contract ontkoppelen" data-testid="ct-ontkoppel-dialog" @hide="onHide">
      <p class="mb-[var(--cd-space-md)] max-w-prose">Deze koppeling met <strong>{{ teOntkoppelen?.contractnaam }}</strong> verwijderen? Het contract zelf blijft bestaan.</p>
      <div class="flex justify-end gap-[var(--cd-space-md)]">
        <Button label="Annuleren" severity="secondary" @click="verwijderOpen = false" />
        <Button label="Ontkoppelen" severity="danger" data-testid="ct-ontkoppel-bevestig" :disabled="bezig" @click="bevestigOntkoppel" />
      </div>
    </Dialog>
  </section>
</template>
