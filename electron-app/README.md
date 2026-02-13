# Upwork DNA - Electron Application

Automated market intelligence application for Upwork data scraping and analysis.

## Features

- ✅ **Automated Scraping**: Queue-based keyword processing with priority management
- ✅ **Real-time Dashboard**: Streamlit dashboard with live market insights
- ✅ **Data Flywheel**: Automatic keyword discovery and queue injection
- ✅ **Statistical Analysis**: Market gap analysis with significance testing
- ✅ **Profile Optimization**: AI-powered title and overview generation
- ✅ **Background Processing**: Continuous operation without user intervention

## Installation

### Prerequisites

- Node.js 18+
- Python 3.9+
- Chrome/Chromium (for extension)

### Setup

```bash
# Install Node dependencies
cd electron-app
npm install

# Install Python dependencies
cd ../analist
pip install -r requirements.txt

# (Optional) Build for production
npm run build
```

## Running

```bash
# Development mode
npm run dev

# Production mode
npm start
```

## File Structure

```
electron-app/
├── main.js           # Electron main process
├── index.html        # App UI
├── styles.css        # Styling
├── renderer.js       # Renderer process
├── package.json      # Dependencies
└── assets/           # Icons and resources

original_repo_v2/     # Chrome extension (embedded)
analist/              # Python analysis pipeline
upwork_dna/           # Auto-exported data
```

## Usage

1. **Launch the app** - Click the Upwork DNA icon
2. **Add keywords** - Use Queue Manager to add keywords
3. **Start scraping** - Click "Start Queue" for automatic processing
4. **View insights** - Check Dashboard for real-time analysis
5. **Export data** - Data auto-exports to `upwork_dna/` folder

## Data Flow

```
┌─────────────────┐
│   Electron App  │
│   (main.js)     │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌──────┐  ┌──────┐
│ Ext  │  │ Py   │
│Queue │  │Pipe  │
└──────┘  └──────┘
    │         │
    ▼         ▼
┌─────────────────┐
│  upwork_dna/    │
│  (Data Storage) │
└─────────────────┘
```

## Troubleshooting

### Dashboard not loading
- Ensure Streamlit is running on port 8501
- Check Python dependencies are installed

### Downloads not working
- Check Chrome download permissions
- Ensure `upwork_dna/` folder exists
- Look for errors in browser console

### Queue not processing
- Check if extension is loaded in Chrome
- Verify keywords have been added
- Check console for errors

## Hotkeys

- `Ctrl+R` - Refresh dashboard
- `Ctrl+Q` - Quick add keywords
- `Ctrl+D` - Open full dashboard

## Version

v2.1.0 - Production Release
