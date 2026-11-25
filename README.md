# Board Game Catalog

A Django-based web application for managing and selling a board game collection with integrated pricing from BoardGameGeek (BGG) and BoardGamePrices APIs.

Continuing from another computer? See the [development handoff](docs/CONTINUE.md)
for the latest work, local setup on port 8001, and the pending Gmail SMTP setup.

## 🎯 Features

- **Public Catalog** - Browse available games with filtering and search
- **Admin Panel** - Full CRUD operations for board games
- **BGG Integration** - Multi-tier fallback strategy (BGG XML API → Board Game Atlas → Web Scraping)
- **Stock Reservation System** - 24-hour automatic reservations to prevent overselling
- **Shopping Cart** - Session-based cart with real-time stock validation
- **WhatsApp Checkout** - Customer accounts and saved quotes with a prepared WhatsApp order message
- **Barcode Scanner** - QuaggaJS integration for UPC/EAN lookup
- **Responsive Design** - Bootstrap 5 with mobile-first approach

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- PostgreSQL (for production) or SQLite (for development)
- Virtual environment tool (venv, virtualenv, or conda)

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/LeandroKeltech/bgcatalog.git
   cd bgcatalog
   ```

2. **Create and activate virtual environment:**
   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate

   # Linux/Mac
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

5. **Run migrations:**
   ```bash
   python manage.py migrate
   ```

6. **Create superuser:**
   ```bash
   python manage.py createsuperuser
   # Or use the interactive wrapper (no default password):
   python create_admin.py
   ```

7. **Collect static files:**
   ```bash
   python manage.py collectstatic --noinput
   ```

8. **Run development server:**
   ```bash
   python manage.py runserver
   ```

9. **Access the application:**
   - Public Catalog: http://127.0.0.1:8000/
   - Admin Panel: http://127.0.0.1:8000/admin-panel/
   - Django Admin: http://127.0.0.1:8000/admin/

## 📦 Project Structure

```
bgcatalog/
├── catalog/
│   ├── models.py              # BoardGame, StockReservation models
│   ├── views.py               # Public catalog views
│   ├── admin_views.py         # Admin panel views
│   ├── cart_views.py          # Shopping cart & checkout
│   ├── bgg_views.py           # BGG search & import
│   ├── bgg_price_service.py   # API integration service
│   ├── urls.py                # URL routing
│   ├── templates/catalog/     # HTML templates
│   └── static/catalog/        # CSS, JS, images
├── bgcatalog_project/
│   ├── settings.py            # Django settings
│   └── urls.py                # Root URL config
├── requirements.txt           # Python dependencies
├── Dockerfile                 # Docker configuration
└── manage.py                  # Django management script
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file with the following variables:

```env
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=sqlite:///db.sqlite3
```

The application loads `.env` automatically. Existing process environment variables
take precedence. Leave `DATABASE_URL` empty for the local `db.sqlite3` database,
or set a PostgreSQL connection URL for production. Startup applies migrations
without dropping existing tables. Create administrators explicitly with
`python manage.py createsuperuser`; startup does not create default credentials.

### Production Settings

Production deployment targets Vercel with an external PostgreSQL database.
Configure private environment variables in Vercel and follow the **Vercel + Neon
PostgreSQL** deployment instructions below. Set `DEBUG=False`, a private
`SECRET_KEY`, and the project's production host and CSRF origin.

## 📚 API Integration

### BoardGameGeek (BGG)

- **XML API2**: Primary source for game data
- **Fallback**: Board Game Atlas API
- **Last Resort**: Web scraping BGG pages

### Board Game Atlas

- **Client ID**: JMc8dOwiQE (public test key)
- **Free Tier**: 100 requests/month

### BoardGamePrices

- **Endpoint**: boardgameprices.co.uk
- **Currency**: EUR (Ireland market)

## 🛒 Stock Reservation System

### Import the inventory spreadsheet

The catalog source is the read-only `BG on sale` sheet:
https://docs.google.com/spreadsheets/d/1S0iPisv9H1OGwALmS3PG_d8Kw0iOtrdto3gOMUsNOlQ/edit

