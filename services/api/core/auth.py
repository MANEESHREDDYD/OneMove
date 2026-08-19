import os
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from urllib.parse import urljoin

import jwt
from fastapi import Depends, HTTPException, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from supabase import Client, create_client

security = HTTPBearer(auto_error=False)

_ASYMMETRIC_ALGORITHMS = frozenset({"ES256", "RS256"})


def _allowed_algorithms() -> set[str]:
    configured = os.environ.get("SUPABASE_JWT_ALGORITHMS")
    if configured:
        return {item.strip() for item in configured.split(",") if item.strip()}

    legacy_algorithm = os.environ.get("SUPABASE_JWT_ALGORITHM")
    if legacy_algorithm:
        return {legacy_algorithm}

    # Supabase projects can issue new asymmetric tokens while legacy sessions
    # remain HS256 during a signing-key migration. The key source is selected
    # independently below, so allowing both cannot create an algorithm-confusion
    # path between a public key and the legacy shared secret.
    return {"ES256", "RS256", "HS256"}


def _expected_issuer() -> str | None:
    configured = os.environ.get("SUPABASE_JWT_ISSUER")
    if configured:
        return configured.rstrip("/")

    supabase_url = os.environ.get("SUPABASE_URL")
    if not supabase_url:
        return None
    return urljoin(f"{supabase_url.rstrip('/')}/", "auth/v1")


@lru_cache(maxsize=4)
def _jwks_client(jwks_url: str) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(
        jwks_url,
        cache_keys=True,
        cache_jwk_set=True,
        lifespan=600,
        timeout=5,
    )


def _verification_key(token: str, algorithm: str):
    if algorithm == "HS256":
        secret = os.environ.get("SUPABASE_JWT_SECRET")
        if not secret:
            raise HTTPException(status_code=500, detail="Supabase JWT verifier is not configured")
        return secret

    public_key = os.environ.get("SUPABASE_JWT_PUBLIC_KEY")
    if public_key:
        return public_key

    supabase_url = os.environ.get("SUPABASE_URL")
    jwks_url = os.environ.get("SUPABASE_JWKS_URL")
    if not jwks_url and supabase_url:
        jwks_url = urljoin(f"{supabase_url.rstrip('/')}/", "auth/v1/.well-known/jwks.json")
    if not jwks_url:
        raise HTTPException(status_code=500, detail="Supabase JWKS verifier is not configured")

    try:
        return _jwks_client(jwks_url).get_signing_key_from_jwt(token).key
    except jwt.PyJWKClientConnectionError as exc:
        raise HTTPException(
            status_code=503,
            detail="Token verification temporarily unavailable",
        ) from exc
    except jwt.PyJWKClientError as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc


def verify_token(token: str) -> dict:
    expected_issuer = _expected_issuer()
    expected_audience = os.environ.get("SUPABASE_JWT_AUDIENCE", "authenticated")

    try:
        algorithm = jwt.get_unverified_header(token).get("alg")
        if algorithm not in _allowed_algorithms() or algorithm not in _ASYMMETRIC_ALGORITHMS | {"HS256"}:
            raise jwt.InvalidAlgorithmError("JWT signing algorithm is not allowed")

        verification_key = _verification_key(token, algorithm)
        decode_kwargs = {
            "algorithms": [algorithm],
            "audience": expected_audience,
        }
        if expected_issuer:
            decode_kwargs["issuer"] = expected_issuer

        payload = jwt.decode(token, verification_key, **decode_kwargs)

        if "sub" not in payload:
            raise HTTPException(status_code=401, detail="Invalid token: missing sub")

        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidIssuerError:
        raise HTTPException(status_code=401, detail="Invalid token: wrong issuer")
    except jwt.InvalidAudienceError:
        raise HTTPException(status_code=401, detail="Invalid token: wrong audience")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


# ---------------------------------------------------------------------------
# Workspace tenancy
# ---------------------------------------------------------------------------


