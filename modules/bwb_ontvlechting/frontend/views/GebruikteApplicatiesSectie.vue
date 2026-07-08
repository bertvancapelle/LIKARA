<script setup>
/**
 * GebruikteApplicatiesSectie (LI033 → ADR-041) — één gedeelde read-only sectie "Gebruikte componenten"
 * voor ZOWEL een organisatie als een afdeling, op ÉÉN bron per niveau (blok en Landschapskaart mogen
 * nooit uiteenlopen):
 *   - niveau="organisatie" → `api.organisatiegebruik.lijstVoorOrganisatie` (het grove feit, grof-only
 *     incluis; per component de `verfijnd`-vlag).
 *   - niveau="afdeling"    → `api.gebruikersgroepen.contextComponenten` (de bestaande afleiding uit de
 *     groepen van deze afdeling; de afdeling ís hier zélf de verfijning → geen "nog niet verfijnd").
 * Beide leveren dezelfde rij-vorm {component_id, component_naam, componenttype[, verfijnd]}.
 *
 * ADR-041 slice 2 — de sectie heet vast "Gebruikte componenten" (component-breed; de read was dat al).
 * Op organisatieniveau kan de gebruiker kiezen welke componenttypen hij als "gebruikt" meerekent en die
 * keuze vastleggen als zijn persoonlijke standaard ("Sla mijn voorkeur op", slice-1-voorkeur
 * `gebruikte_componenttypen`). Baseline zonder voorkeur = alleen `applicatie`.
 *
 * HERBRUIKBAAR "onthoud als mijn standaard"-patroon (slice 4 kan dit 1-op-1 hergebruiken voor
 * ringen/diepte/kleur): één selectie-ref (`geselecteerd`) + één opgeslagen-standaard-ref (`opgeslagen`)
 * + `gewijzigd`-computed (selectie ≠ opgeslagen) → de opslaan-actie is alléén actief bij afwijking;
 * opslaan = PUT van de héle selectie, alles-weggehaald = herroep (DELETE) terug naar baseline.
 */
import { computed, onMounted, ref, watch } from 'vue'
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
    ? 'Deze organisatie gebruikt nog geen componenten.'
    : 'Deze afdeling gebruikt nog geen componenten.',
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
    fout.value = e?.status === 401 ? null : e?.message || 'Laden van gebruikte componenten mislukt.'
    items.value = []
  } finally {
    laden.value = false
  }
}

// Herlaadt bij een wissel van onderwerp (partij-detail → partij-detail hergebruikt de instance).
watch(() => [props.niveau, props.organisatieId, props.afdelingId], laad, { immediate: true })

// ── ADR-041 slice 2 — persoonlijke voorkeur "gebruikte componenttypen" ──────────────────────────
const VOORKEUR_SLEUTEL = 'gebruikte_componenttypen'
const BASELINE_TYPEN = ['applicatie'] // baseline zonder voorkeur (huidig gedrag)
const typeCatalogus = ref([]) // [{ optie_sleutel, label }] uit /componenten/opties
const geselecteerd = ref(new Set()) // de huidige (bewerkbare) keuze
const opgeslagen = ref(new Set()) // de opgeslagen standaard (voor de gewijzigd-/status-indicatie)
const voorkeurFout = ref(null)
const voorkeurBezig = ref(false)

const _setGelijk = (a, b) => a.size === b.size && [...a].every((x) => b.has(x))
const gewijzigd = computed(() => !_setGelijk(geselecteerd.value, opgeslagen.value))

// ADR-041 slice 2 (herzien) — de voorkeur is een KIJKFILTER: op organisatieniveau tonen we alleen de
// rijen waarvan het componenttype in de LIVE geselecteerde set zit (directe preview, ook vóór opslaan).
// Op afdelingsniveau (geen control) geen filter. De read blijft eerlijk component-breed; dit filtert
// alleen de weergave. `verborgenAantal` = wat buiten de huidige kijk-scope valt (nooit verzwegen).
const zichtbareItems = computed(() =>
  isOrganisatie.value ? items.value.filter((c) => geselecteerd.value.has(c.componenttype)) : items.value,
)
const verborgenAantal = computed(() => items.value.length - zichtbareItems.value.length)

