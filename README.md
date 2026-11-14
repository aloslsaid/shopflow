# ShopFlow AI — AI-Powered Store Management

> A full-stack store operations platform for inventory, products, orders, deliveries, sales analytics, and conversational AI-assisted workflows.

## Product overview
ShopFlow aims to give a store owner a unified workspace for managing daily operations. Product information, stock variants, customer orders, delivery details, sales, expenses, and profit summaries are represented in a structured backend. A conversational AI agent helps owners query and operate on that data through a controlled set of business tools.

## Core business features
- Store registration and owner authentication.
- Product catalog with selling price and cost.
- Variant-aware stock tracking for size and color.
- Stock adjustments with checks against negative inventory.
- Customer order creation with contact and delivery information.
- Sales and expense reporting across daily, weekly, monthly, and all-time periods.
- Revenue, cost, gross profit, expenses, and net profit calculations.
- Delivery message generation.
- WhatsApp click-to-chat links for delivery coordination.
- Dashboard and chat-oriented frontend experience.

## AI agent design
The assistant is designed to answer from actual store records rather than inventing product names, prices, quantities, or totals. It uses a constrained tool-calling loop with a limited number of steps. Sensitive operations—such as price changes, stock changes, deletion, cancellation, or recording a sale—are prepared for owner confirmation instead of being silently executed by the model.

## Architecture
- **Frontend:** React, TypeScript, Vite, Tailwind CSS.
- **Backend:** FastAPI and Pydantic.
- **Data layer:** SQLAlchemy with SQLite in the local setup.
- **AI layer:** OpenRouter-compatible LLM client, tool specifications, and agent orchestration.
- **Security:** password hashing, signed tokens, and role-aware authorization.
- **Messaging:** WhatsApp link generation.
- **Testing:** backend tests for API endpoints, core logic, and AI behavior.

## Requirements
- Node.js and npm.
- Python 3.10+.
- Backend packages listed in `requirements.txt`.
- An AI provider API key and application signing secret in a local `.env`.

## Frontend setup
```bash
git clone https://github.com/aloslsaid/shopflow.git
cd shopflow
npm install
npm run dev
```
Open the local URL printed by Vite.

## Backend setup
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Start the API
The FastAPI application is exposed as `app` in `main.py`. The intended development command depends on the package layout:
```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```
If running as a Python package, use the corresponding package module path. The current repository's root-level module layout and nested relative imports should be checked together before startup; this README does not claim an unverified deployment works.

## Tests and build
```bash
pytest
npm run build
```

## Security and data integrity
Store records, customer contact details, and transaction history are sensitive. Use strong secrets, restrict API access, back up the database, and configure production CORS/authentication before deployment. Financial reports are only as reliable as the transactions and cost snapshots entered into the system; verify totals before using them for formal accounting.

## Skills demonstrated
Full-stack application development · Business automation · Inventory management · REST APIs · SQLAlchemy · Authentication · AI tool calling · Financial calculations · WhatsApp workflows · Testing
