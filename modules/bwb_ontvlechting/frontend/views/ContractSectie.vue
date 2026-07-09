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
import BevestigVerwijderDialog from '@/components/BevestigVerwijderDialog.vue'
import { CONTRACTTYPE, REGISTER_FOUT, label } from '../labels'
import ZoekSelect from './ZoekSelect.vue'

const props = defineProps({
  applicatieId: { type: String, required: true },
  appNaam: { type: String, default: '' }, // LI026 — voor de contractketen-breadcrumb
})
const auth = useAuthStore()
const toast = useToast()
const mag = computed(() => auth.hasRole('medewerker', 'beheerder'))

const items = ref([])
// §3 — 'valt onder'-conventie (model garandeert geen uniciteit: 0, 1 of meer).
const valtOnder = computed(() => items.value.filter((r) => r.relatie_rol === 'valt_onder'))
// LI026 — contractketen (bottom-up): contracten van deze app die onder een mantelcontract vallen.
const ketens = computed(() => items.value.filter((r) => r.mantelcontract_id))
const laden = ref(false)
const fout = ref(null)

// Contract-keuze: server-side zoeken (CD049) i.p.v. de volledige lijst vooraf laden.
const zoekContracten = (params) => api.contracten.lijst(params)
const contractWeergave = (c) => `${c.contractnaam} — ${c.leverancier_naam}`
const rolOpties = ref([])
const dialogOpen = ref(false)
const bezig = ref(false)
const eersteVeld = ref(null)
let laatsteTrigger = null

const form = reactive({ contract_id: '', relatie_rol: '' })
const fouten = reactive({})

function _toastFout(e) {
  if (e?.status === 401) return // sessie verlopen — centrale vangrail leidt al naar login
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
    items.value = await api.componenten.contracten(props.applicatieId)
    await laadDekking()
  } catch (e) {
    fout.value = e?.status === 401 ? null : e?.message || 'Laden van gekoppelde contracten mislukt.'
  } finally {
    laden.value = false
  }
}

// ── ADR-030 — per-band (component↔contract) dekking ──────────────────────────────
const dekking = reactive({}) // contract_id → {contract_breed, per_band, per_band_sleutels, toon_per_band}
const dekkingOpties = ref([]) // catalogus dimensie=dekking (voor de bewerk-multiselect)
const bewerkContractId = ref(null)
const bewerkSleutels = ref([])

