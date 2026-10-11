import sys
from getpass import getpass

import bcrypt

from database.postgres import create_user, initialize_database


def add_user(username, password, role):
    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    create_user(username, password_hash, role)
    print(f"{role} created: {username}")


if __name__ == "__main__":
    initialize_database()

    if len(sys.argv) == 3:
        # python create_user.py <username> <SALESPERSON|MANAGER>   (asks for the password)
        add_user(sys.argv[1], getpass("Password: "), sys.argv[2].upper())
    else:
        # Demo users - change these passwords before real use.
        add_user("salesperson", "salesperson123", "SALESPERSON")
        add_user("manager", "manager123", "MANAGER")
