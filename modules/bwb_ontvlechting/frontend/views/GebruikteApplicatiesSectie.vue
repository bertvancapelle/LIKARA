<script setup>
/**
 * GebruikteApplicatiesSectie (LI033) — één gedeelde, read-only sectie "Gebruikte applicaties" voor
 * ZOWEL een organisatie als een afdeling, op ÉÉN bron per niveau (blok en Landschapskaart mogen nooit
 * uiteenlopen):
 *   - niveau="organisatie" → `api.organisatiegebruik.lijstVoorOrganisatie` (het grove feit, grof-only
 *     incluis; per applicatie de `verfijnd`-vlag).
 *   - niveau="afdeling"    → `api.gebruikersgroepen.contextComponenten` (de bestaande afleiding uit de
 *     groepen van deze afdeling; de afdeling ís hier zélf de verfijning → geen "nog niet verfijnd").
 * Beide leveren dezelfde rij-vorm {component_id, component_naam, componenttype[, verfijnd]}.
 *
 * Read-only: koppelen gebeurt elders (op de applicatie). Hier lezen + doorklikken naar de applicatie,
 * plus "Toon op de landschapskaart" (opent exact déze set — zelfde bron, zelfde selectie).
 */
import { computed, ref, watch } from 'vue'
import { Button, Tag } from '@/primevue'
import { useRouter } from '@/composables/router'
import { api } from '@/api'
import { zetKaartHandoff } from '@/composables/kaartHandoff'
import { humaniseer } from '../labels'

const props = defineProps({
  // 'organisatie' | 'afdeling'
  niveau: { type: String, required: true },
  // De organisatie-partij-id (verplicht op beide niveaus).
  organisatieId: { type: String, required: true },
  // De afdeling-partij-id (alleen op niveau 'afdeling').
  afdelingId: { type: String, default: null },
})

const router = useRouter()
const items = ref([])
const laden = ref(false)
const fout = ref(null)

const isOrganisatie = computed(() => props.niveau === 'organisatie')
const heeftGrofOnly = computed(() => items.value.some((c) => c.verfijnd === false))
const legeTekst = computed(() =>
  isOrganisatie.value
    ? 'Deze organisatie gebruikt nog geen applicaties.'
    : 'Deze afdeling gebruikt nog geen applicaties.',
)

async function laad() {
  if (!props.organisatieId) return
  laden.value = true
  fout.value = null
  try {
    items.value = isOrganisatie.value
      ? await api.organisatiegebruik.lijstVoorOrganisatie({ organisatie_id: props.organisatieId })
      : await api.gebruikersgroepen.contextComponenten({
          organisatie_id: props.organisatieId,
          afdeling_id: props.afdelingId || undefined,
        })
  } catch (e) {
    // 401 → centrale vangrail leidt al naar login; nooit een rauwe code tonen.
    fout.value = e?.status === 401 ? null : e?.message || 'Laden van gebruikte applicaties mislukt.'
    items.value = []
  } finally {
    laden.value = false
  }
}

// Herlaadt bij een wissel van onderwerp (partij-detail → partij-detail hergebruikt de instance).
watch(() => [props.niveau, props.organisatieId, props.afdelingId], laad, { immediate: true })

function toonOpKaart() {
  if (!items.value.length) return
  zetKaartHandoff({
    componentIds: items.value.map((c) => c.component_id),
    // Grof-only (nog niet verfijnd) → de kaart markeert deze rustig. Op afdelingsniveau leeg.
    grofOnlyIds: items.value.filter((c) => c.verfijnd === false).map((c) => c.component_id),
  })
  router.push({ name: 'landschapskaart' })
}
</script>

<template>
  <section class="card" aria-labelledby="sectie-gebruikte-applicaties" data-testid="gebruikte-applicaties-sectie">
    <div class="flex items-center gap-[var(--lk-space-md)] mb-[var(--lk-space-sm)]">
      <h2 id="sectie-gebruikte-applicaties" class="text-[length:var(--lk-text-lg)] font-semibold">Gebruikte applicaties</h2>
      <Button
        v-if="items.length"
        label="Toon op de landschapskaart"
        severity="secondary"
        data-testid="ga-toon-kaart"
        class="ml-auto"
        @click="toonOpKaart"
      />
    </div>

    <p v-if="fout" role="alert" data-testid="ga-fout" class="text-[var(--lk-color-danger)] mb-[var(--lk-space-sm)]">{{ fout }}</p>

    <p v-if="laden && !items.length" data-testid="ga-laden" class="text-[var(--lk-color-text-muted)]">Laden…</p>

    <ul v-else-if="items.length" class="flex flex-col gap-[var(--lk-space-xs)]" data-testid="ga-lijst">
      <li
        v-for="c in items"
        :key="c.component_id"
        :data-testid="`ga-item-${c.component_id}`"
        class="flex items-center gap-[var(--lk-space-sm)] text-[length:var(--lk-text-sm)]"
      >
        <router-link
          :to="{ name: 'component-detail', params: { id: c.component_id } }"
          :data-testid="`ga-link-${c.component_id}`"
          class="text-[var(--lk-color-primary)] hover:underline"
        >{{ c.component_naam }}</router-link>
        <span class="text-[var(--lk-color-text-muted)]">{{ humaniseer(c.componenttype) }}</span>
        <!-- Grof-only: de organisatie gebruikt deze applicatie, maar er is nog geen afdeling/groep
             als verfijning. Alleen op organisatieniveau (op afdelingsniveau ís de afdeling de verfijning). -->
        <Tag
          v-if="isOrganisatie && c.verfijnd === false"
          value="Nog niet verfijnd"
          severity="warning"
          :data-testid="`ga-grofonly-${c.component_id}`"
          class="ml-auto"
        />
      </li>
    </ul>

    <p v-else data-testid="ga-leeg" class="text-[var(--lk-color-text-muted)]">{{ legeTekst }}</p>
  </section>
</template>
