# SHOPFLOW AI

## Windows setup (PowerShell)

### 1) Backend

Open PowerShell terminal 1:

```powershell
cd C:\Users\YOUR_USERNAME\Downloads\shopflow
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
cd backend
python -m pip install --upgrade pip
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Keep this terminal open. Backend:
- API: http://127.0.0.1:8000
- Swagger docs: http://127.0.0.1:8000/docs

The project `.env` is loaded automatically. SQLite database is created as `backend/shopflow.db` when the backend is started from the `backend` folder. Do not delete it if you want to keep your store data.

### 2) Frontend

Open a SECOND PowerShell terminal and keep the backend running:

```powershell
cd C:\Users\YOUR_USERNAME\Downloads\shopflow\frontend
npm install
npm run dev
```

Open the Local URL printed by Vite, normally http://localhost:5173.

### 3) First store account

The frontend login screen expects an existing store account. Create one once from Swagger:

1. Open http://127.0.0.1:8000/docs
2. Expand `POST /auth/register-store`
3. Click `Try it out`
4. Enter a unique store name, email, and password (at least 8 characters), for example:

```json
{
  "store_name": "My Store",
  "email": "owner@example.com",
  "password": "ChangeThis123"
}
```

5. Click `Execute`. A successful response returns a `token`.
6. Open the frontend and sign in with the same email and password.

If Swagger returns `409 email in use`, the account already exists. Do not register it again; use `POST /auth/login` or sign in through the frontend.

### Notes

- Frontend API URL defaults to `http://127.0.0.1:8000`.
- CORS allows Vite on ports 5173 and 5174.
- AI chat requires a valid `OPENROUTER_API_KEY` and `OPENROUTER_MODEL` in the root `.env`. Other store functions do not require an AI key.
- Keep `.env` private. The included `.env` is configured for local development; replace secrets before deploying publicly.
