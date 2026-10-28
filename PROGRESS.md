# MediFind – Progress

## Current phase
**Phase 7 – Deployment: done.** You confirmed the live site works on your phone. Waiting for your approval.
Next: Phase 8 – README and demo script for each role.

## Roadmap
1. ✅ Skeleton
2. ✅ Accounts, roles and pharmacy approval
3. ✅ Pharmacy profile and location (Leaflet map)
4. ✅ Medicines and inventory
5. ✅ Customer search, map and pharmacy details
6. ✅ Availability requests
7. ✅ Deployment (Neon, Render, HTTPS settings, health check)
8. README and demo script for each role

## Completed phases

### Phase 1 – Skeleton
- Django project `medifind` and app `core` created.
- Settings read `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `DATABASE_URL` from environment variables (`.env` locally).
- Database: PostgreSQL when `DATABASE_URL` is set (Neon in production), otherwise SQLite.
- WhiteNoise set up for static files.
- Bootstrap 5 base template with responsive navbar, message alerts and footer.
- Public home page.
- Verified: `manage.py check` clean, 2 tests pass, database switch tested both ways, `collectstatic` works with `DEBUG=False`, page checked at desktop and phone width.

### Phase 2 – Accounts, roles and pharmacy approval
- Custom `User` model (`accounts.User`) with `role`: customer / pharmacy / admin. Superusers always get role admin.
- Local database deleted and recreated for the custom User model.
- `Pharmacy` model: owner (one-to-one with User), name, licence number (unique), address, phone, latitude/longitude (blank until Phase 3), status pending / approved / rejected.
- Customer sign-up; pharmacy sign-up creates the user and a **pending** pharmacy in one transaction.
- Login and logout use Django's built-in views. Logout is a POST form.
- `/dashboard/` redirects by role: customer page, pharmacy dashboard, or the admin site.
- `role_required` decorator: logged-out visitors go to login, wrong role gets 403.
- Admin: User shows role; Pharmacy has a status filter, search, and "Approve selected" / "Reject selected" actions.
- Verified: 20 tests pass. Checked in the browser: pharmacy sign-up shows "awaiting approval", customer sign-up works, customer gets 403 on the pharmacy dashboard.
- Manual step done: superuser created with `createsuperuser` (role is admin). "Demo Care Pharmacy" approved through the admin action, and the database shows it as approved.

### Phase 3 – Pharmacy profile and location
- Decisions: approved pharmacies **stay approved** after editing. The licence number and status are locked (only an admin can change them).
- New `Pharmacy` fields: `opening_hours` (optional, max 100 characters). `latitude` / `longitude` now have validators (−90…90, −180…180). Migration `0002`.
- `/pharmacy/profile/`: pharmacy users edit name, address, phone, opening hours and location. No id in the URL: the pharmacy always belongs to `request.user`.
- `PharmacyProfileForm` lists only editable fields, so a tampered `status` / `licence_number` is ignored. Latitude and longitude must be set together or both left empty.
- Leaflet 1.9.4 + OpenStreetMap map (with the "© OpenStreetMap contributors" credit). `static/js/location_picker.js`: click to place the pin, drag to adjust, "Use my current location" (browser geolocation), "Clear location", and typing numbers moves the pin. Read-only mode on the dashboard.
- Dashboard: "Edit profile" button, opening hours, read-only location map, and a warning when no location is set.
- Admin: ✔/✘ "Location set" column in the pharmacy list.
- Verified: **31 tests pass** (11 new). Checked in the browser: Leaflet loads with no console errors and shows the OSM credit. Clicking the map fills lat/lng (6 decimals). Saving keeps the status Approved. The dashboard shows the opening hours and the pin.
- Layout change (requested after Phase 3): **Log in / Sign up are always visible in the navbar**, including on phones, instead of being hidden behind the ☰ menu. Hero call-to-action buttons were tried and then removed because they repeated the navbar; each link now appears once. The hero area is kept free for the Phase 5 search box. Checked at 320 px, 375 px and 1200 px with no horizontal scrolling. 2 new tests in `core/tests.py`; the suite is now **33 tests**.

### Phase 4 – Medicines and inventory
- Decisions: the medicine catalogue is **managed by admins only**, and pharmacies pick from it. **Pending** pharmacies can manage inventory, but **rejected** ones get 403. Pharmacies are created **only through sign-up**: the admin's "Add pharmacy" is disabled (`has_add_permission` returns False).
- New app `medicines`.
  - `Medicine`: name, brand (manufacturer), active ingredient, strength, form (choices), category (choices). Name + strength + form is unique.
  - `InventoryItem`: pharmacy, medicine (PROTECT, so a stocked medicine can't be deleted), quantity (≥ 0), price ₹ (≥ 0), last_updated (automatic). Pharmacy + medicine is unique. `is_available` means quantity > 0; **0 = unavailable**.
- Pharmacy pages: `/pharmacy/inventory/` (list, search, 25 per page, In stock / Out of stock badges, summary counts), `add/`, `<id>/edit/` (quantity and price only), `<id>/delete/` (confirmation page, deletes only on POST).
- Ownership: items are always loaded through the user's own pharmacy, so **another pharmacy's item gives 404**. The pharmacy is set on the server, never taken from the form.
- Home delivery (from the other plan): `home_delivery_available` + `home_delivery_phone`. The phone is required when delivery is ticked, and cleared when it is unticked. Shown on the profile form and the dashboard. Migration `pharmacies/0003`.
- Dashboard: stock summary card with a "Manage inventory" button. The navbar has an **Inventory** link for pharmacy users.
- Admin: Medicines (search, filter by form and category) and Inventory items (filter by availability and pharmacy).
- Forms: the shared Bootstrap styling now draws dropdowns (`form-select`) and checkboxes (`form-check`) correctly.
- Demo data:
  - `medicines/fixtures/medicines.json`: **34 common Indian medicines** (already loaded locally).
  - `manage.py seed_demo --password …`: 4 Indore demo pharmacies with locations and stock. 3 are approved and 1 is pending; 2 offer delivery; some items are at quantity 0. Dolo 650 is out of stock at Shree Krishna on purpose. The password is given on the command line, never stored in code, and checked by Django's password rules. Safe to run again.
  - This is demo data only; brands and strengths are illustrative and not medical advice.
- Manual step done: you ran `seed_demo` with your own password. All 4 Indore demo pharmacies exist, with stock.
- Verified: **60 tests pass** (27 new) and `makemigrations --check` shows no missing migrations. Checked in the browser at phone width (375 px): adding a medicine with quantity 0 shows the red "Out of stock" badge; the list, dropdown and delivery checkbox fit with no horizontal scroll; the Inventory link is in the menu.

### Phase 5 – Customer search, map and pharmacy details
- Decisions: "In stock only" by default; stock older than **7 days** is labelled "may be outdated"; **real medicine names** are kept, while pharmacies, stock and prices are labelled fictional; Directions is a plain Google Maps link (no API key).
- Roadmap aligned with the other chat's plan: their Phase 7 (map, geolocation with Indore fallback, fictional seed data) is covered by our Phases 4–5. Remaining: 6 requests, 7 deployment, 8 README.
- `/search/` (public): case-insensitive search over name, generic name and manufacturer. **Only approved pharmacies.** Filters: availability (in stock only / all), distance (any, 2, 5, 10, 20 km), sort (nearest / lowest price). Validated with `SearchForm`, so tampered values fall back to defaults. 20 per page. Suggestion buttons when the search is empty.
- Distance: `pharmacies/utils.py` `haversine_km()` (Haversine formula, commented). Measured from "Use my location" (browser geolocation → hidden lat/lng) or a preset Indore area (Rajwada (default), Vijay Nagar, Palasia, Bhawarkua). The page says "Distances from: …". Pharmacies without a location show "distance unknown", sort last and are excluded by the distance filter.
- Result cards: medicine, In stock / Out of stock, price, pharmacy name, distance, 🚚 delivery mark, stale-data label, **📞 Call** (`tel:`) and View pharmacy.
- Results map (`static/js/search_map.js`): a pin per pharmacy plus a blue "you" dot. The data is passed with `json_script`, and popups are built with `textContent` (no HTML injection). Map above the list on phones, beside it on desktop.
- `/pharmacies/<id>/` (public, **approved only**, otherwise 404): address, distance, phone, opening hours, map, medicine list (in stock first) with stale labels. Buttons: **📞 Call pharmacy**, **🚚 Call for Home Delivery** (only when delivery is enabled), **🧭 Directions**.
- "Please call the pharmacy to confirm before you travel" notice on search and detail pages. Footer on every page: "Demo project: pharmacies, stock and prices shown are fictional."
- Home page and customer dashboard have a search box. The navbar has a **Search medicines** link.
- `seed_demo` now also marks 3 items per demo pharmacy as last updated 10–20 days ago (stale-label demo). It is still safe to run twice.
- Manual step done: you re-ran `seed_demo`. Each demo pharmacy now has 3 stale items.
- Verified: **85 tests pass** (25 new: search, filters, sorting, tampering, Haversine, stale labels, notices, detail 404s, delivery button). No missing migrations. Checked in the browser at 375 px: search "dolo" shows 4 results nearest first with a map (4 pins, tiles OK, no console errors); the detail page buttons have correct `tel:` and Directions links; all dropdowns fit with no horizontal scroll.

### Phase 6 – Availability requests
- Decisions: customers can request **any medicine a pharmacy lists, even if out of stock**; the pharmacy can add an optional **reply**; the customer can add an optional **contact phone** (shown only to that pharmacy); `seed_demo` creates a **demo customer**.
- New app `availability` (not "requests", to avoid confusion with the Python `requests` library). Model `AvailabilityRequest`: customer, pharmacy, medicine, quantity (1–100), note, contact_phone, status, pharmacy_reply, created_at / updated_at / responded_at.
- Statuses: **pending → confirmed / unavailable** (pharmacy) or **cancelled** (customer). Only pending requests can change; the other three are final. A conditional database rule allows only **one pending request** per customer + pharmacy + medicine.
- Customer pages:
  - **Ask pharmacy** button on search results and pharmacy pages (hidden for pharmacy/admin accounts, which get 403 anyway). Logged-out visitors are sent to log in and back.
  - `/requests/new/<item>/`: approved pharmacies only, otherwise 404. Customer, pharmacy, medicine and status are set by the server, never taken from the form.
  - `/requests/` **My requests**: own requests only, status badges, pharmacy reply, **Cancel** (POST only, otherwise 405), and **📞 Call pharmacy** once confirmed.
  - Customer dashboard shows the 5 latest requests. Navbar: **My requests**.
- Pharmacy pages:
  - `/pharmacy/requests/`: own pharmacy's requests only, with **Pending** / **All** tabs.
  - `/pharmacy/requests/<id>/respond/`: **Confirmed** or **Unavailable** only (a tampered value is rejected) plus an optional reply.
  - Rejected pharmacies get 403. The dashboard shows "N pending requests". Navbar: **Requests**.
- **Ownership:** requests are always loaded through their owner (`customer=request.user` or `pharmacy=<own pharmacy>`), so anyone else's request gives **404**.
- Admin: requests list with status / pharmacy filters and search.
- `seed_demo`: creates `demo_patient` (same password as the other demo accounts) with 5 requests covering all 4 statuses. Each run recreates only that customer's requests, so it is still safe to run twice.
- Limitation: **no notifications** (SMS/email would need an outside service). Customers check **My requests**.
- Verified: **114 tests pass** (29 new: create rules, roles, approved-only, duplicates, quantity limits, tampering, customer and pharmacy ownership, cancel/respond only when pending, POST-only cancel, contact-phone privacy, dashboards, button visibility; plus `seed_demo` request checks). Full flow checked in the browser at 375 px: visitor → **Ask pharmacy** → login → back to form → send → **Pending** → pharmacy dashboard "1 pending request" → **Respond: Confirmed** with a reply → customer sees **Confirmed**, the reply and **📞 Call pharmacy**.

### Phase 7 – Deployment
- (Your original Phase 7 – map, geolocation with an Indore fallback, idempotent fictional seed data – was already built in Phases 3–6.)
- Decisions: **gunicorn** as the production web server; **Singapore** region for both Render and Neon (closest to India, and the same region keeps database queries fast); **HSTS 1 hour** while testing.
- `settings.py`:
  - `RENDER_EXTERNAL_HOSTNAME` (set by Render) is added to `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` automatically.
  - When `DEBUG` is off: trust Render's `X-Forwarded-Proto` header, redirect http → https (except `/healthz/`), secure session and CSRF cookies, HSTS 3600 s.
  - Neon: `conn_health_checks=True`, so connections closed while the database slept are replaced.
  - Errors are logged to the console, so they appear in Render's **Logs** tab.
- `/healthz/` health check: runs `SELECT 1`; answers `ok` (200) or `database unavailable` (503). GET/HEAD only, never cached, no login, no data.
- Friendly `404.html` (uses the normal layout) and `500.html` (standalone on purpose, so it still shows when something is broken).
- `build.sh` (Render build: install, `collectstatic`, `migrate`), `.python-version` (3.13), `.gitattributes` (keeps `build.sh` with Linux line endings).
- Git repository created; `.env`, `db.sqlite3`, `venv/`, `staticfiles/` are not included (checked, plus a scan for secrets).
- `check --deploy` with production values: 2 warnings left **on purpose**: W005 (HSTS for subdomains) and W021 (HSTS preload). `*.onrender.com` subdomains belong to other people's sites, so we must not set those.
- Verified: **118 tests pass** (4 new: health check ok / database down / POST rejected, friendly 404). Production simulated locally with `DEBUG=False`: http → 301 to https, HSTS header sent, CSS served with a hashed filename, `/healthz/` answers over http, unknown host → 400, CSRF cookie marked secure.

- **Live setup** (done by you, step by step):
  - Neon project `medifind`, region AWS Asia Pacific 1 (Singapore), direct connection (pooling off).
  - GitHub repository `Shivansh139/medfinder` (public). Render redeploys automatically on every `git push`.
  - Render free web service `medfinder`, region Singapore. Build: `bash build.sh`. Start: `gunicorn medifind.wsgi`. Environment variables: `SECRET_KEY` (a new key, not the local one), `DEBUG=False`, `DATABASE_URL` (Neon).
  - Admin account and demo data created in Neon from the laptop (`createsuperuser`, `seed_demo` with a new password, not the example one). The live database does not contain the local test accounts.
- **Confirmed by you:** the public URL and the admin panel load on your phone.

## Files created

| File | Purpose |
|---|---|
| `manage.py` | Django command tool (generated) |
| `requirements.txt` | Exact package versions |
| `.env` | Local secrets – git-ignored, never commit |
| `.env.example` | Template of required environment variables |
| `.gitignore` | Keeps `.env`, `venv/`, `db.sqlite3`, `staticfiles/` out of git |
| `.claude/launch.json` | Dev-server config for the Claude browser preview |
| `PROGRESS.md` | This file |
| `build.sh` | Render build script: install, collectstatic, migrate |
| `.python-version` | Python version for Render (3.13) |
| `.gitattributes` | Keeps `.sh` files with Linux line endings |
| `templates/404.html`, `templates/500.html` | Friendly error pages (shown when DEBUG is off) |
| **Project** | |
| `medifind/settings.py` | Settings: env vars, database, static files, `AUTH_USER_MODEL`, login redirects |
| `medifind/urls.py` | Top-level URLs: admin, accounts, dashboard, search, pharmacy detail, pharmacy, inventory, core |
| `medifind/wsgi.py`, `asgi.py` | Web-server entry points (generated) |
| **core app** | |
| `core/urls.py`, `core/views.py` | Home page and `/healthz/` health check |
| `core/tests.py` | Home page, health check and 404 page tests |
| `core/templates/core/home.html` | Home page |
| **accounts app** | |
| `accounts/models.py` | Custom `User` with `role` |
| `accounts/forms.py` | Login form, customer and pharmacy sign-up forms |
| `accounts/decorators.py` | `role_required` server-side permission check |
| `accounts/views.py` | Sign-up views and role-based dashboard redirect |
| `accounts/urls.py` | `/accounts/signup/…`, `/accounts/login/`, `/accounts/logout/` |
| `accounts/admin.py` | User in the admin site, with role |
| `accounts/tests.py` | Sign-up, login redirect, logout, superuser role tests |
| `accounts/migrations/0001_initial.py` | Creates the User table |
| `accounts/templates/accounts/*.html` | Login, sign-up choice, sign-up form, customer dashboard |
| **pharmacies app** | |
| `pharmacies/models.py` | `Pharmacy` with approval status, opening hours, validated location |
| `pharmacies/forms.py` | `PharmacyProfileForm` (editable fields only), `LocationForm` (near / lat / lng) |
| `pharmacies/views.py`, `urls.py` | `/pharmacy/dashboard/` and `/pharmacy/profile/` (pharmacy users only) |
| `pharmacies/admin.py` | Pharmacy admin with approve/reject actions and "Location set" column |
| `pharmacies/tests.py` | Permission, own-pharmacy, approve/reject, profile edit, validation, tampering, dashboard tests |
| `pharmacies/migrations/0001_initial.py` | Creates the Pharmacy table |
| `pharmacies/migrations/0002_…py` | Adds opening_hours and location validators |
| `pharmacies/migrations/0003_…py` | Adds home delivery fields |
| `pharmacies/utils.py` | `haversine_km()`, preset Indore locations, `resolve_location()` |
| `pharmacies/test_detail.py` | Haversine and public pharmacy page tests |
| `pharmacies/templates/pharmacies/detail.html` | Public pharmacy page |
| **medicines app** | |
| `medicines/models.py` | `Medicine` catalogue and `InventoryItem` |
| `medicines/forms.py` | Add form (only medicines not yet stocked), edit form (quantity, price), `SearchForm` |
| `medicines/views.py` | Inventory list, add, edit, delete, with `get_own_pharmacy` / `get_own_item` ownership checks |
| `medicines/urls.py` | `/pharmacy/inventory/…` |
| `medicines/admin.py` | Medicine and inventory admin, availability filter |
| `medicines/tests.py` | Model rules, ownership (404/403), validation, zero stock, delete, demo data tests |
| `medicines/migrations/0001_initial.py`, `0002_…py` | Create Medicine and InventoryItem tables |
| `medicines/fixtures/medicines.json` | 34 demo medicines |
| `medicines/management/commands/seed_demo.py` | `seed_demo` demo-data command (pharmacies, stock, stale items, demo customer and requests) |
| `medicines/templates/medicines/*.html` | Inventory list, add/edit form, delete confirmation, search page |
| `medicines/test_search.py` | Public search tests |
| `pharmacies/templates/pharmacies/dashboard.html` | Status, details, read-only map |
| `pharmacies/templates/pharmacies/profile_form.html` | Profile form with map picker |
| **availability app** | |
| `availability/models.py` | `AvailabilityRequest` with statuses and the one-pending-request rule |
| `availability/forms.py` | `RequestForm` (customer), `RespondForm` (pharmacy, confirmed/unavailable only) |
| `availability/views.py` | Create, my requests, cancel (customer); list, respond (pharmacy) |
| `availability/urls.py` | `/requests/…` and `/pharmacy/requests/…` |
| `availability/admin.py` | Requests admin |
| `availability/tests.py` | Ownership, roles, rules and dashboard tests |
| `availability/migrations/0001_initial.py` | Creates the requests table |
| `availability/templates/availability/*.html` | Request form, my requests, pharmacy requests, respond form |
| **Shared templates and static** | |
| `templates/base.html` | Layout: Bootstrap, navbar (login-aware), messages, footer |
| `templates/includes/form_fields.html` | Renders any form with Bootstrap styling |
| `templates/includes/leaflet_css.html`, `leaflet_js.html` | Load Leaflet (CDN with integrity hash) and our picker script |
| `templates/403.html` | "Access denied" page |
| `templates/includes/search_box.html` | Search box (home page, customer dashboard) |
| `templates/includes/stock_notice.html` | "Call to confirm" notice |
| `static/css/style.css` | Custom styles (including map heights) |
| `static/js/location_picker.js` | Leaflet map: editable picker and read-only view |
| `static/js/search_map.js` | Search page: "Use my location" and results map |

Packages: Django 5.2, dj-database-url, python-dotenv, whitenoise, psycopg[binary].

## Commands

First-time setup (on a new machine):
```bash
python -m venv venv
venv\Scripts\python -m pip install -r requirements.txt
copy .env.example .env
venv\Scripts\python manage.py migrate
```
(Then put a real `SECRET_KEY` in `.env`; the command to generate one is inside `.env.example`.)

Create an admin account (you choose the password):
```bash
venv\Scripts\python manage.py createsuperuser
```

Load the medicine catalogue only:
```bash
venv\Scripts\python manage.py loaddata medicines
```

Create all demo data (medicines, 4 Indore pharmacies with stock, and the demo customer `demo_patient` with sample requests). Choose your own password; all demo logins use it:
```bash
venv\Scripts\python manage.py seed_demo --password "YourOwnDemoPassword"
```

Run the server (then open http://localhost:8000):
```bash
venv\Scripts\python manage.py runserver
```

Run the tests:
```bash
venv\Scripts\python manage.py test
```

Check settings:
```bash
venv\Scripts\python manage.py check
```

After changing a model, create and apply migrations:
```bash
venv\Scripts\python manage.py makemigrations
venv\Scripts\python manage.py migrate
```

Run a command against the live Neon database (PowerShell, one terminal window only; closing the window switches back to SQLite):
```powershell
$env:DATABASE_URL = "your-neon-connection-string"
venv\Scripts\python manage.py shell -c "from django.db import connection; print(connection.vendor)"   # must print postgresql
venv\Scripts\python manage.py createsuperuser
venv\Scripts\python manage.py seed_demo --password "your-live-demo-password"
```

Deploy a change: commit, then `git push`. Render rebuilds automatically (about 3–5 minutes).

Production check (run locally; 2 HSTS warnings, W005 and W021, are expected):
```bash
set DEBUG=False&& venv\Scripts\python manage.py check --deploy
```

## Open issues
- **Viva day (live site on the phone):**
  - The free Render site sleeps after 15 minutes without visitors; the first visit then takes about 50 seconds. Open it 5 minutes before the viva.
  - Neon's free database also sleeps when idle; the first query wakes it in a second or two.
  - Switch accounts with a normal tab plus an Incognito tab, or two browsers.
- Render health check path not set yet (optional): Render → service → **Settings → Health Check Path** → `/healthz/`.
- If a secret is ever exposed (screenshot, chat): generate a new `SECRET_KEY` in Render, and reset the Neon password (then update `DATABASE_URL` in Render).
- Time zone set to `Asia/Kolkata`; confirm this is correct.
- No password reset (needs an email service, which is outside the stack).
- Tests print a harmless WhiteNoise warning ("No directory at staticfiles") because `collectstatic` has not been run locally.
- The local database contains two test accounts from browser testing (they also have one confirmed test request between them): `demo_pharmacy` (approved pharmacy "Demo Care Pharmacy", now with a location, opening hours and one inventory item, Dolo 650 at quantity 0) and `demo_customer`. They can be kept for later demos or deleted in the admin.
- **Local database only:** **Demo Care Pharmacy** (`demo_pharmacy`, a test pharmacy) has its pin in Maharashtra (~485 km from Indore) from an early map test. In search results it zooms the map out to half of India. Before the viva, move its pin to Indore on its profile page, or reject it in the admin.
- The distance filter runs in Python after the database query. Fine for a city-sized demo; a large system would use a spatial database (e.g. PostGIS).
- `medicines/migrations/0002` only removes a duplicate "Price in ₹" help text. It is harmless and kept rather than rewriting migration history.
- "Use my current location" depends on the browser allowing location access. It works only on `localhost` or HTTPS, so it will work on Render, which uses HTTPS. **The Claude in-app browser pane blocks location access** (error "User denied Geolocation"), so test this button in real Chrome/Edge or on a phone. The picker now shows a specific message for each failure (permission blocked, position unavailable, timeout) and gives up after 15 s.
- Fixed: the browser was reusing old copies of our JS/CSS during development. Added `whitenoise.runserver_nostatic` so the dev server sends `Cache-Control: max-age=0`. In production WhiteNoise adds a content hash to filenames, so this problem does not occur there.
- No address search on the map (that would need a geocoding service). Pharmacies click the map instead.
- Map tiles load from OpenStreetMap's public tile server, which is fine for a student project's light traffic.
- Fixed: Firefox showed "403 Access blocked – App is not following the tile usage policy" on the map. Cause: Django's default `Referrer-Policy: same-origin` removed the `Referer` header from tile requests, and OSM's policy requires one. The Leaflet tile layer now uses `referrerPolicy: "strict-origin-when-cross-origin"`, which sends only the site origin and only for map tiles. If a browser still shows the old blocked tiles, they are cached: press Ctrl+F5.