function toggleType(sleutel) {
  const s = new Set(geselecteerd.value)
  s.has(sleutel) ? s.delete(sleutel) : s.add(sleutel)
  geselecteerd.value = s
}

async function laadVoorkeur() {
  if (!isOrganisatie.value) return
  // Catalogus + opgeslagen voorkeur fail-soft laden: onbereikbaar → baseline, de sectie-lijst blijft werken.
  try {
    const opties = await api.componenten.opties()
    typeCatalogus.value = opties?.componenttype || []
  } catch {
    typeCatalogus.value = []
  }
  let typen = BASELINE_TYPEN
  try {
    const alle = await api.voorkeuren.haalAlle()
    const rij = (alle || []).find((v) => v.voorkeur_sleutel === VOORKEUR_SLEUTEL)
    const t = rij?.waarde?.typen
    if (Array.isArray(t) && t.length) typen = t
  } catch {
    /* geen voorkeur bereikbaar → baseline */
  }
  opgeslagen.value = new Set(typen)
  geselecteerd.value = new Set(typen)
}
onMounted(laadVoorkeur)

async function slaVoorkeurOp() {
  if (!gewijzigd.value || voorkeurBezig.value) return
  voorkeurBezig.value = true
  voorkeurFout.value = null
  try {
    const typen = [...geselecteerd.value]
    if (typen.length) {
      await api.voorkeuren.zet(VOORKEUR_SLEUTEL, { typen })
      opgeslagen.value = new Set(typen)
    } else {
      // Alles weggehaald = herroepen → voorkeur weg, terug naar baseline (geen aparte wis-actie).
      await api.voorkeuren.herroep(VOORKEUR_SLEUTEL)
      opgeslagen.value = new Set(BASELINE_TYPEN)
      geselecteerd.value = new Set(BASELINE_TYPEN)
    }
  } catch (e) {
    voorkeurFout.value = e?.message || 'Opslaan van je voorkeur mislukt.'
  } finally {
    voorkeurBezig.value = false
  }
}

function toonOpKaart() {
  // Toont wat je nú ziet (de kijk-scope), zodat kaart en sectie niet uiteenlopen.
  if (!zichtbareItems.value.length) return
  zetKaartHandoff({
    componentIds: zichtbareItems.value.map((c) => c.component_id),
    // Grof-only (nog niet verfijnd) → de kaart markeert deze rustig. Op afdelingsniveau leeg.
    grofOnlyIds: zichtbareItems.value.filter((c) => c.verfijnd === false).map((c) => c.component_id),
  })
  router.push({ name: 'landschapskaart' })
}
</script>

