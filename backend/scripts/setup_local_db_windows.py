"""Create the local PerfumeLab database, app role and .env on Windows (or any OS).

Run from the backend folder:
    python scripts/setup_local_db_windows.py --admin-user postgres
The admin password is read from the PGPASSWORD environment variable (or asked for).
Nothing existing is overwritten, and generated passwords are never printed.
"""
import argparse
import getpass
import os
import secrets
from pathlib import Path

import psycopg
from psycopg import sql

parser = argparse.ArgumentParser()
parser.add_argument("--admin-user", default="postgres")
parser.add_argument("--host", default="127.0.0.1")
parser.add_argument("--port", type=int, default=5432)
parser.add_argument("--db", default="perfume")
parser.add_argument("--app-user", default="perfume_app")
parser.add_argument("--env-path", default=str(Path(__file__).resolve().parent.parent / ".env"))
args = parser.parse_args()

env_path = Path(args.env_path)
if env_path.exists():
    raise SystemExit(f"{env_path} already exists; nothing was changed.")

admin_password = os.environ.get("PGPASSWORD") or getpass.getpass(f"Password of PostgreSQL user {args.admin_user}: ")
app_password = secrets.token_urlsafe(32)
secret_key = secrets.token_urlsafe(64)
test_db = f"test_{args.db}"

with psycopg.connect(
    dbname="postgres", user=args.admin_user, password=admin_password,
    host=args.host, port=args.port, autocommit=True,
) as conn:
    if conn.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (args.app_user,)).fetchone():
        raise SystemExit(f"Role {args.app_user} already exists; nothing was changed.")
    for name in (args.db, test_db):
        if conn.execute("SELECT 1 FROM pg_database WHERE datname = %s", (name,)).fetchone():
            raise SystemExit(f"Database {name} already exists; nothing was changed.")
    # CREATEDB lets Django create/drop its own test database; the role owns both databases
    conn.execute(sql.SQL("CREATE ROLE {} LOGIN CREATEDB PASSWORD {}").format(
        sql.Identifier(args.app_user), sql.Literal(app_password)))
    for name in (args.db, test_db):
        conn.execute(sql.SQL("CREATE DATABASE {} OWNER {}").format(
            sql.Identifier(name), sql.Identifier(args.app_user)))

env_path.write_text(
    f"DJANGO_SECRET_KEY={secret_key}\nDJANGO_DEBUG=true\nDJANGO_ALLOWED_HOSTS=localhost,127.0.0.1\n"
    f"POSTGRES_DB={args.db}\nPOSTGRES_USER={args.app_user}\nPOSTGRES_PASSWORD={app_password}\n"
    f"POSTGRES_HOST={args.host}\nPOSTGRES_PORT={args.port}\n"
    "CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173\n",
    encoding="utf-8",
)
print(f"Created role {args.app_user}, databases {args.db} and {test_db}, and {env_path}. Passwords were not printed.")
