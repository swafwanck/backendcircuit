# Travel API — Django REST Framework

Full backend for the travel website: packages, deals, visas, hotels, activities,
gallery, testimonials, bookings, enquiries, and **Adyen** payments.

## Stack
- Django 5 + DRF + django-filter + SimpleJWT + drf-spectacular (Swagger/Redoc)
- PostgreSQL (SQLite fallback for local)
- Adyen Python SDK — Sessions API, Pay By Link, HMAC-verified webhooks
- Argon2 password hashing, CORS allow-list, CSRF trusted origins, HSTS in prod
- No Docker required

## Setup

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env       # fill in DATABASE_URL, Adyen keys, email, etc.

python manage.py migrate
python manage.py seed_demo        # creates superuser + demo content
python manage.py runserver 0.0.0.0:8000
```

Default admin (from `.env.example`): **admin / Admin@12345**

## API Docs

- Swagger UI: http://localhost:8000/api/docs/
- Redoc:      http://localhost:8000/api/redoc/
- OpenAPI:    http://localhost:8000/api/schema/

## Auth (JWT)

| Endpoint | Method | Body |
|---|---|---|
| `/api/auth/login/`   | POST | `{ "username", "password" }` -> `{ access, refresh }` |
| `/api/auth/refresh/` | POST | `{ "refresh" }` -> `{ access }` |
| `/api/auth/me/`      | GET  | requires `Authorization: Bearer <access>` |

## Resources (all `ModelViewSet` — full CRUD)

Public GET, admin-only writes (except bookings/enquiries which also allow public POST).

| Route | Model |
|---|---|
| `/api/packages/`      | Package |
| `/api/deals/`         | Deal |
| `/api/hotels/`        | Hotel |
| `/api/activities/`    | Activity |
| `/api/visas/`         | Visa |
| `/api/gallery/`       | GalleryItem (photo / video / poster) |
| `/api/testimonials/`  | Testimonial |
| `/api/bookings/`      | Booking (public POST) |
| `/api/enquiries/`     | Enquiry  (public POST) |
| `/api/payments-log/`  | Payment (admin only) |
| `/api/settings/`      | Site settings (key/value) |

Common query params: `?search=`, `?ordering=`, `?is_featured=true`, plus per-resource filters (see filters.py). Slug or numeric ID both work for detail routes.

### "Show on home page" flags
- Packages: `is_trending`
- Deals / Hotels / Activities / Visas / Gallery: `is_featured`
- Testimonials: `is_active`

Frontend example: `GET /api/packages/?is_trending=true`, `GET /api/gallery/?is_featured=true`.

## Payments (Adyen)

Set these in `.env`:
```
ADYEN_API_KEY=...
ADYEN_MERCHANT_ACCOUNT=...
ADYEN_CLIENT_KEY=...
ADYEN_HMAC_KEY=...          # hex string from Adyen Customer Area
ADYEN_ENV=test              # or "live"
```

| Route | Auth | Purpose |
|---|---|---|
| `POST /api/payments/sessions/`         | public | Create Adyen Checkout Session (Drop-in / Components) |
| `POST /api/payments/links/`            | admin  | Generate a Pay By Link (URL) + email to customer |
| `GET  /api/payments/{provider_ref}/`   | public | Payment status |
| `POST /api/payments/webhooks/adyen/`   | public | HMAC-verified notifications (updates status, marks booking confirmed, emails invoice) |

Adyen test cards: https://docs.adyen.com/development-resources/testing/test-card-numbers

## Security features

- JWT auth with refresh rotation + blacklist
- CORS allow-list from `CORS_ALLOWED_ORIGINS`
- CSRF trusted origins from `DJANGO_CSRF_TRUSTED_ORIGINS`
- Argon2 password hashing + Django validators
- Anon + user throttling (120/min, 600/min)
- Security headers: `X-Frame-Options=DENY`, XSS filter, no content sniffing, referrer policy
- HSTS + secure cookies + SSL redirect enabled when `DJANGO_DEBUG=False`
- ORM-parameterised queries (SQL injection safe by design)
- Adyen webhook HMAC-SHA256 signature verification
- All secrets loaded from env (`.env`) — never committed

## Deploy (no Docker)

```bash
pip install -r requirements.txt
export DJANGO_DEBUG=False
export DJANGO_ALLOWED_HOSTS=api.yourdomain.com
python manage.py collectstatic --noinput
python manage.py migrate
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3
```

Serve behind Nginx/Caddy with HTTPS. `WhiteNoise` handles static files.

## Frontend integration

`src/lib/api.ts` in the React app already targets these endpoints. Set:
```
VITE_API_URL=https://api.yourdomain.com
```
