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
    APPLICATIE = "applicatie"
    DATATYPE = "datatype"
    GEBRUIKERSGROEP = "gebruikersgroep"
    KOPPELING = "koppeling"
    CHECKLISTSCORE = "checklistscore"
    BLOKKADE = "blokkade"
    # ADR-020 — contractregister (tenant-zijde, inhoud-entiteiten)
    LEVERANCIER = "leverancier"
    CONTRACT = "contract"
    # ADR-021 Fase D — contract-koppeling generaliseerde naar component-niveau.
    COMPONENT_CONTRACT = "component_contract"
    # ADR-021 — component-herfundering (tenant-zijde, inhoud-entiteiten)
    COMPONENT = "component"
    COMPONENT_STRUCTUUR = "component_structuur"
    CHECKLISTVRAAG = "checklistvraag"
    # ADR-023 — unified getypeerd relatiemodel.
    RELATIE = "relatie"
    # ADR-023 Fase E — migratielaag (plateau, work_package, deliverable; gap volgt).
    PLATEAU = "plateau"
    WORK_PACKAGE = "work_package"
    DELIVERABLE = "deliverable"
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

PERMISSIES: dict[Entiteit, dict[Rol, frozenset[Actie]]] = {
    Entiteit.APPLICATIE: dict(_INHOUD),
    Entiteit.DATATYPE: dict(_INHOUD),
    Entiteit.GEBRUIKERSGROEP: dict(_INHOUD),
    Entiteit.KOPPELING: dict(_INHOUD),
    Entiteit.CHECKLISTSCORE: dict(_INHOUD),
    Entiteit.BLOKKADE: dict(_INHOUD),
    # ADR-020 contractregister — zelfde inhoud-patroon als Applicatie.
    Entiteit.LEVERANCIER: dict(_INHOUD),
    Entiteit.CONTRACT: dict(_INHOUD),
    Entiteit.COMPONENT_CONTRACT: dict(_INHOUD),
    # ADR-021 — component/structuurrelatie, zelfde inhoud-patroon als Applicatie.
    Entiteit.COMPONENT: dict(_INHOUD),
    Entiteit.COMPONENT_STRUCTUUR: dict(_INHOUD),
    # ADR-023 — relatiemodel: zelfde inhoud-patroon (Viewer L · Medewerker LAW ·
    # Beheerder LAWV · Auditor L).
    Entiteit.RELATIE: dict(_INHOUD),
    # ADR-023 Fase E — migratielaag: plateau + work_package + deliverable, zelfde patroon.
    Entiteit.PLATEAU: dict(_INHOUD),
    Entiteit.WORK_PACKAGE: dict(_INHOUD),
    Entiteit.DELIVERABLE: dict(_INHOUD),
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
    dat voorvoegsel geaccepteerd (bv. `cd-beheerder`).
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
