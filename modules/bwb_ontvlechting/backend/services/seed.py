"""Seeddata — checklist-vragenlijst BWB-ontvlechting (ADR-009).

89 vaste checklist-vragen verdeeld over 12 categorieën. Idempotent via
INSERT ... ON CONFLICT (code) DO NOTHING.
"""
from sqlalchemy.dialects.postgresql import insert as pg_insert

from models.models import ChecklistPrioriteit, ChecklistVraag

CHECKLIST_VRAGEN = [
    {"code": "1.1", "categorie_nr": 1, "categorie_naam": "Applicatie-identiteit en eigenaarschap", "vraag": "Wat is de naam van de applicatie?", "prioriteit": "hoog"},
    {"code": "1.2", "categorie_nr": 1, "categorie_naam": "Applicatie-identiteit en eigenaarschap", "vraag": "Wat is het functionele domein (HR, Financiën, Zaakgericht, Archief, etc.)?", "prioriteit": "hoog"},
    {"code": "1.3", "categorie_nr": 1, "categorie_naam": "Applicatie-identiteit en eigenaarschap", "vraag": "Wie is de juridische eigenaar van de applicatie — BWB, Tiel, of gedeeld?", "prioriteit": "hoog"},
    {"code": "1.4", "categorie_nr": 1, "categorie_naam": "Applicatie-identiteit en eigenaarschap", "vraag": "Wie is de juridische eigenaar van de data in de applicatie?", "prioriteit": "hoog"},
    {"code": "1.5", "categorie_nr": 1, "categorie_naam": "Applicatie-identiteit en eigenaarschap", "vraag": "Is de applicatie exclusief in gebruik bij Tiel, of ook bij andere gemeenten/BWB?", "prioriteit": "hoog"},
    {"code": "1.6", "categorie_nr": 1, "categorie_naam": "Applicatie-identiteit en eigenaarschap", "vraag": "Is er een verwerkersovereenkomst aanwezig en met wie?", "prioriteit": "hoog"},
    {"code": "2.1", "categorie_nr": 2, "categorie_naam": "Technische inrichting en hosting", "vraag": "Wat is het hostingmodel: SaaS / on-premise (BWB) / IaaS / PaaS / hybride?", "prioriteit": "hoog"},
    {"code": "2.2", "categorie_nr": 2, "categorie_naam": "Technische inrichting en hosting", "vraag": "Op welke infrastructuur draait de applicatie (server, datacenter, cloudplatform)?", "prioriteit": "hoog", "betekenis": "technische_plaatsing"},
    {"code": "2.3", "categorie_nr": 2, "categorie_naam": "Technische inrichting en hosting", "vraag": "Wat is het besturingssysteem en de technische stack?", "prioriteit": "midden"},
    {"code": "2.4", "categorie_nr": 2, "categorie_naam": "Technische inrichting en hosting", "vraag": "Zijn er specifieke hardware- of netwerkafhankelijkheden?", "prioriteit": "midden"},
    {"code": "2.5", "categorie_nr": 2, "categorie_naam": "Technische inrichting en hosting", "vraag": "Is er een acceptatieomgeving of testomgeving aanwezig?", "prioriteit": "midden"},
    {"code": "2.6", "categorie_nr": 2, "categorie_naam": "Technische inrichting en hosting", "vraag": "Wat zijn de beschikbaarheids- en onderhoudsvereisten (SLA, patchbeleid)?", "prioriteit": "midden"},
    {"code": "2.7", "categorie_nr": 2, "categorie_naam": "Technische inrichting en hosting", "vraag": "Draait de applicatie op gedeelde infrastructuur met andere gemeenten of BWB?", "prioriteit": "hoog"},
    {"code": "3.1", "categorie_nr": 3, "categorie_naam": "Gebruikers en gebruik", "vraag": "Welke organisaties gebruiken de applicatie (Tiel / BWB / Culemborg / West-Betuwe)?", "prioriteit": "hoog"},
    {"code": "3.2", "categorie_nr": 3, "categorie_naam": "Gebruikers en gebruik", "vraag": "Wat is het aantal actieve gebruikers per gemeente?", "prioriteit": "hoog"},
    {"code": "3.3", "categorie_nr": 3, "categorie_naam": "Gebruikers en gebruik", "vraag": "Wie zijn de functioneel beheerder(s) en bij welke organisatie zijn zij in dienst?", "prioriteit": "hoog"},
    {"code": "3.4", "categorie_nr": 3, "categorie_naam": "Gebruikers en gebruik", "vraag": "Zijn er BWB-medewerkers die primair voor Tiel in deze applicatie werken?", "prioriteit": "hoog"},
    {"code": "3.5", "categorie_nr": 3, "categorie_naam": "Gebruikers en gebruik", "vraag": "Wat is de impact op de dagelijkse dienstverlening als de applicatie wordt gemigreerd?", "prioriteit": "hoog"},
    {"code": "3.6", "categorie_nr": 3, "categorie_naam": "Gebruikers en gebruik", "vraag": "Zijn er piekperiodes of kritieke momenten waarop migratie niet mogelijk is?", "prioriteit": "midden"},
    {"code": "3.7", "categorie_nr": 3, "categorie_naam": "Gebruikers en gebruik", "vraag": "Zijn er externe gebruikers (burgers, ketenpartners, andere overheden)?", "prioriteit": "midden"},
    {"code": "4.1", "categorie_nr": 4, "categorie_naam": "Data-inhoud, datatype en -kwaliteit", "vraag": "Welk type data bevat de applicatie (gestructureerd DB / documenten/files / e-mail / spatial / binair / combinatie)?", "prioriteit": "hoog"},
    {"code": "4.2", "categorie_nr": 4, "categorie_naam": "Data-inhoud, datatype en -kwaliteit", "vraag": "Wat is het datavolume (indicatief aantal records, GB)?", "prioriteit": "midden"},
    {"code": "4.3", "categorie_nr": 4, "categorie_naam": "Data-inhoud, datatype en -kwaliteit", "vraag": "Is de data per gemeente te onderscheiden en te isoleren?", "prioriteit": "hoog"},
    {"code": "4.4", "categorie_nr": 4, "categorie_naam": "Data-inhoud, datatype en -kwaliteit", "vraag": "Zijn er gemengde datasets waarbij Tiel-data en BWB/andere data niet zijn te scheiden?", "prioriteit": "hoog"},
    {"code": "4.5", "categorie_nr": 4, "categorie_naam": "Data-inhoud, datatype en -kwaliteit", "vraag": "Wat is de kwaliteit van de data (volledigheid, consistentie, actualiteit)?", "prioriteit": "hoog"},
    {"code": "4.6", "categorie_nr": 4, "categorie_naam": "Data-inhoud, datatype en -kwaliteit", "vraag": "Is de metadata MDTO-conform vastgelegd?", "prioriteit": "hoog"},
    {"code": "4.7", "categorie_nr": 4, "categorie_naam": "Data-inhoud, datatype en -kwaliteit", "vraag": "Zijn bewaartermijnen per dataset/zaaktype vastgesteld (concordantietabel)?", "prioriteit": "hoog"},
    {"code": "4.8", "categorie_nr": 4, "categorie_naam": "Data-inhoud, datatype en -kwaliteit", "vraag": "Zijn er persoonsgegevens aanwezig en zo ja, welke categorieën (regulier / bijzonder)?", "prioriteit": "hoog"},
    {"code": "4.9", "categorie_nr": 4, "categorie_naam": "Data-inhoud, datatype en -kwaliteit", "vraag": "Is er een dataclassificatie (openbaar / intern / vertrouwelijk / geheim)?", "prioriteit": "midden"},
    {"code": "5.1", "categorie_nr": 5, "categorie_naam": "Koppelingen als data-ontvanger", "vraag": "Van welke applicaties of databronnen ontvangt deze applicatie data?", "prioriteit": "hoog"},
    {"code": "5.2", "categorie_nr": 5, "categorie_naam": "Koppelingen als data-ontvanger", "vraag": "Via welk protocol of koppelvlak wordt data ontvangen (API, bestandsuitwisseling, directe DB-koppeling, middleware)?", "prioriteit": "hoog"},
    {"code": "5.3", "categorie_nr": 5, "categorie_naam": "Koppelingen als data-ontvanger", "vraag": "Wat is de frequentie en het volume van de data-aanlevering?", "prioriteit": "midden"},
    {"code": "5.4", "categorie_nr": 5, "categorie_naam": "Koppelingen als data-ontvanger", "vraag": "Is de ontvangende koppeling gedocumenteerd en actueel?", "prioriteit": "midden"},
    {"code": "5.5", "categorie_nr": 5, "categorie_naam": "Koppelingen als data-ontvanger", "vraag": "Wat zijn de gevolgen voor de werking van deze applicatie als de aanlevering wegvalt of wordt omgeleid?", "prioriteit": "hoog"},
    {"code": "5.6", "categorie_nr": 5, "categorie_naam": "Koppelingen als data-ontvanger", "vraag": "Zijn de aanleverende applicaties eigendom van BWB, Tiel of een derde partij?", "prioriteit": "hoog"},
    {"code": "6.1", "categorie_nr": 6, "categorie_naam": "Koppelingen als data-leverancier", "vraag": "Aan welke applicaties of databronnen levert deze applicatie data?", "prioriteit": "hoog"},
    {"code": "6.2", "categorie_nr": 6, "categorie_naam": "Koppelingen als data-leverancier", "vraag": "Via welk protocol of koppelvlak wordt data geleverd (API, bestandsuitwisseling, directe DB-koppeling, middleware)?", "prioriteit": "hoog"},
    {"code": "6.3", "categorie_nr": 6, "categorie_naam": "Koppelingen als data-leverancier", "vraag": "Wat is de frequentie en het volume van de data-levering?", "prioriteit": "midden"},
    {"code": "6.4", "categorie_nr": 6, "categorie_naam": "Koppelingen als data-leverancier", "vraag": "Is de leverende koppeling gedocumenteerd en actueel?", "prioriteit": "midden"},
    {"code": "6.5", "categorie_nr": 6, "categorie_naam": "Koppelingen als data-leverancier", "vraag": "Wat zijn de gevolgen voor de afnemende systemen als deze applicatie wordt gemigreerd of losgekoppeld?", "prioriteit": "hoog"},
    {"code": "6.6", "categorie_nr": 6, "categorie_naam": "Koppelingen als data-leverancier", "vraag": "Zijn de afnemende applicaties eigendom van BWB, Tiel of een derde partij?", "prioriteit": "hoog"},
    {"code": "6.7", "categorie_nr": 6, "categorie_naam": "Koppelingen als data-leverancier", "vraag": "Levert de applicatie aan basisregistraties of landelijke voorzieningen?", "prioriteit": "hoog"},
    {"code": "7.1", "categorie_nr": 7, "categorie_naam": "Toegangsbeheer en security", "vraag": "Hoe is identiteitsbeheer geregeld (Active Directory / Azure AD / lokaal / federatief)?", "prioriteit": "hoog"},
    {"code": "7.2", "categorie_nr": 7, "categorie_naam": "Toegangsbeheer en security", "vraag": "Zijn gebruikersaccounts gemeente-specifiek of gedeeld?", "prioriteit": "hoog"},
    {"code": "7.3", "categorie_nr": 7, "categorie_naam": "Toegangsbeheer en security", "vraag": "Welke data wordt ontsloten via een zelfstandig RBAC binnen de applicatie?", "prioriteit": "hoog"},
    {"code": "7.4", "categorie_nr": 7, "categorie_naam": "Toegangsbeheer en security", "vraag": "Zijn er serviceaccounts of technische accounts die gemeenteoverstijgend worden gebruikt?", "prioriteit": "hoog"},
    {"code": "7.5", "categorie_nr": 7, "categorie_naam": "Toegangsbeheer en security", "vraag": "Wat is de BIO2-classificatie van de applicatie?", "prioriteit": "hoog"},
    {"code": "7.6", "categorie_nr": 7, "categorie_naam": "Toegangsbeheer en security", "vraag": "Zijn er openstaande beveiligingsbevindingen of kwetsbaarheden?", "prioriteit": "hoog"},
    {"code": "7.7", "categorie_nr": 7, "categorie_naam": "Toegangsbeheer en security", "vraag": "Is er een DPIA uitgevoerd en actueel?", "prioriteit": "hoog"},
    {"code": "7.8", "categorie_nr": 7, "categorie_naam": "Toegangsbeheer en security", "vraag": "Wat zijn de AVG-risico's bij overdracht (doorgifte persoonsgegevens)?", "prioriteit": "hoog"},
    {"code": "7.9", "categorie_nr": 7, "categorie_naam": "Toegangsbeheer en security", "vraag": "Is de applicatie opgenomen in de ENSIA-verantwoording?", "prioriteit": "midden"},
    {"code": "8.1", "categorie_nr": 8, "categorie_naam": "Contractuele positie", "vraag": "Wie is de contractpartij — BWB, gemeente Tiel, of gedeeld?", "prioriteit": "hoog"},
    {"code": "8.2", "categorie_nr": 8, "categorie_naam": "Contractuele positie", "vraag": "Wat is de contractvorm (licentie / SaaS-abonnement / maatwerkovereenkomst)?", "prioriteit": "hoog"},
    {"code": "8.3", "categorie_nr": 8, "categorie_naam": "Contractuele positie", "vraag": "Wat is de looptijd en opzegtermijn van het contract?", "prioriteit": "hoog"},
    {"code": "8.4", "categorie_nr": 8, "categorie_naam": "Contractuele positie", "vraag": "Zijn er exit-bepalingen of data-overdrachtsclausules opgenomen?", "prioriteit": "hoog"},
    {"code": "8.5", "categorie_nr": 8, "categorie_naam": "Contractuele positie", "vraag": "Is splitsing van het contract tussen Tiel en BWB contractueel mogelijk?", "prioriteit": "hoog"},
    {"code": "8.6", "categorie_nr": 8, "categorie_naam": "Contractuele positie", "vraag": "Wat zijn de volumekorting-effecten als Tiel afhaakt?", "prioriteit": "hoog"},
    {"code": "8.7", "categorie_nr": 8, "categorie_naam": "Contractuele positie", "vraag": "Zijn er minimum-afname-verplichtingen die BWB stranden bij uittreding Tiel?", "prioriteit": "hoog"},
    {"code": "8.8", "categorie_nr": 8, "categorie_naam": "Contractuele positie", "vraag": "Is de leverancier bereid mee te werken aan migratie en data-export?", "prioriteit": "hoog"},
    {"code": "8.9", "categorie_nr": 8, "categorie_naam": "Contractuele positie", "vraag": "Wat zijn de kosten van contractsplitsing of hercontractering?", "prioriteit": "hoog"},
    {"code": "9.1", "categorie_nr": 9, "categorie_naam": "Archiefwet- en compliance-status", "vraag": "Valt de applicatie onder de Archiefwet (bevat archiefwaardige bescheiden)?", "prioriteit": "hoog"},
    {"code": "9.2", "categorie_nr": 9, "categorie_naam": "Archiefwet- en compliance-status", "vraag": "Zijn bewaartermijnen vastgesteld conform de geldende selectielijst?", "prioriteit": "hoog"},
    {"code": "9.3", "categorie_nr": 9, "categorie_naam": "Archiefwet- en compliance-status", "vraag": "Is de concordantietabel volledig en actueel?", "prioriteit": "hoog"},
    {"code": "9.4", "categorie_nr": 9, "categorie_naam": "Archiefwet- en compliance-status", "vraag": "Zijn er openstaande aanbevelingen van de archieftoezichthouder (RAR) voor deze applicatie?", "prioriteit": "hoog"},
    {"code": "9.5", "categorie_nr": 9, "categorie_naam": "Archiefwet- en compliance-status", "vraag": "Voldoet de applicatie aan de MDTO-norm voor duurzame toegankelijkheid?", "prioriteit": "hoog"},
    {"code": "9.6", "categorie_nr": 9, "categorie_naam": "Archiefwet- en compliance-status", "vraag": "Is er een migratieplan en verklaring van migratie (art. 25 Archiefregeling) aanwezig?", "prioriteit": "hoog"},
    {"code": "9.7", "categorie_nr": 9, "categorie_naam": "Archiefwet- en compliance-status", "vraag": "Loopt er een lopende migratie naar het e-depot van het RAR?", "prioriteit": "hoog"},
    {"code": "9.8", "categorie_nr": 9, "categorie_naam": "Archiefwet- en compliance-status", "vraag": "Voldoet de applicatie aan de nieuwe Archiefwet (inwerkingtreding 1 juli 2026)?", "prioriteit": "hoog"},
    {"code": "10.1", "categorie_nr": 10, "categorie_naam": "Gereedheid ICT-Tiel als ontvanger", "vraag": "Is er een ontvangende omgeving bij Tiel beschikbaar voor deze applicatie?", "prioriteit": "hoog"},
    {"code": "10.2", "categorie_nr": 10, "categorie_naam": "Gereedheid ICT-Tiel als ontvanger", "vraag": "Is er voldoende beheerscapaciteit bij ICT-Tiel voor beheer na overdracht?", "prioriteit": "hoog"},
    {"code": "10.3", "categorie_nr": 10, "categorie_naam": "Gereedheid ICT-Tiel als ontvanger", "vraag": "Is de ontvangende architectuur van Tiel geschikt voor deze applicatie?", "prioriteit": "hoog"},
    {"code": "10.4", "categorie_nr": 10, "categorie_naam": "Gereedheid ICT-Tiel als ontvanger", "vraag": "Zijn er licentie- of contractafspraken nodig aan de Tiel-zijde?", "prioriteit": "hoog"},
    {"code": "10.5", "categorie_nr": 10, "categorie_naam": "Gereedheid ICT-Tiel als ontvanger", "vraag": "Kan er decharge worden gegeven bij overdracht (wie accepteert de data/applicatie)?", "prioriteit": "hoog"},
    {"code": "10.6", "categorie_nr": 10, "categorie_naam": "Gereedheid ICT-Tiel als ontvanger", "vraag": "Is ICT-Tiel ready-to-receive — heeft Tiel expliciet bevestigd dat zij kunnen ontvangen?", "prioriteit": "hoog"},
    {"code": "10.7", "categorie_nr": 10, "categorie_naam": "Gereedheid ICT-Tiel als ontvanger", "vraag": "Zijn er opleidings- of kennisoverdrachtsvereisten voor Tiel-medewerkers?", "prioriteit": "midden"},
    {"code": "11.1", "categorie_nr": 11, "categorie_naam": "Migratiepad en transitiescenario", "vraag": "Wat is het voorgenomen migratiepad: overdracht Tiel / overname BWB / tijdelijk gedeeld / beëindiging?", "prioriteit": "hoog"},
    {"code": "11.2", "categorie_nr": 11, "categorie_naam": "Migratiepad en transitiescenario", "vraag": "Is een gefaseerde migratie (parallel-run) mogelijk?", "prioriteit": "hoog"},
    {"code": "11.3", "categorie_nr": 11, "categorie_naam": "Migratiepad en transitiescenario", "vraag": "Wat is de technische methode voor datamigratie (export/import / replicatie / API / handmatig)?", "prioriteit": "hoog"},
    {"code": "11.4", "categorie_nr": 11, "categorie_naam": "Migratiepad en transitiescenario", "vraag": "Wat is de minimale transitieperiode voor een veilige overdracht?", "prioriteit": "hoog"},
    {"code": "11.5", "categorie_nr": 11, "categorie_naam": "Migratiepad en transitiescenario", "vraag": "Is er een rollback-mogelijkheid als de migratie mislukt?", "prioriteit": "hoog"},
    {"code": "11.6", "categorie_nr": 11, "categorie_naam": "Migratiepad en transitiescenario", "vraag": "Wat zijn de pre-condities voor start van de migratie?", "prioriteit": "hoog"},
    {"code": "11.7", "categorie_nr": 11, "categorie_naam": "Migratiepad en transitiescenario", "vraag": "Wat zijn de post-condities / acceptatiecriteria na afronding?", "prioriteit": "hoog"},
    {"code": "11.8", "categorie_nr": 11, "categorie_naam": "Migratiepad en transitiescenario", "vraag": "Zijn er afhankelijkheden met de migratie van andere applicaties (volgorde)?", "prioriteit": "hoog"},
    {"code": "12.1", "categorie_nr": 12, "categorie_naam": "Risico en prioritering", "vraag": "Wat is de overall migratiecomplexiteit (Laag / Midden / Hoog)?", "prioriteit": "hoog"},
    {"code": "12.2", "categorie_nr": 12, "categorie_naam": "Risico en prioritering", "vraag": "Wat is de impact op dienstverlening als migratie vertraagt?", "prioriteit": "hoog"},
    {"code": "12.3", "categorie_nr": 12, "categorie_naam": "Risico en prioritering", "vraag": "Zijn er juridische of compliance-risico's bij niet-tijdige migratie?", "prioriteit": "hoog"},
    {"code": "12.4", "categorie_nr": 12, "categorie_naam": "Risico en prioritering", "vraag": "Wat is de migratieprioriteit in de ontvlechtingsvolgorde (1=eerst)?", "prioriteit": "hoog"},
    {"code": "12.5", "categorie_nr": 12, "categorie_naam": "Risico en prioritering", "vraag": "Zijn er openstaande blokkades die migratie momenteel verhinderen?", "prioriteit": "hoog"},
    {"code": "12.6", "categorie_nr": 12, "categorie_naam": "Risico en prioritering", "vraag": "Wat is de aanbevolen vervolgactie (inventariseren / escaleren / migreren / parkeren)?", "prioriteit": "hoog"},
]

