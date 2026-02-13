# Upwork DNA - Frontend Setup Guide

## Quick Setup (5 minutes)

### Step 1: Install Dependencies
```bash
cd /Users/dev/Documents/upworkextension/web-app
npm install
```

### Step 2: Configure Environment
```bash
cp .env.local.example .env.local
```

Edit `.env.local` if needed (defaults work for local development):
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
BACKEND_URL=http://localhost:8000
```

### Step 3: Start Development Server
```bash
npm run dev
```

### Step 4: Open Browser
Navigate to: **http://localhost:3000**

## Pages Overview

| Page | URL | Description |
|------|-----|-------------|
| Dashboard | `/` | Main control panel with queue and status |
| Queue | `/queue` | Manage scraping queue items |
| Results | `/results` | View and export scraped jobs |
| Settings | `/settings` | Configure application settings |

## Development Commands

```bash
# Development server (port 3000)
npm run dev

# Production build
npm run build

# Start production server
npm start

# Type checking
npm run type-check

# Clean build artifacts
npm run clean
```

## Component Library (shadcn/ui)

All UI components from shadcn/ui are installed:
- Button, Card, Input, Table
- Badge, Progress, Textarea, Select
- Tabs (for navigation)

## Backend Integration

The frontend expects a backend API running on `http://localhost:8000`.

**Required Endpoints:**
- `GET/POST /queue` - Queue management
- `POST /scrape` - Start scraping
- `GET /results` - Get scraped data
- `GET /status` - System status

## Troubleshooting

**Port 3000 already in use?**
```bash
# Kill process on port 3000
lsof -ti:3000 | xargs kill -9
```

**Build fails?**
```bash
# Clean and rebuild
rm -rf .next node_modules
npm install
npm run build
```

**Backend not connecting?**
- Ensure backend is running on port 8000
- Check `.env.local` configuration
- Verify CORS settings on backend

## File Locations

- **Pages**: `src/app/`
- **Components**: `src/components/`
- **API Routes**: `src/app/api/`
- **Styles**: `src/app/globals.css`
- **Config**: `next.config.ts`, `tailwind.config.ts`
