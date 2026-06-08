<script setup>
/**
 * KoppelingenkaartView — tenant-brede relatiekaart (CD023, #13, ADR-018).
 *
 * Gefocuste ego-graaf: één geselecteerde applicatie centraal, met links de
 * inkomende koppelingen (leveranciers, bron → deze) en rechts de uitgaande
 * (ontvangers, deze → doel). Een buur aanklikken hercentreert. Hand-rolled SVG,
 * geen graaf-library (ADR-018); data uit de bestaande per-richting
 * koppelingenlijst (CD020, levert `tegenpartij_naam`) + de applicatielijst.
 *
 * Toegankelijkheid: de SVG is `role="img"` met samenvattende `aria-label`; de
 * toetsenbord-/screenreader-toegankelijke waarheidsbron is de relatietabel
 * eronder (Inkomend/Uitgaand via AppTabs). Beide ontsluiten dezelfde data.
 * `--cd-`-tokens, geen `<style>`.
 */
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Tag } from '@/primevue'
import { api } from '@/api'
import AppTabs from '@modules/bwb_ontvlechting/frontend/views/AppTabs.vue'
import {
  IMPACT_SEVERITY,
  IMPACT_VERBREKING,
  KOPPELPROTOCOL,
  KOPPELRICHTING,
  LIFECYCLE,
  LIFECYCLE_SEVERITY,
  label,
} from '@modules/bwb_ontvlechting/frontend/labels'

const route = useRoute()
const router = useRouter()

const applicaties = ref([])
const geselecteerd = ref(null) // app-id
const uitgaand = ref([]) // deze app = bron; tegenpartij = doel
const inkomend = ref([]) // deze app = doel; tegenpartij = bron
const laden = ref(false)
const fout = ref(null)
const actieveLijst = ref('uitgaand')

// Alle pagina's ophalen (keyset-cursor). Veiligheidslimiet tegen een onverwachte lus.
async function _allePaginas(fetchFn, params) {
  const items = []
  let after
  for (let i = 0; i < 200; i++) {
    const p = await fetchFn({ ...params, limit: 100, after })
    items.push(...p.items)
    if (!p.volgende_cursor) break
    after = p.volgende_cursor
  }
  return items
}

const geselecteerdeApp = computed(
  () => applicaties.value.find((a) => a.id === geselecteerd.value) || null,
)

async function laadRelaties() {
  if (!geselecteerd.value) {
    uitgaand.value = []
    inkomend.value = []
    return
  }
  laden.value = true
  fout.value = null
  try {
    const [uit, ink] = await Promise.all([
      _allePaginas(api.koppelingen.lijst, { bronApplicatieId: geselecteerd.value }),
      _allePaginas(api.koppelingen.lijst, { doelApplicatieId: geselecteerd.value }),
    ])
    uitgaand.value = uit
    inkomend.value = ink
  } catch (e) {
    fout.value = e?.message || 'Laden van de relaties mislukt.'
  } finally {
    laden.value = false
  }
}

function selecteer(id) {
  if (id) geselecteerd.value = id
}

// Deep-link: ?app=<id> (deelbaar/herlaadbaar); router.replace → geen history-spam.
watch(geselecteerd, (id) => {
  const huidig = route.query.app != null ? String(route.query.app) : undefined
  if (huidig !== (id ?? undefined)) router.replace({ query: id ? { app: id } : {} })
  laadRelaties()
})

onMounted(async () => {
  laden.value = true
  try {
    applicaties.value = await _allePaginas(api.applicaties.lijst, {})
  } catch (e) {
    fout.value = e?.message || 'Laden van applicaties mislukt.'
  } finally {
    laden.value = false
  }
  const q = route.query.app != null ? String(route.query.app) : null
  geselecteerd.value = applicaties.value.some((a) => a.id === q)
    ? q
    : (applicaties.value[0]?.id ?? null)
})

// ── Relatietabel (toegankelijke waarheidsbron) ───────────────────────────────
const lijstTabs = computed(() => [
  { key: 'uitgaand', label: `Uitgaand (${uitgaand.value.length})` },
  { key: 'inkomend', label: `Inkomend (${inkomend.value.length})` },
])
const actieveRelaties = computed(() =>
  actieveLijst.value === 'uitgaand' ? uitgaand.value : inkomend.value,
)
// Tegenpartij-id verschilt per richting (uitgaand → doel, inkomend → bron).
const tegenpartijId = (rij) =>
  actieveLijst.value === 'uitgaand' ? rij.doel_applicatie_id : rij.bron_applicatie_id

// ── Ego-graaf SVG ────────────────────────────────────────────────────────────
const MAX_ZICHTBAAR = 12 // per kolom in de SVG; de rest staat in de tabel
const NODE_H = 40
const NODE_GAP = 14
const NODE_B = 180
const SVG_B = 640
const X_LINKS = 10
const X_CENTER = 230
const X_RECHTS = 450

