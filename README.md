# MediFind

MediFind helps people find medicines at nearby pharmacies. Customers search for a medicine, see which pharmacies have it in stock, how far away they are and what it costs, and ask a pharmacy to confirm availability before travelling. Pharmacies manage their own profile, location and stock. Administrators approve pharmacy registrations.

**Live demo:** https://medfinder-fnid.onrender.com/
(Free hosting: the site sleeps after 15 minutes without visitors, so the first visit can take about 50 seconds.)

> All pharmacies, stock and prices in the demo are **fictional**. Stock shown on the site should always be confirmed by phone.

---

## Contents
1. [Roles and features](#roles-and-features)
2. [Tech stack](#tech-stack)
3. [Project structure](#project-structure)
4. [Local setup](#local-setup)
5. [Creating an admin account](#creating-an-admin-account)
6. [Demo data](#demo-data)
7. [Running the tests](#running-the-tests)
8. [Deployment (Render + Neon)](#deployment-render--neon)
9. [Security](#security)
10. [Known limitations](#known-limitations)
11. [Demo script for each role](#demo-script-for-each-role)

---

## Roles and features

| Role | Can do |
|---|---|
| **Visitor** (not logged in) | Search medicines, see the map and pharmacy pages, call a pharmacy |
| **Customer** | Everything a visitor can, plus ask a pharmacy to confirm availability, follow and cancel own requests |
| **Pharmacy** | Sign up (starts as *pending*), edit profile and map location, manage inventory (add, edit quantity/price, remove), answer customer requests |
| **Administrator** | Approve or reject pharmacies, manage everything in the Django admin |

Main features:
- **Search** by medicine name, brand or active ingredient (case-insensitive), only at **approved** pharmacies.
- Filters: in stock / all, distance (2, 5, 10, 20 km), sort by distance or price.
- **Distance** from your location (browser GPS, "Use my location") or a chosen Indore area if location is blocked, using the **Haversine formula**.
- **Map** (Leaflet + OpenStreetMap) with your position and pharmacy pins.
- **Stale-data label**: stock not updated for more than 7 days is marked "may be outdated".
- **Pharmacy page** with Call, **Call for Home Delivery** (only if the pharmacy offers delivery), and Directions buttons.
- **Availability requests**: pending → confirmed / unavailable (pharmacy) or cancelled (customer), with an optional reply.
- Phone-first layout (Bootstrap 5), tested at 320 px, 375 px and desktop width.

## Tech stack

| Part | Used | Why |
|---|---|---|
| Language / framework | Python 3.13, Django 5.2 | Batteries included: ORM, auth, admin, forms, CSRF protection |
| Pages | Django templates + Bootstrap 5 (CDN) | Server-rendered, responsive, no JavaScript framework needed |
| Maps | Leaflet 1.9 + OpenStreetMap tiles | Free and open, no API key |
| Database | SQLite locally, PostgreSQL on **Neon** in production | Selected automatically by the `DATABASE_URL` environment variable |
| Login | Django built-in auth with a custom `User` model (`role` field) | Secure password hashing and sessions out of the box |
| Static files | WhiteNoise | Serves CSS/JS from Django itself, compressed and cache-friendly |
| Web server | gunicorn | Production server; Django's `runserver` is for development only |
| Hosting | **Render** free web service (Singapore) | Free, deploys automatically from GitHub |

Python packages are listed in [`requirements.txt`](requirements.txt).

## Project structure

```
medifind/       Project settings and main URL list
core/           Home page, /healthz/ health check
accounts/       Custom User model with roles, sign-up, login, dashboard redirect, role_required decorator
pharmacies/     Pharmacy model, profile + map location, admin approval, public pharmacy page, Haversine helper
medicines/      Medicine catalogue, pharmacy inventory, customer search, seed_demo command
availability/   Availability requests between customers and pharmacies
templates/      base.html (layout and navbar), 403/404/500 pages, shared includes
static/         style.css, location_picker.js (profile map), search_map.js (results map)
build.sh        Render build script
```

Each app follows Django's usual layout: `models.py` (database tables), `forms.py` (validation), `views.py` (page logic), `urls.py`, `admin.py`, `templates/`, and `tests.py`.

## Local setup

Requirements: Python 3.13 and Git. Commands are for **Windows** (PowerShell or Command Prompt).

1. Get the code and open the folder:
   ```bash
   git clone https://github.com/Shivansh139/medfinder.git
   cd medfinder
   ```
2. Create a virtual environment and install the packages:
   ```bash
   python -m venv venv
   venv\Scripts\python -m pip install -r requirements.txt
   ```
3. Create your local settings file from the example:
   ```bash
   copy .env.example .env
   ```
4. Generate a secret key and paste it into `.env` as `SECRET_KEY=...`:
   ```bash
   venv\Scripts\python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```
   Keep `DEBUG=True` and leave `DATABASE_URL` empty locally (SQLite is used). **Never commit `.env`**; it is listed in `.gitignore`.
5. Create the database tables:
   ```bash
   venv\Scripts\python manage.py migrate
   ```
6. Start the development server, then open http://localhost:8000:
   ```bash
   venv\Scripts\python manage.py runserver
   ```

## Creating an admin account

```bash
venv\Scripts\python manage.py createsuperuser
```
Choose a username and password when asked. Log in at http://localhost:8000/admin/. A superuser always gets the **admin** role.

To approve a pharmacy: **Admin → Pharmacies →** tick the pharmacy **→ Action: "Approve selected pharmacies" → Go**. Only approved pharmacies appear in search. (Pharmacies can only be created through the pharmacy sign-up page, so "Add pharmacy" is disabled in the admin.)

## Demo data

```bash
venv\Scripts\python manage.py seed_demo --password "ChooseYourOwnPassword"
```

This loads the medicine catalogue (34 medicines) and creates:

| Login (username) | Role | Notes |
|---|---|---|
| `demo_sanjeevani` | Pharmacy (approved) | Vijay Nagar, home delivery, Dolo 650 in stock |
| `demo_shreekrishna` | Pharmacy (approved) | Near Rajwada, **Dolo 650 out of stock** |
| `demo_narmada` | Pharmacy (approved) | Old Palasia, home delivery |
| `demo_arogya` | Pharmacy (**pending**) | Bhawarkua, for demonstrating approval |
| `demo_patient` | Customer | One request in each status: pending, confirmed, unavailable, cancelled |

- **All demo accounts use the password you give** with `--password`. It is never stored in the code, and Django's password rules reject weak ones.
- Each pharmacy gets about 20 medicines with fictional prices; a few items are out of stock and 3 are backdated to show the "may be outdated" label.
- The command is **safe to run more than once**: it updates instead of duplicating. Running it again also resets the demo password and `demo_patient`'s requests.
- To load only the medicine catalogue: `venv\Scripts\python manage.py loaddata medicines`

## Running the tests

```bash
venv\Scripts\python manage.py test
```

**118 tests**, all passing. They use a temporary test database, so your data is not touched.

| File | Tests | Covers |
|---|---|---|
| `core/tests.py` | 8 | Home page, navbar login links, health check, 404 page |
| `accounts/tests.py` | 11 | Sign-up (customer, pharmacy → pending), login redirect by role, logout, superuser role |
| `pharmacies/tests.py` | 22 | Role blocking (403), own pharmacy only, approve/reject, profile validation, tampered fields ignored, home-delivery phone rule |
| `pharmacies/test_detail.py` | 8 | Haversine distance, public pharmacy page (approved only), delivery button |
| `medicines/tests.py` | 23 | Unique rules, other pharmacy's items give 404, zero stock = unavailable, validation, delete needs POST, demo data |
| `medicines/test_search.py` | 17 | Case-insensitive search, approved only, stock/distance filters, sorting, stale label |
| `availability/tests.py` | 29 | Request rules, roles, ownership (customer and pharmacy), only pending can change, tampering, duplicates |

Other useful checks:
```bash
venv\Scripts\python manage.py check
```
```bash
venv\Scripts\python manage.py makemigrations --check --dry-run
```

## Deployment (Render + Neon)

```
Phone ──HTTPS──► Render (gunicorn + Django + WhiteNoise) ──► Neon (PostgreSQL)
                 Singapore                                   Singapore
```

Both run in **Singapore**, the closest region to India, and in the same region so database queries are fast.

**Neon** (database): create a free project in *AWS Asia Pacific 1 (Singapore)* and copy the **direct** connection string (connection pooling off).

**Render** (web server): New → Web Service → this GitHub repository.

| Setting | Value |
|---|---|
| Language / Region / Plan | Python 3 / Singapore / Free |
| Build command | `bash build.sh` (install packages, `collectstatic`, `migrate`) |
| Start command | `gunicorn medifind.wsgi` |
| Environment variables | `SECRET_KEY` (a new random key), `DEBUG` = `False`, `DATABASE_URL` (the Neon string) |
| Health check path (optional) | `/healthz/` |

The Python version comes from `.python-version`. Render sets `RENDER_EXTERNAL_HOSTNAME` itself, and the settings add it to `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` automatically. Every `git push` to `main` redeploys the site.

**Admin and demo data on Neon.** The free Render plan has no shell, so run the commands from your own computer against Neon. In **one PowerShell window**:
```powershell
$env:DATABASE_URL = "your-neon-connection-string"
venv\Scripts\python manage.py shell -c "from django.db import connection; print(connection.vendor)"
venv\Scripts\python manage.py createsuperuser
venv\Scripts\python manage.py seed_demo --password "YourLiveDemoPassword"
```
The second line must print `postgresql`. Close the window afterwards; your computer then uses SQLite again.

## Security

- **Permissions are checked on the server**, never only by hiding buttons. The `role_required` decorator ([`accounts/decorators.py`](accounts/decorators.py)) sends logged-out visitors to the login page and gives **403 Forbidden** for the wrong role.
- **Ownership:** a pharmacy's inventory and requests, and a customer's requests, are always loaded *through their owner* (e.g. `get_object_or_404(InventoryItem, pk=pk, pharmacy=own_pharmacy)`). Someone else's object gives **404**, so the site does not even reveal that it exists.
- **Forms only accept their own fields.** Values such as the pharmacy, customer, status or licence number are set by the server, so a tampered form cannot change them.
- **Database rules** back up the forms: one inventory row per pharmacy + medicine, unique licence numbers, and only one *pending* request per customer + pharmacy + medicine.
- **CSRF protection** on every form; logout and delete actions use POST only.
- **Passwords** are hashed by Django and checked against Django's password rules.
- **Production:** `DEBUG` off, HTTPS redirect, secure cookies, HSTS, allowed hosts restricted. `manage.py check --deploy` reports only two HSTS warnings (subdomains and preload), left off on purpose because `*.onrender.com` subdomains belong to other sites.
- **Secrets** (`SECRET_KEY`, `DATABASE_URL`) come from environment variables and are never committed.

## Known limitations

- **No notifications and no password reset.** Both need an email or SMS service, which is outside the free stack. Customers check "My requests".
- **Stock is only as accurate as the pharmacy keeps it.** That is why results show "last updated", a "may be outdated" label after 7 days, and a notice to confirm by phone.
- **Distance is calculated in Python** after the database query. This is fine for a city; a large system would use a spatial database (PostGIS).
- **No address search on the map** (needs a geocoding service). Pharmacies tap the map or use their current location.
- **"Use my location" needs HTTPS** (or localhost) and the browser's permission. If it is blocked, the user picks an Indore area instead.
- **Free hosting sleeps** when idle: the first visit after 15 minutes takes about 50 seconds, and Neon's database also wakes on the first query.
- **Map tiles** come from OpenStreetMap's public server, which is fine for light student-project traffic but not for a large public site.
- The demo area and preset locations are **Indore only**, and all demo data is fictional.

## Demo script for each role

A 5–8 minute walkthrough on a **phone**, using the demo data. Before you start: open the site a few minutes early (it may be asleep), and have a **normal tab** for the customer and an **Incognito tab** for the pharmacy.

### 1. Visitor: search (1–2 min)
1. Open the home page, type **dolo** in the search box, tap **Search**.
2. Point out: only approved pharmacies, distance from the selected area, price, "last updated", and the notice to confirm stock by phone.
3. Change **Near** to another area: distances and order change (Haversine).
4. Set availability to **All**: Shree Krishna Pharmacy appears **Out of stock** (quantity 0 means unavailable).
5. Show the **map**: your position and pharmacy pins. Tap **Use my location** to use the phone's GPS (allow when asked).
6. Tap **View pharmacy** on Sanjeevani Medicals: **Call**, **Call for Home Delivery** (only shown because it offers delivery), **Directions**, and the medicine list with any "may be outdated" labels. Open Shree Krishna's page: no delivery button.

### 2. Customer: ask a pharmacy (1–2 min)
1. Search **dolo** and tap **Ask pharmacy** on **Narmada Medical Store**: the site asks you to log in first.
2. Log in as **`demo_patient`**. You are brought back to the request form.
3. Enter quantity and an optional note, and send. The request appears under **My requests** as **Pending**.
4. Show the older requests: **Confirmed** (with the pharmacy's reply and a Call button), **Unavailable**, **Cancelled**.
5. Search **dolo** again and tap **Ask pharmacy** on **Sanjeevani Medicals**: refused with "You already have a pending request…", because only one pending request per medicine and pharmacy is allowed (the demo data already has one there).

### 3. Pharmacy: answer and update stock (2 min, Incognito tab)
1. Log in as **`demo_narmada`**. The dashboard shows the pharmacy's status, inventory summary and **pending requests**.
2. Open **Requests**, then **Respond** to the new Dolo 650 request: choose **Confirmed** and write a short reply.
3. Open **Inventory**, **edit** Dolo 650 and set quantity to **0**.
4. Optional: **Edit profile** to show the map location picker and the home-delivery setting.

### 4. Customer again (30 s, normal tab)
1. Refresh **My requests**: the request is now **Confirmed** with the reply.
2. Search **dolo** again: Narmada Medical Store is no longer listed as in stock.

### 5. Administrator: approve a pharmacy (1 min)
1. Log in at **/admin/** with the superuser account.
2. **Pharmacies**: Arogya Chemists is **Pending**, so a search for dolo does not list it.
3. Tick it, **Action → Approve selected pharmacies → Go**.
4. Search **dolo** again: Arogya Chemists now appears (it has Dolo 650 in stock).

### 6. Security check (1 min)
1. Logged in as `demo_patient`, open `/pharmacy/dashboard/`: **403 Access denied** (wrong role), checked on the server.
2. Logged out, open `/requests/`: you are sent to the login page.
3. Logged in as `demo_narmada` (Incognito tab), open **Inventory → Edit** on any item and note the number in the address (`/pharmacy/inventory/<number>/edit/`). Log out, log in as `demo_sanjeevani` and open the same address: **404 Page not found**, because it belongs to another pharmacy.

To reset everything after a demo, run `seed_demo` again (locally, or against Neon as shown in [Deployment](#deployment-render--neon)).
