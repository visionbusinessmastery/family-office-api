import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text

from auth.utils import get_current_user, get_user_id
from database import engine


router = APIRouter()
_workspace_schema_ready = False


def ensure_workspace_tables(conn):
    global _workspace_schema_ready

    if _workspace_schema_ready:
        return

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS workspaces (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            owner_user_id INTEGER NOT NULL,
            plan TEXT DEFAULT 'FREE',
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """))

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS workspace_members (
            id SERIAL PRIMARY KEY,
            workspace_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL DEFAULT 'member',
            status TEXT NOT NULL DEFAULT 'active',
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """))

    conn.execute(text("""
        CREATE UNIQUE INDEX IF NOT EXISTS workspace_members_unique
        ON workspace_members(workspace_id, user_id)
    """))

    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS workspace_invitations (
            id SERIAL PRIMARY KEY,
            workspace_id INTEGER NOT NULL,
            email TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'member',
            token TEXT NOT NULL UNIQUE,
            status TEXT NOT NULL DEFAULT 'pending',
            invited_by_user_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT NOW(),
            accepted_at TIMESTAMP
        )
    """))

    _workspace_schema_ready = True


def require_user_id(conn, email: str):
    if not email or email == "anonymous":
        raise HTTPException(status_code=401, detail="Session invalide")

    user_id = get_user_id(conn, email)

    if not user_id:
        raise HTTPException(status_code=404, detail="User not found")

    return user_id


def ensure_personal_workspace(conn, user_id: int, email: str):
    ensure_workspace_tables(conn)

    row = conn.execute(text("""
        SELECT w.id
        FROM workspaces w
        JOIN workspace_members wm ON wm.workspace_id = w.id
        WHERE wm.user_id = :user_id
        ORDER BY
            CASE WHEN w.owner_user_id = :user_id THEN 0 ELSE 1 END,
            w.id ASC
        LIMIT 1
    """), {"user_id": user_id}).fetchone()

    if row:
        return row.id

    workspace = conn.execute(text("""
        INSERT INTO workspaces (name, owner_user_id)
        VALUES (:name, :owner_user_id)
        RETURNING id
    """), {
        "name": "Family Office",
        "owner_user_id": user_id,
    }).fetchone()

    conn.execute(text("""
        INSERT INTO workspace_members (workspace_id, user_id, role, status)
        VALUES (:workspace_id, :user_id, 'owner', 'active')
    """), {
        "workspace_id": workspace.id,
        "user_id": user_id,
    })

    return workspace.id


def require_workspace_role(conn, workspace_id: int, user_id: int, roles=None):
    roles = roles or ["owner", "admin"]

    member = conn.execute(text("""
        SELECT role
        FROM workspace_members
        WHERE workspace_id = :workspace_id
        AND user_id = :user_id
        AND status = 'active'
    """), {
        "workspace_id": workspace_id,
        "user_id": user_id,
    }).fetchone()

    if not member:
        raise HTTPException(status_code=403, detail="Workspace access denied")

    if member.role not in roles:
        raise HTTPException(status_code=403, detail="Insufficient workspace role")

    return member.role


def resolve_workspace_context(conn, request, email: str, write: bool = False):
    actor_user_id = require_user_id(conn, email)
    ensure_workspace_tables(conn)

    workspace_header = request.headers.get("x-workspace-id")

    if workspace_header:
        try:
            workspace_id = int(workspace_header)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="Invalid workspace id")
    else:
        workspace_id = ensure_personal_workspace(conn, actor_user_id, email)

    workspace = conn.execute(text("""
        SELECT
            w.id,
            w.owner_user_id,
            owner.email AS owner_email,
            wm.role
        FROM workspaces w
        JOIN workspace_members wm ON wm.workspace_id = w.id
        JOIN users owner ON owner.id = w.owner_user_id
        WHERE w.id = :workspace_id
        AND wm.user_id = :actor_user_id
        AND wm.status = 'active'
    """), {
        "workspace_id": workspace_id,
        "actor_user_id": actor_user_id,
    }).fetchone()

    if not workspace:
        raise HTTPException(status_code=403, detail="Workspace access denied")

    if write and workspace.role == "viewer":
        raise HTTPException(status_code=403, detail="Workspace is read only")

    return {
        "workspace_id": workspace.id,
        "actor_user_id": actor_user_id,
        "user_id": workspace.owner_user_id,
        "email": workspace.owner_email,
        "role": workspace.role,
    }


def serialize_workspace(row, members):
    return {
        "id": row.id,
        "name": row.name,
        "plan": row.plan,
        "role": row.role,
        "owner_user_id": row.owner_user_id,
        "members": members,
    }


@router.get("/")
def list_workspaces(email: str = Depends(get_current_user)):
    with engine.begin() as conn:
        user_id = require_user_id(conn, email)
        active_workspace_id = ensure_personal_workspace(conn, user_id, email)

        rows = conn.execute(text("""
            SELECT
                w.id,
                w.name,
                w.plan,
                w.owner_user_id,
                wm.role
            FROM workspaces w
            JOIN workspace_members wm ON wm.workspace_id = w.id
            WHERE wm.user_id = :user_id
            AND wm.status = 'active'
            ORDER BY w.id ASC
        """), {"user_id": user_id}).fetchall()

        workspaces = []

        for row in rows:
            members = conn.execute(text("""
                SELECT u.email, wm.role, wm.status, wm.created_at
                FROM workspace_members wm
                JOIN users u ON u.id = wm.user_id
                WHERE wm.workspace_id = :workspace_id
                ORDER BY
                    CASE wm.role WHEN 'owner' THEN 0 WHEN 'admin' THEN 1 ELSE 2 END,
                    u.email ASC
            """), {"workspace_id": row.id}).fetchall()

            workspaces.append(serialize_workspace(row, [
                {
                    "email": member.email,
                    "role": member.role,
                    "status": member.status,
                    "created_at": member.created_at.isoformat() if member.created_at else None,
                }
                for member in members
            ]))

    return {
        "active_workspace_id": active_workspace_id,
        "workspaces": workspaces,
    }


@router.post("/")
def create_workspace(data: dict, email: str = Depends(get_current_user)):
    name = (data.get("name") or "Family Office").strip()

    with engine.begin() as conn:
        user_id = require_user_id(conn, email)
        ensure_workspace_tables(conn)

        workspace = conn.execute(text("""
            INSERT INTO workspaces (name, owner_user_id)
            VALUES (:name, :owner_user_id)
            RETURNING id
        """), {
            "name": name,
            "owner_user_id": user_id,
        }).fetchone()

        conn.execute(text("""
            INSERT INTO workspace_members (workspace_id, user_id, role, status)
            VALUES (:workspace_id, :user_id, 'owner', 'active')
        """), {
            "workspace_id": workspace.id,
            "user_id": user_id,
        })

    return {"status": "created", "workspace_id": workspace.id}


@router.post("/{workspace_id}/invite")
def invite_member(
    workspace_id: int,
    data: dict,
    email: str = Depends(get_current_user),
):
    invited_email = (data.get("email") or "").strip().lower()
    role = (data.get("role") or "member").strip().lower()

    if not invited_email:
        raise HTTPException(status_code=400, detail="Email requis")

    if role not in ["admin", "member", "viewer"]:
        raise HTTPException(status_code=400, detail="Role invalide")

    with engine.begin() as conn:
        user_id = require_user_id(conn, email)
        ensure_workspace_tables(conn)
        require_workspace_role(conn, workspace_id, user_id)

        token = secrets.token_urlsafe(32)

        conn.execute(text("""
            INSERT INTO workspace_invitations (
                workspace_id,
                email,
                role,
                token,
                invited_by_user_id
            )
            VALUES (
                :workspace_id,
                :email,
                :role,
                :token,
                :invited_by_user_id
            )
        """), {
            "workspace_id": workspace_id,
            "email": invited_email,
            "role": role,
            "token": token,
            "invited_by_user_id": user_id,
        })

    return {
        "status": "invited",
        "token": token,
        "invite_url": f"/dashboard?workspace_invite={token}",
    }


@router.post("/accept-invite")
def accept_invite(data: dict, email: str = Depends(get_current_user)):
    token = data.get("token")

    if not token:
        raise HTTPException(status_code=400, detail="Token requis")

    with engine.begin() as conn:
        user_id = require_user_id(conn, email)
        ensure_workspace_tables(conn)

        invitation = conn.execute(text("""
            SELECT id, workspace_id, email, role, status
            FROM workspace_invitations
            WHERE token = :token
        """), {"token": token}).fetchone()

        if not invitation:
            raise HTTPException(status_code=404, detail="Invitation not found")

        if invitation.status != "pending":
            raise HTTPException(status_code=400, detail="Invitation deja utilisee")

        if invitation.email.lower() != email.lower():
            raise HTTPException(status_code=403, detail="Invitation email mismatch")

        conn.execute(text("""
            INSERT INTO workspace_members (workspace_id, user_id, role, status)
            VALUES (:workspace_id, :user_id, :role, 'active')
            ON CONFLICT (workspace_id, user_id)
            DO UPDATE SET role = EXCLUDED.role, status = 'active', updated_at = NOW()
        """), {
            "workspace_id": invitation.workspace_id,
            "user_id": user_id,
            "role": invitation.role,
        })

        conn.execute(text("""
            UPDATE workspace_invitations
            SET status = 'accepted', accepted_at = NOW()
            WHERE id = :id
        """), {"id": invitation.id})

    return {
        "status": "accepted",
        "workspace_id": invitation.workspace_id,
    }


@router.delete("/{workspace_id}/members/{member_email}")
def remove_member(
    workspace_id: int,
    member_email: str,
    email: str = Depends(get_current_user),
):
    with engine.begin() as conn:
        user_id = require_user_id(conn, email)
        ensure_workspace_tables(conn)
        require_workspace_role(conn, workspace_id, user_id)

        target_id = require_user_id(conn, member_email.lower())

        workspace = conn.execute(text("""
            SELECT owner_user_id FROM workspaces WHERE id = :workspace_id
        """), {"workspace_id": workspace_id}).fetchone()

        if workspace and workspace.owner_user_id == target_id:
            raise HTTPException(status_code=400, detail="Owner cannot be removed")

        conn.execute(text("""
            UPDATE workspace_members
            SET status = 'removed', updated_at = NOW()
            WHERE workspace_id = :workspace_id
            AND user_id = :target_id
        """), {
            "workspace_id": workspace_id,
            "target_id": target_id,
        })

    return {"status": "removed"}
