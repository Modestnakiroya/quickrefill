# QuickRefill

QuickRefill connects households that need cooking gas with verified vendors and delivery riders. Customers can compare available cylinders, place and track orders, while vendors and riders manage fulfilment from role-specific dashboards.

## Features

### Customer

- Sign in securely with an email address and password, or create a customer account.
- Browse available gas brands, cylinder sizes and refill or exchange prices.
- Place an order, choose a delivery address and payment method, and follow delivery progress.
- Review previous orders and submit delivery ratings.

### Rider

- Set availability and receive assigned delivery jobs.
- Review pickup and delivery details, record delivery checklist steps and confirm completion.
- View trip earnings and account details.

### Vendor

- Review incoming orders and manage acceptance.
- Update stock levels and availability.
- View sales settlements, customer ratings and operating statistics.

## Technology

- Python, Django and Django REST Framework
- SQLite for local development
- Django templates, JavaScript and responsive CSS
- Leaflet with OpenStreetMap tiles for order tracking

## Setup

On Windows, run the following from the repository directory:

```powershell
.\run.bat
```

The script prepares a Python environment if required, applies database migrations, seeds product and account data, and starts the application at `http://127.0.0.1:8000/`.

## Developer test accounts

The seeded accounts are maintained by `python manage.py seed_data`.

| Role | Email | Password | Account name |
|---|---|---|---|
| Customer | praise@quickrefill.test | `QuickRefill-Local-Access-2026!` | Praise |
| Rider | musa@quickrefill.test | `QuickRefill-Local-Access-2026!` | Musa Kato |
| Vendor | vendor@quickrefill.test | `QuickRefill-Local-Access-2026!` | Wandegeya Gas Point |

These seeded credentials are for local development. Customer accounts can be created from the sign-in page. Rider and vendor accounts are provisioned by QuickRefill support.

## API summary

All endpoints are rooted at `/api/`. Role-protected endpoints require an authenticated Django session.

| Area | Endpoints | Purpose |
|---|---|---|
| Authentication | `POST /auth/login`, `POST /auth/register`, `GET /me` | Sign in by email and password, register a customer account, and inspect the signed-in account |
| Customer | `GET /stock`, `GET/POST /orders`, `GET /orders/{id}`, `GET /orders/{id}/track`, `POST /orders/{id}/rate` | Browse stock, place orders, track delivery and save a rating |
| Vendor | `/vendor/orders`, `/vendor/stats`, `/vendor/stock`, `/vendor/accepting`, `/vendor/settlement`, `/vendor/ratings` | Manage fulfilment, inventory, availability and business reporting |
| Rider | `/rider/jobs/available`, `/rider/online`, `/rider/jobs/{id}/accept`, `/rider/jobs/{id}/decline`, `/rider/jobs/{id}/step`, `/rider/summary` | Manage rider availability, delivery steps and earnings |

## Roadmap

- Add verified phone numbers and production SMS verification.
- Integrate live MTN MoMo and Airtel Money payment flows.
- Add push notifications for order and delivery updates.
- Migrate production data storage to PostgreSQL.
