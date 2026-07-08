"""RBAC — rollen, rechtenmatrix en permissiecheck (ADR-010).

Eén bron van waarheid voor de door Bert vastgestelde rechtenmatrix. Endpoints
checken via `heeft_permissie(...)` tegen `PERMISSIES`; rollen worden ad hoc
nooit vergeleken. Fail-secure: onbekende rol/entiteit/actie ⇒ geen recht.

Rollen zijn LOS en EXPLICIET — er is GEEN overerving tussen rollen.
"""
from collections.abc import Iterable
from enum import Enum

from app.core.config import settings


class Rol(str, Enum):
    VIEWER = "viewer"
    MEDEWERKER = "medewerker"
    BEHEERDER = "beheerder"
    AUDITOR = "auditor"


class Entiteit(str, Enum):
    # LI059 facade-purge: `APPLICATIE` verwijderd — applicaties zijn componenten (type
    # 'applicatie') en vallen onder het `COMPONENT`-recht.
    DATATYPE = "datatype"
    GEBRUIKERSGROEP = "gebruikersgroep"
    KOPPELING = "koppeling"
    CHECKLISTSCORE = "checklistscore"
    BLOKKADE = "blokkade"
    # ADR-020/ADR-024 — contractregister + partijenregister (tenant-zijde, inhoud-entiteiten).
    # ADR-024 slice 2a: één PARTIJ-recht dekt het beheer van alle partij-aarden (externe_partij /
    # organisatie / organisatie_eenheid / persoon); het oude EXTERNE_PARTIJ-recht is hierin
    # opgegaan. Het contract houdt de term "leverancier" (tegenpartij-koppeling, optie A).
    PARTIJ = "partij"
    CONTRACT = "contract"
    # ADR-036 — grof gebruiksfeit "organisatie gebruikt applicatie" (tenant-zijde, inhoud-entiteit).
    ORGANISATIEGEBRUIK = "organisatiegebruik"
    # ADR-021 Fase D — contract-koppeling generaliseerde naar component-niveau.
    COMPONENT_CONTRACT = "component_contract"
    # ADR-021 — component-herfundering (tenant-zijde, inhoud-entiteiten)
    COMPONENT = "component"
    COMPONENT_STRUCTUUR = "component_structuur"
    CHECKLISTVRAAG = "checklistvraag"
    # ADR-023 — unified getypeerd relatiemodel.
    RELATIE = "relatie"
    # ADR-023 Fase E — migratielaag (plateau, work_package, deliverable, gap).
    PLATEAU = "plateau"
    WORK_PACKAGE = "work_package"
    DELIVERABLE = "deliverable"
    GAP = "gap"
    # ADR-042 slice 1 — procesregister (tenant-zijde, inhoud-entiteit).
    PROCES = "proces"
    # ADR-042 slice 3 — koppelregel component→proces (eigen entiteit: de regel heeft geen
    # eenduidige "bron"-kant om op mee te liften, anders dan roltoewijzing→PARTIJ).
    PROCESVERVULLING = "procesvervulling"
    # ADR-023 Fase F / F-2 — read-only cross-element laagprojectie (architectuuroverzicht).
    ARCHITECTUUR = "architectuur"
    # ADR-027 — niet-scorende categorie-klaarverklaring (tenant-zijde, inhoud-entiteit).
    KLAARVERKLARING = "klaarverklaring"
    # ADR-033 slice 2 — opgeslagen & deelbare Impact-verkenner-views (eigen-beheer-entiteit).
    IMPACT_VIEW = "impact_view"
    # ADR-041 slice 1 — persoonlijke voorkeuren ("onthoud als mijn standaard"). Eigen-scope: elke
    # ingelogde gebruiker beheert uitsluitend zijn éígen voorkeuren (ownership via `sub` in de service).
    GEBRUIKER_VOORKEUR = "gebruiker_voorkeur"
    AUDITLOG = "auditlog"
    GEBRUIKERSBEHEER = "gebruikersbeheer"
    TENANT_INSTELLINGEN = "tenant_instellingen"


class Actie(str, Enum):
    LEZEN = "L"
    AANMAKEN = "A"
    WIJZIGEN = "W"
    VERWIJDEREN = "V"


KNOWN_ROLES: frozenset[str] = frozenset(r.value for r in Rol)

# ── Rechtenmatrix (LEIDEND — weerspiegelt exact de vastgestelde tabel) ─────────

_L = frozenset({Actie.LEZEN})
_LAW = frozenset({Actie.LEZEN, Actie.AANMAKEN, Actie.WIJZIGEN})
_LAWV = frozenset({Actie.LEZEN, Actie.AANMAKEN, Actie.WIJZIGEN, Actie.VERWIJDEREN})
_GEEN: frozenset[Actie] = frozenset()