class WorkspaceRole(str, Enum):
    """Mirrors the zonepilot_workspace_role enum created by migration
    20260817000000_zonepilot_temporal_and_tenancy.sql."""

    OWNER = "OWNER"
    ADMIN = "ADMIN"
    RESEARCHER = "RESEARCHER"
    VIEWER = "VIEWER"
    INTEGRATION_USER = "INTEGRATION_USER"
    COLLECTOR = "COLLECTOR"


#: Roles that may administer a workspace: change its metadata or its membership.
WORKSPACE_ADMIN_ROLES: frozenset[WorkspaceRole] = frozenset({WorkspaceRole.OWNER, WorkspaceRole.ADMIN})

#: Roles that may read the workspace evidence corpus. COLLECTOR is deliberately
#: excluded: it is a write-only acquisition identity, so it must not be able to
#: read the corpus or the workspace's user directory. The same split is encoded
#: in the RLS policies, so the two layers agree.
WORKSPACE_READ_ROLES: frozenset[WorkspaceRole] = frozenset(
    {
        WorkspaceRole.OWNER,
        WorkspaceRole.ADMIN,
        WorkspaceRole.RESEARCHER,
        WorkspaceRole.VIEWER,
        WorkspaceRole.INTEGRATION_USER,
    }
)


@dataclass(frozen=True)
class WorkspacePrincipal:
    """A trusted (user, workspace, role) triple.

    Every field is resolved server-side from the verified session subject and
    the workspace_members table. Nothing here is taken from a request header or
    from an unverified token claim.
    """

    user_id: str
    workspace_id: str
    role: WorkspaceRole

    @property
    def is_workspace_admin(self) -> bool:
        return self.role in WORKSPACE_ADMIN_ROLES


@lru_cache(maxsize=4)
def _membership_client(url: str, service_key: str) -> Client:
    return create_client(url, service_key)


def service_client() -> Client:
    """RLS-bypassing client for server-side tenancy work.

    Membership has to be read with an identity that is not itself subject to
    the workspace policies, otherwise the answer to "is this user a member"
    would depend on the very membership being determined.

    Because this client bypasses RLS, every call site must scope its query by a
    workspace id that came out of :func:`resolve_workspace_principal` and never
    by a value taken from the request.
    """

    url = os.environ.get("SUPABASE_URL")
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not service_key:
        raise _membership_unavailable()
    try:
        return _membership_client(url, service_key)
    except Exception as exc:
        raise _membership_unavailable() from exc


def _membership_unavailable() -> HTTPException:
    # Fail closed. A membership lookup that cannot be completed is not a reason
    # to serve workspace data; it is a reason to refuse.
    return HTTPException(status_code=403, detail="Workspace membership could not be verified")


def workspace_memberships(user_id: str) -> tuple[WorkspacePrincipal, ...]:
    """Return every workspace the verified subject provably belongs to."""
    db_dsn = None
    try:
        from services.common.db_dsn import get_database_dsn

        db_dsn = get_database_dsn()
    except Exception:
        pass

    if db_dsn:
        import psycopg
        from psycopg.rows import dict_row

        try:
            with psycopg.connect(db_dsn, row_factory=dict_row, connect_timeout=5) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT workspace_id, role FROM public.workspace_members WHERE user_id = %s::uuid",
                        (user_id,),
                    )
                    rows = cur.fetchall()
                    memberships: list[WorkspacePrincipal] = []
                    for row in rows:
                        try:
                            role = WorkspaceRole(row["role"])
                        except (KeyError, ValueError):
                            continue
                        memberships.append(
                            WorkspacePrincipal(
                                user_id=user_id,
                                workspace_id=str(row["workspace_id"]),
                                role=role,
                            )
                        )
                    return tuple(memberships)
        except Exception:
            pass

    try:
        client = service_client()
        response = client.table("workspace_members").select("workspace_id, role").eq("user_id", user_id).execute()
        memberships = []
        for row in response.data or []:
            try:
                role = WorkspaceRole(row["role"])
            except (KeyError, ValueError):
                continue
            memberships.append(WorkspacePrincipal(user_id=user_id, workspace_id=str(row["workspace_id"]), role=role))
        return tuple(memberships)
    except Exception as exc:
        raise _membership_unavailable() from exc


