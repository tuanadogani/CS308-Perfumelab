"""Yeni yerel geliştirme veritabanını ve .env dosyasını hazırlar."""
import os
import pwd
import secrets
from pathlib import Path

import psycopg
from psycopg import sql

root = Path(__file__).resolve().parent.parent
env_path = root / ".env"
if env_path.exists():
    raise SystemExit(".env zaten var; mevcut ayarların üzerine yazılmadı.")

password = secrets.token_urlsafe(32)
secret = secrets.token_urlsafe(64)
with psycopg.connect(
    dbname="postgres", user=pwd.getpwuid(os.getuid()).pw_name,
    host="127.0.0.1", port=5432, autocommit=True,
) as conn:
    if conn.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", ("perfume_app",)).fetchone():
        raise SystemExit("perfume_app rolü zaten var; mevcut rol değiştirilmedi.")
    if conn.execute("SELECT 1 FROM pg_database WHERE datname = %s", ("perfume",)).fetchone():
        raise SystemExit("perfume veritabanı zaten var; mevcut veriler değiştirilmedi.")
    conn.execute(sql.SQL("CREATE ROLE {} LOGIN PASSWORD {}").format(
        sql.Identifier("perfume_app"), sql.Literal(password),
    ))
    conn.execute(sql.SQL("CREATE DATABASE {} OWNER {}").format(
        sql.Identifier("perfume"), sql.Identifier("perfume_app"),
    ))

content = (
    f"DJANGO_SECRET_KEY={secret}\nDJANGO_DEBUG=true\n"
    "DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1\n"
    f"POSTGRES_DB=perfume\nPOSTGRES_USER=perfume_app\nPOSTGRES_PASSWORD={password}\n"
    "POSTGRES_HOST=127.0.0.1\nPOSTGRES_PORT=5432\n"
)
fd = os.open(env_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, "w") as stream:
    stream.write(content)
print("Yerel veritabanı ve .env hazırlandı. Parolalar ekrana yazılmadı.")
