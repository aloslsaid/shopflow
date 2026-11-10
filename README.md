# SHOPFLOW AI
# SHOPFLOW AI – Your Business, Managed by AI

**SHOPFLOW AI** is an intelligent business management platform that puts your entire store under your control through a single AI-powered chat assistant.

Manage your business, track profits, monitor inventory, handle orders, and organize deliveries through natural conversations with AI.

### Key Features

- **AI Business Assistant:** Control your entire store using chat commands. Ask questions, request reports, and perform actions through natural language.
- **Profit & Sales Tracking:** Monitor daily, weekly, and monthly revenue, expenses, costs, and net profits.
- **Smart Inventory Management:** Track stock levels, manage products, receive low-stock alerts, and update inventory instantly.
- **Order Management:** Create, update, search, and track customer orders.
- **WhatsApp Integration:** Communicate with customers, send order confirmations, share updates, and coordinate deliveries through WhatsApp.
- **Delivery Management:** Track delivery status, manage delivery assignments, and monitor completed and pending shipments.
- **Business Analytics:** Get AI-powered insights, sales summaries, performance reports, and recommendations to improve your business.
- **Conversational Control:** Ask AI to perform business operations instead of navigating complicated dashboards.

### The Vision

SHOPFLOW AI transforms traditional store management into a conversational experience. Instead of manually navigating multiple tools, you simply tell your AI assistant what you need, and it helps manage your business from one place.

**One Store. One AI Assistant. Complete Business Control.** 
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
# SHOPFLOW AI – Your Business, Managed by AI

**SHOPFLOW AI** is an intelligent business management platform that puts your entire store under your control through a single AI-powered chat assistant.

Manage your business, track profits, monitor inventory, handle orders, and organize deliveries through natural conversations with AI.

### Key Features

- **AI Business Assistant:** Control your entire store using chat commands. Ask questions, request reports, and perform actions through natural language.
- **Profit & Sales Tracking:** Monitor daily, weekly, and monthly revenue, expenses, costs, and net profits.
- **Smart Inventory Management:** Track stock levels, manage products, receive low-stock alerts, and update inventory instantly.
- **Order Management:** Create, update, search, and track customer orders.
- **WhatsApp Integration:** Communicate with customers, send order confirmations, share updates, and coordinate deliveries through WhatsApp.
- **Delivery Management:** Track delivery status, manage delivery assignments, and monitor completed and pending shipments.
- **Business Analytics:** Get AI-powered insights, sales summaries, performance reports, and recommendations to improve your business.
- **Conversational Control:** Ask AI to perform business operations instead of navigating complicated dashboards.

### The Vision

SHOPFLOW AI transforms traditional store management into a conversational experience. Instead of manually navigating multiple tools, you simply tell your AI assistant what you need, and it helps manage your business from one place.

**One Store. One AI Assistant. Complete Business Control.**