def _requested_workspace_id(request: Request, payload: dict) -> str | None:
    """Read the *selector* for which workspace the caller wants to act in.

    A header or a token claim can only ever select among workspaces the caller
    already belongs to; membership is verified separately and server-side. A
    value that is not even a UUID is rejected here so a malformed selector can
    never reach the database.
    """

    candidate = request.headers.get("x-workspace-id") or payload.get("workspace_id")
    if not isinstance(candidate, str) or not candidate.strip():
        return None
    try:
        return str(uuid.UUID(candidate.strip()))
    except ValueError:
        raise HTTPException(status_code=403, detail="Invalid workspace selector")


def resolve_workspace_principal(request: Request, payload: dict) -> WorkspacePrincipal:
    """Resolve the trusted workspace context for a verified session.

    Fails closed on every ambiguous or unproven case: no membership, a selector
    naming a workspace the caller does not belong to, or several memberships
    with nothing selecting between them.
    """

    user_id = payload.get("sub")
    if not isinstance(user_id, str) or not user_id:
        raise HTTPException(status_code=401, detail="Invalid token: missing sub")

    requested = _requested_workspace_id(request, payload)
    memberships = workspace_memberships(user_id)

    if requested is not None:
        for membership in memberships:
            if membership.workspace_id == requested:
                return membership
        raise HTTPException(status_code=403, detail="Not a member of the requested workspace")

    if len(memberships) == 1:
        return memberships[0]
    if not memberships:
        raise HTTPException(status_code=403, detail="No workspace membership")
    raise HTTPException(status_code=403, detail="Workspace selection required")


def get_current_user(request: Request, credentials: HTTPAuthorizationCredentials = Security(security)) -> dict:
    """Verify the session and, when a workspace is selected, prove membership.

    The previous implementation compared a client header against an unverified
    token claim and skipped the check whenever either was absent, and consulted
    a role attribute on ``request.state`` that no production code ever set.
    Both branches were unreachable in production. They are gone: the only
    workspace decision made here is a server-side membership lookup, and role
    checks live in :func:`require_workspace_role`, which real routes depend on.
    """

    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = verify_token(credentials.credentials)

    # Only pay for the membership lookup when the caller actually selected a
    # workspace. Routes that need a workspace unconditionally depend on
    # get_workspace_principal instead.
    if request.headers.get("x-workspace-id") or payload.get("workspace_id"):
        principal = resolve_workspace_principal(request, payload)
        request.state.workspace_principal = principal
        return {
            **payload,
            "workspace_id": principal.workspace_id,
            "workspace_role": principal.role.value,
        }

    return payload


def get_workspace_principal(
    request: Request, credentials: HTTPAuthorizationCredentials = Security(security)
) -> WorkspacePrincipal:
    """Dependency for any route whose data belongs to exactly one workspace."""

    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = verify_token(credentials.credentials)
    principal = resolve_workspace_principal(request, payload)
    request.state.workspace_principal = principal
    return principal


def require_workspace_role(
    *allowed: WorkspaceRole,
) -> Callable[[WorkspacePrincipal], WorkspacePrincipal]:
    """Build a dependency that admits only the listed workspace roles."""

    permitted = frozenset(allowed)
    if not permitted:
        raise ValueError("require_workspace_role needs at least one role")

    def dependency(
        principal: WorkspacePrincipal = Depends(get_workspace_principal),
    ) -> WorkspacePrincipal:
        if principal.role not in permitted:
            raise HTTPException(
                status_code=403,
                detail=f"Role {principal.role.value} is not permitted for this operation",
            )
        return principal

    return dependency


def get_participant_id(credentials: HTTPAuthorizationCredentials = Security(security)) -> str:
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = credentials.credentials
    payload = verify_token(token)
    return payload["sub"]


def get_supabase(credentials: HTTPAuthorizationCredentials = Security(security)) -> Client:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_ANON_KEY")

    if not url or not key:
        raise HTTPException(status_code=500, detail="Supabase environment variables missing")
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = credentials.credentials
    verify_token(token)

    try:
        client = create_client(url, key)
        client.postgrest.auth(token)
        return client
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid authentication token")
