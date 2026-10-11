import bcrypt

from database.postgres import get_user_by_username


def check_password(username, password):
    """Return the user row if the username and password are correct, otherwise None."""
    user = get_user_by_username(username)
    if user and bcrypt.checkpw(password.encode("utf-8"), user["password_hash"].encode("utf-8")):
        return user
    return None
