import bcrypt

from database.postgres import get_user_by_username


# ============================================================
# IN-MEMORY AUTHENTICATED SESSIONS
# ============================================================

SESSIONS = {}


# ============================================================
# LOGIN
# ============================================================

def register_auth_tools(mcp):

    @mcp.tool()
    def login(username: str, password: str):

        user = get_user_by_username(username)

        if not user:
            return {
                "success": False,
                "message": "Invalid username or password"
            }

        password_valid = bcrypt.checkpw(
            password.encode("utf-8"),
            user["password_hash"].encode("utf-8")
        )

        if not password_valid:
            return {
                "success": False,
                "message": "Invalid username or password"
            }

        session_id = f"{user['id']}:{user['username']}"

        SESSIONS[session_id] = {
            "user_id": user["id"],
            "username": user["username"],
            "role": user["role"]
        }

        return {
            "success": True,
            "session_id": session_id,
            "username": user["username"],
            "role": user["role"],
            "message": "Login successful"
        }


    @mcp.tool()
    def logout(session_id: str):

        if session_id not in SESSIONS:
            return {
                "success": False,
                "message": "Invalid session"
            }

        del SESSIONS[session_id]

        return {
            "success": True,
            "message": "Logout successful"
        }


    @mcp.tool()
    def get_authenticated_user(session_id: str):

        user = SESSIONS.get(session_id)

        if not user:
            return {
                "authenticated": False,
                "message": "Not authenticated"
            }

        return {
            "authenticated": True,
            **user
        }


# ============================================================
# INTERNAL AUTHORIZATION FUNCTIONS
# ============================================================

def require_authentication(session_id):

    user = SESSIONS.get(session_id)

    if not user:
        raise PermissionError(
            "Authentication required. Please login first."
        )

    return user


def require_role(session_id, *allowed_roles):

    user = require_authentication(session_id)

    if user["role"] not in allowed_roles:

        raise PermissionError(
            f"Permission denied. Required role: "
            f"{', '.join(allowed_roles)}"
        )

    return user