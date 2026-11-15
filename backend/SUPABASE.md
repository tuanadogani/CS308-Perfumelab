# Using Supabase as the shared database

Supabase is just a hosted PostgreSQL server, so Django talks to it exactly like the local
one. Nothing in the code changes, only the `POSTGRES_*` values in `backend/.env`.

## 1. Create the project (once, by the database owner)
1. supabase.com -> New project. Name `perfumelab`, region **Central EU (Frankfurt)**.
2. Save the database password it asks for (this is `POSTGRES_PASSWORD`).
3. Project -> **Connect** -> "Session pooler". It shows a URI like
   `postgresql://postgres.abcdefghijkl:[PASSWORD]@aws-0-eu-central-1.pooler.supabase.com:5432/postgres`

Use the **session pooler**, not the "direct connection" (`db.<ref>.supabase.co`): the direct
one is IPv6-only and fails on most home/campus networks.

## 2. Fill in backend/.env (every teammate)

    POSTGRES_DB=postgres
    POSTGRES_USER=postgres.abcdefghijkl
    POSTGRES_PASSWORD=<the project password>
    POSTGRES_HOST=aws-0-eu-central-1.pooler.supabase.com
    POSTGRES_PORT=5432
    POSTGRES_SSLMODE=require
    POSTGRES_CONN_MAX_AGE=60

Share these values privately (WhatsApp/Jira DM), never commit `.env`.

## 3. Create the tables and data (once)

    python manage.py migrate
    python manage.py seed_products
    python manage.py link_product_images
    python manage.py seed_demo_users

Check: `python manage.py dbshell` or `GET /api/health/` -> `"database": "connected"`.

## Notes
- Tests: `manage.py test` creates a separate `test_postgres` database. Run tests against
  your LOCAL Postgres, not Supabase (slow, and the free tier may refuse CREATE DATABASE).
- Port 6543 (transaction pooler) also works; settings then turn off server-side cursors
  automatically. Prefer 5432.
- Free projects pause after a week without use: open the dashboard and press "Restore".
- To go back to local Postgres just restore the old `.env` values.