`catalog/data/source_catalog.json` is the 83-row snapshot read on 23 November
2026 from `Sheet1!A1:O999`. Import it after running migrations:

```powershell
python manage.py import_sheet_catalog
python manage.py import_sheet_catalog --enrich
```

The first command imports inventory offline. The second validates game identities,
fetches descriptions and artwork from the Geek network's public website data
endpoint, and checks both image URLs with HTTPS and image content-type validation.
It does not require an XML API token. This public website endpoint is an external
dependency and may change. Responses are cached locally in `.catalog-import/`;
use `--enrich --refresh` to fetch and validate them again.

- Source `id` identifies an inventory row; it is not assumed to be a BGG ID.
- `balance` becomes remaining stock. Sold-out rows are retained with zero stock.
- Explicit `Price` becomes `sale_price`, rounded to euro cents with decimal
  arithmetic. MSRP, original stock, sales, notes, and the source row are preserved.
- Duplicate titles remain separate inventory records. BGG IDs can be shared.
- Reruns preserve existing inventory quantities, sale prices, and manual edits.
  Enrichment only updates BGG metadata, descriptions, artwork, and gameplay fields.
- `catalog/data/bgg_mappings.json` contains reviewed corrections and edition
  mappings. Each correction checks the expected BGG name. D&D books use RPGGeek,
  part of the same Geek network. Dobble Kids uses specific edition artwork.
- Names that cannot be verified keep their original descriptions and blank
  image fields. Their verification status and reasons are stored in
  `source_metadata` and `.catalog-import/import-report.csv`.
- Cover images represent the BGG catalog entry, not a photograph of the physical
  copy being sold. Regional box artwork is not guaranteed unless mapped explicitly.

