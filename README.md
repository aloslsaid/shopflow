# ShopFlow

ShopFlow is an AI-assisted shop-management project. The tracked root includes Python API/business-logic modules, TypeScript/React interface files, a SQLite database file, and several pytest-style test files. The intended features described by the project include product and stock management, orders, reporting, and optional AI assistance.

## Repository layout

The current files are at the repository root (for example `main.py`, `models.py`, `services.py`, `App.tsx`, and `test_api.py`). Earlier setup notes referred to `backend/app` and `frontend` directories, which are not present in the root file listing. The API module also imports `.ai.*` modules; verify that those modules exist before starting the server. Therefore, the old `uvicorn app.main:app` and `cd frontend` commands are not confirmed for this checkout.

## Installation and verification

1. Install Python and Node.js/npm.
2. Create and activate a Python virtual environment.
3. Install Python dependencies with `python -m pip install -r requirements.txt`.
4. Inspect the package structure and resolve the entry point before starting the API; do not assume a server command from the outdated directory instructions.
5. Run the existing tests from the repository root with `python -m pytest` after dependencies and imports are available.
6. The root currently has no `package.json`, so the frontend does not have a verified npm install or start command.

## Configuration and security

The AI integration requires provider configuration; supply secrets through environment variables or an untracked `.env` file and never commit real credentials. The repository contains `shopflow.db`; treat it as local business data and do not publish or overwrite it casually. Use a disposable database for testing. Before deploying, review authentication, token handling, CORS, database backups, and access controls.

## Known onboarding gaps

The current directory layout and API imports do not agree with the previous README setup directions. Confirm and document the actual backend/frontend entry points, environment variables, and test results before describing the application as ready to deploy.
