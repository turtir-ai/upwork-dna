# Upwork DNA - Next.js Frontend

A modern Next.js frontend for the Upwork DNA automated job scraping system.

## Features

- **Dashboard** (`/`) - Real-time queue monitoring and system status
- **Queue Management** (`/queue`) - Add, remove, and manage scraping jobs
- **Results Display** (`/results`) - View and export scraped job data
- **Settings** (`/settings`) - Configure API endpoints and scraping preferences
- **Dark Theme** - Eye-friendly interface with green accent colors
- **Responsive Design** - Works on desktop and mobile devices
- **Real-time Updates** - Auto-refresh every 5 seconds

## Tech Stack

- **Next.js 16** - React framework with App Router
- **TypeScript** - Type-safe development
- **Tailwind CSS** - Utility-first styling
- **shadcn/ui** - Beautiful pre-built components
- **Lucide Icons** - Modern icon library

## Prerequisites

- Node.js 18+ installed
- npm or yarn package manager
- Backend API running (default: `http://localhost:8000`)

## Installation

1. **Install dependencies**:
   ```bash
   npm install
   ```

2. **Configure environment**:
   ```bash
   cp .env.local.example .env.local
   ```

   Edit `.env.local` if your backend runs on a different port:
   ```env
   NEXT_PUBLIC_API_URL=http://localhost:8000
   BACKEND_URL=http://localhost:8000
   ```

3. **Start development server**:
   ```bash
   npm run dev
   ```

4. **Open browser**:
   Navigate to [http://localhost:3000](http://localhost:3000)

## Project Structure

```
web-app/
├── src/
│   ├── app/
│   │   ├── page.tsx          # Dashboard (main page)
│   │   ├── queue/            # Queue management page
│   │   ├── results/          # Results display page
│   │   ├── settings/         # Settings page
│   │   ├── api/              # API route handlers
│   │   │   ├── queue/        # Queue endpoints
│   │   │   ├── scrape/       # Scrape endpoints
│   │   │   ├── results/      # Results endpoints
│   │   │   └── status/       # Status endpoints
│   │   ├── layout.tsx        # Root layout
│   │   └── globals.css       # Global styles
│   ├── components/
│   │   ├── ui/               # shadcn/ui components
│   │   ├── StatusCard.tsx    # Status display card
│   │   ├── QueueList.tsx     # Queue items list
│   │   ├── ResultsTable.tsx  # Results data table
│   │   ├── KeywordInput.tsx  # Keyword input with suggestions
│   │   ├── ProgressBar.tsx   # Progress indicator
│   │   └── index.ts          # Component exports
│   └── lib/
│       └── utils.ts          # Utility functions
├── public/                   # Static assets
├── package.json
├── tsconfig.json
├── tailwind.config.ts
└── next.config.ts
```

## Available Pages

### Dashboard (`/`)
- Add keywords to queue
- View current queue status
- Monitor system status
- Real-time updates (5-second polling)

### Queue (`/queue`)
- View all queue items
- Start/pause scraping jobs
- Remove items from queue
- Real-time queue updates

### Results (`/results`)
- View all scraped jobs
- Filter by keyword
- Search in titles/descriptions
- Export to CSV
- Mark as contacted/ignored

### Settings (`/settings`)
- Configure API URL
- Set scrape interval
- Configure max pages
- Toggle headless mode
- Set custom user agent
- Configure proxy (optional)

## API Integration

The frontend proxies requests to the backend API:

```
Frontend API Route → Backend API
/api/queue         → http://localhost:8000/queue
/api/scrape        → http://localhost:8000/scrape
/api/results       → http://localhost:8000/results
/api/status        → http://localhost:8000/status
```

## Components

### StatusCard
Display system status with icon and color coding.

### QueueList
Display queue items with actions.

### ResultsTable
Display scraped jobs with filtering and export.

### KeywordInput
Input field with suggestions and job type selection.

### ProgressBar
Progress indicator for scraping operations.

## Building for Production

1. **Create production build**:
   ```bash
   npm run build
   ```

2. **Start production server**:
   ```bash
   npm start
   ```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `NEXT_PUBLIC_API_URL` | Public API URL for client-side requests | `http://localhost:8000` |
| `BACKEND_URL` | Internal API URL for server-side requests | `http://localhost:8000` |

## Styling

The app uses a dark theme with green accent colors matching Upwork's brand:

- **Background**: Gray gradients (`from-gray-950 via-gray-900`)
- **Primary**: Green (`from-green-600 to-emerald-600`)
- **Cards**: Semi-transparent with backdrop blur
- **Text**: White and gray variants

## Troubleshooting

### Backend connection issues
- Ensure backend is running on port 8000
- Check `NEXT_PUBLIC_API_URL` in `.env.local`
- Verify CORS settings on backend

### Build errors
- Delete `.next` folder and rebuild
- Clear node_modules and reinstall
- Check Node.js version (requires 18+)

### Component not found
- Ensure all shadcn/ui components are installed
- Run `npx shadcn@latest add <component-name>`

## License

MIT