<template>
  <section class="card" aria-labelledby="sectie-gebruikte-componenten" data-testid="gebruikte-applicaties-sectie">
    <div class="flex items-center gap-[var(--lk-space-md)] mb-[var(--lk-space-sm)]">
      <h2 id="sectie-gebruikte-componenten" class="text-[length:var(--lk-text-lg)] font-semibold">Gebruikte componenten</h2>
      <Button
        v-if="zichtbareItems.length"
        label="Toon op de landschapskaart"
        severity="secondary"
        data-testid="ga-toon-kaart"
        class="ml-auto"
        @click="toonOpKaart"
      />
    </div>

    <!-- ADR-041 slice 2 — "onthoud als mijn standaard": kies welke componenttypen als gebruikt tellen. -->
    <div
      v-if="isOrganisatie"
      data-testid="ga-voorkeur"
      class="mb-[var(--lk-space-md)] flex flex-col gap-[var(--lk-space-xs)] rounded-[var(--lk-radius-card)] border border-[var(--lk-color-border)] bg-[var(--lk-color-accent)]/20 p-[var(--lk-space-sm)]"
    >
      <p class="text-[length:var(--lk-text-sm)] font-semibold">Welke componenttypen tel ik als gebruikt</p>
      <div class="flex flex-wrap gap-[var(--lk-space-sm)]">
        <label
          v-for="t in typeCatalogus"
          :key="t.optie_sleutel"
          class="flex items-center gap-[var(--lk-space-xs)] text-[length:var(--lk-text-sm)]"
        >
          <input
            type="checkbox"
            :checked="geselecteerd.has(t.optie_sleutel)"
            :data-testid="`ga-type-${t.optie_sleutel}`"
            @change="toggleType(t.optie_sleutel)"
          />{{ t.label }}
        </label>
      </div>
      <div class="flex items-center gap-[var(--lk-space-sm)]">
        <button
          type="button"
          data-testid="ga-voorkeur-opslaan"
          :disabled="!gewijzigd || voorkeurBezig"
          class="rounded-[var(--lk-radius-btn)] bg-[var(--lk-color-primary)] px-[var(--lk-space-md)] py-1 text-[length:var(--lk-text-sm)] text-white disabled:cursor-not-allowed disabled:opacity-50"
          @click="slaVoorkeurOp"
        >Sla mijn voorkeur op</button>
        <span
          data-testid="ga-voorkeur-status"
          :class="['text-[length:var(--lk-text-xs)]', gewijzigd ? 'text-[var(--lk-color-warning,#b45309)]' : 'text-[var(--lk-color-text-muted)]']"
        >{{ gewijzigd ? 'Gewijzigd — nog niet opgeslagen' : 'Je standaard' }}</span>
      </div>
      <p data-testid="ga-voorkeur-hint" class="text-[length:var(--lk-text-xs)] text-[var(--lk-color-text-muted)]">
        Dit is je eigen kijkfilter — het bepaalt alleen wat je standaard ziet, niet wat er geregistreerd is. Verbreed om alles te zien.
      </p>
      <p v-if="voorkeurFout" role="alert" data-testid="ga-voorkeur-fout" class="text-[length:var(--lk-text-xs)] text-[var(--lk-color-danger)]">{{ voorkeurFout }}</p>
    </div>

    <p v-if="fout" role="alert" data-testid="ga-fout" class="text-[var(--lk-color-danger)] mb-[var(--lk-space-sm)]">{{ fout }}</p>

    <p v-if="laden && !items.length" data-testid="ga-laden" class="text-[var(--lk-color-text-muted)]">Laden…</p>

    <template v-else>
      <ul v-if="zichtbareItems.length" class="flex flex-col gap-[var(--lk-space-xs)]" data-testid="ga-lijst">
        <li
          v-for="c in zichtbareItems"
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
          <!-- Grof-only: de organisatie gebruikt dit component, maar er is nog geen afdeling/groep als
               verfijning. Alleen op organisatieniveau (op afdelingsniveau ís de afdeling de verfijning). -->
          <Tag
            v-if="isOrganisatie && c.verfijnd === false"
            value="Nog niet verfijnd"
            severity="warning"
            :data-testid="`ga-grofonly-${c.component_id}`"
            class="ml-auto"
          />
        </li>
      </ul>

      <!-- Er zijn gebruikte componenten BUITEN de huidige kijk-scope: eerlijk benoemen náást de lijst
           (nooit verzwijgen; de gebruiker verbreedt hierboven om ze te zien). Alleen op organisatieniveau. -->
      <p
        v-if="verborgenAantal > 0"
        data-testid="ga-buiten-scope"
        :class="['text-[length:var(--lk-text-sm)] text-[var(--lk-color-text-muted)]', zichtbareItems.length ? 'mt-[var(--lk-space-xs)] italic' : '']"
      >{{ verborgenAantal }} gebruikt component{{ verborgenAantal === 1 ? '' : 'en' }} buiten je huidige kijk-scope — verbreed hierboven om {{ verborgenAantal === 1 ? 'het' : 'ze' }} te zien.</p>

      <p v-if="!items.length" data-testid="ga-leeg" class="text-[var(--lk-color-text-muted)]">{{ legeTekst }}</p>
    </template>
  </section>
</template>
