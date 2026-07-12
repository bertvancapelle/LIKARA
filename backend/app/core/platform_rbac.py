"""Platform-RBAC — rollen, rechtenmatrix en check voor het PLATFORM-domein (ADR-012).

Strikt gescheiden van het tenant-domein (`app.core.rbac`). Platform-endpoints
draaien zonder tenant-context (lk_platform) en checken UITSLUITEND tegen deze
matrix; een tenant-rol kan een platform-endpoint nooit bedienen en omgekeerd.

Fail-secure: onbekende/lege rol/entiteit/actie ⇒ geen recht.
"""
from collections.abc import Iterable
from enum import Enum

from app.core.config import settings
from app.core.rbac import Actie, lees_keycloak_rollen


class PlatformRol(str, Enum):
    PLATFORMBEHEERDER = "platformbeheerder"
    PLATFORMOPERATOR = "platformoperator"


class PlatformEntiteit(str, Enum):
    TENANT = "tenant"
    PLATFORMINSTELLINGEN = "platforminstellingen"
    PLATFORMMETADATA = "platformmetadata"
    # ADR-012 Addendum A / ADR-019: beheer van checklist-antwoordconfiguratie.
    CHECKLISTCONFIG = "checklistconfig"
    # ADR-012 Addendum B / ADR-020: beheer van de contract-classificatie-catalogus.
    CONTRACTCONFIG = "contractconfig"
    # ADR-012 Addendum C / ADR-021: beheer van de componentcatalogus.
    COMPONENTCONFIG = "componentconfig"
    # ADR-023 Fase F / F-4: beheer van de relatie-kenmerk-catalogus (dispositie/relatie_rol).
    RELATIEKENMERKCONFIG = "relatiekenmerkconfig"
    # Catalogi-beheer-schuld dichten: vraagbetekenis-markers + partijsoort-catalogus.
    VRAAGBETEKENISCONFIG = "vraagbetekenisconfig"
    PARTIJSOORTCONFIG = "partijsoortconfig"
    # ADR-028: componentclassificatie — componentrol- + BIV-schaal-catalogus.
    COMPONENTROLCONFIG = "componentrolconfig"
    BIVSCHAALCONFIG = "bivschaalconfig"
    # ADR-042: applicatiefunctie-catalogus (het wát-veld op de koppelregel component→proces).
    APPLICATIEFUNCTIECONFIG = "applicatiefunctieconfig"
    # ADR-043: referentiemodel-aanbod (welke modellen LIKARA aanbiedt — platform-gecureerd).
    REFERENTIEMODELCONFIG = "referentiemodelconfig"


KNOWN_PLATFORM_ROLES: frozenset[str] = frozenset(r.value for r in PlatformRol)

_L = frozenset({Actie.LEZEN})
_LAW = frozenset({Actie.LEZEN, Actie.AANMAKEN, Actie.WIJZIGEN})
_LAWV = frozenset({Actie.LEZEN, Actie.AANMAKEN, Actie.WIJZIGEN, Actie.VERWIJDEREN})
_GEEN: frozenset[Actie] = frozenset()