# LI058 (Slice 2) — voorlopige STARTSET checklistvragen voor componenttype `database`, zodat het type
# niet leeg is en end-to-end aantoonbaar scoort. Score-gebaseerd (ja/deels/nee/nvt), net als de
# applicatie-vragen (antwoordtype `geen` via server_default; extra ADR-019-opties kunnen later per vraag
# in de beheer-UI). Stabiele codes (set-once), actief=True. Te verfijnen door de tenant in het scherm.
CHECKLIST_VRAGEN_DATABASE = [
    {"code": "1.1", "categorie_nr": 1, "categorie_naam": "Database-migratiegereedheid (startset)", "vraag": "Is de data-eigenaar van deze database bekend en vastgelegd?", "prioriteit": "hoog"},
    {"code": "1.2", "categorie_nr": 1, "categorie_naam": "Database-migratiegereedheid (startset)", "vraag": "Is de data overdraagbaar/exporteerbaar in een herbruikbaar formaat?", "prioriteit": "hoog"},
    {"code": "1.3", "categorie_nr": 1, "categorie_naam": "Database-migratiegereedheid (startset)", "vraag": "Zijn de koppelingen en afhankelijkheden van deze database in kaart gebracht?", "prioriteit": "hoog"},
    {"code": "1.4", "categorie_nr": 1, "categorie_naam": "Database-migratiegereedheid (startset)", "vraag": "Is er een actuele back-up- en herstelprocedure?", "prioriteit": "hoog"},
    {"code": "1.5", "categorie_nr": 1, "categorie_naam": "Database-migratiegereedheid (startset)", "vraag": "Is de dataclassificatie (gevoeligheid/AVG) van deze database bepaald?", "prioriteit": "midden"},
    {"code": "1.6", "categorie_nr": 1, "categorie_naam": "Database-migratiegereedheid (startset)", "vraag": "Is de database exclusief voor één organisatie of gedeeld (ontvlechtingsrelevant)?", "prioriteit": "hoog"},
]

