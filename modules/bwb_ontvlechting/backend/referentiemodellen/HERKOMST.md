# Herkomst — gecureerde referentiemodel-bestanden

Deze map bevat de gecureerde referentiemodel-bestanden die LIKARA aanbiedt
(besloten LI039: repo-route — het bestand reist mee in de release, precedent
Keycloak-realm-JSON). Elk bestand is hieronder navolgbaar vastgelegd.

## GEMMA_release_2026-07-01.xml

| | |
|---|---|
| **Aanbod-label** | GEMMA Bedrijfsfuncties — release 1 juli 2026 |
| **Bron** | [VNG-Realisatie/GEMMA-Archi-repository](https://github.com/VNG-Realisatie/GEMMA-Archi-repository), bestand `export/GEMMA release.xml` |
| **Commit (gepind)** | `de0984717e69` — 2026-07-01, "Release: Actief openbaarmaken" |
| **Formaat** | ArchiMate Open Exchange (AMEFF), namespace `http://www.opengroup.org/xsd/archimate/3.0/` |
| **Grootte** | 13.411.843 bytes |
| **SHA-256** | `b844f184cd960293a1e6ce690b159353130e81798ee851a8ce97ff3edf0d4cf1` |
| **Licentie** | EUPL (repo-Readme §Licentie: gebruik/aanpassen/delen toegestaan, mét bronvermelding en share-alike) |
| **Inhoud (relevant)** | 2752 elementen waarvan 297 BusinessFunction; 302 aggregation-relaties BF↔BF (de functieboom); 2455 elementen van 25 andere typen vallen buiten scope |
| **Bekrachtigd** | LI039 (Bert) — zie `docs/Verkenning-GEMMA-AMEFF-V040.md` |

Een nieuwe modelversie = een nieuw, opnieuw gepind bestand + bijgewerkte regel
hier + bijgewerkt aanbod (`seed_referentiemodel.py`). Nooit het bestaande
bestand stil overschrijven.

## Releasegeschiedenis (vingerafdrukken — geen bestandsopslag)

Elke bekende release van de bron wordt hier met zijn vingerafdruk vastgelegd,
óók releases die niet (meer) als bestand in deze map staan. Daarmee is elke
oude release exact terug te halen (raw-URL op de commit-hash) en is elke
driftmeting reproduceerbaar (LI040-les: de okt-2025-release was na eenmalig
gebruik kwijt en moest voor de plaatsingsstabiliteitsmeting opnieuw worden
opgehaald).

| Release | Commit (gepind) | SHA-256 | Grootte | Bedrijfsfuncties | Aggregation-plaatsingen (BF↔BF) |
|---|---|---|---|---|---|
| 2025-10-11 "Release" | `7bcba2ad3888` | `682ac4d6df463ac42a521f3af6ee4104a10fbb9258fcfca92df12646b819834c` | 13.307.499 bytes | 296 | 301 |
| 2026-07-01 "Release: Actief openbaarmaken" — **het gecureerde aanbod** | `de0984717e69` | `b844f184cd960293a1e6ce690b159353130e81798ee851a8ce97ff3edf0d4cf1` | 13.411.843 bytes | 297 | 302 |

Gemeten drift tussen deze twee releases (LI040,
`docs/Meting-plaatsingsstabiliteit-V040.md`): 296/296 identifiers stabiel,
0 functies verdwenen, 1 nieuw; 301/301 plaatsingen ongewijzigd, **0 verhangen**,
1 nieuw.
