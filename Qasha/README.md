# Qasha

A Django rental platform for finding rooms and homes, listing your place, and handling applications and messages on Qasha — not over WhatsApp in the listing.

## Features

- **Browse** published listings (timeline-style feed)
- **List your place** on the home timeline; **Manage** tab (saved places, listings, applications, account); **Messages** is its own tab
- **Request booking** → dates → **authorize** card (hold, not charged) → owner **Accept** (capture + confirm) or **Decline** (release authorization)
- **Messages** between tenants and owners (no subject line)
- **Help** (`?` in the nav): FAQ popup + short contact form (one term everywhere — not Support / Contact Us / Help Center)
- **Free vs Premium** accounts (photo/video limits; admin validates Premium after payment)
- **Messages** for tenant–owner chat (no separate feedback form — use Help to report issues)
- **Currency:** all prices in **South African Rand (ZAR)** — shown as `R 12,500`
- **Nav alerts:** unread messages (red) and booking actions on **Manage** (orange) — pending rental requests for hosts, accepted applications awaiting payment for guests
- **One account:** single signup (no tenant/owner split); list or book with the same user
- **Booking alerts:** tenants get an in-app **Message** when a host accepts or declines
- **Legal:** [Privacy](http://127.0.0.1:8000/info/privacy/), [Terms](http://127.0.0.1:8000/info/terms/)

## Tech stack

- Python 3, Django 5.2
- **PostgreSQL** (recommended — via Docker or hosted DB) or SQLite (fallback if `USE_POSTGRES` is not set)
- Bootstrap 5, Font Awesome
- Custom user model: `users.User`

## Setup

```bash
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open http://127.0.0.1:8000/ (redirects to `/rentals/`).

### PostgreSQL (recommended)

**Why:** better concurrency, indexes, and scaling for a national listing site than SQLite.

1. Start Postgres (Docker):

```bash
docker compose up -d
```

2. Configure the app:

```bash
copy .env.example .env          # Windows
# Edit .env if your DB user/password differ
python manage.py migrate
python manage.py createsuperuser
```

Set `USE_POSTGRES=true` in `.env`, or pass `DATABASE_URL=postgresql://user:pass@host:5432/qasha` on hosted platforms (Render, Railway, etc.).

**Moving existing SQLite data:** export with `python manage.py dumpdata --natural-foreign --natural-primary -e contenttypes -e auth.Permission > data.json`, switch to PostgreSQL, `migrate`, then `python manage.py loaddata data.json`. For a fresh launch, just `migrate` on an empty Postgres DB.

**Listing photos and videos** live in the `media/` folder on disk (not inside the Postgres Docker volume). Back up `media/` when you change PCs or deploy. If listings show “file missing” on edit, the database still has filenames but the files are not on disk — on **Edit listing**, use **Remove all missing photos & video**, or run:

```bash
python manage.py prune_missing_media --dry-run
python manage.py prune_missing_media
```

Then re-upload photos/video. **Videos:** MP4/M4V/MOV/WebM/3GP/AVI/MKV/MPEG can be uploaded; **MP4 (H.264)** plays reliably on phones.

Without `.env` / `USE_POSTGRES`, the app still uses `db.sqlite3` for quick local trials.

Optional for Premium video duration checks:

```bash
pip install mutagen
```

## Main URLs

| Path | Purpose |
|------|---------|
| `/rentals/` | Home / browse listings |
| `/rentals/manage/` | Manage (saved places, listings, applications, rental requests, account) |
| `/rentals/list-property/` | List your place |
| `/rentals/messages/` | Inbox |
| `/rentals/?help=1` | Opens Help panel |
| `/info/about/` | About |
| `/info/how-it-works/` | How it works |
| `/admin/` | Django admin (validate Premium, moderation) |

## Project layout

```
Qasha/          # project settings, urls
core/           # about, how-it-works, help contact API
rentals/        # properties, bookings, messages, wishlist
users/          # auth, signup, Premium upgrade request
templates/      # HTML (includes help_modal.html)
```

## Help & contact

Users reach you only through **Help** in the app (navbar `?`). Submissions are stored as `ContactMessage` in the database and visible in Django admin.

Legacy `/info/contact/` redirects to the home feed and opens Help.

## License

Private project — add your license if you open-source it.
