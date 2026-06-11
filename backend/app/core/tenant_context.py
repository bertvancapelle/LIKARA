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

# Geen default-waarde "" — afwezigheid = None ⇒ de hook kan fail-fast onderscheiden.
_tenant_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "cd_tenant_id", default=None
)


def zet_tenant_context(tenant_id) -> contextvars.Token:
    """Zet de tenant-context voor de huidige (async-)context. Retourneert een token
    waarmee de aanroeper hem weer reset (verplicht aan het eind van het request)."""
    return _tenant_id.set(None if tenant_id is None else str(tenant_id))


def reset_tenant_context(token: contextvars.Token) -> None:
    _tenant_id.reset(token)


def huidige_tenant_id() -> str | None:
    return _tenant_id.get()
