# Production Deployment Checklist - Banner Fix

## Issue
Banners not displaying in live app despite being created in PostgreSQL database.

## Root Cause
Production server needs to:
1. Have `DATABASE_URL` environment variable set to PostgreSQL
2. Be restarted to pick up the new banners table

## Solution Steps

### Step 1: Set DATABASE_URL on Production Server

Add this environment variable to your production server (DigitalOcean App Platform, Heroku, etc.):

```bash
DATABASE_URL=postgresql://doadmin:AVNS_WJtLYtseYwMSXA15Q5w@app-916f4ca7-336c-43ee-a2bf-6bd8b35e1f48-do-user-7489418-0.m.db.ondigitalocean.com:25060/defaultdb?sslmode=require
```

### Step 2: Restart Production Server

After setting the environment variable, restart your production app so it connects to PostgreSQL instead of SQLite.

### Step 3: Verify Banners

Visit your live app and check if banners display with gradient backgrounds.

## Alternative: Quick Test Locally

To test if banners work, temporarily update your local `.env`:

```bash
# Comment out SQLite
# DATABASE_URL=sqlite:///./app/data/costs.db

# Add PostgreSQL
DATABASE_URL=postgresql://doadmin:AVNS_WJtLYtseYwMSXA15Q5w@app-916f4ca7-336c-43ee-a2bf-6bd8b35e1f48-do-user-7489418-0.m.db.ondigitalocean.com:25060/defaultdb?sslmode=require
```

Then restart your local server:
```bash
python main.py
```

Visit http://localhost:8001 and you should see the banners with gradients!

## Expected Result

Banner carousel should display 3 slides with gradient backgrounds:
1. **One Piece: Four Emperors** - Red/orange gradient
2. **Pokémon Scarlet & Violet** - Purple/violet gradient
3. **One Piece: Romance Dawn** - Cyan/teal gradient

No broken image icons should appear.
