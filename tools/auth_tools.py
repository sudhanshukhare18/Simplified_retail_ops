import secrets
import time

from services.auth_service import check_password

SESSION_SECONDS = 8 * 3600

# session_id -> {"user_id", "username", "role", "expires"}
# Kept in memory, so everyone has to log in again after the server restarts.
SESSIONS = {}


def _get_session(session_id):
    """The logged-in user for this session, or None if it is unknown or expired."""
    session = SESSIONS.get(session_id)
    if session and session["expires"] < time.time():
        del SESSIONS[session_id]
        return None
    return session


def require_role(session_id, *allowed_roles):
    """Raise PermissionError unless the session belongs to a user with an allowed role."""
    user = _get_session(session_id)
    if not user:
        raise PermissionError("Authentication required. Please login first.")
    if user["role"].upper() not in [role.upper() for role in allowed_roles]:
        raise PermissionError(f"Permission denied. Required role: {', '.join(allowed_roles)}")
    return user


def register_auth_tools(mcp):

    @mcp.tool()
    def login(username: str, password: str):
        """Log in as a salesperson or manager. Returns a session_id to pass to every other tool."""
        user = check_password(username, password)
        if not user:
            return {"success": False, "message": "Invalid username or password"}

        session_id = secrets.token_urlsafe(16)  # random, cannot be guessed
        SESSIONS[session_id] = {
            "user_id": user["id"],
            "username": user["username"],
            "role": user["role"],
            "expires": time.time() + SESSION_SECONDS,
        }
        return {
            "success": True,
            "session_id": session_id,
            "username": user["username"],
            "role": user["role"],
            "message": "Login successful",
        }

    @mcp.tool()
    def logout(session_id: str):
        """End a login session."""
        if SESSIONS.pop(session_id, None) is None:
            return {"success": False, "message": "Invalid session"}
        return {"success": True, "message": "Logout successful"}

    @mcp.tool()
    def get_authenticated_user(session_id: str):
        """Check who a session belongs to."""
        user = _get_session(session_id)
        if not user:
            return {"authenticated": False, "message": "Not authenticated"}
        return {
            "authenticated": True,
            "user_id": user["user_id"],
            "username": user["username"],
            "role": user["role"],
        }