After the initial validation, 79 rows have verified descriptions and images.
Four remain pending: A Game of Wine (incorrect link to Flick 'em Up!), Hum It!
(missing identity and invalid source price), Picadice (no verified BGG entry),
and Dobble Animals (incorrect link to Spot it! 1,2,3; exact animal edition needs
confirmation). Unpriced games are blocked at checkout until their price is set.

The database and external response cache are ignored by Git. The snapshot,
migrations, reviewed mappings, and command are versioned so another checkout can
recreate the inventory using the commands above.

### Formatted descriptions and videos

After BGG enrichment, format descriptions and import matching English videos:

```powershell
.\.venv\Scripts\python.exe manage.py enrich_catalog_content --videos
# Recheck BGG video listings instead of using the local cache:
.\.venv\Scripts\python.exe manage.py enrich_catalog_content --videos --refresh
```

The command preserves paragraphs, lists and emphasis from verified BGG descriptions,
splits long paragraphs, strips unsafe HTML, and stores the formatted content in the
database. Original plain descriptions remain available as a fallback. Formatting
uses cached game metadata from `import_sheet_catalog --enrich`; run that first on
a fresh checkout. Descriptions are sanitized again when displayed.

Video imports accept only visible English YouTube listings associated with the exact
verified BGG game ID. Up to two videos per inventory entry are selected, prioritizing
instructional videos and reviews. Duplicate inventory copies can share videos.
As of 23 November 2026, 79 descriptions are formatted and 128 video links are stored
across 66 inventory entries. Four unresolved game identities are skipped.

Videos appear under **Watch & learn** on the product page, with lazy-loaded YouTube
poster thumbnails. The video player loads only after Play is pressed and uses
`youtube-nocookie.com`. Direct YouTube and
BGG links remain available if embedding is unavailable. Video files are not copied
or hosted locally. A successful metadata import does not guarantee that every
video remains playable; unavailable videos can be removed on a later refresh.
Failed requests retain existing videos and record the error in source metadata.

### Promotions

Open `/admin-panel/promotions/` with a staff account to create, edit, pause or enable
percentage discounts, fixed euro discounts, or promotional selling prices. Choose
individual inventory entries or the whole catalog, and optionally schedule an end.
Times use Europe/Dublin. The lowest active item price wins; individual offers never stack or raise
prices. Extra-percentage cart offers can discount that final item price further. Price filtering, sorting, the cart and checkout use the same rules.
Reservations snapshot the quoted unit price, so confirmation honors the quote
even if a promotion expires before the reservation is confirmed.

Migration `0015` activates **Buy 3+, get an extra 10% off** in each database,
including staging and production through the existing migration build hook.
It counts physical copies and applies 10% once to the final item-price subtotal
(after individual-game discounts), rounded to cents and allocated across the
quote lines. Other cart offers compete for the lowest total. Staff can pause or
edit this promotion; the homepage banner appears only while the matching active
catalog-wide 3+/10% offer is available. No end date is configured.

Cart mechanics are available in the same **Create promotion** screen:

- **Buy N: percentage off eligible games** — for example, set minimum copies to 2
  and percentage to 10 for 10% off all eligible copies once the threshold is met.
- **Buy N: fixed amount off eligible games** — for example, buy 3 eligible copies
  and receive €5 off their combined subtotal, capped at that subtotal.
- **Buy N: cheapest eligible game free** — set minimum copies to 5 for five copies
  total, one of them free (pay for four). By default, the cheapest eligible copy in
  the whole cart is free once. Enable repetition to give one free copy per complete
  group: copies are sorted from highest to lowest price and grouped consecutively
  for the customer's best saving. Leftover copies are paid for normally.

Thresholds count physical copies, including multiple copies of one inventory entry,
and only selected games count for scoped promotions. Standard cart offers use base selling
prices before promotions; extra-percentage cart offers use final item prices.
They compete for the lowest total. They do not change the unit prices shown in catalog filters.
The cart displays eligibility progress, the applied offer, line savings and the
final total. The 3+/10% extra offer is activated by migration `0015`.

Fixed discounts are allocated proportionally in cents. Where copies of the same
game have different final prices, checkout creates separate paid/free or differently
priced reservation lines. The quoted amounts and mechanic are saved. All items in
a cart promotion are confirmed, extended or cancelled together to prevent taking a
free item without its qualifying purchases. Confirmation creates linked sales;
payments are recorded per sale, while free lines have no amount due. A quote remains
valid at its saved price if the promotion is edited, paused, deleted or expires.

### Sales, receipts and partner reconciliation

Use `/admin-panel/` for current stock and prices, including sold-out entries.
Use `/admin-panel/finances/` to record sales, payments, customer refunds and partner
transfers, and export the transaction ledger as CSV. Confirming a reservation
creates an unpaid sale and deducts stock. Record actual payments separately;
historical spreadsheet sales are not assumed to have been paid.

The partner receives 50% of net money received (receipts minus customer refunds),
rounded to cents across the ledger. Payments received directly by the partner and
previous partner transfers reduce what is still owed. A negative balance means
the partner owes the business. Transfers record completed transfers; they do not
move money through a payment provider. Historical sales can be entered without
deducting stock again. Recorded transactions are retained as an audit trail.

### Reservation flow

1. Customer adds items to cart
2. Customer registers or signs in with an email and password, and supplies a name and international phone number
3. On checkout, stock is reserved for 24 hours and a quote is saved to the account
4. Customer opens the prepared WhatsApp message and presses Send to contact the shop
5. Admin can confirm sale (reduces stock), cancel, or extend the reservation
6. Expired reservations stop reducing available stock

Set `WHATSAPP_SHOP_NUMBER=+353899402153` in the local `.env` or deployment environment.
This uses a `wa.me` link and needs no WhatsApp API credentials. The site does not
send WhatsApp messages or quote emails automatically. The message includes the
customer's name, email and phone, quantities, conditions, frozen prices, promotion
savings, total, quote reference and reservation deadline. Shipping is agreed separately.
Quotes are accessible only to their account owner at `/account/`; expired or
processed quotes remain readable without an active checkout link. Customer accounts
receive the `user` role, without administration access. Passwords use Django's
hashing and validation; contact phone numbers and email ownership are not verified.
Existing accounts can complete their contact details before checkout.
Customer sign-in matches the saved email case-insensitively, including accounts
whose internal username differs from their email. Passwords are checked through
Django authentication. Missing or duplicated emails are rejected with the same
generic login error; staff sign-in continues to accept its existing usernames.
Account and registration forms keep the country code separate from the local phone
number. Ireland (+353) is the default for a blank number; existing international
numbers retain their country. The searchable country picker uses locally hosted
SVG flags and falls back to a native select without JavaScript. Numbers are parsed
with phonenumberslite and remain stored as a single E.164 string, including in quote
snapshots and WhatsApp messages. National trunk prefixes are handled per country.

### Reservation notifications

Every successful customer checkout creates one durable alert at
`/admin-panel/notifications/`, in the same transaction as the stock holds.
The customer does not have to open or send the WhatsApp message. Admins see an
unread badge and can open the quote's reservations from the inbox. Reading an alert
does not confirm or cancel the reservation; each admin has their own read status.
Alerts remain available after expiry. This does not change the 24-hour stock hold.

Admin pages check for new alerts every 30 seconds. Browser notifications are
optional: click **Enable browser alerts** and grant browser permission. They require
an admin page to stay open, a supported browser, and HTTPS (localhost also works).
An inbox notification is saved even while the site is closed.

Email alerts are attempted after the reservation transaction commits. Set
`RESERVATION_NOTIFICATION_EMAIL` and configure `EMAIL_BACKEND`, `DEFAULT_FROM_EMAIL`,
`EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`,
`EMAIL_USE_TLS`, and `EMAIL_USE_SSL` in the local `.env` or deployment environment.
For Gmail SMTP use `smtp.gmail.com`, port `587`, TLS enabled, SSL disabled, the full
Gmail address as user and sender, and a Google app password stored only in the
environment. [Google app passwords](https://support.google.com/accounts/answer/185833)
require 2-Step Verification. Keep credentials out of Git and chat.

Missing credentials or console-only email settings show **Email setup required**.
Email failures preserve the reservation and inbox alert. Use **Retry email alert**
or `python manage.py send_reservation_alerts` after fixing delivery. Emails already
accepted by the sending service are skipped. Acceptance does not guarantee inbox
delivery; a process interruption after SMTP acceptance but before saving the status
can require manual reconciliation to avoid a duplicate retry. No scheduler is
installed by this feature. SMTP uses a 10-second socket timeout; slow responses
from the sending service can delay the checkout response.

### Admin Management

- View all reservations at `/admin-panel/reservations/`
- Confirm, cancel, or extend reservation time
- Automatic expiry prevents overselling

## 🎨 Frontend

### Technologies

- **Bootstrap 5** - UI framework
- **Bootstrap Icons** - Icon library
- **QuaggaJS** - Barcode scanning
- **Vanilla JavaScript** - No heavy frameworks

### Responsive Design

- Mobile-first approach
- Optimized for desktop, tablet, and mobile
- Touch-friendly interface
- Shared original-price and selling-price display, with savings calculated from
  the actual prices rather than the configured discount percentage.
- Catalog price filters and sorting use the selling price, including explicit
  spreadsheet prices; unknown prices appear last when sorting by price.
- Search stays visible, with expandable filters and 24 games per page. Pagination
  preserves search and filter parameters.
- Cover images fit inside their frames without cropping, and catalog images load
  lazily. Phone layouts use one column; larger screens expand the grid.
- Controls have at least 44px touch targets. Staff inventory and reservation
  tables become labeled records on narrow screens.

The app continues to use Django and Bootstrap; a Next.js migration is not required
for these pricing and responsive-layout changes.

## 📊 Database Schema

### BoardGame Model

- Basic info: name, year, designer, description
- Images: thumbnail_url, image_url
- Gameplay: players, playtime, age
- Ratings: average, rank, num_ratings
- Pricing: msrp_price, discount_percentage
- Inventory: stock_quantity, condition, is_sold

### StockReservation Model

- Reservation details: game, quantity, status
- Customer info: name, email, phone
- Timestamps: reserved_at, expires_at, confirmed_at
- Session tracking: session_key

## 🔐 Security

Administrative routes, including Django's `/admin/`, require an active account in
the `admin` group. `is_staff` and `is_superuser` alone do not grant access. New
ordinary accounts automatically join `user`; promotion to `admin` removes
that common role, and removing or clearing `admin` membership restores it. Changes
take effect on the next request, including for existing sessions.

Migrations `0008_account_roles` and `0009_rename_common_user_group` preserve existing
superusers as members of `admin` and assign other accounts to `user` unless already
in `admin`. Explicitly
creating a new superuser also assigns `admin` to allow initial setup. Saving an
existing superuser never restores revoked group membership. Use the superuser's
Django user editor to grant or revoke group membership; ordinary admin-group
members still need Django model permissions to manage users and groups there.

- CSRF protection enabled
- Session-based authentication
- SQL injection prevention (Django ORM)
- XSS protection (auto-escaped templates)
- HTTPS enforced in production

Production defaults to `DEBUG=False` and refuses a missing, short or placeholder
`SECRET_KEY` and any SQLite or non-TLS PostgreSQL connection. Vercel always disables debug. Generate an independent production key with
`python -c "import secrets; print(secrets.token_urlsafe(64))"` and store it in the
hosting provider's secret manager. `.dockerignore` and `.vercelignore` exclude
environment files, local databases, Git history and backup files. The container
runs as an unprivileged user. Dependencies are pinned to patched releases;
GitHub Actions checks dependencies, migrations and tests on PostgreSQL.

Both login forms share limits of 10 POST attempts per account and 30 per IP per
15-minute window. Registration allows 5 attempts per IP per hour. Checkout allows
5 attempts per account and 20 per IP per 30-minute window, with at most 3 active
quotes per account. Limits count submissions, including successful submissions;
blocked requests return HTTP 429 and `Retry-After`. Counters are shared in the
database, store HMAC identifiers rather than raw email/IP values, and do not rely
on per-process memory. Only configured hosting-provider IP headers are trusted.
IPv6 addresses share a /64 bucket. Private account, cart, checkout and admin pages
use `no-store`. BGG refresh requires POST and CSRF, and all BGG HTTPS calls verify
certificates. Customer passwords require 6 characters and reject common passwords;
the administrative password policy keeps the stricter 12-character minimum,
personal-information similarity check and prohibition on entirely numeric passwords.

HSTS initially lasts one hour on the serving hostname. `HSTS_INCLUDE_SUBDOMAINS`
and `HSTS_PRELOAD` default to `False` until the domain's full HTTPS coverage has
been verified. Django's deployment check reports advisory W005/W021 for these
two opt-ins; they do not disable HTTPS or secure cookies. Do not request browser
preload registration before committing the domain to HTTPS long term.

Run `python manage.py security_cleanup` from the hosting scheduler regularly to
remove expired rate counters and sessions and mark expired reservations. A new
deployment must apply migrations before receiving requests.

### Database backups and restoration

Create a consistent local backup with:

```powershell
python manage.py backup_database --output backups/catalog-YYYYMMDD.sqlite3
```

For production, run the same command with a **direct PostgreSQL connection** and
an output ending in `.dump`; it uses `pg_dump --format=custom` and requires the
PostgreSQL client tools to match the database server's major version. It refuses
to overwrite a backup or save under public media/static directories, and passes
database credentials through the child process environment. SQLite backups are
integrity checked. A SQLite restoration is exercised in local tests; the CI
workflow also backs up and restores PostgreSQL into an isolated test database.

Production backup configuration is an infrastructure step: enable the provider's
retention/point-in-time recovery, keep encrypted off-host copies with restricted
access, and restore a copy into an isolated database before launch. Backups on an
ephemeral application filesystem are not durable backups. To restore a PostgreSQL
dump, use `pg_restore --no-owner --no-acl --exit-on-error --dbname TARGET_DB backup.dump`
against a new isolated database, then verify migrations, inventory and accounts
before choosing a cutover. Never test a restoration over the live database.

## 🚢 Deployment

### Release flow: staging to main

Develop and test on `staging`. Push changes there first; GitHub Actions runs the
application, migration, dependency and PostgreSQL checks. For local testing, keep
the development SQLite database and run `python manage.py test catalog` followed
by `python manage.py runserver` inside the development environment.

After reviewing the site and passing CI, merge `staging` into `main`. Configure
Vercel's Production environment to track **main**, with automatic Git deployments
enabled. Each merge into main triggers a production build and applies database
migrations through the build hook. `vercel.json` enables automatic builds only
for `main` and `staging`. Staging creates a Preview deployment for review using
an isolated Neon branch. Keep Vercel Authentication set to **All Deployments**
until the owner explicitly approves public access, including production domains.
Use the default automatic Ignored Build Step behavior in the Vercel dashboard.
Production database credentials belong only to the Production environment.

### Vercel + Neon PostgreSQL

This checkout is configured for Vercel's native Django support. Dependencies stay
in `requirements.txt`, Python is pinned to 3.12 in `.python-version`, and
`vercel.json` configures the migration build command; Vercel discovers the WSGI
application from Django settings. Vercel collects static files and
serves them from its CDN; `start.sh` is only used by the container deployment.

1. Create a **Free** PostgreSQL project in Neon and select a European region.
   Use its **pooled** connection URL with `sslmode=require`.
2. Import `LeandroKeltech/bgcatalog` into Vercel, with the repository root as the
   project root and **Django** as the framework. Choose a function region near
   the database. Deploy the intended local changes only after committing and
   pushing them; the GitHub repository does not contain uncommitted files.
3. Before deploying, set these environment variables for **Production**:
   - `DATABASE_URL`: the Neon PostgreSQL connection URL.
   - `DATABASE_URL_UNPOOLED`: the direct Neon connection URL (without `-pooler`),
     used only for schema migrations during the production build.
   - `SECRET_KEY`: a newly generated random secret of at least 50 characters.
     Generate locally with `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`.
   - `DEBUG=False` (Vercel deployments also enforce this in code).
   - `ALLOWED_HOSTS`: the final public hostname, plus any custom domains,
     comma-separated. Vercel's deployment, branch and project hostnames are
     automatically included when supplied by Vercel.
   - `CSRF_TRUSTED_ORIGINS`: the corresponding HTTPS URLs, comma-separated.
4. The build hook applies migrations for production and the `staging` preview,
   and aborts on a migration failure. Other previews skip migrations. Configure
   Preview variables restricted to the `staging` Git branch, using a **separate
   Neon database branch**, its own `SECRET_KEY`, and its own direct and pooled
   connection URLs; never assign production database URLs to Preview. Schema isolation alone is not enough
   if preview code can still write to the production database.
5. Transfer existing local data once into the new, otherwise empty database.
   Keep a SQLite backup first. The prepared backup and import fixture are under
   the ignored `.catalog-import/deployment/` directory. Fixtures include accounts,
   catalog and business records, but omit sessions, admin logs and generated
   permissions/content types. Do not commit or upload these files publicly.
   Export a fresh fixture if local data has changed since preparation:

   ```powershell
   .\.venv\Scripts\python.exe -X utf8 manage.py dumpdata --natural-foreign --natural-primary --exclude contenttypes --exclude auth.permission --exclude sessions.session --exclude admin.logentry --output .catalog-import/deployment/current.json
   ```

   Using a terminal scoped to the **new PostgreSQL database** (with `DATABASE_URL`
   set securely to the direct/unpooled URL in that terminal's environment), run:

   ```powershell
   .\.venv\Scripts\python.exe manage.py migrate --noinput
   .\.venv\Scripts\python.exe manage.py loaddata .catalog-import/deployment/current.json
   ```

   Substitute the prepared fixture filename if using the snapshot. Import before
   allowing customer traffic; do not re-import later over active production data.
   Existing account password hashes are preserved. If starting without accounts,
   use `python manage.py createsuperuser` against PostgreSQL.
6. Verify catalog images and CSS, administrative login, interest/reservation
   submission and stock persistence across a redeploy before sharing the URL.

Vercel deliberately refuses to fall back to local SQLite. PostgreSQL connections
require TLS and are closed after requests, allowing Neon to suspend idle compute.
Neon's Free compute wakes on the next query; a first request can have extra latency.
Free usage quotas apply to both providers. No paid plan is required by this
configuration and no hosted resources exist merely because these files exist.

The catalog currently stores remote image URLs, so no upload storage is needed.
If file uploads are added later, configure external object storage; Vercel's
local filesystem is not persistent. Email currently uses Django's console backend:
requests can be managed in the admin, but outgoing emails are not delivered until
an email provider is configured.

Local `.env*`, SQLite files and import snapshots are excluded from Vercel uploads
by `.vercelignore`. Only `.env.example` is eligible for Git; real secrets belong in
Vercel's environment settings. Do not place database credentials in source files.

## 📝 Development

### Local setup verification

The public catalog defaults to **Relevance**: product clicks descending, then BGG
average rating descending, with unrated games last on tied click counts. Remaining
ties use the inventory ID for stable pagination. Other sort choices still work.
Click counters start at zero; historical clicks were not tracked. A public product
page open counts once per game/browser session in a rolling 30-minute window.
Refreshes within that window, staff views, HEAD requests and explicit browser
prefetches do not count. Increments use a database expression to avoid lost updates.
This is a lightweight popularity signal, not a count of authenticated unique people.
No IP addresses or external analytics service are recorded. Staff can see **Clicks**
in the inventory table.

Populate or refresh the BGG rating tie-break after importing verified identities:

```powershell
.\.venv\Scripts\python.exe manage.py refresh_bgg_ratings
# Fetch fresh website statistics rather than reusing the response cache:
.\.venv\Scripts\python.exe manage.py refresh_bgg_ratings --refresh
```

The command reads public Geek website statistics and validates rating ranges. It
updates ratings, complexity (weight), and their source metadata, preserving stock,
conditions, prices and click counters. Unverified game identities are skipped;
games without BGG ratings or complexity remain blank. Failed refreshes preserve
existing stored values.

For automatic browser refresh while editing in Cursor, install the optional
development dependencies inside the project environment:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

In Cursor, use **Terminal → Run Task → Dev: Django + LiveReload**. The two tasks
use `.venv` directly, so terminal activation is not required. Django listens on
`127.0.0.1:8000`; LiveReload listens on `127.0.0.1:35729` and watches templates and
static files. If Django is already running, run only **Django: LiveReload**.
Reload an existing browser tab once to connect it. LiveReload is enabled only
when `DEBUG=True` and its optional package is installed; set
`ENABLE_LIVERELOAD=False` to disable it locally. It is excluded in production.

The inventory admin now uses a compact table with 50 entries per page by default.
Choose 25, 50 or 100 entries, keeping search and availability filters. Small screens
can scroll the table horizontally to access stock, prices and management actions.

Use **Condition → Not new** to review used and like-new copies together, or choose
an exact condition. The condition pricing policy is **New: 30% off; Like New: 40%
off; Used (including other used grades): 60% off** the stored original price.

```powershell
# Preview changes; no prices are saved:
.\.venv\Scripts\python.exe manage.py reprice_inventory
# Explicitly apply the policy to current inventory:
.\.venv\Scripts\python.exe manage.py reprice_inventory --apply
```

Applying the policy updates base selling prices with decimal cent rounding and
saves the previous values to an ignored `.catalog-import/condition-pricing-*.json`
recovery snapshot. Games without an original price retain their existing price.
Stock, recorded sales, receipts and existing quote price snapshots are preserved.
Manual condition changes are retained when the spreadsheet importer is rerun.
The policy command is explicit: editing a condition alone does not replace a
manually entered selling price. Run it again when you want to reapply these rates.

On Windows, after installing dependencies into `.venv`:

```powershell
.\.venv\Scripts\python.exe manage.py migrate --noinput
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test catalog
.\.venv\Scripts\python.exe manage.py createsuperuser
.\.venv\Scripts\python.exe manage.py runserver
```

The SQLite database is a local development file and is ignored by Git. For
production, configure PostgreSQL and backups before accepting customer data.
Database constraints reject negative stock and prices, discounts outside 0–100,
nonpositive reservation quantities, and unknown reservation statuses. Existing
invalid rows must be corrected before applying the constraint migration.

### Improvement priorities from the code review

1. **Reservation concurrency:** confirmation, cancellation and extension now reload
   state under transaction locks and reject invalid transitions. Concurrent buyer and atomic rate-limit integration tests are
   included for PostgreSQL in CI; SQLite cannot exercise equivalent row locks.
2. **Input validation:** replace direct `int()` conversions and raw POST field
   assignment with Django forms. Validate positive quantities, email addresses,
   choices, prices, and gameplay ranges. Require POST on cart mutations and
   refresh operations. Staff inventory, promotions and finance now use validated
   forms; checkout rejects sold and unpriced games. Public cart input validation
   still needs consolidation into forms.
3. **External integrations:** HTTPS certificate verification is enabled in
   `bgg_price_service.py`, with invalid-certificate regression coverage.
   Add mocked integration tests, caching, bounded retries, and background jobs
   for slow imports. The GBP/EUR conversion is a hardcoded constant.
4. **Production configuration:** private secrets, disabled debug, HTTPS and
   TLS PostgreSQL are enforced. Email settings currently use the console
   backend regardless of the environment values shown in `.env.example`.
   Checkout now uses customer-initiated WhatsApp messages. Add account recovery
   and email verification before opening public registration at scale.
5. **Query performance:** public and staff listings are now paginated. Load
   cart games in one query, prefetch active offers and annotate reserved quantities. The stock
   properties currently issue aggregate queries each time templates access them.
6. **Sales history:** sales and quote price snapshots, payments, refunds and
   partner reconciliation are now implemented. Games referenced by recorded
   sales are protected from deletion. Grouped multi-item orders and accounting
   period closure remain future improvements.
7. **Operations and coverage:** CI checks dependencies, migration drift and tests.
   Configure hosting alerts, schedule `security_cleanup`, and verify durable
   production backup retention and restoration. The reset script is destructive
   and should remain a manual maintenance tool, separate from startup.

### Running Tests

```bash
python manage.py test catalog
```

### Code Style

- **Python**: PEP 8
- **JavaScript**: Standard JS
- **HTML/CSS**: BEM methodology

### Git Workflow

1. Create feature branch
2. Make changes
3. Create pull request
4. Merge to main and deploy through the configured release process

## 🐛 Troubleshooting

### BGG API 401 Errors

If BGG API returns 401 errors:
- Fallback to Board Game Atlas will activate automatically
- Web scraping serves as final fallback
- Check logs for detailed error information

### Stock Reservation Issues

If reservations aren't working:
- Ensure migrations are up to date
- Check that session middleware is enabled
- Verify database transactions are supported

### Static Files Not Loading

```bash
# Collect static files
python manage.py collectstatic --noinput

# In production, ensure WhiteNoise is configured
```

## 📖 Documentation

- **API Documentation**: See inline docstrings in `bgg_price_service.py`
- **Stock Reservations**: Check `STOCK_RESERVATION_SYSTEM.md`
- **Models**: Review `catalog/models.py` for field descriptions

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

This project is open source and available under the MIT License.

## 👥 Contact

- **Repository**: https://github.com/LeandroKeltech/bgcatalog
- **Issues**: https://github.com/LeandroKeltech/bgcatalog/issues

## 🙏 Acknowledgments

- BoardGameGeek for game data
- Board Game Atlas for API fallback
- BoardGamePrices for pricing information

---

**Built with ❤️ using Django 5.2.7**
