# TCG Nakama Marketplace

A premium TCG marketplace built with FastAPI, Tailwind CSS, and HTMX.

## Features

- **Public Marketplace** — Browse, search, and filter TCG cards (Pokémon, One Piece) with real-time Shopify inventory
- **Admin Vault Dashboard** — Manage inventory, track buy prices, profit/loss, and days-in-vault metrics
- **Analytics** — PSA 10 grading candidates, trending searches, customer insights, and inventory value charts
- **Mobile-First Design** — Bottom sheet filters, swipeable carousels, responsive grid, and touch-optimized buttons
- **Cart System** — Add to cart with visual feedback, quantity controls, and Shopify checkout integration
- **Banner Management** — Upload and manage homepage carousel banners from the admin panel

## Getting Started

### 1. Requirements
- Python 3.11+
- A Shopify Storefront API Token (Optional, fallback mock data included)

### 2. Setup
1. **Clone the repository**:
   ```bash
   git clone https://github.com/AdminAsistee/TCGNakama.git
   cd TCGNakama
   ```

2. **Create a Virtual Environment**:
   ```bash
   python -m venv venv
   .\venv\Scripts\activate  # Windows
   source venv/bin/activate # Mac/Linux
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables**:
   Copy `.env.example` to a new file named `.env` and fill in your Shopify credentials if you have them. If left blank, the app will use **Mock Data** for the design.
   ```bash
   cp .env.example .env
   ```

### 3. Running Locally
Run the server using Uvicorn from the root directory:
```bash
uvicorn main:app --reload --port 8001
```
Open [http://localhost:8001](http://localhost:8001) in your browser.

> [!IMPORTANT]
> **Don't open HTML files directly!** This app uses the Jinja2 template engine. Opening the `.html` files in a browser without the server running will not show the design correctly.

## Tech Stack
- **FastAPI** + **Uvicorn**: Backend framework and ASGI server
- **Jinja2**: Server-side templating
- **HTMX**: Dynamic interactivity without heavy JS frameworks
- **Tailwind CSS**: Utility-first styling (via CDN)
- **SQLAlchemy** + **PostgreSQL**: Database ORM and storage
- **Shopify Storefront API**: Live inventory and checkout
- **Chart.js**: Inventory value charts in admin dashboard
