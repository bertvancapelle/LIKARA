<script setup>
/**
 * ImpactSectie — read-only impactanalyse (ADR-021 Besluit 10 / Fase E).
 *
 * Vanaf één component: wie steunt — direct of transitief — op dít component
 * (`api.componenten.impact`). Toont de contracten op de bron, een samenvatting en een
 * toegankelijke tabel van geraakte componenten (naam · type · niveau · relatie ·
 * lifecycle · open blokkades) met rij-navigatie (subtypen → ApplicatieDetail). Het pad
 * staat als title/uitklap bij niveau > 1. Volledig read-only: géén acties, géén
 * schrijf-affordances, géén engine-koppeling. De tabel is de waarheidsbron (geen graaf).
 */
import { ref } from 'vue'
import { Button, Column, DataTable, Tag } from '@/primevue'
import { detailRoute } from '@/detailIngang'
import { api } from '@/api'
import { LIFECYCLE, LIFECYCLE_SEVERITY, label } from '../labels'

const props = defineProps({ componentId: { type: String, required: true } })

const data = ref(null)
const laden = ref(false)
const fout = ref(null)
const geladen = ref(false)

async function analyseer() {
  laden.value = true
  fout.value = null
  try {
    data.value = await api.componenten.impact(props.componentId)
    geladen.value = true
  } catch (e) {
    fout.value = e?.status === 401 ? null : e?.message || 'Impactanalyse mislukt.'
  } finally {
    laden.value = false
  }
}

// LI059 Slice 4 — één detailscherm voor élk type.
function rijRoute(rij) {
  return detailRoute('component', rij.component_id)
}
const lifecycleLabel = (c) => label(LIFECYCLE, c)
const lifecycleSeverity = (c) => LIFECYCLE_SEVERITY[c] || 'info'
</script>

<template>
  <section class="card" aria-labelledby="sectie-impact">
    <div class="flex items-center gap-[var(--lk-space-md)] mb-[var(--lk-space-sm)]">
      <h2 id="sectie-impact" class="text-[length:var(--lk-text-lg)] font-semibold">Impactanalyse</h2>
      <Button label="Impactanalyse" data-testid="im-analyseer" class="ml-auto" :disabled="laden" @click="analyseer" />
    </div>

    <p v-if="fout" role="alert" data-testid="im-fout" class="text-[var(--lk-color-danger)] mb-[var(--lk-space-sm)]">{{ fout }}</p>

    <p v-if="!geladen && !laden" data-testid="im-uitleg" class="text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]">
      Toont welke componenten — direct of transitief — op dit component steunen.
    </p>

    <template v-if="geladen && data">
      <!-- Contracten op de bron (compact) -->
      <p data-testid="im-contracten" class="mb-[var(--lk-space-sm)] text-[length:var(--lk-text-sm)]">
        <span class="font-semibold">Contracten op dit component:</span>
        <template v-if="data.contracten.length">
          <span v-for="(c, i) in data.contracten" :key="c.koppeling_id">
            {{ c.contractnaam }} ({{ c.leverancier_naam }}, {{ c.relatie_rol_label }}){{ i < data.contracten.length - 1 ? ', ' : '' }}
          </span>
        </template>
        <span v-else class="text-[var(--lk-color-text-muted)]"> geen.</span>
      </p>

      <!-- Samenvatting -->
      <p data-testid="im-samenvatting" class="mb-[var(--lk-space-sm)] text-[length:var(--lk-text-sm)]">
        <strong>{{ data.samenvatting.aantal_geraakt }}</strong> component(en) afhankelijk —
        waarvan <strong>{{ data.samenvatting.aantal_applicaties }}</strong> applicatie(s),
        <strong>{{ data.samenvatting.aantal_geblokkeerd }}</strong> geblokkeerd.
      </p>

      <DataTable v-if="data.geraakt.length" :value="data.geraakt" data-testid="im-tabel">
        <Column header="Component">
          <template #body="{ data: r }">
            <router-link :to="rijRoute(r)" class="text-[var(--lk-color-primary)] hover:underline">{{ r.naam }}</router-link>
          </template>
        </Column>
        <Column header="Type"><template #body="{ data: r }"><Tag :value="r.componenttype_label" :severity="r.lifecycle_status != null ? 'info' : 'secondary'" /></template></Column>
        <Column header="Niveau">
          <template #body="{ data: r }">
            <span :data-testid="`im-niveau-${r.component_id}`" :title="r.niveau > 1 ? 'Pad: ' + r.pad.join(' → ') : null">{{ r.niveau }}</span>
          </template>
        </Column>
        <Column header="Relatie"><template #body="{ data: r }">{{ r.relatietype_label }}</template></Column>
        <Column header="Status">
          <template #body="{ data: r }">
            <Tag v-if="r.lifecycle_status != null" :value="lifecycleLabel(r.lifecycle_status)" :severity="lifecycleSeverity(r.lifecycle_status)" />
            <span v-else>—</span>
          </template>
        </Column>
        <Column header="Open blokkades"><template #body="{ data: r }">{{ r.open_blokkades != null ? r.open_blokkades : '—' }}</template></Column>
        <!-- Pad uitgeklapt bij niveau > 1 (uitlegbaarheid van de keten) -->
        <Column header="Pad">
          <template #body="{ data: r }">
            <span v-if="r.niveau > 1" :data-testid="`im-pad-${r.component_id}`" class="text-[length:var(--lk-text-xs)] text-[var(--lk-color-text-muted)]">{{ r.pad.join(' → ') }}</span>
            <span v-else>—</span>
          </template>
        </Column>
      </DataTable>
      <p v-else data-testid="im-leeg" class="text-[var(--lk-color-text-muted)] text-[length:var(--lk-text-sm)]">
        Geen componenten afhankelijk van dit component.
      </p>
    </template>
  </section>
</template>