# Platform-rechtenmatrix (LEIDEND — ADR-012 + Addendum A):
#   platformbeheerder: Tenant LAWV · Platforminstellingen LAWV · Platformmetadata L · Checklistconfig LAW
#   platformoperator : Tenant L    · Platforminstellingen —    · Platformmetadata L · Checklistconfig L
# Checklistconfig kent bewust GEEN V: een optie wordt soft-gedeactiveerd (W), nooit hard verwijderd.
PLATFORM_PERMISSIES: dict[PlatformEntiteit, dict[PlatformRol, frozenset[Actie]]] = {
    PlatformEntiteit.TENANT: {
        PlatformRol.PLATFORMBEHEERDER: _LAWV,
        PlatformRol.PLATFORMOPERATOR: _L,
    },
    PlatformEntiteit.PLATFORMINSTELLINGEN: {
        PlatformRol.PLATFORMBEHEERDER: _LAWV,
        PlatformRol.PLATFORMOPERATOR: _GEEN,
    },
    PlatformEntiteit.PLATFORMMETADATA: {
        PlatformRol.PLATFORMBEHEERDER: _L,
        PlatformRol.PLATFORMOPERATOR: _L,
    },
    PlatformEntiteit.CHECKLISTCONFIG: {
        PlatformRol.PLATFORMBEHEERDER: _LAW,
        PlatformRol.PLATFORMOPERATOR: _L,
    },
    # Addendum B: contractcatalogus — beheerder LAW (geen V), operator L.
    PlatformEntiteit.CONTRACTCONFIG: {
        PlatformRol.PLATFORMBEHEERDER: _LAW,
        PlatformRol.PLATFORMOPERATOR: _L,
    },
    # Addendum C: componentcatalogus — beheerder LAW (geen V), operator L.
    PlatformEntiteit.COMPONENTCONFIG: {
        PlatformRol.PLATFORMBEHEERDER: _LAW,
        PlatformRol.PLATFORMOPERATOR: _L,
    },
    # F-4: relatie-kenmerk-catalogus — beheerder LAW (geen V), operator L (soft-deactivate, geen hard delete).
    PlatformEntiteit.RELATIEKENMERKCONFIG: {
        PlatformRol.PLATFORMBEHEERDER: _LAW,
        PlatformRol.PLATFORMOPERATOR: _L,
    },
    # Vraagbetekenis-markers — beheerder LAW (geen V), operator L (soft-deactivate).
    PlatformEntiteit.VRAAGBETEKENISCONFIG: {
        PlatformRol.PLATFORMBEHEERDER: _LAW,
        PlatformRol.PLATFORMOPERATOR: _L,
    },
    # Partijsoort-catalogus (platform-laag) — beheerder LAW (geen V), operator L (soft-deactivate).
    PlatformEntiteit.PARTIJSOORTCONFIG: {
        PlatformRol.PLATFORMBEHEERDER: _LAW,
        PlatformRol.PLATFORMOPERATOR: _L,
    },
    # ADR-028: componentrol-catalogus — beheerder LAW (geen V), operator L (soft-deactivate).
    PlatformEntiteit.COMPONENTROLCONFIG: {
        PlatformRol.PLATFORMBEHEERDER: _LAW,
        PlatformRol.PLATFORMOPERATOR: _L,
    },
    # ADR-028: BIV-schaal-catalogus — beheerder LAW (geen V), operator L (soft-deactivate).
    PlatformEntiteit.BIVSCHAALCONFIG: {
        PlatformRol.PLATFORMBEHEERDER: _LAW,
        PlatformRol.PLATFORMOPERATOR: _L,
    },
    # ADR-042: applicatiefunctie-catalogus — beheerder LAW (geen V), operator L (soft-deactivate).
    PlatformEntiteit.APPLICATIEFUNCTIECONFIG: {
        PlatformRol.PLATFORMBEHEERDER: _LAW,
        PlatformRol.PLATFORMOPERATOR: _L,
    },
    # ADR-043: referentiemodel-aanbod — beheerder LAW (geen V), operator L (soft-deactivate).
    PlatformEntiteit.REFERENTIEMODELCONFIG: {
        PlatformRol.PLATFORMBEHEERDER: _LAW,
        PlatformRol.PLATFORMOPERATOR: _L,
    },
}


def _platform_rol(keycloak_rol: str) -> str | None:
    """Map één Keycloak-rolnaam op een platform-rol, of None (fail-secure)."""
    prefix = settings.keycloak_role_prefix
    if prefix:
        if not keycloak_rol.startswith(prefix):
            return None
        keycloak_rol = keycloak_rol[len(prefix):]
    keycloak_rol = keycloak_rol.lower()
    return keycloak_rol if keycloak_rol in KNOWN_PLATFORM_ROLES else None


def extract_platform_rollen(payload: dict) -> list[str]:
    """Lees de PLATFORM-rollen uit de Keycloak-JWT. Tenant-rollen worden genegeerd."""
    rollen = {p for r in lees_keycloak_rollen(payload) if (p := _platform_rol(r))}
    return sorted(rollen)


def heeft_platform_permissie(
    rollen: Iterable[str], entiteit: PlatformEntiteit, actie: Actie
) -> bool:
    """True alleen als minstens één platform-rol de actie op de entiteit mag."""
    matrix = PLATFORM_PERMISSIES.get(entiteit)
    if not matrix:
        return False
    for rol in rollen:
        if rol in KNOWN_PLATFORM_ROLES and actie in matrix.get(PlatformRol(rol), _GEEN):
            return True
    return False
