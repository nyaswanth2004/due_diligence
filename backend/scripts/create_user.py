"""Create a user from the CLI. Usage:

    .venv\\Scripts\\python -m scripts.create_user --username admin --password secret --role admin --email admin@example.com
"""

import argparse
import getpass
import sys

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal, create_all_tables
from app.models import User

VALID_ROLES = ("admin", "analyst", "viewer")


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a VeritasIQ user.")
    parser.add_argument("--username", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--role", choices=VALID_ROLES, default="viewer")
    parser.add_argument("--password", help="Prompted interactively if omitted.")
    args = parser.parse_args()

    password = args.password or getpass.getpass("Password: ")

    create_all_tables()
    with SessionLocal() as session:
        existing = session.execute(
            select(User).where(
                (User.username == args.username) | (User.email == args.email)
            )
        ).scalar_one_or_none()
        if existing:
            print(f"error: a user with username '{args.username}' or email '{args.email}' already exists", file=sys.stderr)
            return 1

        user = User(
            username=args.username,
            email=args.email,
            password_hash=hash_password(password),
            role=args.role,
        )
        session.add(user)
        session.commit()
        session.refresh(user)

    print(f"created user '{user.username}' (id={user.id}, role={user.role})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