# LI060 — STARTSETS (1 vraag) voor de drie nieuw-beoordeelbare componenttypen, exact hetzelfde stramien
# als de database-startset (betekenis=None; antwoordtype via server_default `geen`; stabiele code in de
# type-namespace; actief=True). Te verfijnen door de tenant in het beheerscherm.
CHECKLIST_VRAGEN_SERVER_COMPUTE = [
    {"code": "1.1", "categorie_nr": 1, "categorie_naam": "Server/compute-migratiegereedheid (startset)", "vraag": "Is bekend en vastgelegd waar deze server/compute draait (locatie/omgeving) en wie hem beheert?", "prioriteit": "hoog"},
]
CHECKLIST_VRAGEN_INTEGRATIEVOORZIENING = [
    {"code": "1.1", "categorie_nr": 1, "categorie_naam": "Integratie-/koppelvoorziening-migratiegereedheid (startset)", "vraag": "Zijn de koppelingen die via deze voorziening lopen in kaart gebracht (welke systemen, welk protocol)?", "prioriteit": "hoog"},
]
CHECKLIST_VRAGEN_LANDELIJKE_VOORZIENING = [
    {"code": "1.1", "categorie_nr": 1, "categorie_naam": "Landelijke voorziening-migratiegereedheid (startset)", "vraag": "Is de aansluiting op deze landelijke voorziening vastgelegd (aansluitvorm en afhankelijkheid)?", "prioriteit": "hoog"},
]

