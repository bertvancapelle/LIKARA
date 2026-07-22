# Checkpoint — de drie cross-skill-parkeeritems (READ-ONLY meting)

**Sessie:** LI049 · **Build:** V049 · **Branch:** master · **HEAD:** `3c7268a` · werktree schoon
**Grond:** stap 1 (§Cross-skill-kandidaten, `201092d`) · gate-rapport stap 2 (`558f39d`)
**Datum meting:** 2026-07-22 · Niets gewijzigd behalve dit rapport. Scan groen (5 passed).

De parkeersectie staat op **r520–539** van `likara-tests/SKILL.md` en draagt 5 bullets: 2
afgehandelde verwijzingen uit stap 2 (baseline r522–524, gate r525–527) en de **3 geparkeerde
items** hieronder.

---

## Item 1 — Read-only meting in het gate-rapport (r528–530)

1. **Inhoud:** *"bij een afgeleide read-API meet je de feitelijke dev-stand (welke componenten
   welk signaal, met waarom) via een klein script onder `_run_rls`, en zet je die in het
   gate-rapport zodat Bert de regel op echte data toetst (F-3: 8× `beoordeeld_niet_vastgelegd`)"*.
   Functioneel: een **inhoudseis aan het gate-rapport** bij een read-only-slice. Gebruiker: CC
   op het moment dat hij een gate-rapport voor een afgeleide lees-API schrijft.
2. **Testregel of anders:** werkwijze (wat het gate-rapport draagt), geen testpatroon — al leunt
   de uitvoering op een test-harnas (`_run_rls` komt voor in **35** module-testbestanden).
   **Thuisskill-kandidaat: likara-werkprotocol** — wie een gate-rapport schrijft kijkt daar.
3. **Leeft het daar al?** Nee. Werkprotocol kent 4 gate-rapport-inhoudsplekken (r187 gate-basis ·
   r195–198 dependency-rebuild-eis · r251 "tellingen zijn momentopnamen" · r429
   browsercheck-draaiboek) — déze regel staat er niet bij. Verplaatsen = **toevoegen**, geen
   samenvoegen. Hij sluit inhoudelijk direct aan op r251 (beide over metingen in gate-rapporten).
4. **Landingskop:** twee kandidaten — **§Gate-discipline** (daar staat de zuster-eis
   dependency-rebuild al) of **§Meet tenant-data BINNEN de tenant-context** (de meting-hub,
   direct naast "hermeten of de commit erbij noemen"). Beide bestaand; keuze aan Bert.
5. **Marker:** ✓ eigen — "(V010 Fase F, geverifieerd)" + "(F-3: 8×…)" in de tekst.

## Item 2 — OPVOLGPUNTEN is een tracked bestand + gerichte staging (r531–536)

1. **Inhoud:** OPVOLGPUNTEN.md is een normaal tracked projectbestand (besluit DC011, geverifieerd
   `git ls-files`); de achterhaalde untracked-aanname niet herintroduceren; een
   OPVOLGPUNTEN-wijziging lift niet stil mee in een feature-commit → **gerichte staging** met
   `git diff --cached --stat`-bewijs; afsluit-updates landen in de sessie-afsluit-commit.
   Gebruiker: CC vlak vóór staging/commit.
2. **Testregel of anders:** zuivere **commit-werkwijze**. **Thuisskill-kandidaat:
   likara-werkprotocol §Commit-discipline.**
3. **Leeft het daar al?** Nee — 0 OPVOLGPUNTEN-hits in werkprotocol §Commit-discipline (de 2
   werkprotocol-hits op "OPVOLGPUNTEN" zijn andere regels: r276 correctie-vastlegging, r521
   geen-schuld). **Verwant maar ánders:** CLAUDE.md:450 draagt de
   "Gerichte-staging-uitzondering (noodprocedure, CD055)" — dat is de verstrengelde-werktree-
   casus, niet de OPVOLGPUNTEN-casus. Verplaatsen = **toevoegen**; kanttekening: er staan dan
   twee gerichte-staging-regels in twee bestanden (CLAUDE.md + werkprotocol) — verwante familie,
   geen dubbeling, maar het scheelt één zoekplek. Melden bij het besluit.
4. **Landingskop:** **§Commit-discipline** (bestaand; geen alternatief nodig).
5. **Marker:** ✓ eigen — "(V010 Fase F, geverifieerd)" + "(besluit DC011 — geverifieerd
   `git ls-files`)" in de tekst.

## Item 3 — Dev-ergonomie (r537–539) — het enige item dat splitst

1. **Inhoud, twee halves:** (a) `psql` staat niet op de host → `docker exec lk-postgres psql -U
   lk_admin …` voor read-only metingen (ziet álle tenants); (b) `rm` is geweigerd → opruimen met
   `find <pad> -type f -delete`. Gebruiker: wie een losse meting of opruimactie in de
   dev-omgeving doet — **bediening**, geen testpatroon en geen resilience-eigenschap.
