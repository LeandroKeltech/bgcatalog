# Development handoff — 2026-11-25

## Repository and completed work

- Repository: https://github.com/LeandroKeltech/bgcatalog
- Continue development on branch `staging`.
- Product detail spacing, breadcrumbs, and video presentation were improved.
- My account and registration use a separate searchable country selector with SVG flags; Ireland (+353) is the default for blank phone numbers. Existing numbers retain their country.
- Customer sign-in now accepts email addresses even when the internal username differs. The login layout and error messages were improved.
- Empty and populated cart layouts were improved.
- These application changes are already on `staging` and `main`, released through PRs [#7](https://github.com/LeandroKeltech/bgcatalog/pull/7) and [#8](https://github.com/LeandroKeltech/bgcatalog/pull/8).
- Latest application commit: `03f2f48` (staging); production merge: `b3f989b` (main). This handoff is a later documentation change.
- No database migration is pending for those UI and login changes.

Production: https://bgcatalog.vercel.app

Staging: https://bgcatalog-git-staging-popperl1.vercel.app

## Start on another Windows computer

From PowerShell:

```powershell
git clone --branch staging https://github.com/LeandroKeltech/bgcatalog.git
cd bgcatalog
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env`: set `DEBUG=True` and generate a private `SECRET_KEY` using:

```powershell
.\venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(64))"
```

Leave `DATABASE_URL` empty to use a new local SQLite database. To work with existing data, use a separate development database or restore a backup into development following the README. The local database and private environment values are not transferred by Git. Do not use the production database for development.

```powershell
.\venv\Scripts\python.exe manage.py migrate
.\venv\Scripts\python.exe manage.py createsuperuser
.\venv\Scripts\python.exe manage.py runserver 127.0.0.1:8001
```

Open http://127.0.0.1:8001/ . Port 8001 avoids the other project's server.

## Reservation email alerts: configured and verified

The application already uses Django's standard SMTP backend. No custom SSL backend is needed.

The following values have been saved in Vercel for Production and Preview scoped to the `staging` branch:

```dotenv
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
EMAIL_HOST_USER=popperl@gmail.com
DEFAULT_FROM_EMAIL=popperl@gmail.com
RESERVATION_NOTIFICATION_EMAIL=popperl@gmail.com
```

`EMAIL_HOST_PASSWORD` is saved as a Secret in Production and Preview scoped to `staging`. Both environments were redeployed with the Gmail configuration on 2026-11-25. Never copy the app password into Git, documentation, or chat.

A single owner-approved test was sent from the staging notification panel to `popperl@gmail.com` at 18:47 UTC on 2026-11-25. SMTP acceptance was recorded as `sent`, and receipt was confirmed in the Gmail inbox. The staging-only test quote is `e907f9f2-2c5b-4d4c-b4ae-7e7ce6944ba3`, labelled `TESTE EMAIL BG CATALOG - SEM RESERVA`; it has no stock reservations and a zero total. No test email was sent from production.

For future credential rotation:

1. Create a new Google app password for `popperl@gmail.com`; Google 2-Step Verification is required. See [Google's instructions](https://support.google.com/accounts/answer/185833).
2. Replace `EMAIL_HOST_PASSWORD`, type Secret, in [Vercel environment variables](https://vercel.com/popperl1/bgcatalog/settings/environment-variables) for Production and Preview/staging.
3. Redeploy staging, validate an explicitly approved test, then redeploy production. Existing deployments do not pick up newly saved variables until redeployed.
4. Check Admin Panel > Notifications. `sent` means accepted by the sending service; verify inbox receipt separately. Missing configuration and SMTP errors preserve the reservation and its inbox notification.

Retry individual failed notifications from the admin interface. `python manage.py send_reservation_alerts` retries pending, failed, and configuration-blocked notifications in bulk and can send real emails; review its scope before running it.

Keep the console email backend from `.env.example` for ordinary local development. Do not copy live SMTP credentials into the repository.

## Validation already completed

- The account, phone, login, and cart release passed 159 local Django tests (2 PostgreSQL-only tests skipped locally), with PostgreSQL checks passing in GitHub CI.
- After preparing the SMTP environment variables, all 9 tests in `catalog.test_notifications` passed against an isolated in-memory SQLite test database.
- Live staging SMTP delivery and Gmail inbox receipt were verified on 2026-11-25. Production was redeployed with the configured secret, and its catalog returned HTTP 200.
