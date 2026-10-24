# README.md

## IBM AI Challenge at SpartHill Hacks 2026: AI for Sustainable Impact

[event timeline](https://sparthillhack2026.vercel.app/timeline)

[dev post prompts](https://sparthill-ibm-2026.devpost.com/)

## Running the backend locally

Requires Python 3.12+ (Django 6.1).

1. Create and activate a virtual environment, then install dependencies:

   ```sh
   python3 -m venv .venv
   source .venv/bin/activate        # fish: source .venv/bin/activate.fish
   pip install -r requirements.txt
   ```

2. Create the env file. Settings refuse to start without `SECRET_KEY` and `GOOGLE_OAUTH_CLIENT_ID`:

   ```sh
   cp .env.example backend/.env
   python -c "import secrets; print(secrets.token_urlsafe(50))"   # paste into SECRET_KEY
   ```

   Any non-empty `GOOGLE_OAUTH_CLIENT_ID` works until Google login is wired up.

3. Apply migrations and start the dev server:

   ```sh
   cd backend
   python manage.py migrate
   python manage.py runserver
   ```

   App runs at http://127.0.0.1:8000/ (admin at `/admin/`, API routes under `/api/`).

4. Optional: create an admin user with `python manage.py createsuperuser`.

## Seeding menu items

`seed_menu` loads one meal period of The Commons menu into the database. It scrapes the Dine On Campus API via `lib/menu_scraper.py`, creating any new `Food` rows and a `MenuEntry` per item. Re-running is safe; existing entries are skipped.

```sh
cd backend
python manage.py seed_menu --period lunch                      # today
python manage.py seed_menu --period dinner --date 2026-10-24   # specific date
python manage.py seed_menu --period breakfast --dry-run        # print items, save nothing
python manage.py seed_menu --period lunch --names-file foods.txt   # skip scraping, one name per line
```

`--period` is required: `breakfast`, `lunch`, or `dinner`.

Note: `lib/food_recommender.py` downloads an embedding model via `fastembed` on first use.