2. **Thuiskandidaat per helft:**
   - **psql-helft → `docs/LOKAAL-TESTEN.md`** — exact wat de LI040-regel (nu werkprotocol
     §Browsercheck) voorschrijft: *"bedieningskennis hoort in de bedieningsdoc"*. Gemeten:
     LOKAAL-TESTEN.md bevat **géén** psql-recept (0 hits) → toevoegen. ⚠ LOKAAL-TESTEN is een
     doc, geen skill: een eventuele verwijzing ernaartoe is **niet scan-bewaakt** (zelfde
     beperking als de CLAUDE.md-verwijzing uit stap 2.4).
   - **rm/find-delete-helft → is al gedekt**: het feit staat **3×** in werkprotocol
     §Browsercheck (r384–386 stap-0-recept · r395–396 glob-les · r414 deny-lijst-noot).
     Verplaatsen zou een vierde kopie maken; deze helft kan alleen netjes weg via
     vervallen-of-samenvoegen = **herformuleren = eigen besluit**.
3. **Leeft al:** zie 2 — helft (b) drievoudig, helft (a) nergens.
4. **Landingskop:** psql-helft → LOKAAL-TESTEN (sectie met metingen/reset; geen skill-kop nodig);
   rm-helft → n.v.t. (al gedekt).
5. **Marker:** ✓ eigen — "(V010 Fase F, geverifieerd)".

---

## Verwijzingen en bewaking

1. **Externe verwijzers naar de drie items: 0.** Repo-brede zoek op de kernfrasen ("Read-only
   meting in het gate-rapport", "NORMAAL TRACKED", "Dev-ergonomie") buiten likara-tests en de
   vastleggingen: geen enkele treffer in levende bronnen of code. Ook de parkeerkop zelf wordt
   alleen in LI049-vastleggingen genoemd.
2. **De scan vangt een verplaatsing van deze drie dus niet** — er ís geen kop-genoemde
   verwijzing die rood kan worden. Keerzijde: er breekt ook niets; de verplaatsing is volledig
   vrij. Onbewaakt handwerk: 0 (niets te raken).
3. **Staat:** `git status` skills schoon · branch `master` · HEAD `3c7268a` · scan **5 passed**.

---

## Twee losse metingen

### 2.3 — force-recreate ↔ resilience §P10

**De stap-2-meting houdt stand.** Tests §Live-DB-tests draagt een *live-testrun-voorwaarde*
("herstart vóór élke live-check ná een codewijziging"); resilience §P10 draagt een
*diagnose-volgorde* ("bij een onverwacht symptoom eerst de goedkope omgevingscheck"). Twee
verschillende vragen op twee logische zoekplekken, met één gedeeld feit (bind-mounts laden geen
code in een draaiend proces). **Uitkomst in één regel: laten staan — geen dubbeling.**

### De `bijgewerkt:`-frontmatter — alle 9 wijken af

| Skill | Frontmatter | Werkelijke laatste inhoud |
|---|---|---|
| likara-db | **V015** | V049 (o.a. LI040-patronen) |
| likara-backend | V040 | V049 |
| likara-resilience | V040 | V049 |
| likara-tests | V042 | **V049 — deze sessie herbouwd** |
| likara-security | V042 | V049 |
| likara-werkprotocol | V042 | **V049 — deze sessie herbouwd** |
| likara-domeinmodel | V043 | V049 — deze sessie geraakt |
| likara-frontend | V043 | V049 — deze sessie geraakt |
| likara-ux | V043 | V049 — deze sessie herordend |

Spreiding V015–V043 tegen huidige build V049; **9 van de 9 verouderd**, waarvan 5 deze sessie
inhoudelijk gewijzigd zonder frontmatter-bump. Niet bijgewerkt (afsluitwerk, conform opdracht).

---

## Wat je tegenkwam (buiten de vragen)

1. **De parkeerkop dekt zijn inhoud niet meer half:** 2 van de 5 bullets zijn afgehandelde
   stap-2-verwijzingen ("horen inhoudelijk elders" is op hen niet meer van toepassing). Zodra de
   drie items een bestemming krijgen, kan de sectie leeg — de twee verwijzingsregels verdienen
   dan een gewone plek (gate-verwijzing bij §Bronscans/§Live-DB-tests-omgeving of gewoon weg,
   want beide wijzen alleen door) — eigen besluit.
2. **`_run_rls` is geen gedeelde helper maar een per-bestand-harnas** (35 testbestanden dragen
   elk hun eigen kopie/variant). Observatie, geen actie — maar het relativeert item 1's
   verwijzing: die wijst naar een patroon, niet naar één vindplaats.
3. **Item 3b bewijst de waarde van deze meting:** zonder leeft-al-check was de rm/find-regel als
   vierde kopie ergens geland — precies de dubbeling-soort die stap 2 net opruimde.

*Einde meting. Werktree ongewijzigd behalve dit rapport.*
