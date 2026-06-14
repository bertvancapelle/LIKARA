"""Service-laag — audit-spoor lezen (ADR-006 Fase E).

Read-only. Levert **correlatie-gegroepeerde gebeurtenissen**: per `correlatie_id` één
gebeurtenis met de driver + al haar afgeleide gevolgen (lifecycle/blokkade), gebonden
via dat correlatie-id. Tenant-scoped (RLS + expliciete `tenant_id`-filter, dubbele
bescherming). Keyset-paginering over de gebeurtenissen (anker = vroegste tijdstip per
groep, aflopend = nieuwste eerst); filterbaar op actor / entiteit-type / component /
periode.

De groepering haalt voor elke gepaginate `correlatie_id` de **volledige** groep op —
ook records die zelf niet aan het filter voldoen (de afgeleide gevolgen horen erbij).
"""
import base64
import uuid
from datetime import datetime

from sqlalchemy import Text, and_, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.models import AuditLog

_STANDAARD_LIMIT = 25
_MAX_LIMIT = 100


def _tenant_uuid(tenant_id) -> uuid.UUID:
    return tenant_id if isinstance(tenant_id, uuid.UUID) else uuid.UUID(str(tenant_id))


def _encode_cursor(anker: datetime, correlatie_id) -> str:
    rauw = f"{anker.isoformat()}|{correlatie_id}"
    return base64.urlsafe_b64encode(rauw.encode("utf-8")).decode("ascii")


def _decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    """`(anker_tijdstip, correlatie_id)`; `ValueError` bij een misvormde cursor."""
    if not cursor:
        raise ValueError("lege cursor")
    try:
        rauw = base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8")
        anker_str, corr_str = rauw.rsplit("|", 1)
        return datetime.fromisoformat(anker_str), uuid.UUID(corr_str)
    except (ValueError, TypeError, UnicodeDecodeError) as exc:
        raise ValueError("ongeldige cursor") from exc


def _record_filters(tid: uuid.UUID, *, actor, entiteit_type, component_id, van, tot):
    """Record-niveau filterclausules (een groep kwalificeert als ≥1 record matcht)."""
    clauses = [AuditLog.tenant_id == tid]
    if actor:
        clauses.append(AuditLog.actor_sub == actor)
    if entiteit_type:
        clauses.append(AuditLog.entiteit_type == entiteit_type)
    if van is not None:
        clauses.append(AuditLog.tijdstip >= van)
    if tot is not None:
        clauses.append(AuditLog.tijdstip <= tot)
    if component_id is not None:
        cid = str(component_id)
        # Een component-gebeurtenis: de entiteit ís het component (component/applicatie/
        # component_profiel/blokkade: entiteit_id == component_id) óf het component_id
        # zit in de diff (checklistscore/blokkade dragen component_id in `wijziging`).
        clauses.append(
            or_(
                cast(AuditLog.entiteit_id, Text) == cid,
                AuditLog.wijziging["component_id"]["nieuw"].astext == cid,
                AuditLog.wijziging["component_id"]["oud"].astext == cid,
            )
        )
    return clauses


async def lijst(
    session: AsyncSession,
    tenant_id,
    *,
    limit: int = _STANDAARD_LIMIT,
    after: str | None = None,
    actor: str | None = None,
    entiteit_type: str | None = None,
    component_id: uuid.UUID | None = None,
    van: datetime | None = None,
    tot: datetime | None = None,
) -> tuple[list[dict], str | None]:
    """Correlatie-gegroepeerde gebeurtenissen, nieuwste eerst. Cursor-mismatch/-corruptie
    ⇒ `ValueError` (route ⇒ 400)."""
    limit = max(1, min(limit, _MAX_LIMIT))
    tid = _tenant_uuid(tenant_id)

    filters = _record_filters(
        tid, actor=actor, entiteit_type=entiteit_type, component_id=component_id,
        van=van, tot=tot,
    )

    # (1) Pagineer de groepen: per correlatie_id het anker (vroegste tijdstip = driver),
    # geordend nieuwste-eerst met correlatie_id als stabiele tiebreaker.
    anker = func.min(AuditLog.tijdstip).label("anker")
    groep_q = (
        select(AuditLog.correlatie_id, anker)
        .where(and_(*filters))
        .group_by(AuditLog.correlatie_id)
    )
    if after:
        cur_anker, cur_corr = _decode_cursor(after)
        groep_q = groep_q.having(
            or_(
                anker < cur_anker,
                and_(anker == cur_anker, AuditLog.correlatie_id < cur_corr),
            )
        )
    groep_q = groep_q.order_by(anker.desc(), AuditLog.correlatie_id.desc()).limit(limit + 1)
    groep_rijen = list((await session.execute(groep_q)).all())

    heeft_meer = len(groep_rijen) > limit
    pagina = groep_rijen[:limit]
    if not pagina:
        return [], None

    corr_ids = [r.correlatie_id for r in pagina]

    # (2) Haal de VOLLEDIGE groepen op (incl. afgeleide records die niet aan het filter
    # voldoen), chronologisch per groep (driver eerst).
    recs = list(
        (
            await session.execute(
                select(AuditLog)
                .where(AuditLog.tenant_id == tid, AuditLog.correlatie_id.in_(corr_ids))
                .order_by(AuditLog.correlatie_id, AuditLog.tijdstip.asc(), AuditLog.id.asc())
            )
        )
        .scalars()
        .all()
    )
    per_corr: dict = {}
    for rec in recs:
        per_corr.setdefault(rec.correlatie_id, []).append(rec)

    gebeurtenissen: list[dict] = []
    for r in pagina:
        records = per_corr.get(r.correlatie_id, [])
        driver = records[0] if records else None
        gebeurtenissen.append({
            "correlatie_id": r.correlatie_id,
            "tijdstip": r.anker,
            "actor_sub": driver.actor_sub if driver else None,
            "actor_email": driver.actor_email if driver else None,
            "records": records,
        })

    volgende = (
        _encode_cursor(pagina[-1].anker, pagina[-1].correlatie_id) if heeft_meer else None
    )
    return gebeurtenissen, volgende
