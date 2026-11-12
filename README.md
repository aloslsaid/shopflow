# ShopFlow — Shop Management API

ShopFlow is a Python/FastAPI shop-management backend with tenant-scoped stores, products, stock, orders, delivery handoff, sales reports, expenses and audit logging. The repository also contains early React/TypeScript UI files.

> **Current checkout status:** the core API modules are present. The optional `ai/` integration package referenced by the AI assistant routes is not included in this branch. Core inventory/order features remain importable; AI routes return HTTP 503 until those modules are restored. The frontend source has no package manifest yet, so it is not currently a standalone npm app.

## Core capabilities

- Store registration and JWT-based authentication.
- Owner/manager/staff role checks.
- Store-scoped product, stock and order queries.
- Order approval, rejection, dispatch and delivery workflow.
- WhatsApp delivery-message link generation.
- Sales, gross-profit, expense and net-profit reporting.
- Audit log support and local SQLite persistence.

## Requirements

Python 3.10+.

## Setup

Create a virtual environment in the repository root and install dependencies:

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Copy `.env.example` to `.env`. Set a strong random `JWT_SECRET`. If credential encryption is enabled, set `CREDENTIALS_KEY` to a generated Fernet key. Keep `.env` private and untracked.

Run the API from the directory containing the repository folder:

```bash
uvicorn shopflow.main:app --reload
```

API documentation is available at `http://127.0.0.1:8000/docs`.

The default SQLite database is `shopflow.local.db` inside the repository and is ignored by Git. The previously tracked `shopflow.db` file is not used as the default runtime database.

## Tests

From the parent directory:

```bash
python -m pytest shopflow
```

The core API and pure business-logic tests are included. AI-specific tests are skipped while the optional AI package is absent. A skipped test is not a passing verification of the AI integration.

## Security notes

- Use a unique, high-entropy `JWT_SECRET`; never use the example placeholder.
- Use a separate database for tests and back up production data.
- Keep the local database, secrets and logs out of Git.
- Review authentication, role enforcement, CORS, rate limiting, password policy and audit logging before public deployment.
- Never expose the development server directly to the internet.
- Restore and review the missing AI tool package before enabling assistant-driven writes. Sensitive actions should require explicit confirmation and tenant scoping.

## Known gaps

- AI modules are missing from this repository snapshot; AI chat/confirm/cancel endpoints are intentionally disabled with 503 responses.
- React files are present, but no `package.json`, build configuration or frontend dependency lockfile is included.
- Production database migrations, deployment configuration and full security review remain outstanding.

## License

No license is declared. All rights reserved unless the repository owner adds an explicit license.
