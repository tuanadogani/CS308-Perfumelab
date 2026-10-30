# Backend setup on Windows (PowerShell)

1. Install **PostgreSQL 16 or 17** from postgresql.org. Remember the password you give the `postgres` user.
2. Install Python 3.10 or newer. Python 3.13 (as in `README.md`) is not required.
3. From the `backend` folder:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

$env:PGPASSWORD = "your-postgres-password"
python scripts\setup_local_db_windows.py --admin-user postgres
Remove-Item Env:PGPASSWORD

python manage.py migrate
python manage.py seed_products        # 29 real perfumes
python manage.py seed_demo_users      # one account per role, password Demo1234
python manage.py runserver
```

`setup_local_db_windows.py` creates the `perfume` and `test_perfume` databases, the `perfume_app` role and a `.env` (never commit `.env`).

## Demo accounts (password `Demo1234`)

| Email | Role |
|---|---|
| customer@demo.com | customer (has a saved Visa 4242 4242 4242 4242) |
| sales@demo.com | sales manager |
| product@demo.com | product manager |
| support@demo.com | support agent |

The mock bank approves any card except one ending in `0002`, which is declined.

## Tests

```powershell
python manage.py test --keepdb
```

Emails are printed by Django's test backend. For local runs, set `EMAIL_BACKEND` to the console backend if you want to see them.
