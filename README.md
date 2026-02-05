# TCG Nakama Marketplace

A premium TCG marketplace prototype built with FastAPI, Tailwind CSS, and HTMX.

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
- **FastAPI**: Backend framework
- **Tailwind CSS**: Utility-first styling (via CDN)
- **HTMX**: High-performance interactivity without complex JS
- **Jinja2**: Templating engine engine
