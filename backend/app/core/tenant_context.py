"""Request-scoped tenant-context (RLS) via een ContextVar (CD048).

De tenant-id wordt per request gezet (tenant-middleware) resp. per worker-/seed-run
(`get_worker_session`), en door de SQLAlchemy `after_begin`-hook in `app.core.database`
bij **élke transactie** transactie-lokaal toegepast:
`SELECT set_config('app.tenant_id', :tid, true)`.

Transactie-lokaal (`is_local=true`) ⇒ de context verdwijnt automatisch bij commit/rollback
en lekt **niet** naar de volgende pool-checkout. Daarmee is het CD047-mechanisme verholpen
(een post-commit `refresh()` op een opnieuw-uitgecheckte verbinding krijgt opnieuw context)
én het cross-tenant-restrisico structureel gesloten (geen rest-context op poolverbindingen).
"""
import contextvars
import uuid

# Geen default-waarde "" — afwezigheid = None ⇒ de hook kan fail-fast onderscheiden.
_tenant_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "cd_tenant_id", default=None
)

# ADR-006 — actor-identiteit + correlatie-id van de huidige handeling (request/seed/
# platform). De audit-capture-hook (app.core.audit) leest deze per flush. Afwezig =
# None ⇒ de hook valt terug op `system:onbekend` resp. een verse correlatie-id.
_actor_sub: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "cd_actor_sub", default=None
)
_actor_email: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "cd_actor_email", default=None
)
_correlatie_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "cd_correlatie_id", default=None
)


def zet_tenant_context(tenant_id) -> contextvars.Token:
    """Zet de tenant-context voor de huidige (async-)context. Retourneert een token
    waarmee de aanroeper hem weer reset (verplicht aan het eind van het request)."""
    return _tenant_id.set(None if tenant_id is None else str(tenant_id))


def reset_tenant_context(token: contextvars.Token) -> None:
    _tenant_id.reset(token)


def huidige_tenant_id() -> str | None:
    return _tenant_id.get()


def zet_audit_context(
    actor_sub: str, actor_email: str | None = None, correlatie_id: str | None = None
) -> list[contextvars.Token]:
    """Zet de actor + correlatie-id voor de huidige handeling (ADR-006 Besluit 3).

    Eén `correlatie_id` per handeling bindt de driver-mutatie aan haar afgeleide
    gevolgen (lifecycle/blokkade) — die delen dezelfde context. Ontbreekt er een
    `correlatie_id`, dan wordt er één gegenereerd. Retourneert tokens voor reset.
    """
    if correlatie_id is None:
        correlatie_id = str(uuid.uuid4())
    return [
        _actor_sub.set(actor_sub),
        _actor_email.set(actor_email),
        _correlatie_id.set(correlatie_id),
    ]


def reset_audit_context(tokens: list[contextvars.Token]) -> None:
    # Reset in omgekeerde volgorde (sub, email, correlatie → correlatie, email, sub).
    _correlatie_id.reset(tokens[2])
    _actor_email.reset(tokens[1])
    _actor_sub.reset(tokens[0])


def huidige_actor() -> tuple[str | None, str | None]:
    """(actor_sub, actor_email) van de huidige handeling, of (None, None)."""
    return _actor_sub.get(), _actor_email.get()


def huidige_correlatie_id() -> str | None:
    return _correlatie_id.get()
