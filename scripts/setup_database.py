"""Membuat database MySQL dan .env untuk install.bat."""

import os
import re
import secrets
import sys
from pathlib import Path
from urllib.parse import quote_plus

import pymysql


def required(name, default=None):
    value = os.getenv(name, default)
    if value is None or not str(value).strip():
        raise ValueError(f"Konfigurasi {name} kosong.")
    return str(value).strip()


def main():
    host = required("INSTALL_DB_HOST", "127.0.0.1")
    port = int(required("INSTALL_DB_PORT", "3306"))
    username = required("INSTALL_DB_USER", "root")
    password = os.getenv("INSTALL_DB_PASSWORD", "")
    database = required("INSTALL_DB_NAME", "db_kopi_topsis")
    if not re.fullmatch(r"[A-Za-z0-9_]+", database):
        raise ValueError("Nama database hanya boleh berisi huruf, angka, dan underscore.")

    print(f"Memeriksa MySQL di {host}:{port} ...")
    connection = pymysql.connect(
        host=host,
        port=port,
        user=username,
        password=password,
        charset="utf8mb4",
        connect_timeout=5,
        autocommit=True,
    )
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{database}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
            cursor.execute("SHOW DATABASES LIKE %s", (database,))
            if not cursor.fetchone():
                raise RuntimeError("Database gagal dibuat atau tidak dapat diakses.")
    finally:
        connection.close()

    url = f"mysql+pymysql://{quote_plus(username)}:{quote_plus(password)}@{host}:{port}/{database}?charset=utf8mb4"
    env_path = Path(__file__).resolve().parent.parent / ".env"
    existing_secret = None
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("SECRET_KEY="):
                existing_secret = line.partition("=")[2].strip()
                break
    secret = existing_secret or secrets.token_urlsafe(48)
    env_path.write_text(
        "FLASK_ENV=development\n"
        f"SECRET_KEY={secret}\n"
        f"DATABASE_URL={url}\n"
        "SESSION_COOKIE_SECURE=false\n",
        encoding="utf-8",
    )
    print(f"Database `{database}` siap dan .env berhasil dibuat.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
