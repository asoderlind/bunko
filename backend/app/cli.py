"""Small admin CLI: user management and first-run seeding."""

from __future__ import annotations

import argparse
import getpass
import sys

from sqlalchemy import select

from app.auth import hash_password
from app.config import get_settings
from app.db import SessionLocal, engine
from app.models import AppUser, ProviderProfile, Tag


def get_or_create_user(username: str, password: str) -> AppUser:
    with SessionLocal() as session:
        user = session.scalars(select(AppUser).where(AppUser.username == username)).first()
        if user is None:
            user = AppUser(username=username, password_hash=hash_password(password))
            session.add(user)
        else:
            user.password_hash = hash_password(password)
        session.commit()
        return user


def seed() -> None:
    """Create the provider profile from env, if none exists."""
    settings = get_settings()
    if not settings.ollama_base_url:
        print("OLLAMA_BASE_URL not set; skipping provider seed")
        return
    with SessionLocal() as session:
        if session.scalars(select(ProviderProfile)).first():
            print("provider profile already exists; not overwriting")
            return
        session.add(
            ProviderProfile(
                label="Ollama (tailnet MacBook)",
                base_url=settings.ollama_base_url,
                model=settings.ollama_model,
                api_key_env="OLLAMA_API_KEY",
                is_default=True,
                is_local=True,
                enabled=True,
            )
        )
        session.commit()
        print(f"seeded provider at {settings.ollama_base_url}")


def init_db() -> None:
    """Create tables if missing, then stamp the Alembic baseline.

    Pragmatic for a single-user app: SQLAlchemy's metadata is the source of
    truth for the baseline schema, and Alembic tracks anything after it.
    """
    from alembic import command
    from alembic.config import Config

    from app.models import Base

    Base.metadata.create_all(bind=engine)
    cfg = Config("alembic.ini")
    command.stamp(cfg, "0001_baseline")
    print("database initialised and stamped at 0001_baseline")


def main() -> int:
    parser = argparse.ArgumentParser(prog="app.cli")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_user = sub.add_parser("set-password", help="create or update a user")
    p_user.add_argument("--username", default="axel")

    sub.add_parser("init-db", help="create tables and stamp the alembic baseline")
    sub.add_parser("seed", help="seed the provider profile from env")
    sub.add_parser("tags", help="list tags")

    args = parser.parse_args()

    if args.cmd == "set-password":
        pw = getpass.getpass("Password: ")
        if pw != getpass.getpass("Repeat: "):
            print("Passwords do not match", file=sys.stderr)
            return 1
        user = get_or_create_user(args.username, pw)
        print(f"password set for {user.username}")
    elif args.cmd == "init-db":
        init_db()
    elif args.cmd == "seed":
        seed()
    elif args.cmd == "tags":
        with SessionLocal() as session:
            for tag in session.scalars(select(Tag).order_by(Tag.slug)):
                print(f"{tag.slug:<12} {tag.color:<8} {tag.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