# Inhoud-entiteiten delen hetzelfde patroon: Viewer L · Medewerker LAW ·
# Beheerder LAWV · Auditor L.
_INHOUD = {
    Rol.VIEWER: _L,
    Rol.MEDEWERKER: _LAW,
    Rol.BEHEERDER: _LAWV,
    Rol.AUDITOR: _L,
}

# Read-only entiteit: élke tenant-rol mag uitsluitend LEZEN (geen A/W/V). Voor
# afgeleide leesvlakken zonder mutatie (bv. de cross-element laagprojectie, F-2).
_ALLEEN_LEZEN = {
    Rol.VIEWER: _L,
    Rol.MEDEWERKER: _L,
    Rol.BEHEERDER: _L,
    Rol.AUDITOR: _L,
}

# Eigen-beheer-entiteit (ADR-033 slice 2): Viewer/Auditor lezen (gebruiken gedeelde records);
# Medewerker én Beheerder mogen volledig CRUD — óók VERWIJDEREN (je eigen record weggooien is
# geen geprivilegieerde destructieve actie). De fijnere "alleen de maker muteert"-regel zit
# als eigenaarschaps-guard in de servicelaag, bovenop deze RBAC-gate.
_EIGEN_BEHEER = {
    Rol.VIEWER: _L,
    Rol.MEDEWERKER: _LAWV,
    Rol.BEHEERDER: _LAWV,
    Rol.AUDITOR: _L,
}

# Persoonlijke-voorkeur-entiteit (ADR-041 slice 1): een voorkeur is STRIKT PERSOONLIJK en wordt NOOIT
# gedeeld — anders dan `impact_view` bestaat er geen "andermans record lezen"-geval. Élke ingelogde
# tenant-rol (óók Viewer/Auditor) beheert daarom volledig zijn EIGEN voorkeuren; zonder schrijfrecht
# zou de feature voor die rollen onbruikbaar zijn. De eigen-scope ("alleen je eigen `sub`") wordt
# server-side in de service afgedwongen, bovenop deze RBAC-gate. (Afwijking t.o.v. het `_INHOUD`-
# patroon: bewust, omdat een persoonlijke voorkeur geen inhoud-/content-record is.)
_EIGEN_VOORKEUR = {
    Rol.VIEWER: _LAWV,
    Rol.MEDEWERKER: _LAWV,
    Rol.BEHEERDER: _LAWV,
    Rol.AUDITOR: _LAWV,
}