const inkomendZichtbaar = computed(() => inkomend.value.slice(0, MAX_ZICHTBAAR))
const uitgaandZichtbaar = computed(() => uitgaand.value.slice(0, MAX_ZICHTBAAR))
const rijen = computed(() =>
  Math.max(inkomendZichtbaar.value.length, uitgaandZichtbaar.value.length, 1),
)
const svgHoogte = computed(() => NODE_GAP + rijen.value * (NODE_H + NODE_GAP))
const centerY = computed(() => svgHoogte.value / 2 - NODE_H / 2)
const rijY = (i) => NODE_GAP + i * (NODE_H + NODE_GAP)
const kort = (s, n = 24) => (s && s.length > n ? `${s.slice(0, n - 1)}…` : s || '')

const svgLabel = computed(() =>
  geselecteerdeApp.value
    ? `Relatiekaart voor ${geselecteerdeApp.value.naam}: ${inkomend.value.length} inkomend, ${uitgaand.value.length} uitgaand`
    : 'Relatiekaart',
)
</script>

<template>
  <section aria-labelledby="kaart-titel">
    <h1
      id="kaart-titel"
      class="mb-[var(--cd-space-md)] text-[length:var(--cd-text-2xl)] font-semibold text-[var(--cd-color-primary)]"
    >
      Koppelingenkaart
    </h1>

    <label class="mb-[var(--cd-space-md)] flex flex-col gap-[var(--cd-space-xs)] max-w-[28rem]">
      <span class="text-[length:var(--cd-text-sm)] font-semibold text-[var(--cd-color-text-muted)]">Applicatie</span>
      <select
        v-model="geselecteerd"
        data-testid="kaart-app-select"
        aria-label="Kies een applicatie om de relaties te tonen"
        class="rounded-[var(--cd-radius-input)] border border-[var(--cd-color-border)] bg-white px-[var(--cd-space-sm)] py-[var(--cd-space-xs)] focus:outline-2 focus:outline-offset-2 focus:outline-[var(--cd-color-primary)]"
      >
        <option v-for="a in applicaties" :key="a.id" :value="a.id">{{ a.naam }}</option>
      </select>
    </label>

    <p v-if="fout" role="alert" data-testid="kaart-fout" class="text-[var(--cd-color-danger)]">{{ fout }}</p>
    <p v-else-if="!applicaties.length && !laden" data-testid="kaart-leeg" class="text-[var(--cd-color-text-muted)]">
      Er zijn nog geen applicaties in deze tenant.
    </p>

    <template v-if="geselecteerdeApp">
      <div class="mb-[var(--cd-space-sm)] flex items-center gap-[var(--cd-space-sm)]">
        <h2 class="text-[length:var(--cd-text-lg)] font-semibold">{{ geselecteerdeApp.naam }}</h2>
        <Tag
          :value="label(LIFECYCLE, geselecteerdeApp.lifecycle_status)"
          :severity="LIFECYCLE_SEVERITY[geselecteerdeApp.lifecycle_status] || 'info'"
        />
        <router-link
          :to="{ name: 'applicatie-detail', params: { id: geselecteerdeApp.id } }"
          data-testid="kaart-naar-detail"
          class="ml-auto text-[length:var(--cd-text-sm)] text-[var(--cd-color-primary)] hover:underline focus:outline-2 focus:outline-offset-2 focus:outline-[var(--cd-color-primary)]"
        >
          Naar detail ▸
        </router-link>
      </div>

      <!-- Visuele ego-graaf (verrijking; tabel hieronder is de a11y-waarheidsbron) -->
      <div class="card overflow-x-auto">
        <svg
          :viewBox="`0 0 ${SVG_B} ${svgHoogte}`"
          :height="svgHoogte"
          width="100%"
          role="img"
          :aria-label="svgLabel"
          data-testid="kaart-svg"
          class="min-w-[640px]"
        >
          <defs>
            <marker id="kaart-pijl" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
              <path d="M0,0 L8,4 L0,8 Z" fill="var(--cd-color-text-muted)" />
            </marker>
          </defs>

          <!-- Inkomend (links) → midden -->
          <g v-for="(r, i) in inkomendZichtbaar" :key="`in-${r.id}`">
            <line
              :x1="X_LINKS + NODE_B" :y1="rijY(i) + NODE_H / 2"
              :x2="X_CENTER" :y2="centerY + NODE_H / 2"
              stroke="var(--cd-color-text-muted)" stroke-width="1.5" marker-end="url(#kaart-pijl)"
            />
            <g
              :data-testid="`kaart-node-in-${r.bron_applicatie_id}`"
              class="cursor-pointer"
              @click="selecteer(r.bron_applicatie_id)"
            >
              <rect :x="X_LINKS" :y="rijY(i)" :width="NODE_B" :height="NODE_H" rx="6"
                fill="var(--cd-color-surface)" stroke="var(--cd-color-border)" />
              <text :x="X_LINKS + 10" :y="rijY(i) + NODE_H / 2 + 4" class="text-[length:11px]">{{ kort(r.tegenpartij_naam) }}</text>
            </g>
          </g>

          <!-- Midden (geselecteerde applicatie) -->
          <rect :x="X_CENTER" :y="centerY" :width="NODE_B" :height="NODE_H" rx="6"
            fill="var(--cd-color-accent)" stroke="var(--cd-color-primary)" stroke-width="1.5" />
          <text :x="X_CENTER + NODE_B / 2" :y="centerY + NODE_H / 2 + 4" text-anchor="middle"
            class="text-[length:12px] font-semibold">{{ kort(geselecteerdeApp.naam, 22) }}</text>

          <!-- Midden → uitgaand (rechts) -->
          <g v-for="(r, i) in uitgaandZichtbaar" :key="`uit-${r.id}`">
            <line
              :x1="X_CENTER + NODE_B" :y1="centerY + NODE_H / 2"
              :x2="X_RECHTS" :y2="rijY(i) + NODE_H / 2"
              stroke="var(--cd-color-text-muted)" stroke-width="1.5" marker-end="url(#kaart-pijl)"
            />
            <g
              :data-testid="`kaart-node-uit-${r.doel_applicatie_id}`"
              class="cursor-pointer"
              @click="selecteer(r.doel_applicatie_id)"
            >
              <rect :x="X_RECHTS" :y="rijY(i)" :width="NODE_B" :height="NODE_H" rx="6"
                fill="var(--cd-color-surface)" stroke="var(--cd-color-border)" />
              <text :x="X_RECHTS + 10" :y="rijY(i) + NODE_H / 2 + 4" class="text-[length:11px]">{{ kort(r.tegenpartij_naam) }}</text>
            </g>
          </g>
        </svg>
        <p
          v-if="inkomend.length > MAX_ZICHTBAAR || uitgaand.length > MAX_ZICHTBAAR"
          data-testid="kaart-meer-hint"
          class="mt-[var(--cd-space-xs)] text-[length:var(--cd-text-xs)] text-[var(--cd-color-text-muted)]"
        >
          Niet alle buren passen in de kaart — de volledige lijst staat hieronder.
        </p>
      </div>

      <!-- Toegankelijk alternatief: toetsenbord-navigeerbare relatietabel -->
      <div class="mt-[var(--cd-space-lg)]">
        <AppTabs
          v-model="actieveLijst"
          :tabs="lijstTabs"
          aria-label="Relaties van de geselecteerde applicatie"
          id-prefix="kaartrel"
          class="mb-[var(--cd-space-sm)]"
        />
        <div
          :id="`kaartrel-panel-${actieveLijst}`"
          role="tabpanel"
          :aria-labelledby="`kaartrel-tab-${actieveLijst}`"
        >
          <table class="w-full" data-testid="kaart-relatietabel">
            <thead>
              <tr class="text-left text-[length:var(--cd-text-sm)] text-[var(--cd-color-text-muted)]">
                <th class="py-[var(--cd-space-xs)]">Tegenpartij</th>
                <th>Richting</th>
                <th>Protocol</th>
                <th>Impact</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="r in actieveRelaties" :key="r.id" :data-testid="`kaart-rij-${r.id}`">
                <td class="py-[var(--cd-space-xs)]">
                  <router-link
                    :to="{ name: 'applicatie-detail', params: { id: tegenpartijId(r) } }"
                    class="text-[var(--cd-color-primary)] hover:underline focus:outline-2 focus:outline-offset-2 focus:outline-[var(--cd-color-primary)]"
                  >
                    {{ r.tegenpartij_naam }}
                  </router-link>
                </td>
                <td>{{ label(KOPPELRICHTING, r.richting) }}</td>
                <td>{{ label(KOPPELPROTOCOL, r.protocol) }}</td>
                <td>
                  <Tag
                    :value="label(IMPACT_VERBREKING, r.impact_bij_verbreking)"
                    :severity="IMPACT_SEVERITY[r.impact_bij_verbreking] || 'info'"
                  />
                </td>
                <td>
                  <button
                    type="button"
                    :data-testid="`kaart-hercentreer-${r.id}`"
                    class="text-[length:var(--cd-text-sm)] text-[var(--cd-color-primary)] hover:underline focus:outline-2 focus:outline-offset-2 focus:outline-[var(--cd-color-primary)]"
                    @click="selecteer(tegenpartijId(r))"
                  >
                    Hercentreer
                  </button>
                </td>
              </tr>
              <tr v-if="!actieveRelaties.length">
                <td colspan="5" data-testid="kaart-rel-leeg" class="py-[var(--cd-space-sm)] text-[var(--cd-color-text-muted)]">
                  Geen {{ actieveLijst }}e koppelingen.
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>
  </section>
</template>
