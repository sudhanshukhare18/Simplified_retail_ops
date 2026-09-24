# create_users.py

import bcrypt
from database.postgres import get_connection


def create_user(username, password, role):
    password_hash = bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (username, password_hash, role)
                VALUES (%s, %s, %s)
                ON CONFLICT (username)
                DO UPDATE SET
                    password_hash = EXCLUDED.password_hash,
                    role = EXCLUDED.role
                """,
                (username, password_hash, role)
            )

        conn.commit()

    print(f"{role} created: {username}")


if __name__ == "__main__":

    create_user(
        username="salesperson",
        password="salesperson123",
        role="SALESPERSON"
    )

    create_user(
        username="manager",
        password="manager123",
        role="MANAGER"
    )

    print("\nUsers created successfully.")