PERMISSIES: dict[Entiteit, dict[Rol, frozenset[Actie]]] = {
    Entiteit.DATATYPE: dict(_INHOUD),
    Entiteit.GEBRUIKERSGROEP: dict(_INHOUD),
    Entiteit.KOPPELING: dict(_INHOUD),
    Entiteit.CHECKLISTSCORE: dict(_INHOUD),
    Entiteit.BLOKKADE: dict(_INHOUD),
    # ADR-020/ADR-024 contract- + partijenregister — zelfde inhoud-patroon als Applicatie.
    Entiteit.PARTIJ: dict(_INHOUD),
    Entiteit.CONTRACT: dict(_INHOUD),
    # ADR-036 — grof gebruiksfeit: zelfde inhoud-patroon (Viewer L · Medewerker LAW ·
    # Beheerder LAWV · Auditor L).
    Entiteit.ORGANISATIEGEBRUIK: dict(_INHOUD),
    Entiteit.COMPONENT_CONTRACT: dict(_INHOUD),
    # ADR-021 — component/structuurrelatie, zelfde inhoud-patroon als Applicatie.
    Entiteit.COMPONENT: dict(_INHOUD),
    Entiteit.COMPONENT_STRUCTUUR: dict(_INHOUD),
    # ADR-023 — relatiemodel: zelfde inhoud-patroon (Viewer L · Medewerker LAW ·
    # Beheerder LAWV · Auditor L).
    Entiteit.RELATIE: dict(_INHOUD),
    # ADR-023 Fase E — migratielaag: plateau + work_package + deliverable + gap, zelfde patroon.
    Entiteit.PLATEAU: dict(_INHOUD),
    Entiteit.WORK_PACKAGE: dict(_INHOUD),
    Entiteit.DELIVERABLE: dict(_INHOUD),
    Entiteit.GAP: dict(_INHOUD),
    # ADR-042 slice 1 — procesregister: inhoud-patroon.
    Entiteit.PROCES: dict(_INHOUD),
    # ADR-042 slice 3 — koppelregel: inhoud-patroon (verbreken guardt op WIJZIGEN, zie routes).
    Entiteit.PROCESVERVULLING: dict(_INHOUD),
    # ADR-023 Fase F / F-2: cross-element laagprojectie — read-only overzicht; élke
    # tenant-rol mag lezen (consistent met het feit dat alle rollen al elk element-type lezen).
    Entiteit.ARCHITECTUUR: dict(_ALLEEN_LEZEN),
    # ADR-027 — categorie-klaarverklaring: inhoud-patroon (zelfde als PLATEAU/applicatie).
    Entiteit.KLAARVERKLARING: dict(_INHOUD),
    # ADR-033 slice 2 — opgeslagen views: eigen-beheer-patroon (Viewer/Auditor L; Medewerker/
    # Beheerder LAWV). Ownership (maker muteert) borgt de servicelaag.
    Entiteit.IMPACT_VIEW: dict(_EIGEN_BEHEER),
    # ADR-041 slice 1 — persoonlijke voorkeuren: elke tenant-rol beheert zijn eigen voorkeuren
    # (ownership via `sub` in de servicelaag). Strikt persoonlijk, nooit gedeeld.
    Entiteit.GEBRUIKER_VOORKEUR: dict(_EIGEN_VOORKEUR),
    # ADR-022 W1: de vragenset is tenant-eigendom — vraagbeheer is een tenant-
    # bevoegdheid (eigen entiteit, los van scoren via CHECKLISTSCORE). Inhoud-patroon:
    # Viewer L · Medewerker LAW · Beheerder LAWV · Auditor L. ("Verwijderen" =
    # soft-deactivatie via WIJZIGEN; geen hard-delete-pad in dit blok.)
    Entiteit.CHECKLISTVRAAG: dict(_INHOUD),
    # Auditlog — alleen Beheerder en Auditor mogen lezen; niemand muteert hier.
    Entiteit.AUDITLOG: {
        Rol.VIEWER: _GEEN,
        Rol.MEDEWERKER: _GEEN,
        Rol.BEHEERDER: _L,
        Rol.AUDITOR: _L,
    },
    # Beheer — uitsluitend Beheerder, volledig CRUD.
    Entiteit.GEBRUIKERSBEHEER: {
        Rol.VIEWER: _GEEN,
        Rol.MEDEWERKER: _GEEN,
        Rol.BEHEERDER: _LAWV,
        Rol.AUDITOR: _GEEN,
    },
    Entiteit.TENANT_INSTELLINGEN: {
        Rol.VIEWER: _GEEN,
        Rol.MEDEWERKER: _GEEN,
        Rol.BEHEERDER: _LAWV,
        Rol.AUDITOR: _GEEN,
    },
}


# ── Keycloak-rolmapping ────────────────────────────────────────────────────────

def _platform_rol(keycloak_rol: str) -> str | None:
    """Map één Keycloak-rolnaam op een platform-rol, of None (fail-secure).

    Standaard 1-op-1 met de canonieke namen (viewer/medewerker/beheerder/
    auditor). Met `keycloak_role_prefix` gezet worden uitsluitend rollen mét
    dat voorvoegsel geaccepteerd (bv. `lk-beheerder`).
    """
    prefix = settings.keycloak_role_prefix
    if prefix:
        if not keycloak_rol.startswith(prefix):
            return None
        keycloak_rol = keycloak_rol[len(prefix):]
    keycloak_rol = keycloak_rol.lower()
    return keycloak_rol if keycloak_rol in KNOWN_ROLES else None


def lees_keycloak_rollen(payload: dict) -> list[str]:
    """Ruwe rolnamen uit de Keycloak-JWT (realm- én client-rollen), ongefilterd.

    Gedeelde claim-bron voor zowel het tenant- (deze module) als het
    platform-domein (`platform_rbac`). Bevat geen domein-logica.
    """
    ruw: list[str] = []
    realm_access = payload.get("realm_access") or {}
    ruw += realm_access.get("roles") or []
    resource_access = payload.get("resource_access") or {}
    client = resource_access.get(settings.keycloak_client_id) or {}
    ruw += client.get("roles") or []
    return ruw


def extract_rollen(payload: dict) -> list[str]:
    """Lees de TENANT-rollen uit de Keycloak-JWT (ADR-010/012).

    Onbekende/ontbrekende rollen worden genegeerd ⇒ lege lijst = geen rechten.
    Platform-rollen vallen buiten dit domein en worden hier niet teruggegeven.
    """
    platform = {p for r in lees_keycloak_rollen(payload) if (p := _platform_rol(r))}
    return sorted(platform)


def heeft_permissie(rollen: Iterable[str], entiteit: Entiteit, actie: Actie) -> bool:
    """True alleen als minstens één rol de actie op de entiteit mag (fail-secure)."""
    matrix = PERMISSIES.get(entiteit)
    if not matrix:
        return False
    for rol in rollen:
        if rol in KNOWN_ROLES and actie in matrix.get(Rol(rol), _GEEN):
            return True
    return False