# (componenttype-sleutel, startset) — de niet-applicatie beoordeelbare typen; per type gekopieerd.
_STARTSETS_PER_TYPE: list[tuple[str, list[dict]]] = [
    ("database", CHECKLIST_VRAGEN_DATABASE),
    ("server_compute", CHECKLIST_VRAGEN_SERVER_COMPUTE),
    ("integratievoorziening", CHECKLIST_VRAGEN_INTEGRATIEVOORZIENING),
    ("landelijke_voorziening", CHECKLIST_VRAGEN_LANDELIJKE_VOORZIENING),
]


async def seed_checklist_vragen(session, tenant_id) -> int:
    """Voegt de baseline (89 applicatie + startsets per beoordeeld type) idempotent toe **voor één tenant**.
    Geeft het aantal vragen terug.

    ADR-022 W1: `checklistvraag` is tenant-scoped — de baseline wordt per tenant
    gekopieerd (`tenant_id` gezet, uniciteit `(tenant_id, componenttype, code)`).
    Draait onder de `lk_app`-RLS-context van de tenant (INSERT-`WITH CHECK` eist
    `tenant_id = app.tenant_id`). De surrogate-PK `id` wordt door de DB gegenereerd."""
    rows = [
        {
            **v,
            "tenant_id": tenant_id,
            "componenttype": "applicatie",
            "prioriteit": ChecklistPrioriteit(v["prioriteit"]),
            # ADR-023 Fase F (F-3): de baseline draagt de betekenis al → fresh deploys zijn
            # meteen gelijk aan de gemigreerde stand. Alle rijen dezelfde sleutels (pg_insert).
            "betekenis": v.get("betekenis"),
        }
        for v in CHECKLIST_VRAGEN
    ]
    # LI058/LI060 — startsets per niet-applicatie beoordeelbaar type (database + de drie LI060-typen),
    # zelfde patroon (betekenis=None; antwoordtype via server_default `geen`). Aparte conflict-scope:
    # (tenant, componenttype, code) is per type uniek.
    type_rows = [
        {
            **v,
            "tenant_id": tenant_id,
            "componenttype": sleutel,
            "prioriteit": ChecklistPrioriteit(v["prioriteit"]),
            "betekenis": None,
        }
        for sleutel, startset in _STARTSETS_PER_TYPE
        for v in startset
    ]
    stmt = pg_insert(ChecklistVraag).values(rows + type_rows).on_conflict_do_nothing(
        index_elements=["tenant_id", "componenttype", "code"]
    )
    await session.execute(stmt)
    await session.commit()
    return len(CHECKLIST_VRAGEN) + len(type_rows)