async function laadDekking() {
  const contracten = [...new Set(items.value.map((r) => r.contract_id))]
  await Promise.all(contracten.map(async (cid) => {
    try { dekking[cid] = await api.contracten.bandDekking.ophalen(cid, props.applicatieId) }
    catch { /* dekking optioneel; de koppeling-rij blijft bruikbaar */ }
  }))
}
async function _zorgDekkingOpties() {
  if (dekkingOpties.value.length) return
  try { dekkingOpties.value = (await api.contractconfig.opties()).dekking || [] } catch (e) { _toastFout(e) }
}
async function bewerkBandDekking(rij) {
  await _zorgDekkingOpties()
  bewerkSleutels.value = [...(dekking[rij.contract_id]?.per_band_sleutels || [])]
  bewerkContractId.value = rij.contract_id
}
function toggleDekkingSleutel(s) {
  const i = bewerkSleutels.value.indexOf(s)
  if (i >= 0) bewerkSleutels.value.splice(i, 1)
  else bewerkSleutels.value.push(s)
}
async function slaBandDekkingOp(rij) {
  try {
    await api.contracten.bandDekking.instellen(rij.contract_id, props.applicatieId, bewerkSleutels.value)
    dekking[rij.contract_id] = await api.contracten.bandDekking.ophalen(rij.contract_id, props.applicatieId)
    bewerkContractId.value = null
    toast.add({ severity: 'success', summary: 'Dekking opgeslagen', life: 2500 })
  } catch (e) { _toastFout(e) }
}
// LI035 regel-acties-patroon — terugzetten naar de algemene dekking vraagt bevestiging
// (de per-band-registratie verdwijnt; de gedeelde BevestigVerwijderDialog toont dat leesbaar).
const bandTerugOpen = ref(false)
const bandTerugRij = ref(null)
const bandTerugBezig = ref(false)
function vraagBandDekkingTerug(rij) {
  bandTerugRij.value = rij
  bandTerugOpen.value = true
}
async function bevestigBandDekkingTerug() {
  const rij = bandTerugRij.value
  bandTerugBezig.value = true
  try {
    await api.contracten.bandDekking.verwijderen(rij.contract_id, props.applicatieId)
    dekking[rij.contract_id] = await api.contracten.bandDekking.ophalen(rij.contract_id, props.applicatieId)
    bewerkContractId.value = null
    bandTerugOpen.value = false
    toast.add({ severity: 'success', summary: 'Terug naar algemene dekking', life: 2500 })
  } catch (e) {
    bandTerugOpen.value = false
    _toastFout(e)
  } finally {
    bandTerugBezig.value = false
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
  await _zorgRolOpties() // rol-select blijft native (catalogus); contract via ZoekSelect.
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
  setTimeout(() => eersteVeld.value?.focus?.(), 0) // ZoekSelect exposeert focus()
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
    await api.componentContracten.maak({
      component_id: props.applicatieId,  // shared-PK: applicatie-id == component-id
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
    await api.componentContracten.werkBij(rij.koppeling_id, { relatie_rol: nieuw })
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
    await api.componentContracten.verwijder(teOntkoppelen.value.koppeling_id)
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
defineExpose({ items, laad, dekking, dekkingOpties, bewerkContractId, bewerkSleutels, bewerkBandDekking, slaBandDekkingOp, vraagBandDekkingTerug, bevestigBandDekkingTerug })
</script>

<template>
  <section class="card" aria-labelledby="sectie-contracten">
    <div class="flex items-center gap-[var(--lk-space-md)] mb-[var(--lk-space-sm)]">
      <h2 id="sectie-contracten" class="text-[length:var(--lk-text-lg)] font-semibold">Contracten</h2>
      <Button v-if="mag" label="Contract koppelen" severity="secondary" data-testid="ct-koppelen" class="ml-auto" @click="openKoppelen" />
    </div>

    <p v-if="fout" role="alert" data-testid="ct-fout" class="text-[var(--lk-color-danger)] mb-[var(--lk-space-sm)]">{{ fout }}</p>

    <!-- §3 — 'valt onder'-samenvatting boven de tabel -->
    <p data-testid="ct-valt-onder" class="mb-[var(--lk-space-sm)] text-[length:var(--lk-text-sm)]">
      <template v-if="valtOnder.length">
        <span class="font-semibold">Valt onder:</span>
        <span v-for="(r, i) in valtOnder" :key="r.koppeling_id">
          <router-link :to="{ name: 'contract-detail', params: { id: r.contract_id } }" class="text-[var(--lk-color-primary)] hover:underline">{{ r.contractnaam }}</router-link>
          ({{ r.leverancier_naam }}){{ i < valtOnder.length - 1 ? ', ' : '' }}
        </span>
      </template>
      <span v-else class="text-[var(--lk-color-text-muted)]">Geen valt-onder-contract geregistreerd.</span>
    </p>

    <!-- LI026 — contractketen App → Contract → Mantelcontract (alleen contracten met een mantel). -->
    <div v-if="ketens.length" data-testid="ct-ketens" class="mb-[var(--lk-space-sm)] flex flex-col gap-0.5 text-[length:var(--lk-text-sm)]">
      <p v-for="r in ketens" :key="r.koppeling_id" :data-testid="`ct-keten-${r.koppeling_id}`" class="flex flex-wrap items-center gap-1">
        <template v-if="appNaam"><span class="font-semibold">{{ appNaam }}</span><span class="text-[var(--lk-color-text-muted)]">→</span></template>
        <router-link :to="{ name: 'contract-detail', params: { id: r.contract_id } }" class="text-[var(--lk-color-primary)] hover:underline">{{ r.contractnaam }}</router-link>
        <span class="text-[var(--lk-color-text-muted)]">→</span>
        <router-link :to="{ name: 'contract-detail', params: { id: r.mantelcontract_id } }" class="text-[var(--lk-color-primary)] hover:underline">{{ r.mantelcontract_naam || 'mantelcontract' }}</router-link>
      </p>
    </div>

    <table v-if="items.length" class="w-full text-[length:var(--lk-text-sm)]" data-testid="ct-tabel">
      <thead>
        <tr class="text-left text-[var(--lk-color-text-muted)]">
          <th class="py-[var(--lk-space-xs)]">Contract</th>
          <th>Leverancier</th>
          <th>Type</th>
          <th>Rol</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="rij in items" :key="rij.koppeling_id" class="border-t border-[var(--lk-color-border)]">
          <td class="py-[var(--lk-space-xs)]">
            <router-link :to="{ name: 'contract-detail', params: { id: rij.contract_id } }" class="text-[var(--lk-color-primary)] hover:underline">{{ rij.contractnaam }}</router-link>
            <!-- ADR-030 — dekking: algemeen (contract-breed) + per-band (alleen als afwijkend). -->
            <div class="mt-0.5 flex flex-col gap-0.5 text-[length:var(--lk-text-xs)] text-[var(--lk-color-text-muted)]">
              <span v-if="dekking[rij.contract_id]?.contract_breed?.length" :data-testid="`ct-dekking-breed-${rij.koppeling_id}`">
                Algemene dekking: {{ dekking[rij.contract_id].contract_breed.join(' · ') }}
              </span>
              <span v-if="dekking[rij.contract_id]?.toon_per_band" :data-testid="`ct-dekking-band-${rij.koppeling_id}`" class="text-[var(--lk-color-text)]">
                Dekking voor dit component: {{ dekking[rij.contract_id].per_band.join(' · ') }}
              </span>
              <button
                v-if="mag && bewerkContractId !== rij.contract_id"
                type="button"
                :data-testid="`ct-dekking-bewerk-${rij.koppeling_id}`"
                class="self-start text-[var(--lk-color-primary)] hover:underline"
                @click="bewerkBandDekking(rij)"
              >Dekking aanpassen</button>
              <!-- Inline bewerken: multiselect uit de dekking-catalogus -->
              <div v-if="bewerkContractId === rij.contract_id" :data-testid="`ct-dekking-editor-${rij.koppeling_id}`" class="mt-0.5 flex flex-col gap-0.5 text-[var(--lk-color-text)]">
                <label v-for="o in dekkingOpties" :key="o.optie_sleutel" class="flex items-center gap-1">
                  <input
                    type="checkbox"
                    :data-testid="`ct-dekking-optie-${rij.koppeling_id}-${o.optie_sleutel}`"
                    :checked="bewerkSleutels.includes(o.optie_sleutel)"
                    @change="toggleDekkingSleutel(o.optie_sleutel)"
                  />{{ o.label }}
                </label>
                <div class="mt-0.5 flex flex-wrap gap-2">
                  <button type="button" :data-testid="`ct-dekking-opslaan-${rij.koppeling_id}`" class="text-[var(--lk-color-primary)] hover:underline" @click="slaBandDekkingOp(rij)">Opslaan</button>
                  <button type="button" :data-testid="`ct-dekking-terug-${rij.koppeling_id}`" class="text-[var(--lk-color-text-muted)] hover:underline" @click="vraagBandDekkingTerug(rij)">Terug naar algemene dekking</button>
                  <button type="button" :data-testid="`ct-dekking-annuleer-${rij.koppeling_id}`" class="text-[var(--lk-color-text-muted)] hover:underline" @click="bewerkContractId = null">Annuleren</button>
                </div>
              </div>
            </div>
          </td>
          <td>{{ rij.leverancier_naam }}</td>
          <td>{{ typeLabel(rij.contracttype) }}</td>
          <td>
            <select
              v-if="mag"
              :value="rij.relatie_rol"
              :data-testid="`ct-rol-${rij.koppeling_id}`"
              :aria-label="`Rol van ${rij.contractnaam}`"
              class="rounded-[var(--lk-radius-input)] border border-[var(--lk-color-border)] px-[var(--lk-space-sm)] py-[var(--lk-space-xs)] bg-white"
              @change="(e) => wijzigRol(rij, e)"
            >
              <option v-for="o in rolOpties" :key="o.optie_sleutel" :value="o.optie_sleutel">{{ o.label }}</option>
              <option v-if="!rolOpties.some((o) => o.optie_sleutel === rij.relatie_rol)" :value="rij.relatie_rol">{{ rij.relatie_rol_label }}</option>
            </select>
            <span v-else>{{ rij.relatie_rol_label }}</span>
          </td>
          <td class="text-right">
            <Button v-if="mag" label="Ontkoppelen" severity="danger" :data-testid="`ct-ontkoppel-${rij.koppeling_id}`" @click="(e) => vraagOntkoppel(e, rij)" />
          </td>
        </tr>
      </tbody>
    </table>
    <p v-else-if="!laden" data-testid="ct-leeg" class="text-[var(--lk-color-text-muted)]">Nog geen gekoppelde contracten.</p>

    <Dialog v-model:visible="dialogOpen" modal :closable="false" header="Contract koppelen" data-testid="ct-dialog" @show="focusEerste" @hide="onHide">
      <form class="flex flex-col gap-[var(--lk-space-md)] min-w-[22rem]" data-testid="ct-form" @submit.prevent="koppel">
        <div class="flex flex-col gap-[var(--lk-space-xs)]">
          <label for="ct-contract" class="font-semibold">Contract *</label>
          <ZoekSelect
            id="ct-contract"
            ref="eersteVeld"
            testid="ct-veld-contract"
            v-model="form.contract_id"
            :zoek-functie="zoekContracten"
            :weergave="contractWeergave"
            :invalid="!!fouten.contract_id"
            placeholder="Zoek een contract…"
          />
          <span v-if="fouten.contract_id" role="alert" data-testid="ct-fout-contract" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ fouten.contract_id }}</span>
        </div>
        <div class="flex flex-col gap-[var(--lk-space-xs)]">
          <label for="ct-rol" class="font-semibold">Rol *</label>
          <select id="ct-rol" v-model="form.relatie_rol" data-testid="ct-veld-rol" :aria-invalid="!!fouten.relatie_rol" class="rounded-[var(--lk-radius-input)] border border-[var(--lk-color-border)] px-[var(--lk-space-sm)] py-[var(--lk-space-xs)] bg-white">
            <option value="" disabled>— kies een rol —</option>
            <option v-for="o in rolOpties" :key="o.optie_sleutel" :value="o.optie_sleutel">{{ o.label }}</option>
          </select>
          <span v-if="fouten.relatie_rol" role="alert" data-testid="ct-fout-rol" class="text-[var(--lk-color-danger)] text-[length:var(--lk-text-sm)]">{{ fouten.relatie_rol }}</span>
        </div>
        <div class="flex gap-[var(--lk-space-md)]">
          <Button type="submit" label="Koppelen" data-testid="ct-opslaan" :disabled="bezig" />
          <Button type="button" label="Annuleren" severity="secondary" @click="dialogOpen = false" />
        </div>
      </form>
    </Dialog>

    <Dialog v-model:visible="verwijderOpen" modal header="Contract ontkoppelen" data-testid="ct-ontkoppel-dialog" @hide="onHide">
      <p class="mb-[var(--lk-space-md)] max-w-prose">Deze koppeling met <strong>{{ teOntkoppelen?.contractnaam }}</strong> verwijderen? Het contract zelf blijft bestaan.</p>
      <div class="flex justify-end gap-[var(--lk-space-md)]">
        <Button label="Annuleren" severity="secondary" @click="verwijderOpen = false" />
        <Button label="Ontkoppelen" severity="danger" data-testid="ct-ontkoppel-bevestig" :disabled="bezig" @click="bevestigOntkoppel" />
      </div>
    </Dialog>

    <!-- Band-dekking terugzetten — gedeelde bevestiging (LI035 regel-acties-patroon). -->
    <BevestigVerwijderDialog
      v-model:visible="bandTerugOpen"
      kop="Terug naar algemene dekking"
      :omschrijving="bandTerugRij ? `De specifieke dekking van deze koppeling met ${bandTerugRij.contractnaam || 'dit contract'} vervalt; daarna geldt weer de algemene contract-dekking.` : ''"
      bevestig-label="Terugzetten"
      :bezig="bandTerugBezig"
      testid="ct-dekking-terugzetten"
      @bevestig="bevestigBandDekkingTerug"
    />
  </section>
</template>
